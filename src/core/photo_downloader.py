"""Photo downloader powered by gallery-dl with WEBP conversion support."""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, cast
from urllib.parse import parse_qs, urlparse

import httpx
from PIL import Image

from core import symbols as sym
from core.constants import (
    BASE_DIR,
    DATA_DIR,
    PHOTO_AUTH_REQUIRED_HINTS,
    PHOTO_DEFAULT_HTTP_HEADERS,
    PHOTO_DESCRIPTION_PATHS,
    PHOTO_HANDLE_PATTERN,
    PHOTO_IMAGE_EXTENSIONS,
    PHOTO_LIKES_PATHS,
    PHOTO_USERNAME_PATHS,
)
from core.logger import log_debug, log_warning
from core.runtime_config import runtime_config

if TYPE_CHECKING:
    from core.client import BotClient


class PhotoDownloadError(Exception):
    """Raised when photo extraction/download fails."""


@dataclass
class PhotoItem:
    """A single prepared media payload for sending."""

    payload: str | bytes
    source_url: str
    referer_url: str = ""
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


HANDLE_PATTERN = re.compile(PHOTO_HANDLE_PATTERN)


def _normalize_text(value: str) -> str:
    """Normalize text for captions/logs by collapsing whitespace."""
    return " ".join((value or "").strip().split())


def _truncate_text(value: str, max_len: int) -> str:
    """Truncate text to max length with ellipsis."""
    if len(value) <= max_len:
        return value
    return f"{value[: max_len - 1].rstrip()}…"


def _meta_get(meta: dict, path: str):
    """Get nested metadata value from dotted path."""
    value = meta
    for part in path.split("."):
        if isinstance(value, dict):
            value = value.get(part)
            continue
        if isinstance(value, list) and part.isdigit():
            index = int(part)
            if 0 <= index < len(value):
                value = value[index]
                continue
        return None
    return value


def _extract_text_value(value) -> str:
    """Convert metadata value to normalized non-empty text when possible."""
    if isinstance(value, str):
        return _normalize_text(value)
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        for item in value:
            text = _extract_text_value(item)
            if text:
                return text
    return ""


def _extract_first_text(candidates: list[dict], paths: tuple[str, ...]) -> str:
    """Extract first available text from metadata candidates."""
    for meta in candidates:
        if not isinstance(meta, dict):
            continue
        for path in paths:
            text = _extract_text_value(_meta_get(meta, path))
            if text:
                return text
    return ""


def _extract_first_int(candidates: list[dict], paths: tuple[str, ...]) -> int | None:
    """Extract first available integer from metadata candidates."""
    for meta in candidates:
        if not isinstance(meta, dict):
            continue
        for path in paths:
            value = _meta_get(meta, path)
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                return int(value)
            if isinstance(value, str):
                digits = re.sub(r"[^0-9]", "", value)
                if digits:
                    return int(digits)
    return None


def _format_user_display(username: str, unknown_user: str) -> str:
    """Format username display with @ only for handle-like values."""
    value = _normalize_text(username) or unknown_user
    if value == unknown_user:
        return value
    if value.startswith("@"):
        return value
    if HANDLE_PATTERN.match(value):
        return f"@{value}"
    return value


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

    user_display = _format_user_display(result.username, unknown_user)

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
    if ext in PHOTO_IMAGE_EXTENSIONS:
        return True

    try:
        query = parse_qs(urlparse(url).query)
        for values in query.values():
            for value in values:
                v = value.lower()
                if any(v.endswith(f".{e}") for e in PHOTO_IMAGE_EXTENSIONS):
                    return True
    except Exception:
        pass

    return False


def _is_image_entry(url: str, metadata: dict) -> bool:
    """Determine if gallery-dl JSON event represents an image file."""
    ext = str(metadata.get("extension", "")).lower().strip()
    if ext in PHOTO_IMAGE_EXTENSIONS:
        return True
    return _is_image_url(url)


def _make_http_headers(referer: str = "") -> dict[str, str]:
    """Build request headers for image fetches."""
    headers = dict(PHOTO_DEFAULT_HTTP_HEADERS)
    if referer:
        headers["Referer"] = referer
    return headers


def _looks_like_html(data: bytes) -> bool:
    """Best-effort HTML payload detection."""
    probe = data[:256].lstrip().lower()
    return probe.startswith(b"<!doctype html") or probe.startswith(b"<html")


def _is_valid_image_bytes(data: bytes) -> bool:
    """Validate image bytes using Pillow parser."""
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
        return True
    except Exception:
        return False


