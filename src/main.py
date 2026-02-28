"""
Zero Ichi - WhatsApp Bot entry point.
"""

import asyncio
import base64
import importlib
import io
import os
import signal
import sys
import traceback
from pathlib import Path

_src_dir = Path(__file__).parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

_project_root = _src_dir.parent

import segno  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from google.protobuf.json_format import MessageToDict  # noqa: E402
from neonize.aioze.client import ClientFactory, NewAClient  # noqa: E402
from neonize.events import (  # noqa: E402
    CallAcceptEv,
    CallOfferEv,
    CallOfferNoticeEv,
    CallTerminateEv,
    ConnectedEv,
    GroupInfoEv,
    MessageEv,
)
from neonize.proto.waCompanionReg.WAWebProtobufsCompanionReg_pb2 import DeviceProps  # noqa: E402
from neonize.utils.enum import BlocklistAction  # noqa: E402
from watchfiles import awatch  # noqa: E402

load_dotenv(_project_root / ".env")

_ai_api_key = os.getenv("AI_API_KEY")
if _ai_api_key and not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = str(_ai_api_key)

from config.settings import (  # noqa: E402
    AUTO_RELOAD,
    BOT_NAME,
    LOGIN_METHOD,
    PHONE_NUMBER,
)
from core.cache import message_cache  # noqa: E402
from core.client import BotClient  # noqa: E402
from core.command import command_loader  # noqa: E402
from core.env import validate_environment  # noqa: E402
from core.handlers.welcome import handle_member_join, handle_member_leave  # noqa: E402
from core.i18n import init_i18n, reload_locales, t  # noqa: E402
from core.jid_resolver import get_user_part, jids_match, resolve_pair  # noqa: E402
from core.logger import (  # noqa: E402
    console,
    log_bullet,
    log_error,
    log_info,
    log_raw_message,
    log_step,
    log_success,
    log_warning,
    show_banner,
    show_connected,
    show_pair_help,
    show_qr_prompt,
)
from core.message import MessageHelper  # noqa: E402
from core.middleware import MessageContext  # noqa: E402
from core.middlewares import build_pipeline  # noqa: E402
from core.runtime_config import runtime_config  # noqa: E402
from core.scheduler import init_scheduler  # noqa: E402
from core.session import session_state  # noqa: E402
from core.shared import set_bot  # noqa: E402

validate_environment()
client = NewAClient(
    f"{BOT_NAME}.session",
    props=DeviceProps(
        os="Zero Ichi",
        platformType=DeviceProps.SAFARI,
    ),
)
bot = BotClient(client)
bot.message_cache = message_cache

init_i18n()

set_bot(bot)


scheduler = init_scheduler(bot)
pipeline = build_pipeline()

_handled_call_ids: dict[str, float] = {}
_CALL_GUARD_DEDUP_TTL_SECONDS = 120.0


def _jid_to_str(jid_obj) -> str:
    """Convert a protobuf JID object into a jid@server string."""
    if not jid_obj:
        return ""
    user = getattr(jid_obj, "User", "")
    server = getattr(jid_obj, "Server", "")
    if not user or not server:
        return ""
    return f"{user}@{server}"


def _extract_call_meta(event) -> tuple[str, str]:
    """Extract call_id and caller_jid from call events."""
    basic = getattr(event, "basicCallMeta", None)
    if not basic:
        return "", ""

    call_id = getattr(basic, "callID", "") or ""

    creator = _jid_to_str(getattr(basic, "callCreator", None))
    creator_alt = _jid_to_str(getattr(basic, "callCreatorAlt", None))
    candidates = [jid for jid in [creator, creator_alt] if jid]

    caller_jid = ""
    for jid in candidates:
        if jid.endswith("@s.whatsapp.net"):
            caller_jid = jid
            break
    if not caller_jid and candidates:
        caller_jid = candidates[0]

    return call_id, caller_jid


def _is_duplicate_call_offer(call_id: str) -> bool:
    """Best-effort dedup for repeated call offer events."""
    if not call_id:
        return False

    now = asyncio.get_running_loop().time()
    for seen_id, ts in list(_handled_call_ids.items()):
        if now - ts > _CALL_GUARD_DEDUP_TTL_SECONDS:
            _handled_call_ids.pop(seen_id, None)

    seen = _handled_call_ids.get(call_id)
    if seen and now - seen <= _CALL_GUARD_DEDUP_TTL_SECONDS:
        return True

    _handled_call_ids[call_id] = now
    return False


