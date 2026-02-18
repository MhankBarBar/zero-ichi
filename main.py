import asyncio
import base64
import importlib
import io
import signal
import sys
from pathlib import Path

import segno
from dotenv import load_dotenv
from google.protobuf.json_format import MessageToDict
from neonize.aioze.client import ClientFactory, NewAClient
from neonize.events import ConnectedEv, GroupInfoEv, MessageEv
from neonize.proto.waCompanionReg.WAWebProtobufsCompanionReg_pb2 import DeviceProps
from watchfiles import awatch

from config.settings import (
    AUTO_RELOAD,
    BOT_NAME,
    LOGIN_METHOD,
    PHONE_NUMBER,
)
from core.cache import message_cache
from core.client import BotClient
from core.command import command_loader
from core.handlers.welcome import handle_member_join, handle_member_leave
from core.i18n import init_i18n
from core.jid_resolver import resolve_pair
from core.logger import (
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
from core.message import MessageHelper
from core.middleware import MessageContext
from core.middlewares import build_pipeline
from core.runtime_config import runtime_config
from core.scheduler import init_scheduler
from core.session import session_state
from core.shared import set_bot

load_dotenv()
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
        event_dict = MessageToDict(event)

        if "join" in event_dict or "leave" in event_dict or "participants" in event_dict:
            group_jid = event_dict.get("jid", "")

            if "join" in event_dict:
                for participant in event_dict.get("join", []):
                    member_jid = participant.get("jid", "")
                    member_name = participant.get("pushName", member_jid.split("@")[0])
                    log_info(f"Member joined: {member_name} ({member_jid}) in {group_jid}")
                    await handle_member_join(bot, group_jid, member_jid, member_name)

            if "leave" in event_dict:
                for participant in event_dict.get("leave", []):
                    member_jid = participant.get("jid", "")
                    member_name = participant.get("pushName", member_jid.split("@")[0])
                    log_info(f"Member left: {member_name} ({member_jid}) from {group_jid}")
                    await handle_member_leave(bot, group_jid, member_jid, member_name)
    except Exception as e:
        log_warning(f"Error handling group info event: {e}")


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
        import traceback

        log_error(traceback.format_exc())


async def start_bot() -> None:
    """Main async entry point execution."""
    session_state.is_logged_in = False
    session_state.qr_code = None
    session_state.pair_code = None
    session_state.is_pairing = False

    show_banner("Zero Ichi", "WhatsApp Bot built with 💖")

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

    log_step("Starting bot...")
    log_bullet(f"Session: {BOT_NAME}")
    log_bullet(f"Login Method: {LOGIN_METHOD}")

    num_commands = command_loader.load_commands()
    log_success(f"Loaded {num_commands} commands")

    log_step("Connecting to WhatsApp...")

    if LOGIN_METHOD == "PAIR_CODE":
        if not PHONE_NUMBER:
            log_error("PHONE_NUMBER is required for PAIR_CODE login method!")
            log_warning("Please update config.json")
            return
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

        project_dir = Path(__file__).parent
        watch_dirs = [
            project_dir / "commands",
            project_dir / "core",
            project_dir / "config",
            project_dir / "ai",
        ]
        watch_files = [
            project_dir / "dashboard_api.py",
        ]

        log_info("Auto-reload enabled. Watching for file changes...")

        async for changes in awatch(*watch_dirs, *watch_files):
            for _, path in changes:
                path = Path(path)
                if path.suffix == ".py" and not path.name.startswith("_"):
                    rel_path = path.relative_to(project_dir)
                    module_name = str(rel_path.with_suffix("")).replace("\\", ".").replace("/", ".")

                    try:
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


if __name__ == "__main__":
    signal.signal(signal.SIGINT, interrupt_handler)

    try:
        client.loop.run_until_complete(start_bot())
    except KeyboardInterrupt:
        pass
