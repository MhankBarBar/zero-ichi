"""Download reply middleware — handle replies to download options and search results."""

import asyncio
import re
import time
from dataclasses import replace
from types import SimpleNamespace

from core import symbols as sym
from core.applemusic import AppleMusicError, applemusic_client
from core.applemusic_amdl import AmDlError, amdl_client, raw_track_to_apple_music_track
from core.downloader import (
    DownloadAbortedError,
    DownloadError,
    FileTooLargeError,
    downloader,
)
from core.downloader_render import (
    build_album_header,
    build_album_text,
    build_format_sections,
    build_options_header,
    build_options_text,
    build_playlist_header,
    build_playlist_sections,
    build_playlist_text,
    build_search_header,
    build_search_sections,
    build_search_text,
    build_track_sections,
)
from core.errors import report_error
from core.i18n import t, t_error
from core.pending_store import (
    PendingAppleMusic,
    PendingAppleMusicQuality,
    PendingDownload,
    PendingPlaylist,
    PendingSearch,
    pending_downloads,
)
from core.progress import build_complete_bar, build_progress_text
from core.selection_ui import send_selection


async def download_reply_middleware(ctx, next):
    """Handle replies to download option and search result messages."""
    quoted = ctx.msg.quoted_message
    if not quoted:
        await next()
        return

    text = ctx.msg.text.strip()
    stanza_id = quoted.get("id", "")

    nav_page = _parse_nav_page(text)
    if nav_page is not None:
        if not stanza_id:
            await next()
            return
        pending = pending_downloads.get(stanza_id)
        if not pending or ctx.msg.sender_jid != pending.sender_jid:
            await next()
            return
        await _handle_page_nav(ctx, pending, nav_page)
        return

    if not stanza_id:
        await next()
        return

    pending = pending_downloads.get(stanza_id)
    if not pending:
        await next()
        return

    if isinstance(pending, PendingAppleMusicQuality):
        quality_choice = _parse_quality(text)
        if not quality_choice or ctx.msg.sender_jid != pending.sender_jid:
            await next()
            return
        await _handle_applemusic_quality(ctx, pending, stanza_id, quality_choice)
        return

    is_all = text.lower() in ("all", "0")
    selection = _parse_selection(text) if not is_all else None

    if not is_all and not selection:
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


_QUALITY_ALIASES = {
    "standard": "standard",
    "1": "standard",
    "alac": "alac",
    "2": "alac",
    "atmos": "atmos",
    "3": "atmos",
}


def _parse_quality(text: str) -> str | None:
    """Parse a quality-picker reply: 'standard'/'alac'/'atmos' or their '1'/'2'/'3' aliases."""
    return _QUALITY_ALIASES.get(text.strip().lower())


def _parse_nav_page(text: str) -> int | None:
    """Parse a pagination nav row id like 'page:2' into its target page number."""
    if not text.startswith("page:"):
        return None
    try:
        page = int(text[5:])
    except ValueError:
        return None
    return page if page >= 0 else None


