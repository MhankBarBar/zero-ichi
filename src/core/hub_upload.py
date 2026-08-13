"""
Joy Hub upload helper — Telegram channel (T2).

Uploads files (e.g. ALAC/Atmos Apple Music tracks) to the Joy Hub storage
service (https://hub.mhankbarbar.dev) using the *Telegram* storage channel
so WhatsApp only ever receives a *link* instead of a huge lossless binary
that WhatsApp corrupts in transit.

Flow (live-verified 2026-08):

    POST /upload?uploadChannel=telegram&channelName=T2
        multipart file=<bytes>  +  header authCode: <code>
    -> [{"src": "/file/<id>"}]

Notes / quirks discovered live:

* The chunked API (initChunked/chunked/merge) documented in llms.txt is NOT
  implemented on the deployed workers — every init returns
  "Missing initialization parameters". Single-shot upload is the only
  working path to the Telegram channel, so large files rely on a long
  client timeout + streaming (the VPS uplink is ~1 Mbps, so a 50 MB ALAC
  track takes several minutes; progress is reported via `on_status`).
* The hub load-balances across workers with different configs; some route
  T2 to an encrypted channel that is unreliable. Single uploads to the
  plain Telegram channel work and are byte-exact (verified via GET range).
* The hub prefixes the stored id with its own unix timestamp (server-side,
  unavoidable); the multipart filename is the real filename passed by the
  caller — never an internal name with timestamps.
* Auth is a stateless ``authCode`` header on every request.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Callable

import httpx

from core.logger import log_info, log_warning

DEFAULT_HUB_URL = "https://hub.mhankbarbar.dev"
_TIMEOUT = 120.0
_UPLOAD_TIMEOUT = 1500.0  # 1 Mbps VPS: ~120 MB ≈ 16 min + server-side time
_STREAM_CHUNK = 1024 * 1024


def _hub_config() -> dict:
    """Resolve hub settings: config.json `hub` section, env fallbacks."""
    try:
        from core.runtime_config import runtime_config

        cfg = runtime_config.get_nested("hub", default={}) or {}
    except Exception:
        cfg = {}
    return {
        "url": os.getenv("HUB_URL", "") or cfg.get("url") or DEFAULT_HUB_URL,
        "auth_code": os.getenv("HUB_AUTH_CODE", "") or cfg.get("auth_code") or "",
        "channel": os.getenv("HUB_UPLOAD_CHANNEL", "") or cfg.get("channel") or "telegram",
        "channel_name": os.getenv("HUB_CHANNEL_NAME", "") or cfg.get("channel_name") or "",
    }


def sanitize_filename(name: str, max_len: int = 120) -> str:
    """Strip path-hostile characters while keeping the real name readable."""
    name = (name or "").strip()
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    if len(name) > max_len:
        base, dot, ext = name.rpartition(".")
        keep = max_len - len(ext) - 1
        name = f"{base[:keep]}.{ext}" if dot else name[:max_len]
    return name or "file"


async def upload_file(
    file_path: Path,
    real_filename: str | None = None,
    on_status: Callable[[str], None] | None = None,
) -> str:
    """Upload a file to the hub (Telegram channel) and return its full URL.

    Args:
        file_path: local file to upload.
        real_filename: multipart filename — pass the real track name
            (e.g. "Artist - Song.m4a"), never internal names with
            timestamps. Defaults to the file's own name.
        on_status: optional callback for progress text.

    Returns:
        Full URL, e.g. https://hub.mhankbarbar.dev/file/<ts>_<name>.

    Raises:
        HubUploadError: if auth fails or the upload cannot complete.
    """
    cfg = _hub_config()
    if not cfg.get("auth_code"):
        raise HubUploadError(
            "Hub auth code not configured (set config.json hub.auth_code or HUB_AUTH_CODE)"
        )

    file_path = Path(file_path)
    if not file_path.is_file():
        raise HubUploadError(f"File not found: {file_path}")

    name = sanitize_filename(real_filename or file_path.name)
    base = (cfg.get("url") or DEFAULT_HUB_URL).rstrip("/")
    url = f"{base}/upload"
    params = []
    if cfg.get("channel"):
        params.append(f"uploadChannel={cfg['channel']}")
    if cfg.get("channel_name"):
        params.append(f"channelName={cfg['channel_name']}")
    if params:
        url = f"{url}?{'&'.join(params)}"

    headers = {
        "authCode": cfg["auth_code"],
        "User-Agent": "zero-ichi/hub-upload",
    }

    if on_status:
        on_status("Uploading to hub...")

    last_err = ""
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=_UPLOAD_TIMEOUT, headers=headers) as client:
                with file_path.open("rb") as fh:
                    resp = await client.post(
                        url,
                        files={"file": (name, fh, "application/octet-stream")},
                    )
        except httpx.HTTPError as e:
            last_err = f"upload request failed: {e}"
            log_warning(f"[Hub] {last_err} (attempt {attempt + 1}/3)")
            if on_status:
                on_status(f"Upload failed, retrying ({attempt + 1}/3)...")
            continue

        if resp.status_code == 401:
            raise HubUploadError(
                "Hub upload rejected: 401 Unauthorized (bad auth code?)"
            )
        if resp.status_code != 200:
            last_err = f"hub upload failed ({resp.status_code}): {resp.text[:300]}"
            log_warning(f"[Hub] {last_err} (attempt {attempt + 1}/3)")
            if on_status:
                on_status(f"Upload failed, retrying ({attempt + 1}/3)...")
            continue

        src = _extract_src(resp.json())
        if not src:
            raise HubUploadError(f"hub upload returned no file id: {resp.text[:300]}")
        public_url = src if src.startswith("http") else f"{base}{src if src.startswith('/') else '/' + src}"
        log_info(f"[Hub] uploaded {name} -> {public_url}")
        return public_url

    raise HubUploadError(f"Hub upload failed after 3 attempts: {last_err}")


def _extract_src(payload) -> str | None:
    """Pull the first `src` (or publicUrl) from an upload response."""
    if isinstance(payload, list) and payload:
        entry = payload[0] if isinstance(payload[0], dict) else None
        if entry:
            return entry.get("src") or entry.get("publicUrl")
    if isinstance(payload, dict):
        return payload.get("src") or payload.get("publicUrl") or payload.get("url")
    return None


class HubUploadError(Exception):
    """Raised when a hub upload cannot complete."""
