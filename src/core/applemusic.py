"""
Apple Music downloader API client.

Calls the aaplmusicdownloader.com API directly (no proxy needed server-side).

Flow:
  1. song_url.php (single song) or pl.php (album) → get track metadata
  2. composer/swd.php with full track params → get download link
  3. Download the file from dlink
"""

from __future__ import annotations

import html
import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import httpx

from core.constants import DOWNLOADS_DIR
from core.logger import log_error, log_info

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

API_BASE_URL = "https://aaplmusicdownloader.com/api"
ROOT_URL = "https://aaplmusicdownloader.com"

_BROWSER_HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "en-US,en;q=0.9",
    "dnt": "1",
    "priority": "u=1, i",
    "sec-ch-ua": '"Not?A_Brand";v="99", "Chromium";v="130"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "sec-gpc": "1",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "x-requested-with": "XMLHttpRequest",
    "origin": ROOT_URL,
    "referer": f"{ROOT_URL}/",
}


def _decode(text: str) -> str:
    """Decode HTML entities (matching frontend's decodeHtmlEntities)."""
    return html.unescape(text) if text else ""


def _clean_name(name: str) -> str:
    """Remove quotes from names (matching frontend's cleanName)."""
    return re.sub(r"['\"]", "", name)


@dataclass
class AppleMusicTrack:
    """A single Apple Music track."""

    name: str
    artist: str
    link: str
    album: str
    duration: str
    thumb: str


@dataclass
class AlbumData:
    """Album/playlist metadata with tracks."""

    album: str
    artist: str
    thumb: str
    date: str
    count: int
    tracks: list[AppleMusicTrack]


class AppleMusicError(Exception):
    """Raised when an Apple Music API call fails."""

    pass


def is_single_song(url: str) -> bool:
    """Check if URL is a single song (vs album/playlist). Matches frontend logic."""
    try:
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(url)
        if parse_qs(parsed.query).get("i"):
            return True
        segments = [s for s in parsed.path.split("/") if s]
        song_idx = segments.index("song") if "song" in segments else -1
        if song_idx > -1 and song_idx < len(segments) - 1:
            return True
        return False
    except Exception:
        return False


