import asyncio
import base64
import importlib
import io
import sys
import time
from pathlib import Path

import httpx
import segno
from dotenv import load_dotenv
from google.protobuf.json_format import MessageToDict
from neonize.aioze.client import ClientFactory, NewAClient
from neonize.events import ConnectedEv, GroupInfoEv, MessageEv
from neonize.proto.waCompanionReg.WAWebProtobufsCompanionReg_pb2 import DeviceProps
from watchfiles import awatch

from ai import agentic_ai
from config.settings import (
    AUTO_RELOAD,
    BOT_NAME,
    IGNORE_SELF_MESSAGES,
    LOG_MESSAGES,
    LOGIN_METHOD,
    PHONE_NUMBER,
)
from core import symbols as sym
from core.cache import message_cache
from core.client import BotClient
from core.command import CommandContext, command_loader
from core.downloader import DownloadError, FileTooLargeError, _format_size, downloader
from core.errors import report_error
from core.handlers import afk as afk_handler
from core.handlers import antidelete
from core.handlers import antilink as antilink_handler
from core.handlers import blacklist as blacklist_handler
from core.handlers import features as features_handler
from core.handlers import mute as mute_handler
from core.handlers.welcome import handle_member_join, handle_member_leave
from core.i18n import init_i18n, set_context, t, t_error
from core.logger import (
    console,
    log_bullet,
    log_command,
    log_command_execution,
    log_command_skip,
    log_error,
    log_info,
    log_raw_message,
    log_step,
    log_success,
    log_warning,
    show_banner,
    show_connected,
    show_message,
    show_pair_help,
    show_qr_prompt,
)
from core.message import MessageHelper
from core.middleware import MessageContext, MiddlewarePipeline
from core.pending_store import PendingDownload, PendingPlaylist, PendingSearch, pending_downloads
from core.permissions import check_command_permissions, is_owner_for_bypass
from core.rate_limiter import rate_limiter
from core.runtime_config import runtime_config
from core.scheduler import init_scheduler
from core.session import session_state
from core.shared import set_bot
from core.storage import Storage

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
        from core.jid_resolver import resolve_pair

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


async def self_mode_middleware(ctx, next):
    """Skip messages not from self when in self mode."""
    if runtime_config.self_mode:
        if not ctx.msg.is_from_me:
            return
    elif IGNORE_SELF_MESSAGES and ctx.msg.is_from_me:
        return
    await next()


async def stats_middleware(ctx, next):
    """Track message stats and resolve chat type."""
    stats_storage = Storage()
    stats_storage.increment_stat("messages_total")

    if ctx.msg.is_group:
        group_name = await ctx.bot.get_group_name(ctx.msg.chat_jid)
        ctx.chat_type = f"Group ({group_name})"

    if LOG_MESSAGES:
        show_message(ctx.chat_type, ctx.msg.sender_name, ctx.msg.text)

    ctx.extras["stats_storage"] = stats_storage
    await next()


async def auto_actions_middleware(ctx, next):
    """Handle auto-read and auto-react."""
    if runtime_config.get_nested("bot", "auto_read", default=False):
        await ctx.bot.mark_read(ctx.msg)

    emoji = runtime_config.get_nested("bot", "auto_react_emoji", default="")
    if emoji and runtime_config.get_nested("bot", "auto_react", default=False):
        try:
            await ctx.bot.send_reaction(ctx.msg, emoji)
        except Exception:
            pass

    await next()


async def antidelete_middleware(ctx, next):
    """Cache messages and handle anti-delete revocations."""
    await antidelete.handle_anti_delete_cache(ctx.bot, ctx.event, ctx.msg)
    await antidelete.handle_anti_revoke(ctx.bot, ctx.event, ctx.msg)
    await next()


async def blacklist_middleware(ctx, next):
    """Block messages containing blacklisted words."""
    if await blacklist_handler.handle_blacklist(ctx.bot, ctx.msg):
        return
    await next()


