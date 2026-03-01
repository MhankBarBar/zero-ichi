"""Auto-download middleware — detect links and auto-run downloader."""

from __future__ import annotations

import re
import time

from core.applemusic import AppleMusicError, applemusic_client
from core.command import command_loader
from core.downloader import DownloadError, downloader
from core.event_bus import event_bus
from core.i18n import t
from core.logger import log_info, log_warning
from core.photo_downloader import (
    PhotoDownloadError,
    build_photo_caption,
    photo_downloader,
    send_photo_items,
)
from core.runtime_config import runtime_config

URL_PATTERN = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE)
APPLE_MUSIC_URL_PATTERN = re.compile(
    r"https?://(?:music\.apple\.com|embed\.music\.apple\.com)/", re.IGNORECASE
)
_cooldown_map: dict[str, float] = {}


def _pick_format(info, mode: str):
    videos = [f for f in info.formats if f.type == "video"]
    audios = [f for f in info.formats if f.type == "audio"]

    if mode == "audio":
        return audios[0] if audios else (videos[0] if videos else None)
    if mode == "video":
        return videos[0] if videos else (audios[0] if audios else None)

    with_audio = [f for f in videos if f.has_audio]
    if with_audio:
        return with_audio[0]
    if videos:
        return videos[0]
    return audios[0] if audios else None


def _safe_apple_filename(name: str) -> str:
    """Build a safe filename for Apple Music track downloads."""
    safe = re.sub(r"[^\w\s-]", "", name).strip()[:50] or "track"
    return f"am_{safe.replace(' ', '_')}"


async def _handle_apple_music_url(ctx, url: str) -> bool:
    """Handle Apple Music URL using Apple downloader pipeline."""
    info = await applemusic_client.fetch_info(url)
    if not info.tracks:
        return False

    track = info.tracks[0]
    dlink = await applemusic_client.get_download_link(track)
    filepath = await applemusic_client.download_track(dlink, _safe_apple_filename(track.name))
    try:
        await ctx.bot.send_media(
            ctx.msg.chat_jid,
            "audio",
            str(filepath),
            caption=t("autodl.apple_caption", title=track.name, artist=track.artist),
            quoted=ctx.msg.event,
        )
        return True
    finally:
        applemusic_client.cleanup(filepath)


async def _handle_photo_url(ctx, url: str, cfg: dict) -> bool:
    """Handle photo URL using gallery-dl + album sending."""
    photo_cfg = cfg.get("photo", {})
    if not isinstance(photo_cfg, dict):
        photo_cfg = {}

    max_per_link = max(1, min(int(photo_cfg.get("max_images_per_link", 20) or 20), 100))
    max_per_album = max(2, min(int(photo_cfg.get("max_images_per_album", 10) or 10), 30))

    result = await photo_downloader.fetch(url, max_items=max_per_link)
    caption = build_photo_caption(
        result,
        title_fallback=t("autodl.photo_title"),
        likes_label=t("photo.likes_label"),
        images_label=t("photo.images_label"),
        unknown_user=t("photo.unknown_user"),
    )
    sent = await send_photo_items(
        ctx.bot,
        ctx.msg.chat_jid,
        result.items,
        caption=caption,
        quoted=ctx.msg.event,
        max_images_per_album=max_per_album,
    )
    return sent > 0


async def _try_photo_fallback(ctx, url: str, cfg: dict, reason: str) -> bool:
    """Try photo pipeline as fallback for auto mode links."""
    try:
        sent = await _handle_photo_url(ctx, url, cfg)
        if sent:
            log_info(f"[AUTO-DL] Sent photo media fallback for {url} ({reason})")
            return True
    except PhotoDownloadError as e:
        log_warning(f"[AUTO-DL] Photo fallback skipped for {url}: {e}")
    except Exception as e:
        log_warning(f"[AUTO-DL] Photo fallback failed for {url}: {e}")
    return False


