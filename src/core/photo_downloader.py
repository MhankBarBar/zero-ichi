"""Photo downloader powered by gallery-dl with WEBP conversion support."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

import httpx
from PIL import Image

from core import symbols as sym
from core.constants import BASE_DIR, DATA_DIR
from core.logger import log_debug, log_warning
from core.runtime_config import runtime_config

if TYPE_CHECKING:
    from core.client import BotClient

IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
    "gif",
    "bmp",
    "tif",
    "tiff",
    "avif",
}


class PhotoDownloadError(Exception):
    """Raised when photo extraction/download fails."""


@dataclass
class PhotoItem:
    """A single prepared media payload for sending."""

    payload: str | bytes
    source_url: str
    converted_from_webp: bool = False


@dataclass
class PhotoResult:
    """Prepared photo download result."""

    items: list[PhotoItem]
    source_url: str
    total_urls: int
    converted_count: int
    description: str = ""
    username: str = ""
    likes: int | None = None


def _normalize_text(value: str) -> str:
    """Normalize text for captions/logs by collapsing whitespace."""
    return " ".join((value or "").strip().split())


def _truncate_text(value: str, max_len: int) -> str:
    """Truncate text to max length with ellipsis."""
    if len(value) <= max_len:
        return value
    return f"{value[: max_len - 1].rstrip()}…"


def build_photo_caption(
    result: PhotoResult,
    *,
    title_fallback: str,
    likes_label: str,
    images_label: str,
    unknown_user: str,
) -> str:
    """Build downloader-style caption with description, username, and likes."""
    count = len(result.items)
    title = _normalize_text(result.description) or title_fallback
    title = _truncate_text(title, 120)

    username = _normalize_text(result.username) or unknown_user
    user_display = f"@{username}" if username != unknown_user else username

    details = [user_display]
    if isinstance(result.likes, int):
        details.append(f"{result.likes:,} {likes_label}")
    details.append(f"{count} {images_label}")
    separator = f" {sym.BULLET} "

    return f"{sym.IMAGE} *{title}*\n{sym.ARROW} {separator.join(details)}"


def _extract_extension(url: str) -> str:
    """Extract lowercase extension from URL path."""
    try:
        path = urlparse(url).path or ""
        if "." not in path:
            return ""
        return path.rsplit(".", 1)[-1].lower().strip()
    except Exception:
        return ""


def _is_image_url(url: str) -> bool:
    """Best-effort image URL detection."""
    ext = _extract_extension(url)
    if ext in IMAGE_EXTENSIONS:
        return True

    try:
        query = parse_qs(urlparse(url).query)
        for values in query.values():
            for value in values:
                v = value.lower()
                if any(v.endswith(f".{e}") for e in IMAGE_EXTENSIONS):
                    return True
    except Exception:
        pass

    return False


def _is_image_entry(url: str, metadata: dict) -> bool:
    """Determine if gallery-dl JSON event represents an image file."""
    ext = str(metadata.get("extension", "")).lower().strip()
    if ext in IMAGE_EXTENSIONS:
        return True
    return _is_image_url(url)


class PhotoDownloader:
    """Extract image URLs with gallery-dl and prepare send-ready payloads."""

    def _gallery_dl_cmd(self) -> list[str]:
        """Resolve gallery-dl command (binary or python module)."""
        if shutil.which("gallery-dl"):
            return ["gallery-dl"]
        return [sys.executable, "-m", "gallery_dl"]

    @staticmethod
    def _resolve_path(value: str) -> str:
        """Resolve relative paths from project root."""
        expanded = os.path.expandvars(os.path.expanduser(value))
        path = Path(expanded)
        if not path.is_absolute():
            path = BASE_DIR / path
        return str(path)

    @staticmethod
    def _build_inline_config(raw_config: dict, base_config_file: str) -> dict:
        """Build inline gallery-dl config object with optional subconfigs."""
        inline_config = dict(raw_config)

        if base_config_file:
            subconfigs_raw = inline_config.get("subconfigs")
            subconfigs: list[str] = []
            if isinstance(subconfigs_raw, list):
                subconfigs = [str(item) for item in subconfigs_raw if str(item).strip()]
            elif isinstance(subconfigs_raw, str) and subconfigs_raw.strip():
                subconfigs = [subconfigs_raw.strip()]

            subconfigs = [base_config_file, *subconfigs]
            inline_config["subconfigs"] = subconfigs

        return inline_config

    @staticmethod
    def _write_temp_config(config_obj: dict) -> str:
        """Write gallery-dl config object into a temporary JSON file."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        fd, path = tempfile.mkstemp(prefix="gdl_cfg_", suffix=".json", dir=str(DATA_DIR))
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(config_obj, f, ensure_ascii=False, indent=2)
        return path

    def _gallery_dl_options(self) -> tuple[list[str], list[str]]:
        """Build gallery-dl options from runtime config and env overrides."""
        cfg = runtime_config.get_nested("downloader", "gallery_dl", default={})
        if not isinstance(cfg, dict):
            cfg = {}

        config_file = os.getenv("GALLERY_DL_CONFIG_FILE") or str(cfg.get("config_file", "") or "")
        cookies_file = os.getenv("GALLERY_DL_COOKIES_FILE") or str(
            cfg.get("cookies_file", "") or ""
        )
        cookies_from_browser = os.getenv("GALLERY_DL_COOKIES_FROM_BROWSER") or str(
            cfg.get("cookies_from_browser", "") or ""
        )
        inline_config = cfg.get("config", {})
        if not isinstance(inline_config, dict):
            inline_config = {}
        extra_args = cfg.get("extra_args", [])
        if not isinstance(extra_args, list):
            extra_args = []

        options: list[str] = []
        cleanup_paths: list[str] = []

        inline_obj = self._build_inline_config(
            inline_config,
            self._resolve_path(config_file.strip()) if config_file.strip() else "",
        )

        if inline_obj:
            inline_config_path = self._write_temp_config(inline_obj)
            options.extend(["--config", inline_config_path])
            cleanup_paths.append(inline_config_path)
        elif config_file.strip():
            options.extend(["--config", self._resolve_path(config_file.strip())])

        if cookies_file.strip():
            options.extend(["--cookies", self._resolve_path(cookies_file.strip())])
        if cookies_from_browser.strip():
            options.extend(["--cookies-from-browser", cookies_from_browser.strip()])

        for arg in extra_args:
            value = str(arg).strip()
            if value:
                options.append(value)

        return options, cleanup_paths

    async def _run_gallery_dl(self, target_url: str) -> tuple[list[tuple[str, dict]], dict]:
        """Run gallery-dl JSON mode and return URL+metadata pairs and source metadata."""
        options, cleanup_paths = self._gallery_dl_options()
        cmd = [*self._gallery_dl_cmd(), *options, "--no-download", "-j", target_url]
        log_debug(f"[PHOTO] Running: {' '.join(cmd)}")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as e:
            for path in cleanup_paths:
                try:
                    os.remove(path)
                except Exception:
                    pass
            raise PhotoDownloadError("gallery-dl is not installed") from e

        stdout, stderr = await proc.communicate()
        output = stdout.decode("utf-8", errors="replace")
        error_text = stderr.decode("utf-8", errors="replace").strip()

        for path in cleanup_paths:
            try:
                os.remove(path)
            except Exception:
                pass

        if proc.returncode != 0:
            if "No module named gallery_dl" in error_text:
                raise PhotoDownloadError("gallery-dl is not installed")
            raise PhotoDownloadError(error_text or "gallery-dl failed to extract URLs")

        entries: list = []
        source_meta: dict = {}
        try:
            parsed = json.loads(output)
            if isinstance(parsed, list):
                entries = parsed
        except Exception:
            for line in output.splitlines():
                value = line.strip()
                if not value:
                    continue
                try:
                    item = json.loads(value)
                except Exception:
                    continue
                entries.append(item)

        media_entries: list[tuple[str, dict]] = []

        for entry in entries:
            if not isinstance(entry, list) or len(entry) < 2:
                continue

            if isinstance(entry[1], str):
                meta = entry[2] if len(entry) >= 3 and isinstance(entry[2], dict) else {}
                media_entries.append((entry[1], meta))
                if not source_meta and isinstance(meta, dict):
                    source_meta = dict(meta)
                continue

            if not source_meta and isinstance(entry[1], dict):
                source_meta = dict(entry[1])

        return media_entries, source_meta

    async def _is_webp_response(self, url: str) -> bool:
        """Check if source resolves to WEBP based on URL or content-type."""
        if _extract_extension(url) == "webp":
            return True

        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                head = await client.head(url)
                content_type = str(head.headers.get("content-type", "")).lower()
                if "image/webp" in content_type:
                    return True
        except Exception:
            return False

        return False

    async def _download_bytes(self, url: str) -> bytes:
        """Download remote media bytes."""
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    @staticmethod
    def _convert_webp_to_png(data: bytes) -> bytes:
        """Convert WEBP bytes into PNG bytes."""
        with Image.open(BytesIO(data)) as image:
            out = BytesIO()
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA")
            image.save(out, format="PNG")
            return out.getvalue()

    async def _prepare_item(self, media_url: str, metadata: dict | None = None) -> PhotoItem:
        """Prepare one media item, converting WEBP when needed."""
        ext = ""
        if isinstance(metadata, dict):
            ext = str(metadata.get("extension", "")).lower().strip()

        is_webp = ext == "webp" or await self._is_webp_response(media_url)
        if not is_webp:
            return PhotoItem(payload=media_url, source_url=media_url, converted_from_webp=False)

        data = await self._download_bytes(media_url)
        converted = await asyncio.to_thread(self._convert_webp_to_png, data)
        return PhotoItem(payload=converted, source_url=media_url, converted_from_webp=True)

    async def fetch(self, source_url: str, max_items: int = 20) -> PhotoResult:
        """Extract and prepare media payloads from a social/photo URL."""
        max_items = max(1, min(int(max_items), 100))
        media_entries, source_meta = await self._run_gallery_dl(source_url)
        image_entries = [(u, m) for u, m in media_entries if _is_image_entry(u, m)]

        if not image_entries:
            raise PhotoDownloadError("No images found")

        selected = image_entries[:max_items]
        items: list[PhotoItem] = []
        converted = 0

        description = _normalize_text(str(source_meta.get("description", "")))
        username = _normalize_text(str(source_meta.get("username", "")))
        likes_raw = source_meta.get("likes")
        likes: int | None = None
        if isinstance(likes_raw, int):
            likes = likes_raw
        elif isinstance(likes_raw, str) and likes_raw.isdigit():
            likes = int(likes_raw)

        if not description or not username or likes is None:
            for _url, meta in selected:
                if not isinstance(meta, dict):
                    continue
                if not description:
                    description = _normalize_text(str(meta.get("description", "")))
                if not username:
                    username = _normalize_text(str(meta.get("username", "")))
                if likes is None:
                    value = meta.get("likes")
                    if isinstance(value, int):
                        likes = value
                    elif isinstance(value, str) and value.isdigit():
                        likes = int(value)

        for media_url, metadata in selected:
            try:
                item = await self._prepare_item(media_url, metadata)
                if item.converted_from_webp:
                    converted += 1
                items.append(item)
            except Exception as e:
                log_warning(f"[PHOTO] Failed media item: {media_url} ({e})")

        if not items:
            raise PhotoDownloadError("No sendable images found")

        log_debug(
            f"[PHOTO] Prepared {len(items)}/{len(image_entries)} image(s), converted webp={converted}"
        )
        return PhotoResult(
            items=items,
            source_url=source_url,
            total_urls=len(image_entries),
            converted_count=converted,
            description=description,
            username=username,
            likes=likes,
        )