async def _is_whitelisted_caller(caller_jid: str) -> bool:
    """Return True if caller is in call guard whitelist."""
    whitelist = runtime_config.get_nested("call_guard", "whitelist", default=[])
    if not isinstance(whitelist, list):
        return False

    caller_user = caller_jid.split("@")[0].split(":")[0]

    for candidate in whitelist:
        if not isinstance(candidate, str) or not candidate.strip():
            continue

        entry = candidate.strip()
        try:
            if await jids_match(caller_jid, entry, bot):
                return True
        except Exception:
            pass

        entry_user = entry.split("@")[0].split(":")[0]
        if entry_user and entry_user == caller_user:
            return True

    return False


async def _resolve_call_jids(caller_jid: str) -> tuple[str, str]:
    """Resolve caller into PN/LID JIDs when possible."""
    try:
        pair = await bot.resolve_jid_pair(caller_jid)
        pn = str(pair.get("pn") or "").strip()
        lid = str(pair.get("lid") or "").strip()
        return pn, lid
    except Exception:
        return "", ""


def _caller_display(caller_jid: str, pn_jid: str, lid_jid: str) -> str:
    """Format caller for logs and owner notices, preferring PN JID."""
    if pn_jid:
        number = get_user_part(pn_jid)
        if lid_jid:
            return f"{pn_jid} (number: {number}, lid: {lid_jid})"
        return f"{pn_jid} (number: {number})"
    if lid_jid:
        return lid_jid
    return caller_jid


async def _handle_call_offer(event, source: str = "offer") -> None:
    """Handle incoming call-like events with configurable block action."""
    call_id, caller_jid = _extract_call_meta(event)
    if not caller_jid:
        log_warning(f"Call guard: incoming call has no caller JID (source={source})")
        return

    pn_jid, lid_jid = await _resolve_call_jids(caller_jid)
    caller_display = _caller_display(caller_jid, pn_jid, lid_jid)

    log_info(f"Incoming call ({source}): caller={caller_display} id={call_id or '-'}")

    cfg = runtime_config.get("call_guard", default={})
    if not isinstance(cfg, dict):
        return

    enabled = bool(cfg.get("enabled", False))
    action = str(cfg.get("action", "block")).lower()
    if not enabled or action == "off":
        return

    if _is_duplicate_call_offer(call_id):
        return

    if await runtime_config.is_owner_async(caller_jid, bot):
        log_info(f"Call guard: owner call ignored ({caller_display})")
        return

    if await _is_whitelisted_caller(caller_jid):
        log_info(f"Call guard: whitelisted caller ignored ({caller_display})")
        return

    delay = cfg.get("delay_seconds", 3)
    try:
        delay = int(delay)
    except (TypeError, ValueError):
        delay = 3
    delay = max(0, min(delay, 60))

    notify_target = pn_jid or caller_jid
    if bool(cfg.get("notify_caller", True)):
        try:
            await bot.send(notify_target, t("callguard.caller_notice"))
        except Exception as e:
            if notify_target != caller_jid:
                try:
                    await bot.send(caller_jid, t("callguard.caller_notice"))
                except Exception as fallback_error:
                    log_warning(
                        f"Call guard: failed to notify caller {caller_display}: {fallback_error}"
                    )
            else:
                log_warning(f"Call guard: failed to notify caller {caller_display}: {e}")

    if delay > 0:
        await asyncio.sleep(delay)

    block_targets: list[str] = []
    for target in [pn_jid, lid_jid, caller_jid]:
        if target and target not in block_targets:
            block_targets.append(target)

    blocked_any = False
    for target in block_targets:
        try:
            await bot._client.update_blocklist(bot.to_jid(target), BlocklistAction.BLOCK)
            blocked_any = True
        except Exception as e:
            log_warning(f"Call guard: failed to block {target}: {e}")

    if blocked_any:
        log_warning(f"Call guard: blocked caller {caller_display} (call_id={call_id or '-'})")
    else:
        log_warning(
            f"Call guard: unable to block caller {caller_display} (call_id={call_id or '-'})"
        )

    if bool(cfg.get("notify_owner", True)):
        owner_jid = runtime_config.get_owner_jid()
        if owner_jid:
            try:
                await bot.send(
                    owner_jid,
                    t(
                        "callguard.owner_notice",
                        caller=caller_display,
                        delay=delay,
                        call_id=call_id or "-",
                    ),
                )
            except Exception as e:
                log_warning(f"Call guard: failed to notify owner: {e}")


@client.qr
async def qr_handler(c: NewAClient, qr_data: bytes) -> None:
    """Handle QR code event - displays QR in terminal."""
    session_state.is_logged_in = False

    show_qr_prompt()
    qr = segno.make_qr(qr_data)
    qr.terminal(compact=True)

    buff = io.BytesIO()
    qr.save(buff, kind="png", scale=10)
    qr_b64 = base64.b64encode(buff.getvalue()).decode("utf-8")

    session_state.qr_code = qr_b64
    session_state.is_pairing = False