class AppleMusicClient:
    """Async client for the Apple Music downloader API."""

    def __init__(self) -> None:
        self.download_dir = DOWNLOADS_DIR
        self.download_dir.mkdir(parents=True, exist_ok=True)

    async def _get_session_cookies(self, client: httpx.AsyncClient) -> str:
        """Fetch homepage to get a fresh session cookie."""
        try:
            resp = await client.get(
                ROOT_URL,
                headers={"User-Agent": _BROWSER_HEADERS["user-agent"]},
                follow_redirects=True,
            )
            cookies = "; ".join(f"{name}={value}" for name, value in resp.cookies.items())
            return f"{cookies}; att=9" if cookies else "att=9"
        except Exception:
            return "att=9"

    async def _api_get(self, client: httpx.AsyncClient, path: str, cookies: str) -> dict:
        """Make a GET request to the API with proper headers."""
        headers = {**_BROWSER_HEADERS, "Cookie": cookies}
        resp = await client.get(f"{API_BASE_URL}/{path}", headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def _api_post(
        self, client: httpx.AsyncClient, path: str, data: dict, cookies: str
    ) -> dict:
        """Make a POST request to the API with proper headers."""
        headers = {
            **_BROWSER_HEADERS,
            "Cookie": cookies,
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "referer": f"{ROOT_URL}/song.php",
        }
        resp = await client.post(f"{API_BASE_URL}/{path}", data=data, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def fetch_song_info(self, url: str) -> AlbumData:
        """Fetch info for a single song URL via song_url.php."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                cookies = await self._get_session_cookies(client)
                data = await self._api_get(
                    client,
                    f"song_url.php?url={quote(url, safe='')}",
                    cookies,
                )
        except httpx.HTTPStatusError as e:
            raise AppleMusicError(
                f"Failed to fetch song info: HTTP {e.response.status_code}"
            ) from e
        except Exception as e:
            raise AppleMusicError(f"Failed to fetch song info: {e}") from e

        if not data or not data.get("name") or not data.get("url"):
            raise AppleMusicError("Invalid response from song API")

        track = AppleMusicTrack(
            name=_decode(data.get("name", "")),
            artist=_decode(data.get("artist", "")),
            link=_decode(data.get("url", "")),
            album=_decode(data.get("albumname", "")),
            duration=_decode(data.get("duration", "N/A")),
            thumb=_decode(data.get("thumb", "")),
        )

        return AlbumData(
            album=track.album,
            artist=track.artist,
            thumb=track.thumb,
            date="1 Song",
            count=1,
            tracks=[track],
        )

    async def fetch_album_info(self, url: str) -> AlbumData:
        """Fetch info for an album/playlist URL via pl.php."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                cookies = await self._get_session_cookies(client)
                data = await self._api_get(
                    client,
                    f"pl.php?url={quote(url, safe='')}",
                    cookies,
                )
        except httpx.HTTPStatusError as e:
            raise AppleMusicError(
                f"Failed to fetch album info: HTTP {e.response.status_code}"
            ) from e
        except Exception as e:
            raise AppleMusicError(f"Failed to fetch album info: {e}") from e

        album_details = data.get("album_details")
        if not album_details:
            raise AppleMusicError("Invalid response from album API")

        tracks: list[AppleMusicTrack] = []
        for key in album_details:
            if key.isdigit():
                raw = album_details[key]
                tracks.append(
                    AppleMusicTrack(
                        name=_decode(raw.get("name", "")),
                        artist=_decode(raw.get("artist", "")),
                        link=_decode(raw.get("link", "")),
                        album=_decode(raw.get("album", "")),
                        duration=_decode(raw.get("duration", "")),
                        thumb=_decode(raw.get("thumb", "")),
                    )
                )

        return AlbumData(
            album=_decode(album_details.get("album", "")),
            artist=_decode(album_details.get("artist", "")),
            thumb=album_details.get("thumb", ""),
            date=album_details.get("date", ""),
            count=int(album_details.get("count", len(tracks))),
            tracks=tracks,
        )

    async def fetch_info(self, url: str) -> AlbumData:
        """Fetch track/album info — auto-detects single song vs album."""
        if is_single_song(url):
            return await self.fetch_song_info(url)
        return await self.fetch_album_info(url)

    async def get_download_link(self, track: AppleMusicTrack, quality: str = "m4a") -> str:
        """Get the download link for a track via swd.php (with all required params)."""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                cookies = await self._get_session_cookies(client)
                data = await self._api_post(
                    client,
                    "composer/swd.php",
                    data={
                        "song_name": _clean_name(track.name),
                        "artist_name": _clean_name(track.artist),
                        "url": track.link,
                        "token": "na",
                        "zip_download": "false",
                        "quality": quality,
                    },
                    cookies=cookies,
                )
        except httpx.HTTPStatusError as e:
            raise AppleMusicError(
                f"Failed to get download link: HTTP {e.response.status_code}"
            ) from e
        except Exception as e:
            raise AppleMusicError(f"Failed to get download link: {e}") from e

        if data.get("status") != "success" or not data.get("dlink"):
            msg = data.get("comments", "No download link returned")
            raise AppleMusicError(msg)

        return data["dlink"]

    async def download_track(
        self,
        dlink: str,
        filename: str | None = None,
        progress_hook: Callable[[int, int], None] | None = None,
    ) -> Path:
        """Download a track from its direct download link."""
        if not filename:
            ts = int(time.time() * 1000)
            filename = f"am_{ts}"

        filename = filename.replace(" ", "_")

        ext = ".m4a"
        url_path = dlink.split("?")[0]
        for candidate in [".m4a", ".mp3", ".aac", ".ogg", ".wav"]:
            if url_path.lower().endswith(candidate):
                ext = candidate
                break

        if not filename.endswith(ext):
            filename = f"{filename}{ext}"

        dest_path = self.download_dir / filename

        try:
            async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
                async with client.stream("GET", dlink) as resp:
                    resp.raise_for_status()
                    total = int(resp.headers.get("content-length", 0))
                    downloaded = 0
                    with open(dest_path, "wb") as f:
                        async for chunk in resp.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_hook and total > 0:
                                progress_hook(downloaded, total)
        except Exception as e:
            if dest_path.exists():
                dest_path.unlink()
            raise AppleMusicError(f"Download failed: {e}") from e

        if not dest_path.exists() or dest_path.stat().st_size == 0:
            if dest_path.exists():
                dest_path.unlink()
            raise AppleMusicError("Downloaded file is empty")

        size_mb = dest_path.stat().st_size / (1024 * 1024)
        log_info(f"[APPLEMUSIC] Downloaded: {dest_path.name} ({size_mb:.1f} MB)")
        return dest_path

    def cleanup(self, filepath: Path) -> None:
        """Remove a downloaded file."""
        try:
            if filepath.exists():
                filepath.unlink()
                log_info(f"[APPLEMUSIC] Cleaned up: {filepath}")
        except Exception as e:
            log_error(f"[APPLEMUSIC] Cleanup failed: {e}")


applemusic_client = AppleMusicClient()