async def antilink_middleware(ctx, next):
    """Block messages containing links if anti-link is enabled."""
    if await antilink_handler.handle_anti_link(ctx.bot, ctx.msg):
        return
    await next()


async def mute_middleware(ctx, next):
    """Skip messages from muted users."""
    if await mute_handler.handle_muted_users(ctx.bot, ctx.msg):
        return
    await next()


async def features_middleware(ctx, next):
    """Handle notes, filters, and other group features."""
    set_context(ctx.msg.chat_jid)
    await features_handler.handle_features(ctx.bot, ctx.msg)
    await afk_handler.handle_afk_mentions(ctx.bot, ctx.msg)
    await next()


async def download_reply_middleware(ctx, next):
    """Handle replies to download option and search result messages."""
    quoted = ctx.msg.quoted_message
    if not quoted:
        await next()
        return

    text = ctx.msg.text.strip()
    if not text.isdigit():
        await next()
        return

    stanza_id = quoted.get("id", "")
    if not stanza_id:
        await next()
        return

    pending = pending_downloads.get(stanza_id)
    if not pending:
        await next()
        return

    if ctx.msg.sender_jid != pending.sender_jid:
        await next()
        return

    if isinstance(pending, PendingSearch):
        await _handle_search_reply(ctx, pending, stanza_id, int(text))
    elif isinstance(pending, PendingPlaylist):
        await _handle_playlist_reply(ctx, pending, stanza_id, int(text))
    elif isinstance(pending, PendingDownload):
        await _handle_download_reply(ctx, pending, stanza_id, int(text))


async def _handle_playlist_reply(ctx, pending, stanza_id, choice_num):
    """Handle reply to playlist track list: treat selected track like a search result."""

    if choice_num < 1 or choice_num > len(pending.entries):
        await ctx.bot.reply(ctx.msg, t_error("downloader.invalid_choice"))
        return

    selected = pending.entries[choice_num - 1]
    pending_downloads.remove(stanza_id)

    await ctx.bot.send_reaction(ctx.msg, "⏳")

    try:
        info = await downloader.get_info(selected.url)
    except DownloadError as e:
        await ctx.bot.send_reaction(ctx.msg, "❌")
        await ctx.bot.reply(ctx.msg, t_error("downloader.failed", error=str(e)))
        return

    if not info.formats:
        await ctx.bot.send_reaction(ctx.msg, "❌")
        await ctx.bot.reply(
            ctx.msg,
            f"{sym.INFO} {t('downloader.no_formats')}\n"
            f"{sym.INFO} {t('downloader.use_audio_video_hint')}",
        )
        return

    if len(info.formats) == 1:
        fmt = info.formats[0]
        try:
            filepath = await downloader.download_format(
                info.url,
                fmt.format_id,
                merge_audio=not fmt.has_audio,
                is_audio=fmt.type == "audio",
            )
            media_type = "audio" if fmt.type == "audio" else "video"
            caption = f"{sym.SPARKLE} {info.title}"
            await ctx.bot.send_media(
                ctx.msg.chat_jid,
                media_type,
                str(filepath),
                caption=caption,
                quoted=ctx.msg.event,
            )
            downloader.cleanup(filepath)
            await ctx.bot.send_reaction(ctx.msg, "✅")
        except Exception as e:
            await ctx.bot.send_reaction(ctx.msg, "❌")
            await report_error(ctx.bot, ctx.msg, "dl", e)
        return

    await ctx.bot.send_reaction(ctx.msg, "")

    options_text = _build_options_text(info)
    response = None

    if info.thumbnail:
        try:
            async with httpx.AsyncClient(timeout=5) as http:
                resp = await http.get(info.thumbnail)
                if resp.status_code == 200 and len(resp.content) > 0:
                    response = await ctx.bot.send_image(
                        ctx.msg.chat_jid,
                        resp.content,
                        caption=options_text,
                        quoted=ctx.msg.event,
                    )
        except Exception:
            pass

    if not response:
        response = await ctx.bot.reply(ctx.msg, options_text)

    pending_downloads.add(
        response.ID,
        PendingDownload(
            url=info.url,
            info=info,
            sender_jid=pending.sender_jid,
            chat_jid=pending.chat_jid,
        ),
    )