def chunk_photo_items(items: list[PhotoItem], size: int) -> list[list[PhotoItem]]:
    """Chunk photo items into fixed-size batches."""
    chunk_size = max(1, size)
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


async def send_photo_items(
    bot: BotClient,
    chat_jid: str,
    items: list[PhotoItem],
    caption: str = "",
    quoted=None,
    max_images_per_album: int = 10,
) -> int:
    """Send photo items using album when possible; fallback to single images."""
    if not items:
        return 0

    max_images_per_album = max(2, min(int(max_images_per_album), 30))
    sent = 0

    if len(items) == 1:
        await bot.send_image(chat_jid, items[0].payload, caption=caption, quoted=quoted)
        return 1

    batches = chunk_photo_items(items, max_images_per_album)
    for idx, batch in enumerate(batches):
        payloads = [item.payload for item in batch]
        batch_caption = caption if idx == 0 else ""

        if len(payloads) < 2:
            await bot.send_image(chat_jid, payloads[0], caption=batch_caption, quoted=quoted)
            sent += 1
            continue

        try:
            await bot.send_album(chat_jid, payloads, caption=batch_caption, quoted=quoted)
            sent += len(payloads)
        except Exception as e:
            log_warning(f"[PHOTO] Album send failed, fallback to single images: {e}")
            for payload_idx, payload in enumerate(payloads):
                single_caption = batch_caption if payload_idx == 0 else ""
                await bot.send_image(chat_jid, payload, caption=single_caption, quoted=quoted)
                sent += 1

    return sent


photo_downloader = PhotoDownloader()