async def _handle_page_nav(ctx, pending, target_page: int) -> None:
    """Re-render the requested page of a pending selection as a new button message.

    Doesn't consume the pending item — the original page's message stays valid.
    """
    if isinstance(pending, PendingSearch):
        response = await send_selection(
            ctx.bot,
            ctx.msg,
            fallback_text=build_search_text(pending.query, pending.results),
            sections=build_search_sections(pending.results),
            header=build_search_header(pending.query),
            menu_title="Choose a result",
            card_title=f"{sym.SEARCH} Search Results",
            page=target_page,
        )
    elif isinstance(pending, PendingDownload):
        info = pending.info
        response = await send_selection(
            ctx.bot,
            ctx.msg,
            fallback_text=build_options_text(info),
            sections=build_format_sections(info),
            header=build_options_header(info),
            menu_title="Choose a quality",
            card_title=f"{sym.SPARKLE} {info.title}",
            thumbnail=info.thumbnail or None,
            page=target_page,
        )
    elif isinstance(pending, PendingPlaylist):
        playlist_like = SimpleNamespace(
            title=pending.title, entries=pending.entries, count=len(pending.entries)
        )
        response = await send_selection(
            ctx.bot,
            ctx.msg,
            fallback_text=build_playlist_text(playlist_like),
            sections=build_playlist_sections(pending.entries),
            header=build_playlist_header(playlist_like),
            menu_title="Choose a track",
            card_title=f"{sym.SPARKLE} {pending.title}",
            allow_all=True,
            page=target_page,
        )
    elif isinstance(pending, PendingAppleMusic):
        album_like = SimpleNamespace(
            album=pending.album_name, artist="", count=len(pending.tracks), tracks=pending.tracks
        )
        response = await send_selection(
            ctx.bot,
            ctx.msg,
            fallback_text=build_album_text(album_like),
            sections=build_track_sections(pending.tracks),
            header=build_album_header(album_like),
            menu_title="Choose a track",
            card_title=f"{sym.MUSIC} {pending.album_name}",
            allow_all=True,
            page=target_page,
        )
    else:
        return

    pending_downloads.add(response.ID, replace(pending, created_at=time.time()))


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

    response = await send_selection(
        ctx.bot,
        ctx.msg,
        fallback_text=build_options_text(info),
        sections=build_format_sections(info),
        header=build_options_header(info),
        menu_title="Choose a quality",
        card_title=f"{sym.SPARKLE} {info.title}",
        thumbnail=info.thumbnail or None,
    )

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
    loop = asyncio.get_running_loop()

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


def _quality_done_text(requested: str, used: str, failures: list[str] | None = None) -> str:
    """Completion text, listing any failed attempts before the fallback that succeeded."""
    text = (
        t("applemusic.done")
        if used == requested
        else t("applemusic.quality_used", quality=used.upper())
    )
    if failures:
        notes = "\n".join(f"{sym.WARNING} {note}" for note in failures)
        text = f"{text}\n{notes}"
    return text


async def _download_apple_track(ctx, track, quality: str, header: str, chat_jid: str, msg_id: str):
    """
    Download one Apple Music track at the given quality, editing the message at
    msg_id with progress along the way. Returns (filepath, quality_actually_used,
    failures) — failures lists any earlier fallback attempts that failed first.

    "standard" uses the existing byte-progress download path unchanged; "alac"/
    "atmos" go through amdl_client's job-polling/decrypt path (with its own
    atmos->alac->standard fallback), reporting status text instead of bytes.
    """
    last_edit = [0.0]
    loop = asyncio.get_running_loop()

    if quality == "standard":
        dlink = await applemusic_client.get_download_link(track)

        def _on_progress(downloaded: int, total: int):
            now = time.time()
            if now - last_edit[0] < 3:
                return
            last_edit[0] = now
            progress_text = build_progress_text(header, downloaded, total)
            asyncio.run_coroutine_threadsafe(
                ctx.bot.edit_message(chat_jid, msg_id, progress_text),
                loop,
            )

        safe_name = re.sub(r"[^\w\s-]", "", track.name)[:50] or "track"
        filepath = await applemusic_client.download_track(dlink, f"am_{safe_name}", _on_progress)
        return filepath, "standard", []

    def _on_status(status: str):
        now = time.time()
        if now - last_edit[0] < 3:
            return
        last_edit[0] = now
        asyncio.run_coroutine_threadsafe(
            ctx.bot.edit_message(chat_jid, msg_id, f"{header}\n{sym.LOADING} {status}"),
            loop,
        )

    return await amdl_client.download_with_fallback(track.raw, quality, _on_status)