async def _handle_search_reply(ctx, pending, stanza_id, choice_num):
    """Handle reply to search results: fetch info for chosen result and show formats."""

    if choice_num < 1 or choice_num > len(pending.results):
        await ctx.bot.reply(ctx.msg, t_error("downloader.invalid_choice"))
        return

    selected = pending.results[choice_num - 1]
    pending_downloads.remove(stanza_id)

    await ctx.bot.send_reaction(ctx.msg, "⏳")

    try:
        info = await downloader.get_info(selected.url)
    except DownloadError as e:
        await ctx.bot.send_reaction(ctx.msg, "❌")
        await ctx.bot.reply(ctx.msg, t_error("downloader.failed", error=str(e)))
        return

    if not info.formats:
        await ctx.bot.send_reaction(ctx.msg, "❌")
        await ctx.bot.reply(
            ctx.msg,
            f"{sym.INFO} {t('downloader.no_formats')}\n"
            f"{sym.INFO} {t('downloader.use_audio_video_hint')}",
        )
        return

    if len(info.formats) == 1:
        fmt = info.formats[0]
        try:
            filepath = await downloader.download_format(
                info.url,
                fmt.format_id,
                merge_audio=not fmt.has_audio,
                is_audio=fmt.type == "audio",
            )
            media_type = "audio" if fmt.type == "audio" else "video"
            caption = f"{sym.SPARKLE} {info.title}"
            await ctx.bot.send_media(
                ctx.msg.chat_jid,
                media_type,
                str(filepath),
                caption=caption,
                quoted=ctx.msg.event,
            )
            downloader.cleanup(filepath)
            await ctx.bot.send_reaction(ctx.msg, "✅")
        except Exception as e:
            await ctx.bot.send_reaction(ctx.msg, "❌")
            await report_error(ctx.bot, ctx.msg, "dl", e)
        return

    await ctx.bot.send_reaction(ctx.msg, "")

    options_text = _build_options_text(info)
    response = None

    if info.thumbnail:
        try:
            async with httpx.AsyncClient(timeout=5) as http:
                resp = await http.get(info.thumbnail)
                if resp.status_code == 200 and len(resp.content) > 0:
                    response = await ctx.bot.send_image(
                        ctx.msg.chat_jid,
                        resp.content,
                        caption=options_text,
                        quoted=ctx.msg.event,
                    )
        except Exception:
            pass

    if not response:
        response = await ctx.bot.reply(ctx.msg, options_text)

    pending_downloads.add(
        response.ID,
        PendingDownload(
            url=info.url,
            info=info,
            sender_jid=pending.sender_jid,
            chat_jid=pending.chat_jid,
        ),
    )


