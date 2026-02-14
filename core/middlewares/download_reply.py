"""Download reply middleware — handle replies to download options and search results."""

import asyncio
import time

import httpx

from core import symbols as sym
from core.downloader import DownloadError, FileTooLargeError, _format_size, downloader
from core.errors import report_error
from core.i18n import t, t_error
from core.pending_store import PendingDownload, PendingPlaylist, PendingSearch, pending_downloads


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

    options_text = build_options_text(info)
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

    options_text = build_options_text(info)
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


def build_options_text(info) -> str:
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
