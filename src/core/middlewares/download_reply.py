"""Download reply middleware — handle replies to download options and search results."""

import asyncio
import re
import time

import httpx

from core import symbols as sym
from core.applemusic import AppleMusicError, applemusic_client
from core.downloader import (
    DownloadAbortedError,
    DownloadError,
    FileTooLargeError,
    downloader,
)
from core.errors import report_error
from core.i18n import t, t_error
from core.pending_store import (
    PendingAppleMusic,
    PendingDownload,
    PendingPlaylist,
    PendingSearch,
    pending_downloads,
)
from core.progress import build_complete_bar, build_progress_text


async def download_reply_middleware(ctx, next):
    """Handle replies to download option and search result messages."""
    quoted = ctx.msg.quoted_message
    if not quoted:
        await next()
        return

    text = ctx.msg.text.strip()
    is_all = text.lower() in ("all", "0")
    selection = _parse_selection(text) if not is_all else None

    if not is_all and not selection:
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

    is_multi = is_all or (selection and len(selection) > 1)

    if isinstance(pending, PendingAppleMusic):
        if is_all:
            await _handle_applemusic_all(ctx, pending, stanza_id)
        elif is_multi:
            await _handle_applemusic_all(ctx, pending, stanza_id, selection)
        else:
            await _handle_applemusic_reply(ctx, pending, stanza_id, selection[0])
    elif isinstance(pending, PendingSearch):
        if selection:
            await _handle_search_reply(ctx, pending, stanza_id, selection[0])
    elif isinstance(pending, PendingPlaylist):
        if is_all:
            await _handle_playlist_all(ctx, pending, stanza_id)
        elif is_multi:
            await _handle_playlist_all(ctx, pending, stanza_id, selection)
        else:
            await _handle_playlist_reply(ctx, pending, stanza_id, selection[0])
    elif isinstance(pending, PendingDownload):
        if selection:
            await _handle_download_reply(ctx, pending, stanza_id, selection[0])


def _parse_selection(text: str) -> list[int] | None:
    """Parse selection text into a sorted list of unique 1-based indices.

    Supports: '3', '1-5', '1, 3, 5', '1-3, 7, 9-12'
    Returns None if the text is not a valid selection.
    """
    text = text.replace(" ", "")
    if not text:
        return None

    indices = set()
    try:
        for part in text.split(","):
            if "-" in part:
                bounds = part.split("-", 1)
                start, end = int(bounds[0]), int(bounds[1])
                if start < 1 or end < start:
                    return None
                indices.update(range(start, end + 1))
            else:
                val = int(part)
                if val < 1:
                    return None
                indices.add(val)
    except (ValueError, IndexError):
        return None

    return sorted(indices) if indices else None


async def _handle_playlist_reply(ctx, pending, stanza_id, choice_num):
    """Handle reply to playlist track list."""
    await _handle_selection_reply(ctx, pending, stanza_id, choice_num, pending.entries)


async def _handle_search_reply(ctx, pending, stanza_id, choice_num):
    """Handle reply to search results."""
    await _handle_selection_reply(ctx, pending, stanza_id, choice_num, pending.results)


async def _handle_selection_reply(ctx, pending, stanza_id, choice_num, items):
    """Shared handler for search/playlist replies: fetch info and show format options."""
    if choice_num < 1 or choice_num > len(items):
        await ctx.bot.reply(ctx.msg, t_error("downloader.invalid_choice"))
        return

    selected = items[choice_num - 1]
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
                chat_jid=ctx.msg.chat_jid,
                sender_jid=ctx.msg.sender_jid,
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

        header = f"{sym.ARROW} {t('downloader.downloading', title=pending.info.title, quality=quality_label)}\n\n"
        text = build_progress_text(header, downloaded_bytes, total_bytes, speed, eta)
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
            chat_jid=ctx.msg.chat_jid,
            sender_jid=ctx.msg.sender_jid,
        )

        dl_header = f"{sym.ARROW} {t('downloader.downloading', title=pending.info.title, quality=quality_label)}\n\n"
        await ctx.bot.edit_message(
            ctx.msg.chat_jid,
            progress_msg_id,
            build_complete_bar(dl_header, t("downloader.sending")),
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
            build_complete_bar(dl_header, t("downloader.done")),
        )
        await ctx.bot.send_reaction(ctx.msg, "✅")

    except FileTooLargeError as e:
        await ctx.bot.send_reaction(ctx.msg, "❌")
        await ctx.bot.reply(
            ctx.msg,
            t_error("downloader.too_large", size=f"{e.size_mb:.1f}", max=f"{e.max_mb:.0f}"),
        )
    except DownloadAbortedError:
        await ctx.bot.edit_message(
            ctx.msg.chat_jid,
            progress_msg_id,
            f"{sym.ARROW} {t('downloader.downloading', title=pending.info.title, quality=quality_label)}\n\n"
            f"{sym.INFO} {t('downloader.cancelled')}",
        )

        await ctx.bot.send_reaction(ctx.msg, "🚫")
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