async def _handle_download_reply(ctx, pending, stanza_id, choice_num):
    """Handle reply to format options: download the selected format."""

    if choice_num < 1 or choice_num > len(pending.info.formats):
        await ctx.bot.reply(ctx.msg, t_error("downloader.invalid_choice"))
        return

    selected = pending.info.formats[choice_num - 1]
    pending_downloads.remove(stanza_id)

    await ctx.bot.send_reaction(ctx.msg, "⏳")

    quality_label = f"{selected.quality} {selected.ext.upper()}"
    progress_msg = await ctx.bot.reply(
        ctx.msg,
        f"{sym.ARROW} {t('downloader.downloading', title=pending.info.title, quality=quality_label)}",
    )

    progress_msg_id = progress_msg.ID
    last_edit_time = [0.0]
    loop = asyncio.get_event_loop()

    def _progress_hook(downloaded_bytes, total_bytes, speed, eta):
        now = time.time()
        if now - last_edit_time[0] < 5:
            return
        last_edit_time[0] = now

        if not total_bytes or total_bytes <= 0:
            return

        pct = (downloaded_bytes / total_bytes) * 100
        filled = int(pct / 5)
        bar = "█" * filled + "░" * (20 - filled)

        speed_str = _format_size(speed) + "/s" if speed else "?"
        eta_str = f"{int(eta)}s" if eta else "?"
        dl_str = _format_size(downloaded_bytes)
        total_str = _format_size(total_bytes)

        text = (
            f"{sym.ARROW} {t('downloader.downloading', title=pending.info.title, quality=quality_label)}\n\n"
            f"`[{bar}]` {pct:.0f}%\n"
            f"{sym.BULLET} {dl_str} / {total_str}\n"
            f"{sym.BULLET} {speed_str} {sym.BULLET} ETA: {eta_str}"
        )

        asyncio.run_coroutine_threadsafe(
            ctx.bot.edit_message(ctx.msg.chat_jid, progress_msg_id, text),
            loop,
        )

    try:
        filepath = await downloader.download_format(
            pending.url,
            selected.format_id,
            merge_audio=not selected.has_audio,
            is_audio=selected.type == "audio",
            progress_hook=_progress_hook,
        )

        await ctx.bot.edit_message(
            ctx.msg.chat_jid,
            progress_msg_id,
            f"{sym.ARROW} {t('downloader.downloading', title=pending.info.title, quality=quality_label)}\n\n"
            f"`[{'█' * 20}]` 100%\n"
            f"{sym.BULLET} {t('downloader.sending')}",
        )

        media_type = "audio" if selected.type == "audio" else "video"
        caption = f"{sym.SPARKLE} {pending.info.title}"

        await ctx.bot.send_media(
            ctx.msg.chat_jid,
            media_type,
            str(filepath),
            caption=caption,
            quoted=ctx.msg.event,
        )

        downloader.cleanup(filepath)
        await ctx.bot.edit_message(
            ctx.msg.chat_jid,
            progress_msg_id,
            f"{sym.ARROW} {t('downloader.downloading', title=pending.info.title, quality=quality_label)}\n\n"
            f"`[{'█' * 20}]` 100%\n"
            f"{sym.BULLET} {t('downloader.done')}",
        )
        await ctx.bot.send_reaction(ctx.msg, "✅")

    except FileTooLargeError as e:
        await ctx.bot.send_reaction(ctx.msg, "❌")
        await ctx.bot.reply(
            ctx.msg,
            t_error("downloader.too_large", size=f"{e.size_mb:.1f}", max=f"{e.max_mb:.0f}"),
        )
    except DownloadError as e:
        await ctx.bot.send_reaction(ctx.msg, "❌")
        await ctx.bot.reply(ctx.msg, t_error("downloader.failed", error=str(e)))
    except Exception as e:
        await ctx.bot.send_reaction(ctx.msg, "❌")
        await report_error(ctx.bot, ctx.msg, "dl", e)


def _build_options_text(info) -> str:
    """Build the numbered format options text (shared with middleware)."""
    lines = [
        f"{sym.SPARKLE} *{info.title}*",
        "",
        f"{sym.ARROW} {info.uploader}",
        f"{sym.BULLET} {info.platform} {sym.BULLET} {info.duration_str}",
    ]

    if info.filesize_approx:
        lines[-1] += f" {sym.BULLET} ~{info.filesize_str}"

    lines.append("")

    video_formats = [f for f in info.formats if f.type == "video"]
    audio_formats = [f for f in info.formats if f.type == "audio"]

    idx = 1

    if video_formats:
        lines.append(f"*{sym.VIDEO} {t('downloader.video_options')}*")
        for fmt in video_formats:
            size = f" ({fmt.filesize_str})" if fmt.filesize else ""
            lines.append(f" {sym.BULLET} `{idx}.` {fmt.quality} {fmt.ext.upper()}{size}")
            idx += 1
        lines.append("")

    if audio_formats:
        lines.append(f"*{sym.AUDIO} {t('downloader.audio_options')}*")
        for fmt in audio_formats:
            size = f" ({fmt.filesize_str})" if fmt.filesize else ""
            lines.append(f" {sym.BULLET} `{idx}.` {fmt.quality} {fmt.ext.upper()}{size}")
            idx += 1
        lines.append("")

    lines.append(f"{sym.INFO} {t('downloader.choose_hint')}")

    return "\n".join(lines)


