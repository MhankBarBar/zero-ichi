"""
am-dl downloader API client — ALAC and Atmos quality for Apple Music.

Ported from the am-dl project (am-dl.pages.dev backend). Covers:

  - ALAC: server-side job (submit -> poll -> download already-decrypted file).
  - Atmos: client-side dual-key decryption via the `mp4decrypt` (Bento4)
    binary, requires that binary on PATH.
  - Standard (am-dl's own): HLS + single-key `mp4decrypt` decryption. Used
    only as a last-resort fallback — `core.applemusic.applemusic_client`
    (aaplmusicdownloader.com) remains the primary standard-quality backend
    since it needs no local binary.

`download_with_fallback` tries the requested quality, then falls down the
chain atmos -> alac -> standard (aaplmusicdownloader.com) -> standard
(am-dl's own HLS path), stopping at the first one that succeeds.

The site's API paths are obfuscated and rotate on every am-dl deploy, so
endpoints aren't hardcoded — `_resolve_endpoints()` mirrors am-dl's own
`_load_endpoints()`: fetch the live page, find the current JS bundle,
deobfuscate it with `npx webcrack`, and extract the current paths. Cached
to disk keyed by JS filename, refreshed only when that filename changes.
Falls back to a hardcoded snapshot if npx/webcrack or the network isn't
available.
"""

from __future__ import annotations

import asyncio
import base64
import gzip
import json
import re
import shutil
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote as urlquote
from urllib.parse import urlparse

import httpx

from core.applemusic import AppleMusicTrack, applemusic_client
from core.constants import AMDL_ENDPOINTS_CACHE_FILE, DOWNLOADS_DIR
from core.logger import log_error, log_info, log_warning

AMDL_API_BASE = "https://am-dl.pages.dev"

# JS variable name -> our internal endpoint key, mirrors am-dl's own _JS_KEY_MAP.
_JS_KEY_MAP = {
    "x7f": "album_fetch",
    "k9m": "track_details",
    "d4v": "proxy",
    "atmosKeys": "atmos_keys",
    "alacSubmit": "alac_submit",
    "alacStream": "alac_stream",
    "alacFile": "alac_file",
}

# Last-known-good snapshot, used only if live resolution fails.
_FALLBACK_ENDPOINTS = {
    "album_fetch": f"{AMDL_API_BASE}/api/197888c7",
    "track_details": f"{AMDL_API_BASE}/api/274210f5",
    "proxy": f"{AMDL_API_BASE}/api/af89167f",
    "atmos_keys": f"{AMDL_API_BASE}/api/atmos/cb55b30e",
    "alac_submit": f"{AMDL_API_BASE}/api/alac/434d3b46",
    "alac_stream": f"{AMDL_API_BASE}/api/alac/ec6d92da",
    "alac_file": f"{AMDL_API_BASE}/api/alac/b41cab17",
}

QUALITY_STANDARD = "standard"
QUALITY_ALAC = "alac"
QUALITY_ATMOS = "atmos"

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_TIMEOUT = 90

_endpoints_cache: dict[str, str] | None = None
_endpoints_lock = asyncio.Lock()


async def _resolve_endpoints() -> dict[str, str]:
    """Return the current am-dl API endpoints, resolved once per process.

    Retries transient network failures a few times; falls back to the last
    known-good endpoints from disk if the live resolution keeps failing.
    """
    global _endpoints_cache
    if _endpoints_cache is not None:
        return _endpoints_cache

    async with _endpoints_lock:
        if _endpoints_cache is not None:
            return _endpoints_cache

        last_err: str = "unknown error"
        for attempt in range(3):
            try:
                resolved = await _load_endpoints()
                _endpoints_cache = resolved
                return resolved
            except Exception as e:
                last_err = str(e)
                log_warning(f"[AMDL] endpoint resolution failed (attempt {attempt + 1}/3): {e}")
                await asyncio.sleep(1.5 * (attempt + 1))

        # Last resort: whatever is on disk, even if stale, beats a hard fail.
        try:
            if AMDL_ENDPOINTS_CACHE_FILE.exists():
                cached = json.loads(AMDL_ENDPOINTS_CACHE_FILE.read_text("utf-8"))
                if cached.get("endpoints"):
                    resolved = cached["endpoints"]
                    _endpoints_cache = resolved
                    log_warning("[AMDL] using cached endpoints after resolution failures")
                    return resolved
        except Exception:
            pass

        raise AmDlError(f"Failed to resolve am-dl endpoints: {last_err}") from None