@client.event(ConnectedEv)
async def connected_handler(c: NewAClient, event: ConnectedEv) -> None:
    """Called when successfully connected to WhatsApp."""
    session_state.is_logged_in = True
    session_state.qr_code = None
    session_state.pair_code = None

    show_connected(
        device=event.device.User,
        bot_name=BOT_NAME,
        commands_count=len(command_loader.enabled_commands),
    )

    log_info(
        f"Connected event fired, scheduler: {scheduler}, running: {scheduler._scheduler.running if scheduler else 'N/A'}"
    )
    if scheduler and not scheduler._scheduler.running:
        scheduler.start()
        log_success("Scheduler start() called")

    owner_jid = runtime_config.get_owner_jid()
    if owner_jid:
        await resolve_pair(owner_jid, bot)
        log_info(f"Preloaded JID cache for owner: {owner_jid}")


@client.event(GroupInfoEv)
async def group_info_handler(c: NewAClient, event: GroupInfoEv) -> None:
    """Handle group info events (join/leave)."""
    try:
        group_jid = f"{event.JID.User}@{event.JID.Server}" if event.JID else ""
        if not group_jid or not group_jid.endswith("@g.us"):
            return

        joined = list(event.Join)
        left = list(event.Leave)

        if not joined and not left:
            return

        for participant in joined:
            member_jid = f"{participant.User}@{participant.Server}" if participant else ""
            if not member_jid:
                continue
            member_name = participant.User
            log_info(f"Member joined: {member_name} ({member_jid}) in {group_jid}")
            await handle_member_join(bot, group_jid, member_jid, member_name)

        for participant in left:
            member_jid = f"{participant.User}@{participant.Server}" if participant else ""
            if not member_jid:
                continue
            member_name = participant.User
            log_info(f"Member left: {member_name} ({member_jid}) from {group_jid}")
            await handle_member_leave(bot, group_jid, member_jid, member_name)
    except Exception as e:
        log_warning(f"Error handling group info event: {e}")


@client.event(CallOfferEv)
async def call_offer_handler(c: NewAClient, event: CallOfferEv) -> None:
    """Handle incoming call offers based on call guard config."""
    try:
        await _handle_call_offer(event, source="offer")
    except Exception as e:
        log_warning(f"Error handling call offer event: {e}")


@client.event(CallOfferNoticeEv)
async def call_offer_notice_handler(c: NewAClient, event: CallOfferNoticeEv) -> None:
    """Handle incoming call offer notices (some devices emit this first)."""
    try:
        await _handle_call_offer(event, source="offer_notice")
    except Exception as e:
        log_warning(f"Error handling call offer notice event: {e}")


@client.event(CallAcceptEv)
async def call_accept_handler(c: NewAClient, event: CallAcceptEv) -> None:
    """Log call accept events for diagnostics."""
    try:
        call_id, caller_jid = _extract_call_meta(event)
        pn_jid, lid_jid = await _resolve_call_jids(caller_jid)
        caller_display = _caller_display(caller_jid, pn_jid, lid_jid)
        if call_id or caller_display:
            log_info(f"Call accepted: caller={caller_display or '-'} id={call_id or '-'}")
    except Exception:
        pass


@client.event(CallTerminateEv)
async def call_terminate_handler(c: NewAClient, event: CallTerminateEv) -> None:
    """Log call terminate events for diagnostics."""
    try:
        call_id, caller_jid = _extract_call_meta(event)
        pn_jid, lid_jid = await _resolve_call_jids(caller_jid)
        caller_display = _caller_display(caller_jid, pn_jid, lid_jid)
        reason = getattr(event, "reason", "") or ""
        if call_id or caller_display or reason:
            log_info(
                f"Call terminated: caller={caller_display or '-'} id={call_id or '-'} reason={reason or '-'}"
            )

        # Fallback: some clients only emit terminate, not offer/offer_notice.
        await _handle_call_offer(event, source="terminate_fallback")
    except Exception:
        pass


@client.event(MessageEv)
async def message_handler(c: NewAClient, event: MessageEv) -> None:
    """Handle incoming messages through the middleware pipeline."""

    global bot

    msg = MessageHelper(event)

    try:
        raw_msg_dict = MessageToDict(event.Message)
    except Exception:
        raw_msg_dict = {"error": "Failed to convert protobuf"}

    try:
        log_raw_message(
            {
                "id": event.Info.ID,
                "chat": msg.chat_jid,
                "sender": msg.sender_jid,
                "sender_name": msg.sender_name,
                "is_from_me": msg.is_from_me,
                "is_group": msg.is_group,
                "text": msg.text,
                "timestamp": event.Info.Timestamp,
                "raw_message": raw_msg_dict,
            }
        )
    except Exception as e:
        log_error(f"Failed to log raw message: {e}")

    try:
        ctx = MessageContext(bot=bot, msg=msg, event=event)
        await pipeline.execute(ctx)
    except Exception as e:
        log_error(f"Unhandled error in message handler: {e}")
        log_error(traceback.format_exc())