async def _handle_applemusic_reply(ctx, pending, stanza_id, choice_num):
    """Handle reply to Apple Music track list: download selected track."""
    if choice_num < 1 or choice_num > len(pending.tracks):
        await ctx.bot.reply(ctx.msg, t_error("downloader.invalid_choice"))
        return

    selected = pending.tracks[choice_num - 1]
    pending_downloads.remove(stanza_id)

    await ctx.bot.send_reaction(ctx.msg, "⏳")

    header = f"{sym.MUSIC} *{selected.name}*\n{sym.ARROW} {selected.artist}"
    if selected.album:
        header += f" {sym.BULLET} {selected.album}"
    header += "\n"

    progress_msg = await ctx.bot.reply(
        ctx.msg,
        f"{header}\n{sym.LOADING} {t('applemusic.fetching_link')}",
    )

    try:
        dlink = await applemusic_client.get_download_link(selected)

        last_edit = [0.0]
        loop = asyncio.get_event_loop()
        msg_id = progress_msg.ID

        def _on_progress(downloaded: int, total: int):
            now = time.time()
            if now - last_edit[0] < 3:
                return
            last_edit[0] = now
            text = build_progress_text(header, downloaded, total)
            asyncio.run_coroutine_threadsafe(
                ctx.bot.edit_message(ctx.msg.chat_jid, msg_id, text),
                loop,
            )

        safe_name = re.sub(r"[^\w\s-]", "", selected.name)[:50] or "track"
        filename = f"am_{safe_name}"
        filepath = await applemusic_client.download_track(dlink, filename, _on_progress)

        await ctx.bot.edit_message(
            ctx.msg.chat_jid,
            msg_id,
            build_complete_bar(header, t("applemusic.sending")),
        )

        await ctx.bot.send_media(
            ctx.msg.chat_jid,
            "audio",
            str(filepath),
            quoted=ctx.msg.event,
        )

        applemusic_client.cleanup(filepath)
        await ctx.bot.edit_message(
            ctx.msg.chat_jid,
            msg_id,
            build_complete_bar(header, t("applemusic.done")),
        )
        await ctx.bot.send_reaction(ctx.msg, "✅")

    except AppleMusicError as e:
        await ctx.bot.send_reaction(ctx.msg, "❌")
        await ctx.bot.reply(ctx.msg, t_error("applemusic.failed", error=str(e)))
    except Exception as e:
        await ctx.bot.send_reaction(ctx.msg, "❌")
        await report_error(ctx.bot, ctx.msg, "applemusic", e)