def _reset_endpoints_cache() -> None:
    """Force the next call to re-resolve endpoints (after repeated failures)."""
    global _endpoints_cache
    _endpoints_cache = None


async def _load_endpoints() -> dict[str, str]:
    try:
        headers = {"User-Agent": DEFAULT_USER_AGENT}
        async with httpx.AsyncClient(timeout=15, headers=headers) as client:
            html = (await client.get(AMDL_API_BASE)).text
            match = re.search(r'<script[^>]+src="([^"]+\.js)"', html)
            if not match:
                return _FALLBACK_ENDPOINTS

            js_path = match.group(1).lstrip("/")
            js_filename = Path(js_path).name

            if AMDL_ENDPOINTS_CACHE_FILE.exists():
                try:
                    cached = json.loads(AMDL_ENDPOINTS_CACHE_FILE.read_text("utf-8"))
                    if cached.get("script_name") == js_filename and cached.get("endpoints"):
                        return cached["endpoints"]
                except Exception:
                    pass

            js_content = (await client.get(f"{AMDL_API_BASE}/{js_path}")).text

        if not shutil.which("npx"):
            log_info("[AMDL] npx not found, using fallback endpoints")
            return _FALLBACK_ENDPOINTS

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            js_file = tmp_path / js_filename
            js_file.write_text(js_content, encoding="utf-8")
            out_dir = tmp_path / "deobf"

            proc = await asyncio.create_subprocess_exec(
                "npx",
                "-y",
                "webcrack",
                str(js_file),
                "-o",
                str(out_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                await asyncio.wait_for(proc.communicate(), timeout=60)
            except TimeoutError:
                proc.kill()
                return _FALLBACK_ENDPOINTS

            deobf_file = out_dir / "deobfuscated.js"
            if proc.returncode != 0 or not deobf_file.exists():
                return _FALLBACK_ENDPOINTS

            content = deobf_file.read_text("utf-8")
            endpoints = _FALLBACK_ENDPOINTS.copy()
            for js_key, path in re.findall(r"(\w+)\s*:\s*[\"'](/api/[^\"']+)[\"']", content):
                internal_key = _JS_KEY_MAP.get(js_key)
                if internal_key:
                    endpoints[internal_key] = f"{AMDL_API_BASE}{path}"

            AMDL_ENDPOINTS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            AMDL_ENDPOINTS_CACHE_FILE.write_text(
                json.dumps({"script_name": js_filename, "endpoints": endpoints}, indent=2),
                encoding="utf-8",
            )
            return endpoints
    except Exception as e:
        log_error(f"[AMDL] Failed to resolve live endpoints, using fallback: {e}")
        return _FALLBACK_ENDPOINTS


class AmDlError(Exception):
    """Raised when an am-dl API call or local decrypt/tag step fails."""

    pass


def _fnv1a32(data: str) -> int:
    h = 2166136261
    for ch in data:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def _mulberry32(seed: int) -> Callable[[], float]:
    state = seed & 0xFFFFFFFF

    def _next() -> float:
        nonlocal state
        state = (state + 1831565813) & 0xFFFFFFFF
        t = state ^ (state >> 15)
        t = (t * (state | 1)) & 0xFFFFFFFF
        t ^= (t + ((t ^ (t >> 7)) * (t | 61) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return _next


def _xor_with_keystream(data: bytes, seed: int) -> bytes:
    rng = _mulberry32(seed & 0xFFFFFFFF)
    out = bytearray(len(data))
    for i in range(len(data)):
        out[i] = data[i] ^ int(rng() * 256)
    return bytes(out)


def _build_permutation(length: int, seed: int) -> list[int]:
    perm = list(range(length))
    rng = _mulberry32(seed & 0xFFFFFFFF)
    for i in range(length - 1, 0, -1):
        j = int(rng() * (i + 1))
        perm[i], perm[j] = perm[j], perm[i]
    return perm


def _unpermute(data: bytes, perm: list[int]) -> bytes:
    out = bytearray(len(data))
    for i in range(len(perm)):
        out[perm[i]] = data[i]
    return bytes(out)


def _base64url_decode(s: str) -> bytes | None:
    try:
        s = s.replace("-", "+").replace("_", "/")
        padding = 4 - len(s) % 4
        if padding != 4:
            s += "=" * padding
        return base64.b64decode(s)
    except Exception:
        return None


def _get_pathname(url: str) -> str:
    try:
        return urlparse(url).path or "/"
    except Exception:
        return "/"


def encode_q(data: dict) -> str:
    """Encode request data as the `?q=` query param (JSON -> base64url -> swap halves)."""
    try:
        raw = json.dumps(data, separators=(",", ":"))
        b64 = base64.b64encode(raw.encode("utf-8")).decode("ascii")
        b64 = b64.replace("+", "-").replace("/", "_").rstrip("=")
        mid = len(b64) // 2
        return b64[mid:] + b64[:mid]
    except Exception:
        return ""


def _unwrap_envelope(envelope: dict, request_url: str) -> Any | None:
    data_bytes = _base64url_decode(envelope["d"])
    wrap_bytes = _base64url_decode(envelope["w"])
    if data_bytes is None or wrap_bytes is None or len(wrap_bytes) != 16:
        return None

    expected_len = int(envelope.get("l", 0) or 0)
    if expected_len > 0 and len(data_bytes) != expected_len:
        return None

    pathname = _get_pathname(request_url)
    ua_len = len(DEFAULT_USER_AGENT)
    identity = f"{envelope.get('i', '')}|{envelope.get('n', '')}|{pathname}|{ua_len}"
    h = _fnv1a32(identity)

    wrap_seed = _fnv1a32(f"{h}|wrap|{len(data_bytes)}")
    unwrapped = _xor_with_keystream(wrap_bytes, wrap_seed)
    hex_key = unwrapped.hex()

    combined_h = _fnv1a32(f"{hex_key}|{h}")
    xor_seed = _fnv1a32(f"{combined_h}|xor|{len(data_bytes)}")
    perm_seed = _fnv1a32(f"{combined_h}|perm|{len(data_bytes)}")

    perm = _build_permutation(len(data_bytes), perm_seed)
    unperm_data = _unpermute(data_bytes, perm)
    decrypted = _xor_with_keystream(unperm_data, _fnv1a32(f"{xor_seed}|{hex_key}"))

    try:
        decompressed = gzip.decompress(decrypted)
    except Exception:
        decompressed = decrypted

    return json.loads(decompressed.decode("utf-8"))


def _decode_v2(text: str, request_url: str) -> Any | None:
    if not isinstance(text, str) or len(text) < 2 or text[0] != "{":
        return None
    try:
        obj = json.loads(text)
    except Exception:
        return None
    if not obj or obj.get("v") != 2:
        return None
    if not isinstance(obj.get("d"), str) or not isinstance(obj.get("w"), str):
        return None
    try:
        return _unwrap_envelope(obj, request_url)
    except Exception:
        return None


def _decode_v3(text: str, request_url: str) -> Any | None:
    s = text
    if isinstance(s, str) and s.startswith('"3.') and s.endswith('"'):
        try:
            s = json.loads(s)
        except Exception:
            s = s[1:-1]

    if not isinstance(s, str) or not s.startswith("3."):
        return None

    parts = s.split(".")
    if len(parts) < 6:
        return None

    envelope = {
        "i": parts[1],
        "n": parts[2],
        "l": int(parts[3]) if parts[3].isdigit() else 0,
        "w": parts[4],
        "d": parts[5],
    }
    try:
        return _unwrap_envelope(envelope, request_url)
    except Exception:
        return None


def _decode_legacy(text: str) -> Any | None:
    try:
        return json.loads(gzip.decompress(base64.b64decode(text)).decode("utf-8"))
    except Exception:
        pass
    try:
        return json.loads(text)
    except Exception:
        return None


def decode_response(text: str, request_url: str = "") -> Any | None:
    """Try V3, then V2, then legacy base64+gzip, then plain JSON."""
    if not text or not text.strip():
        return None
    text = text.strip()
    return _decode_v3(text, request_url) or _decode_v2(text, request_url) or _decode_legacy(text)


def _tag_file(audio_path: Path, tags: dict, cover_data: bytes | None, lyrics: str | None) -> None:
    from mutagen.mp4 import MP4, MP4Cover, MP4FreeForm

    audio = MP4(str(audio_path))
    for tag in ["pgap", "©too", "tool"]:
        if tag in audio:
            del audio[tag]

    for key, value in tags.items():
        if key in ("coverArtData", "lyrics") or value is None:
            continue
        if key.startswith("----"):
            if isinstance(value, list) and value:
                audio[key] = [MP4FreeForm(str(value[0]).encode("utf-8"), dataformat=1)]
        elif key in ("cpil", "pcst"):
            audio[key] = bool(value[0]) if isinstance(value, list) else bool(value)
        else:
            audio[key] = value

    if lyrics:
        audio["©lyr"] = [lyrics]

    if cover_data:
        fmt = MP4Cover.FORMAT_JPEG if cover_data[:3] == b"\xff\xd8\xff" else MP4Cover.FORMAT_PNG
        audio["covr"] = [MP4Cover(cover_data, imageformat=fmt)]

    audio.save()


def _get_tag_value(tag_value: Any) -> str:
    if isinstance(tag_value, list) and tag_value:
        return str(tag_value[0][0] if isinstance(tag_value[0], list) else tag_value[0])
    return str(tag_value) if tag_value else ""


def _format_duration_ms(ms: int) -> str:
    if not ms:
        return ""
    seconds = ms // 1000
    return f"{seconds // 60}:{seconds % 60:02d}"


def _clean_status_text(text: str) -> str:
    """
    Extract a human-readable status from am-dl's job-status polling response,
    which sometimes returns a raw JSON object instead of a plain string —
    without this, that JSON would get displayed to the user verbatim.
    """
    text = text.strip()
    if text.startswith("{") or text.startswith("["):
        try:
            parsed = json.loads(text)
        except Exception:
            return text[:80]
        if isinstance(parsed, dict):
            for key in ("message", "status", "state", "error"):
                value = parsed.get(key)
                if isinstance(value, str) and value:
                    return value[:80]
        return "Processing..."
    return text[:80]


def raw_track_to_apple_music_track(raw: dict) -> AppleMusicTrack:
    """Adapt an am-dl raw track object (MP4 tag dict) into an AppleMusicTrack
    so it can flow through the existing selection UI / pending-store machinery
    unchanged. `raw` is kept on the result for the actual ALAC/Atmos download step."""
    tags = raw.get("tags", {})
    return AppleMusicTrack(
        name=_get_tag_value(tags.get("©nam", "Unknown")),
        artist=_get_tag_value(tags.get("©ART", "Unknown")),
        link="",
        album=_get_tag_value(tags.get("©alb", "")),
        duration=_format_duration_ms(raw.get("durationInMillis", 0) or 0),
        thumb=raw.get("coverUrl", "") or "",
        raw=raw,
    )


class AmDlClient:
    """Async client for the am-dl (am-dl.pages.dev) ALAC/Atmos backend."""

    def __init__(self) -> None:
        self.download_dir = DOWNLOADS_DIR
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def _headers(self) -> dict:
        return {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json, text/plain, */*",
        }

    async def fetch_album_data(self, url: str) -> dict | None:
        """Fetch album/track metadata from am-dl. Returns None on failure.

        Retries a few times with backoff — the am-dl backend is flaky
        (intermittent 4xx/5xx). Between attempts the endpoint cache is
        reset so a stale resolution doesn't poison every retry.
        """
        for attempt in range(3):
            try:
                result = await self._fetch_album_data_once(url)
                if result is not None:
                    return result
            except AmDlError:
                raise
            except Exception as e:
                log_error(f"[AMDL] fetch_album_data attempt {attempt + 1} failed: {e}")
            log_warning(f"[AMDL] fetch_album_data returned nothing (attempt {attempt + 1}/3), retrying...")
            _reset_endpoints_cache()
            await asyncio.sleep(1.5 * (attempt + 1))
        return None

    async def _fetch_album_data_once(self, url: str) -> dict | None:
        try:
            endpoints = await _resolve_endpoints()
            q_data = {
                "url": url,
                "metadataStorefront": "default",
                "allowUnsyncedLyricsFallback": True,
                "fetchSyllable": False,
            }
            request_url = f"{endpoints['album_fetch']}?q={encode_q(q_data)}"
            async with httpx.AsyncClient(timeout=_TIMEOUT, headers=self._headers()) as client:
                resp = await client.get(request_url)
                resp.raise_for_status()
                response_text = resp.text

            tracks: list[dict] = []
            notes = None
            video = None
            for line in response_text.strip().split("\n"):
                if not line.strip():
                    continue
                data = None
                try:
                    parsed = json.loads(line)
                    if isinstance(parsed, dict) and "type" in parsed:
                        data = parsed
                    elif isinstance(parsed, str):
                        data = decode_response(parsed, request_url)
                except json.JSONDecodeError:
                    pass
                if data is None:
                    data = decode_response(line, request_url)
                if not data or not isinstance(data, dict) or "type" not in data:
                    continue
                if data.get("type") == "data":
                    tracks.append(data.get("track"))
                elif data.get("type") == "fallback":
                    if isinstance(data.get("tracks"), list):
                        tracks.extend(data.get("tracks"))
                elif data.get("type") == "editorialNotes":
                    notes = data.get("notes")
                elif data.get("type") == "editorialVideo":
                    video = data.get("video")
                elif data.get("type") == "error":
                    log_error(f"[AMDL] API error: {data.get('message')}")
                    return None

            if not tracks:
                return None
            return {"tracks": tracks, "editorialNotes": notes, "editorialVideo": video}
        except Exception as e:
            log_error(f"[AMDL] fetch_album_data failed: {e}")
            return None

    async def _download_file(self, client: httpx.AsyncClient, url: str) -> bytes:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content

    async def download_alac(
        self, track: dict, on_status: Callable[[str], None] | None = None
    ) -> bytes:
        """Submit an ALAC conversion job, poll it, then download the finished file."""
        track_id = track.get("trackId")
        if not track_id:
            raise AmDlError("Track is missing an ID")

        endpoints = await _resolve_endpoints()
        track_url = f"https://music.apple.com/us/song/-/{track_id}"
        q_data = {"url": track_url, "mode": QUALITY_ALAC, "originalUrl": track_url}
        submit_url = f"{endpoints['alac_submit']}?q={encode_q(q_data)}"

        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=self._headers()) as client:
            resp = await client.get(submit_url)
            resp.raise_for_status()
            job_data = decode_response(resp.text, submit_url)
            if not job_data:
                try:
                    job_data = json.loads(resp.text)
                except Exception as e:
                    raise AmDlError("Failed to submit ALAC job") from e

            job_id = job_data.get("job_id")
            if not job_id:
                raise AmDlError("ALAC job submission returned no job_id")

            max_attempts = 120
            for _attempt in range(max_attempts):
                await asyncio.sleep(5)
                try:
                    status_resp = await client.get(
                        f"{endpoints['alac_stream']}?id={job_id}", timeout=10
                    )
                    status_text = status_resp.text
                except Exception:
                    continue

                if on_status:
                    on_status(_clean_status_text(status_text))

                if "Job Completed" in status_text or "complete" in status_text.lower():
                    break
                if any(x in status_text.lower() for x in ("error", "failed", "not found")):
                    raise AmDlError(f"ALAC conversion failed on server: {status_text[:200]}")
            else:
                raise AmDlError("ALAC server processing timed out")

            download_url = f"{endpoints['alac_file']}?id={job_id}"
            dl_resp = await client.post(download_url, json={}, timeout=120)
            dl_resp.raise_for_status()
            data = dl_resp.content

        if not data:
            raise AmDlError("ALAC download returned no data")
        return data

    async def download_atmos(
        self, track: dict, on_status: Callable[[str], None] | None = None
    ) -> bytes:
        """Fetch Atmos keys, download the encrypted stream, and decrypt locally."""
        mp4decrypt = shutil.which("mp4decrypt")
        if not mp4decrypt:
            raise AmDlError(
                "mp4decrypt not found (required for Atmos). Install Bento4 tools: "
                "https://www.bento4.com/downloads/"
            )

        tags = track.get("tags", {})
        track_id = str(track.get("trackId", ""))
        track_url = f"https://music.apple.com/us/song/-/{track_id}"

        q_data = {
            "id": track_id,
            "url": track_url,
            "codec": "atmos",
            "storefront": "us",
            "link": track_url,
        }
        song_name = _get_tag_value(tags.get("©nam", ""))
        artist_name = _get_tag_value(tags.get("©ART", ""))
        if song_name:
            q_data["song_name"] = song_name
            q_data["title"] = song_name
        if artist_name:
            q_data["artist_name"] = artist_name
            q_data["artist"] = artist_name

        if on_status:
            on_status("Fetching Atmos keys...")

        endpoints = await _resolve_endpoints()
        request_url = f"{endpoints['atmos_keys']}?q={encode_q(q_data)}"

        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=self._headers()) as client:
            resp = await client.get(request_url)
            resp.raise_for_status()
            keys_data = decode_response(resp.text, request_url)
            if not keys_data:
                try:
                    keys_data = json.loads(resp.text)
                except Exception:
                    keys_data = None

            if not keys_data or not keys_data.get("stream_url") or not keys_data.get("key1"):
                raise AmDlError("Atmos not available for this track")

            stream_url = keys_data["stream_url"]
            key1 = keys_data["key1"]
            kid1 = keys_data.get("kid1", "1")
            key0 = keys_data.get("key0")
            kid0 = keys_data.get("kid0")

            if keys_data.get("tags"):
                tags = {**tags, **keys_data["tags"]}

            if on_status:
                on_status("Downloading Atmos stream...")

            if stream_url.endswith(".m3u8"):
                playlist_resp = await client.get(
                    f"{endpoints['proxy']}?target={urlquote(stream_url, safe='')}"
                )
                playlist_resp.raise_for_status()
                media_url = None
                for line in playlist_resp.text.split("\n"):
                    if line.strip() and not line.strip().startswith("#"):
                        media_url = (
                            line.strip()
                            if line.strip().startswith("http")
                            else f"{'/'.join(stream_url.split('/')[:-1])}/{line.strip()}"
                        )
                        break
                if not media_url:
                    raise AmDlError("Failed to resolve Atmos HLS playlist")
                encrypted_data = await self._download_file(
                    client, f"{endpoints['proxy']}?target={urlquote(media_url, safe='')}"
                )
            else:
                encrypted_data = await self._download_file(
                    client, f"{endpoints['proxy']}?target={urlquote(stream_url, safe='')}"
                )

            cover_url = track.get("coverUrl")
            cover_data = None
            if cover_url:
                try:
                    cover_data = await self._download_file(
                        client, f"{endpoints['proxy']}?target={urlquote(cover_url, safe='')}"
                    )
                except Exception:
                    cover_data = None

        if on_status:
            on_status("Decrypting Atmos audio...")

        decrypted_data = await self._decrypt_mp4(encrypted_data, key1, kid1, key0, kid0)
        if not decrypted_data:
            raise AmDlError("Atmos decryption failed")

        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as tmp:
            tmp.write(decrypted_data)
            tmp_path = Path(tmp.name)

        try:
            lyrics = track.get("lrcContent")
            _tag_file(tmp_path, tags, cover_data, lyrics)
            return tmp_path.read_bytes()
        finally:
            tmp_path.unlink(missing_ok=True)

    async def fetch_track_details(self, track_id: str) -> dict | None:
        """Fetch HLS playlist URL + decryption key for am-dl's own standard-quality path."""
        endpoints = await _resolve_endpoints()
        request_url = endpoints["track_details"]
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=self._headers()) as client:
            resp = await client.post(request_url, json={"trackId": track_id, "isVideo": False})
            resp.raise_for_status()
            response_text = resp.text.strip()

        try:
            parsed = json.loads(response_text)
            if isinstance(parsed, str):
                result = decode_response(parsed, request_url)
                if result is not None:
                    return result
            elif isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        result = decode_response(response_text, request_url)
        if result is not None:
            return result

        try:
            return json.loads(response_text) if response_text else None
        except Exception:
            return None

    async def download_standard(
        self, track: dict, on_status: Callable[[str], None] | None = None
    ) -> bytes:
        """
        am-dl's own standard-quality path (HLS + single-key mp4decrypt) — used
        only as a further fallback if the primary aaplmusicdownloader.com
        backend fails.
        """
        if not shutil.which("mp4decrypt"):
            raise AmDlError("mp4decrypt not found (required for am-dl's standard fallback)")

        tags = track.get("tags", {})
        track_id = str(track.get("trackId", ""))

        if on_status:
            on_status("Fetching track details...")

        details = await self.fetch_track_details(track_id)
        if not details:
            raise AmDlError("Failed to get track details")

        hls_url = details.get("hlsPlaylistUrl")
        decryption_key = details.get("key")
        if not hls_url or not decryption_key:
            raise AmDlError("Missing HLS URL or decryption key")

        if details.get("tags"):
            tags = {**tags, **details["tags"]}

        if on_status:
            on_status("Downloading standard stream...")

        endpoints = await _resolve_endpoints()
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=self._headers()) as client:
            playlist_resp = await client.get(
                f"{endpoints['proxy']}?target={urlquote(hls_url, safe='')}"
            )
            playlist_resp.raise_for_status()
            media_url = None
            for line in playlist_resp.text.split("\n"):
                if line.strip() and not line.strip().startswith("#"):
                    media_url = (
                        line.strip()
                        if line.strip().startswith("http")
                        else f"{'/'.join(hls_url.split('/')[:-1])}/{line.strip()}"
                    )
                    break
            if not media_url:
                raise AmDlError("Failed to resolve standard HLS playlist")

            encrypted_data = await self._download_file(
                client, f"{endpoints['proxy']}?target={urlquote(media_url, safe='')}"
            )

            cover_url = track.get("coverUrl")
            cover_data = None
            if cover_url:
                try:
                    cover_data = await self._download_file(
                        client, f"{endpoints['proxy']}?target={urlquote(cover_url, safe='')}"
                    )
                except Exception:
                    cover_data = None

        if on_status:
            on_status("Decrypting audio...")

        decrypted_data = await self._decrypt_mp4(encrypted_data, decryption_key, "1", None, None)
        if not decrypted_data:
            raise AmDlError("Decryption failed")

        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as tmp:
            tmp.write(decrypted_data)
            tmp_path = Path(tmp.name)

        try:
            lyrics = track.get("lrcContent")
            _tag_file(tmp_path, tags, cover_data, lyrics)
            return tmp_path.read_bytes()
        finally:
            tmp_path.unlink(missing_ok=True)

    async def _decrypt_mp4(
        self,
        encrypted_data: bytes,
        key1: str,
        kid1: str,
        key0: str | None,
        kid0: str | None,
    ) -> bytes | None:
        mp4decrypt = shutil.which("mp4decrypt")
        if not mp4decrypt:
            return None

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            enc_path = tmp_path / "enc.m4a"
            dec_path = tmp_path / "dec.m4a"
            enc_path.write_bytes(encrypted_data)

            cmd = [mp4decrypt, "--key", f"{kid1}:{key1}"]
            if key0 and kid0:
                cmd.extend(["--key", f"{kid0}:{key0}"])
            cmd.extend([str(enc_path), str(dec_path)])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            if proc.returncode != 0:
                return None
            return dec_path.read_bytes()

    def _save_bytes(self, data: bytes, safe_name: str, quality: str) -> Path:
        ts = int(time.time() * 1000)
        ext = ".zip" if data[:2] == b"PK" else ".m4a"
        filename = f"am_{quality}_{safe_name}_{ts}{ext}".replace(" ", "_")
        dest = self.download_dir / filename
        dest.write_bytes(data)
        return dest

    async def download_with_fallback(
        self,
        track: dict,
        requested: str,
        on_status: Callable[[str], None] | None = None,
    ) -> tuple[Path, str, list[str]]:
        """
        Try the requested quality, falling back atmos -> alac -> standard
        (aaplmusicdownloader.com) -> standard (am-dl's own HLS path) on
        failure. Returns (saved file path, quality actually used, list of
        "Label failed: reason" notes for every step that was tried and
        failed before the one that succeeded).
        """
        tags = track.get("tags", {})
        safe_name = (
            "".join(
                c for c in _get_tag_value(tags.get("©nam", "track")) if c.isalnum() or c in " -_"
            )[:50].strip()
            or "track"
        )

        STD_AAMDL = "standard_aamdl"
        STD_AMDL = "standard_amdl"

        async def _aamdl_standard() -> Path:
            track_id = track.get("trackId")
            track_url = f"https://music.apple.com/us/song/-/{track_id}"
            album_data = await applemusic_client.fetch_song_info(track_url)
            dlink = await applemusic_client.get_download_link(album_data.tracks[0])
            return await applemusic_client.download_track(dlink, f"am_std_{safe_name}")

        # step -> (label, quality reported to the caller, runner returning
        # either raw bytes needing _save_bytes, or an already-saved Path)
        steps = {
            QUALITY_ATMOS: ("Atmos", QUALITY_ATMOS, lambda: self.download_atmos(track, on_status)),
            QUALITY_ALAC: ("ALAC", QUALITY_ALAC, lambda: self.download_alac(track, on_status)),
            STD_AAMDL: ("Standard", QUALITY_STANDARD, _aamdl_standard),
            STD_AMDL: (
                "Standard (am-dl fallback)",
                QUALITY_STANDARD,
                lambda: self.download_standard(track, on_status),
            ),
        }
        needs_save = {QUALITY_ATMOS, QUALITY_ALAC, STD_AMDL}
        chain = {
            QUALITY_ATMOS: [QUALITY_ATMOS, QUALITY_ALAC, STD_AAMDL, STD_AMDL],
            QUALITY_ALAC: [QUALITY_ALAC, STD_AAMDL, STD_AMDL],
            QUALITY_STANDARD: [STD_AAMDL, STD_AMDL],
        }.get(requested, [STD_AAMDL, STD_AMDL])

        failures: list[str] = []
        last_error: Exception | None = None
        for step in chain:
            label, quality_out, run = steps[step]
            try:
                if on_status:
                    on_status(f"Trying {label}...")
                result = await run()
                path = self._save_bytes(result, safe_name, step) if step in needs_save else result
                return path, quality_out, failures
            except Exception as e:
                last_error = e
                reason = str(e) or type(e).__name__
                failures.append(f"{label} failed: {reason}")
                log_info(f"[AMDL] {step} failed, trying next in chain: {e}")
                if on_status:
                    on_status(f"{label} failed: {reason} — trying next option...")
                continue

        raise AmDlError(f"All quality options failed: {last_error}")


amdl_client = AmDlClient()