async def start_bot() -> None:
    """Main async entry point execution."""
    session_state.is_logged_in = False
    session_state.qr_code = None
    session_state.pair_code = None
    session_state.is_pairing = False

    show_banner("Zero Ichi", "WhatsApp Bot built with 💖")

    dashboard_enabled = runtime_config.get_nested("dashboard", "enabled", default=False)
    if dashboard_enabled:
        try:
            import uvicorn

            from dashboard_api import app as api_app

            config = uvicorn.Config(api_app, host="0.0.0.0", port=8000, log_level="warning")
            server = uvicorn.Server(config)
            asyncio.create_task(server.serve())
            log_success("Dashboard API starting on http://localhost:8000")
        except ImportError:
            log_warning("Dashboard API not available (install fastapi & uvicorn)")
        except Exception as e:
            log_warning(f"Dashboard API failed to start: {e}")
    else:
        log_info("Dashboard API is disabled in config.json")

    log_step("Starting bot...")
    log_bullet(f"Session: {BOT_NAME}")
    log_bullet(f"Login Method: {LOGIN_METHOD}")

    num_commands = command_loader.load_commands()
    log_success(f"Loaded {num_commands} commands")

    log_step("Connecting to WhatsApp...")

    if LOGIN_METHOD == "PAIR_CODE":
        log_step(f"Initiating Pair Code login for {PHONE_NUMBER}...")
        try:
            session_state.is_pairing = True
            session_state.phone_number = PHONE_NUMBER
            x = await client.PairPhone(PHONE_NUMBER, True)
            session_state.pair_code = x
            console.print(x)
            show_pair_help()
        except Exception as e:
            log_error(f"Pairing failed: {e}")
            return
    else:
        await client.connect()

    if scheduler and not scheduler._scheduler.running:
        scheduler.start()
        log_success("Scheduler started")

    async def watch_and_reload():
        """Watch for file changes and reload commands and core modules."""
        global bot

        project_dir = _src_dir
        locales_dir = project_dir / "locales"
        watch_dirs = [
            project_dir / "commands",
            project_dir / "core",
            project_dir / "config",
            project_dir / "ai",
            locales_dir,
        ]
        watch_files = [
            project_dir / "dashboard_api.py",
        ]

        log_info("Auto-reload enabled. Watching for file changes...")

        async for changes in awatch(*watch_dirs, *watch_files):
            for _, path in changes:
                path = Path(path)
                try:
                    if path.suffix == ".json" and (
                        path.parent == locales_dir or path.parent.name == "locales"
                    ):
                        reload_locales()
                        log_success(f"[b]↻ Reloaded:[/b] {path.name} (locales)")
                        continue

                    if path.suffix == ".py" and not path.name.startswith("_"):
                        rel_path = path.relative_to(project_dir)
                        module_name = (
                            str(rel_path.with_suffix("")).replace("\\", ".").replace("/", ".")
                        )

                        if module_name in sys.modules:
                            importlib.reload(sys.modules[module_name])

                        if module_name == "dashboard_api":
                            if "dashboard_api" in sys.modules:
                                importlib.reload(sys.modules["dashboard_api"])
                            log_success(f"[b]↻ Reloaded:[/b] {path.name} (API module)")
                        elif module_name.startswith("core."):
                            importlib.reload(sys.modules["core.client"])
                            from core.client import BotClient as ReloadedBotClient
                            from core.shared import set_bot

                            bot = ReloadedBotClient(client)
                            bot.message_cache = message_cache
                            set_bot(bot)
                            log_success(f"[b]↻ Reloaded:[/b] {path.name} (core module)")
                        else:
                            command_loader._commands.clear()
                            count = command_loader.load_commands()
                            log_success(f"[b]↻ Reloaded:[/b] {path.name} ({count} commands)")
                except Exception as e:
                    log_error(f"Reload failed for {path.name}: {e}")

    if AUTO_RELOAD:
        asyncio.create_task(watch_and_reload())
    else:
        log_info("Auto-reload disabled. Set 'auto_reload: true' in config.json to enable.")

    log_success("Bot is running! Press Ctrl+C to stop.")
    await client.idle()


def interrupt_handler(signal, frame):
    """Graceful shutdown handler."""
    console.print("\n\n[yellow]■[/yellow] Bot stopping...")
    loop = asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(ClientFactory.stop(), loop)


def main():
    """Entry point for the bot."""
    signal.signal(signal.SIGINT, interrupt_handler)

    try:
        client.loop.run_until_complete(start_bot())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