async def _handle_applemusic_all(ctx, pending, stanza_id, selection=None):
    """Handle batch download: all tracks or a selection of them."""
    all_tracks = pending.tracks
    if selection:
        tracks = [all_tracks[i - 1] for i in selection if 1 <= i <= len(all_tracks)]
    else:
        tracks = all_tracks
    if not tracks:
        await ctx.bot.reply(ctx.msg, t_error("downloader.invalid_choice"))
        return
    total = len(tracks)
    pending_downloads.remove(stanza_id)

    is_group = ctx.msg.is_group
    send_to = pending.sender_jid if is_group else ctx.msg.chat_jid

    await ctx.bot.send_reaction(ctx.msg, "⏳")

    album_header = f"{sym.MUSIC} *{pending.album_name}*\n" if pending.album_name else ""

    if is_group:
        await ctx.bot.reply(
            ctx.msg,
            f"{album_header}{sym.INFO} {t('applemusic.dm_notice', count=total)}",
        )

    progress_msg = await ctx.bot.reply(
        ctx.msg,
        f"{album_header}{sym.LOADING} {t('applemusic.downloading_all', count=total)}",
    )

    sent = 0
    failed = 0

    for i, track in enumerate(tracks, 1):
        track_header = f"{sym.MUSIC} *{track.name}*\n{sym.ARROW} {track.artist}\n"

        try:
            await ctx.bot.edit_message(
                ctx.msg.chat_jid,
                progress_msg.ID,
                f"{album_header}{sym.LOADING} {t('applemusic.track_progress', current=i, total=total)}\n{track_header}",
            )

            dlink = await applemusic_client.get_download_link(track)

            last_edit = [0.0]
            loop = asyncio.get_event_loop()
            msg_id = progress_msg.ID

            def _on_progress(
                downloaded: int,
                total_bytes: int,
                _hdr=track_header,
                _last=last_edit,
                _loop=loop,
                _mid=msg_id,
                _idx=i,
            ):
                now = time.time()
                if now - _last[0] < 3:
                    return
                _last[0] = now
                text = build_progress_text(
                    f"{album_header}{sym.BULLET} {_idx}/{total}\n{_hdr}",
                    downloaded,
                    total_bytes,
                )
                asyncio.run_coroutine_threadsafe(
                    ctx.bot.edit_message(ctx.msg.chat_jid, _mid, text),
                    _loop,
                )

            safe_name = re.sub(r"[^\w\s-]", "", track.name)[:50] or "track"
            filename = f"am_{safe_name}"
            filepath = await applemusic_client.download_track(dlink, filename, _on_progress)

            await ctx.bot.send_media(
                send_to,
                "audio",
                str(filepath),
                quoted=ctx.msg.event if not is_group else None,
            )

            applemusic_client.cleanup(filepath)
            sent += 1

        except Exception:
            failed += 1

        if i < total:
            await asyncio.sleep(5)

    if failed == 0:
        summary = f"{album_header}{sym.BULLET} {t('applemusic.all_done', count=sent)}"
    else:
        summary = f"{album_header}{sym.BULLET} {t('applemusic.all_partial', sent=sent, total=total, failed=failed)}"

    await ctx.bot.edit_message(ctx.msg.chat_jid, progress_msg.ID, summary)
    await ctx.bot.send_reaction(ctx.msg, "✅" if failed == 0 else "⚠️")


async def _handle_playlist_all(ctx, pending, stanza_id, selection=None):
    """Handle batch download: all playlist tracks or a selection of them."""
    all_entries = pending.entries
    if selection:
        entries = [all_entries[i - 1] for i in selection if 1 <= i <= len(all_entries)]
    else:
        entries = all_entries
    if not entries:
        await ctx.bot.reply(ctx.msg, t_error("downloader.invalid_choice"))
        return
    total = len(entries)
    pending_downloads.remove(stanza_id)

    is_group = ctx.msg.is_group
    send_to = pending.sender_jid if is_group else ctx.msg.chat_jid

    await ctx.bot.send_reaction(ctx.msg, "⏳")

    playlist_header = f"{sym.SPARKLE} *{pending.title}*\n" if pending.title else ""

    if is_group:
        await ctx.bot.reply(
            ctx.msg,
            f"{playlist_header}{sym.INFO} {t('downloader.dm_notice', count=total)}",
        )

    progress_msg = await ctx.bot.reply(
        ctx.msg,
        f"{playlist_header}{sym.LOADING} {t('downloader.downloading_all', count=total)}",
    )

    sent = 0
    failed = 0

    for i, entry in enumerate(entries, 1):
        track_header = f"{sym.MUSIC} *{entry.title}*\n"
        if entry.uploader:
            track_header += f"{sym.ARROW} {entry.uploader}\n"

        try:
            await ctx.bot.edit_message(
                ctx.msg.chat_jid,
                progress_msg.ID,
                f"{playlist_header}{sym.LOADING} {t('downloader.track_progress', current=i, total=total)}\n{track_header}",
            )

            filepath = await downloader.download_audio(
                entry.url,
                chat_jid=ctx.msg.chat_jid,
                sender_jid=ctx.msg.sender_jid,
            )

            caption = f"{sym.MUSIC} {entry.title}"
            if entry.uploader:
                caption += f"\n{sym.ARROW} {entry.uploader}"

            await ctx.bot.send_media(
                send_to,
                "audio",
                str(filepath),
                caption=caption,
                quoted=ctx.msg.event if not is_group else None,
            )

            downloader.cleanup(filepath)
            sent += 1

        except Exception:
            failed += 1

        if i < total:
            await asyncio.sleep(5)

    if failed == 0:
        summary = f"{playlist_header}{sym.BULLET} {t('downloader.all_done', count=sent)}"
    else:
        summary = f"{playlist_header}{sym.BULLET} {t('downloader.all_partial', sent=sent, total=total, failed=failed)}"

    await ctx.bot.edit_message(ctx.msg.chat_jid, progress_msg.ID, summary)
    await ctx.bot.send_reaction(ctx.msg, "✅" if failed == 0 else "⚠️")