async def auto_download_middleware(ctx, next):
    """Auto-download supported media links when enabled."""
    cfg = runtime_config.get_nested("downloader", "auto_link_download", default={})
    if not isinstance(cfg, dict) or not cfg.get("enabled", False):
        await next()
        return

    if ctx.msg.is_from_me or not ctx.msg.text:
        await next()
        return

    if cfg.get("group_only", True) and not ctx.msg.is_group:
        await next()
        return

    command_name, _raw, _args = command_loader.parse_command(ctx.msg.text)
    if command_name:
        await next()
        return

    links = URL_PATTERN.findall(ctx.msg.text or "")
    if not links:
        await next()
        return

    max_links = max(1, int(cfg.get("max_links_per_message", 1) or 1))
    links = links[:max_links]
    mode = str(cfg.get("mode", "auto")).lower()
    if mode not in {"auto", "audio", "video", "photo"}:
        mode = "auto"

    cooldown = max(0, int(cfg.get("cooldown_seconds", 30) or 0))
    now = time.time()
    cooldown_key = f"{ctx.msg.chat_jid}:{ctx.msg.sender_jid}"
    if cooldown > 0 and now - _cooldown_map.get(cooldown_key, 0) < cooldown:
        await next()
        return

    sent_any = False
    for url in links:
        if mode == "photo":
            try:
                sent = await _handle_photo_url(ctx, url, cfg)
                if sent:
                    sent_any = True
                    log_info(f"[AUTO-DL] Sent photo media for {url}")
                continue
            except PhotoDownloadError as e:
                log_warning(f"[AUTO-DL] Photo extraction error for {url}: {e}")
                continue
            except Exception as e:
                log_warning(f"[AUTO-DL] Photo handling failed for {url}: {e}")
                continue

        if APPLE_MUSIC_URL_PATTERN.search(url):
            try:
                sent = await _handle_apple_music_url(ctx, url)
                if sent:
                    sent_any = True
                    log_info(f"[AUTO-DL] Sent audio (apple music) for {url}")
                continue
            except AppleMusicError as e:
                log_warning(f"[AUTO-DL] Apple Music error for {url}: {e}")
                continue
            except Exception as e:
                log_warning(f"[AUTO-DL] Apple Music failed for {url}: {e}")
                continue

        try:
            info = await downloader.get_info(url)
            fmt = _pick_format(info, mode)
            if not fmt:
                if mode == "auto":
                    if await _try_photo_fallback(ctx, url, cfg, "no-matching-format"):
                        sent_any = True
                continue

            filepath = await downloader.download_format(
                info.url,
                fmt.format_id,
                merge_audio=fmt.type == "video" and not fmt.has_audio,
                is_audio=fmt.type == "audio",
                chat_jid=ctx.msg.chat_jid,
                sender_jid=ctx.msg.sender_jid,
            )

            media_type = "audio" if fmt.type == "audio" else "video"
            await ctx.bot.send_media(
                ctx.msg.chat_jid,
                media_type,
                str(filepath),
                caption=t("autodl.caption", title=info.title),
                quoted=ctx.msg.event,
            )
            downloader.cleanup(filepath)
            sent_any = True
            log_info(f"[AUTO-DL] Sent {media_type} for {url}")
        except DownloadError as e:
            if mode == "auto":
                if await _try_photo_fallback(ctx, url, cfg, f"downloader-error: {e}"):
                    sent_any = True
                    continue
            log_warning(f"[AUTO-DL] Download error for {url}: {e}")
        except Exception as e:
            log_warning(f"[AUTO-DL] Failed for {url}: {e}")

    if sent_any:
        _cooldown_map[cooldown_key] = now
        await event_bus.emit(
            "auto_download",
            {
                "group_id": ctx.msg.chat_jid,
                "sender": ctx.msg.sender_jid,
                "links": len(links),
                "mode": mode,
            },
        )
        return

    await next()