async def _handle_applemusic_quality(ctx, pending, stanza_id, quality):
    """Handle a quality-picker reply: fetch info from the chosen backend, then
    either download directly (single track) or show the track list (album).

    No placeholder "fetching..." message is sent up front — only the ⏳
    reaction — so a single track/album ends up with exactly one bot message
    (the download progress, or the track-list selection), matching the
    /dl flow instead of stacking a redundant status message before it.
    """
    pending_downloads.remove(stanza_id)
    await ctx.bot.send_reaction(ctx.msg, "⏳")

    try:
        if quality == "standard":
            info = await applemusic_client.fetch_info(pending.url)
            tracks = info.tracks
        else:
            album_data = await amdl_client.fetch_album_data(pending.url)
            if not album_data or not album_data.get("tracks"):
                raise AmDlError("Failed to fetch album data")
            tracks = [raw_track_to_apple_music_track(raw) for raw in album_data["tracks"] if raw]
    except (AppleMusicError, AmDlError) as e:
        await ctx.bot.send_reaction(ctx.msg, "❌")
        await ctx.bot.reply(ctx.msg, t_error("applemusic.failed", error=str(e)))
        return

    if not tracks:
        await ctx.bot.send_reaction(ctx.msg, "❌")
        await ctx.bot.reply(
            ctx.msg,
            f"{sym.WARNING} {t('applemusic.no_results', query=pending.url)}",
        )
        return

    if len(tracks) == 1:
        track = tracks[0]
        header = f"{sym.MUSIC} *{track.name}*\n{sym.ARROW} {track.artist}"
        if track.album:
            header += f" {sym.BULLET} {track.album}"
        header += "\n"

        progress_msg = await ctx.bot.reply(
            ctx.msg,
            f"{header}\n{sym.LOADING} {t('applemusic.fetching_link')}",
        )

        try:
            filepath, used, failures = await _download_apple_track(
                ctx, track, quality, header, ctx.msg.chat_jid, progress_msg.ID
            )

            await ctx.bot.edit_message(
                ctx.msg.chat_jid,
                progress_msg.ID,
                build_complete_bar(header, t("applemusic.sending")),
            )

            await ctx.bot.send_media(ctx.msg.chat_jid, "audio", str(filepath), quoted=ctx.msg.event)

            applemusic_client.cleanup(filepath)
            await ctx.bot.edit_message(
                ctx.msg.chat_jid,
                progress_msg.ID,
                build_complete_bar(header, _quality_done_text(quality, used, failures)),
            )
            await ctx.bot.send_reaction(ctx.msg, "✅")
        except (AppleMusicError, AmDlError) as e:
            await ctx.bot.send_reaction(ctx.msg, "❌")
            await ctx.bot.reply(ctx.msg, t_error("applemusic.failed", error=str(e)))
        except Exception as e:
            await ctx.bot.send_reaction(ctx.msg, "❌")
            await report_error(ctx.bot, ctx.msg, "applemusic", e)
        return

    await ctx.bot.send_reaction(ctx.msg, "")

    album_like = SimpleNamespace(
        album=tracks[0].album, artist=tracks[0].artist, count=len(tracks), tracks=tracks
    )

    response = await send_selection(
        ctx.bot,
        ctx.msg,
        fallback_text=build_album_text(album_like),
        sections=build_track_sections(tracks),
        header=build_album_header(album_like),
        menu_title="Choose a track",
        card_title=f"{sym.MUSIC} {album_like.album}",
        allow_all=True,
    )

    pending_downloads.add(
        response.ID,
        PendingAppleMusic(
            tracks=tracks,
            album_name=album_like.album,
            sender_jid=pending.sender_jid,
            chat_jid=pending.chat_jid,
            quality=quality,
        ),
    )


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
        filepath, used, failures = await _download_apple_track(
            ctx, selected, pending.quality, header, ctx.msg.chat_jid, progress_msg.ID
        )

        await ctx.bot.edit_message(
            ctx.msg.chat_jid,
            progress_msg.ID,
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
            progress_msg.ID,
            build_complete_bar(header, _quality_done_text(pending.quality, used, failures)),
        )
        await ctx.bot.send_reaction(ctx.msg, "✅")

    except (AppleMusicError, AmDlError) as e:
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

            filepath, _used, _failures = await _download_apple_track(
                ctx,
                track,
                pending.quality,
                f"{album_header}{sym.BULLET} {i}/{total}\n{track_header}",
                ctx.msg.chat_jid,
                progress_msg.ID,
            )

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