def is_auth_required_error(error_text: str) -> bool:
    """Return True when extraction failure indicates login is required."""
    text = (error_text or "").lower()
    return any(hint in text for hint in PHOTO_AUTH_REQUIRED_HINTS)


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
        extraction_error = ""

        for entry in entries:
            if not isinstance(entry, list) or len(entry) < 2:
                continue

            if entry[0] == -1 and isinstance(entry[1], dict):
                message = str(entry[1].get("message", "")).strip()
                if message:
                    extraction_error = message
                continue

            if isinstance(entry[1], str):
                meta = entry[2] if len(entry) >= 3 and isinstance(entry[2], dict) else {}
                media_entries.append((entry[1], meta))
                if not source_meta and isinstance(meta, dict):
                    source_meta = dict(meta)
                continue

            if not source_meta and isinstance(entry[1], dict):
                source_meta = dict(entry[1])

        if not media_entries and extraction_error:
            raise PhotoDownloadError(extraction_error)

        return media_entries, source_meta

    @staticmethod
    def _should_force_gallery_download(source_url: str, source_meta: dict) -> bool:
        """Return True when URL payload mode is known to be unreliable."""
        try:
            host = (urlparse(source_url).hostname or "").lower()
        except Exception:
            host = ""

        category = str(source_meta.get("category", "")).lower().strip()

        if category == "danbooru":
            return True
        if host.endswith("donmai.us"):
            return True
        return False

    async def _download_via_gallery_dl(
        self, source_url: str, max_items: int
    ) -> tuple[list[PhotoItem], int]:
        """Download media files with gallery-dl and return send-ready items."""
        options, cleanup_paths = self._gallery_dl_options()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        temp_dir = tempfile.mkdtemp(prefix="gdl_media_", dir=str(DATA_DIR))

        cmd = [
            *self._gallery_dl_cmd(),
            *options,
            "--range",
            f"1-{max_items}",
            "-D",
            temp_dir,
            source_url,
        ]
        log_debug(f"[PHOTO] Download fallback: {' '.join(cmd)}")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await proc.communicate()
            error_text = stderr.decode("utf-8", errors="replace").strip()

            if proc.returncode != 0:
                raise PhotoDownloadError(error_text or "gallery-dl download fallback failed")

            allowed = {f".{ext}" for ext in PHOTO_IMAGE_EXTENSIONS}
            file_paths = [
                p
                for p in sorted(Path(temp_dir).rglob("*"))
                if p.is_file() and p.suffix.lower() in allowed
            ]

            items: list[PhotoItem] = []
            converted = 0
            for path in file_paths[:max_items]:
                data = path.read_bytes()
                if path.suffix.lower() == ".webp":
                    data = await asyncio.to_thread(self._convert_webp_to_png, data)
                    converted += 1
                items.append(
                    PhotoItem(
                        payload=data,
                        source_url=source_url,
                        referer_url=source_url,
                        converted_from_webp=path.suffix.lower() == ".webp",
                    )
                )

            return items, converted
        finally:
            for path in cleanup_paths:
                try:
                    os.remove(path)
                except Exception:
                    pass
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def _is_webp_response(self, url: str, referer: str = "") -> bool:
        """Check if source resolves to WEBP based on URL or content-type."""
        if _extract_extension(url) == "webp":
            return True

        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                head = await client.head(url, headers=_make_http_headers(referer))
                content_type = str(head.headers.get("content-type", "")).lower()
                if "image/webp" in content_type:
                    return True
        except Exception:
            return False

        return False

    async def _download_bytes(self, url: str, referer: str = "") -> bytes:
        """Download remote media bytes."""
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            response = await client.get(url, headers=_make_http_headers(referer))
            response.raise_for_status()
            content_type = str(response.headers.get("content-type", "")).lower()
            data = response.content

            if "image/" not in content_type and _looks_like_html(data):
                raise PhotoDownloadError("Source returned HTML instead of image")

            return data

    @staticmethod
    def _convert_webp_to_png(data: bytes) -> bytes:
        """Convert WEBP bytes into PNG bytes."""
        with Image.open(BytesIO(data)) as image:
            out = BytesIO()
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA")
            image.save(out, format="PNG")
            return out.getvalue()

    async def _prepare_item(
        self,
        media_url: str,
        referer_url: str,
        metadata: dict | None = None,
    ) -> PhotoItem:
        """Prepare one media item, converting WEBP when needed."""
        ext = ""
        if isinstance(metadata, dict):
            ext = str(metadata.get("extension", "")).lower().strip()

        is_webp = ext == "webp" or await self._is_webp_response(media_url, referer=referer_url)
        if not is_webp:
            return PhotoItem(
                payload=media_url,
                source_url=media_url,
                referer_url=referer_url,
                converted_from_webp=False,
            )

        data = await self._download_bytes(media_url, referer=referer_url)
        converted = await asyncio.to_thread(self._convert_webp_to_png, data)
        return PhotoItem(
            payload=converted,
            source_url=media_url,
            referer_url=referer_url,
            converted_from_webp=True,
        )

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

        meta_candidates = [source_meta] + [
            meta for _url, meta in selected if isinstance(meta, dict)
        ]
        description = _extract_first_text(meta_candidates, PHOTO_DESCRIPTION_PATHS)
        username = _extract_first_text(meta_candidates, PHOTO_USERNAME_PATHS)
        likes = _extract_first_int(meta_candidates, PHOTO_LIKES_PATHS)

        if self._should_force_gallery_download(source_url, source_meta):
            try:
                items, converted = await self._download_via_gallery_dl(source_url, max_items)
                if not items:
                    raise PhotoDownloadError("No sendable images found")
                log_debug(
                    "[PHOTO] Using gallery-dl download fallback "
                    f"for {source_url} -> {len(items)} item(s)"
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
            except Exception as e:
                log_warning(f"[PHOTO] gallery-dl download fallback failed: {e}")

        for media_url, metadata in selected:
            try:
                item = await self._prepare_item(media_url, source_url, metadata)
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


async def _materialize_url_payload(url: str, referer: str = "") -> bytes:
    """Download URL payload into verified image bytes."""
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        response = await client.get(url, headers=_make_http_headers(referer))
        response.raise_for_status()
        content_type = str(response.headers.get("content-type", "")).lower()
        data = response.content

    if "image/" in content_type:
        return data

    if _looks_like_html(data):
        raise PhotoDownloadError("Source returned HTML instead of image")

    is_valid = await asyncio.to_thread(_is_valid_image_bytes, data)
    if not is_valid:
        raise PhotoDownloadError("Source bytes are not a valid image")

    return data


async def _send_single_item(
    bot: BotClient,
    chat_jid: str,
    item: PhotoItem,
    caption: str,
    quoted,
) -> bool:
    """Send one photo item with URL-to-bytes fallback."""
    try:
        await bot.send_image(chat_jid, item.payload, caption=caption, quoted=quoted)
        return True
    except Exception as e:
        if not isinstance(item.payload, str):
            log_warning(f"[PHOTO] Single image send failed: {e}")
            return False

        try:
            materialized = await _materialize_url_payload(item.payload, referer=item.referer_url)
            await bot.send_image(chat_jid, materialized, caption=caption, quoted=quoted)
            return True
        except Exception as fallback_error:
            log_warning(f"[PHOTO] Single image fallback failed: {fallback_error}")
            return False


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
        ok = await _send_single_item(bot, chat_jid, items[0], caption, quoted)
        return 1 if ok else 0

    batches = chunk_photo_items(items, max_images_per_album)
    for idx, batch in enumerate(batches):
        payloads = [item.payload for item in batch]
        batch_caption = caption if idx == 0 else ""

        if len(payloads) < 2:
            ok = await _send_single_item(bot, chat_jid, batch[0], batch_caption, quoted)
            if ok:
                sent += 1
            continue

        try:
            await bot.send_album(chat_jid, payloads, caption=batch_caption, quoted=quoted)
            sent += len(payloads)
        except Exception as e:
            log_warning(f"[PHOTO] Album send failed, fallback to single images: {e}")

            materialized_payloads: list[str | bytes] = []
            can_retry_album = True
            for item in batch:
                if isinstance(item.payload, bytes):
                    materialized_payloads.append(item.payload)
                    continue
                try:
                    payload_bytes = await _materialize_url_payload(
                        item.payload,
                        referer=item.referer_url,
                    )
                    materialized_payloads.append(payload_bytes)
                except Exception as materialize_error:
                    can_retry_album = False
                    log_warning(f"[PHOTO] URL materialize failed: {materialize_error}")
                    break

            if can_retry_album and len(materialized_payloads) >= 2:
                try:
                    await bot.send_album(
                        chat_jid,
                        cast(list[str | bytes], materialized_payloads),
                        caption=batch_caption,
                        quoted=quoted,
                    )
                    sent += len(materialized_payloads)
                    continue
                except Exception as retry_error:
                    log_warning(f"[PHOTO] Materialized album retry failed: {retry_error}")

            for payload_idx, item in enumerate(batch):
                single_caption = batch_caption if payload_idx == 0 else ""
                ok = await _send_single_item(bot, chat_jid, item, single_caption, quoted)
                if ok:
                    sent += 1

    return sent


photo_downloader = PhotoDownloader()