async def ai_middleware(ctx, next):
    """Process message with AI agent if applicable."""
    parsed_cmd = command_loader.parse_command(ctx.msg.text)[0]
    is_command = parsed_cmd is not None and command_loader.get(parsed_cmd) is not None

    if not is_command and await agentic_ai.should_respond(ctx.msg, ctx.bot):
        try:
            response = await agentic_ai.process(ctx.msg, ctx.bot)
            if response and response.strip():
                await ctx.bot.reply(ctx.msg, response)
            return
        except Exception as e:
            log_error(f"AI agent error: {e}")

    await next()


async def command_middleware(ctx, next):
    """Parse and execute bot commands."""
    command_name, raw_args, args = command_loader.parse_command(ctx.msg.text)
    if not command_name:
        return

    cmd = command_loader.get(command_name)
    if not cmd:
        return

    text = ctx.msg.text.strip()
    cmd_start = text.lower().find(command_name.lower())
    used_prefix = text[:cmd_start] if cmd_start > 0 else "/"

    perm_result = await check_command_permissions(cmd, ctx.msg, ctx.bot)
    if not perm_result:
        if perm_result.error_message:
            await ctx.bot.reply(ctx.msg, perm_result.error_message)
        log_command_skip(command_name, "permission denied", prefix=used_prefix)
        return

    is_owner = await is_owner_for_bypass(ctx.msg, ctx.bot)
    if not is_owner and rate_limiter.is_limited(ctx.msg.sender_jid, command_name):
        remaining = rate_limiter.get_remaining_cooldown(ctx.msg.sender_jid, command_name)
        log_command_skip(
            command_name, f"rate limited ({remaining:.1f}s remaining)", prefix=used_prefix
        )
        await ctx.bot.reply(
            ctx.msg, f"{sym.CLOCK} {t('errors.cooldown', remaining=f'{remaining:.1f}')}"
        )
        return

    rate_limiter.record(ctx.msg.sender_jid, command_name)

    stats_storage = ctx.extras.get("stats_storage")
    if stats_storage:
        stats_storage.increment_stat("commands_used")

    log_command(command_name, ctx.msg.sender_name, ctx.chat_type, prefix=used_prefix)

    try:
        cmd_ctx = CommandContext(
            client=ctx.bot,
            message=ctx.msg,
            args=args,
            raw_args=raw_args,
            command_name=command_name,
        )
        await cmd.execute(cmd_ctx)

        log_command_execution(
            command_name,
            ctx.msg.sender_name,
            ctx.chat_type,
            ctx.msg.chat_jid,
            success=True,
            prefix=used_prefix,
        )
    except Exception as e:
        log_command_execution(
            command_name,
            ctx.msg.sender_name,
            ctx.chat_type,
            ctx.msg.chat_jid,
            success=False,
            error=str(e),
            prefix=used_prefix,
        )

        await report_error(cmd_ctx.client, cmd_ctx.message, command_name, e)

    await next()


pipeline = MiddlewarePipeline()
pipeline.use("self_mode", self_mode_middleware)
pipeline.use("stats", stats_middleware)
pipeline.use("auto_actions", auto_actions_middleware)
pipeline.use("antidelete", antidelete_middleware)
pipeline.use("blacklist", blacklist_middleware)
pipeline.use("antilink", antilink_middleware)
pipeline.use("mute", mute_middleware)
pipeline.use("features", features_middleware)
pipeline.use("download_reply", download_reply_middleware)
pipeline.use("ai", ai_middleware)
pipeline.use("command", command_middleware)


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
    import signal

    signal.signal(signal.SIGINT, interrupt_handler)

    try:
        client.loop.run_until_complete(start_bot())
    except KeyboardInterrupt:
        pass
