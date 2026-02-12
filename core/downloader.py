"""
yt-dlp wrapper for downloading media from various platforms.

Provides a clean async API around yt-dlp's library for downloading
audio and video from YouTube, TikTok, Instagram, Twitter/X, and 1000+ sites.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from core.logger import log_error, log_info
from core.runtime_config import runtime_config

DOWNLOADS_DIR = Path("data/downloads")
MAX_FILE_SIZE_MB = runtime_config.get_nested("downloader", "max_file_size_mb", default=50)


def _format_size(size_bytes: int | float) -> str:
    """Format bytes as human-readable string."""
    if not size_bytes or size_bytes <= 0:
        return "~"
    mb = size_bytes / (1024 * 1024)
    if mb >= 1:
        return f"{mb:.1f}MB"
    kb = size_bytes / 1024
    return f"{kb:.0f}KB"


@dataclass
class FormatOption:
    """A single downloadable format option."""

    format_id: str
    ext: str
    quality: str
    filesize: int = 0
    type: str = "video"
    note: str = ""
    has_video: bool = True
    has_audio: bool = True

    @property
    def filesize_str(self) -> str:
        return _format_size(self.filesize)

    @property
    def label(self) -> str:
        """Human-readable label like '720p MP4 ~15MB' or '128kbps MP3 ~5MB'."""
        parts = [self.quality, self.ext.upper()]
        if self.filesize:
            parts.append(f"~{self.filesize_str}")
        if self.note:
            parts.append(f"({self.note})")
        return " ".join(parts)


@dataclass
class MediaInfo:
    """Extracted media metadata."""

    title: str = ""
    duration: int = 0
    uploader: str = ""
    platform: str = ""
    url: str = ""
    thumbnail: str = ""
    filesize_approx: int = 0
    formats: list[FormatOption] = field(default_factory=list)

    @property
    def duration_str(self) -> str:
        """Format duration as mm:ss or hh:mm:ss."""
        if self.duration <= 0:
            return "Unknown"
        hours, remainder = divmod(self.duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    @property
    def filesize_str(self) -> str:
        return _format_size(self.filesize_approx)


class DownloadError(Exception):
    """Raised when a download fails."""

    pass


class FileTooLargeError(DownloadError):
    """Raised when the downloaded file exceeds the size limit."""

    def __init__(self, size_mb: float, max_mb: float):
        self.size_mb = size_mb
        self.max_mb = max_mb
        super().__init__(f"File too large: {size_mb:.1f} MB (max {max_mb:.0f} MB)")


class Downloader:
    """yt-dlp wrapper for downloading media."""

    def __init__(self, download_dir: Path | None = None, max_size_mb: float = MAX_FILE_SIZE_MB):
        self.download_dir = download_dir or DOWNLOADS_DIR
        self.max_size_mb = max_size_mb
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def _make_output_path(self, prefix: str = "dl") -> str:
        """Generate a unique output path template for yt-dlp."""
        ts = int(time.time() * 1000)
        return str(self.download_dir / f"{prefix}_{ts}_%(id)s.%(ext)s")

    @staticmethod
    def _parse_formats(raw_formats: list[dict]) -> list[FormatOption]:
        """Parse yt-dlp format list into clean FormatOption objects."""
        video_map: dict[str, FormatOption] = {}
        audio_map: dict[str, FormatOption] = {}

        for f in raw_formats:
            fmt_id = f.get("format_id", "")
            ext = f.get("ext", "")
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            has_video = vcodec != "none"
            has_audio = acodec != "none"
            filesize = f.get("filesize") or f.get("filesize_approx") or 0

            if ext in ("mhtml", "json", "3gp"):
                continue

            if has_video:
                height = int(f.get("height", 0) or 0)
                if not height:
                    continue
                fps = int(f.get("fps", 0) or 0)
                quality = f"{height}p" if height else "unknown"
                if fps and fps > 30:
                    quality += f"{fps}"

                key = quality
                existing = video_map.get(key)

                is_combined = has_video and has_audio
                ext_priority = ext == "mp4"

                if existing:
                    existing_combined = existing.has_video and existing.has_audio
                    existing_ext_priority = existing.ext == "mp4"
                    if is_combined and not existing_combined:
                        pass
                    elif (
                        is_combined == existing_combined
                        and ext_priority
                        and not existing_ext_priority
                    ):
                        pass
                    else:
                        continue

                video_map[key] = FormatOption(
                    format_id=fmt_id,
                    ext=ext,
                    quality=quality,
                    filesize=filesize,
                    type="video",
                    note="" if has_audio else "no audio",
                    has_video=True,
                    has_audio=has_audio,
                )

            elif has_audio:
                abr = int(f.get("abr", 0) or 0)
                quality = f"{int(abr)}kbps" if abr else "unknown"

                key = quality
                existing = audio_map.get(key)

                if existing:
                    existing_ext_priority = existing.ext in ("m4a", "mp3")
                    new_ext_priority = ext in ("m4a", "mp3")
                    if new_ext_priority and not existing_ext_priority:
                        pass
                    elif existing.filesize and filesize and filesize < existing.filesize:
                        pass
                    else:
                        continue

                audio_map[key] = FormatOption(
                    format_id=fmt_id,
                    ext=ext,
                    quality=quality,
                    filesize=filesize,
                    type="audio",
                    note="",
                    has_video=False,
                    has_audio=True,
                )

        videos = sorted(
            video_map.values(),
            key=lambda o: int("".join(c for c in o.quality if c.isdigit()) or "0"),
            reverse=True,
        )[:5]

        audios = sorted(
            audio_map.values(),
            key=lambda o: int("".join(c for c in o.quality if c.isdigit()) or "0"),
            reverse=True,
        )[:3]

        return videos + audios

    async def get_info(self, url: str) -> MediaInfo:
        """Extract media info without downloading."""
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "skip_download": True,
        }

        def _extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            info = await asyncio.to_thread(_extract)
        except Exception as e:
            raise DownloadError(f"Failed to extract info: {e}") from e

        if not info:
            raise DownloadError("No info returned for URL")

        raw_formats = info.get("formats", [])
        format_options = self._parse_formats(raw_formats) if raw_formats else []

        return MediaInfo(
            title=info.get("title", "Unknown"),
            duration=info.get("duration", 0) or 0,
            uploader=info.get("uploader", info.get("channel", "Unknown")),
            platform=info.get("extractor_key", info.get("extractor", "Unknown")),
            url=url,
            thumbnail=info.get("thumbnail", ""),
            filesize_approx=info.get("filesize_approx", 0) or info.get("filesize", 0) or 0,
            formats=format_options,
        )

    async def download_format(
        self, url: str, format_id: str, max_size_mb: float | None = None, merge_audio: bool = False
    ) -> Path:
        """
        Download a specific format by its format_id.

        Args:
            merge_audio: If True, merge best audio into video-only streams.

        Returns path to the downloaded file.
        """
        limit = max_size_mb or self.max_size_mb
        output_template = self._make_output_path("dl")

        fmt = f"{format_id}+bestaudio/{format_id}" if merge_audio else format_id

        ydl_opts = {
            "format": fmt,
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
            "max_filesize": int(limit * 1024 * 1024),
        }

        return await self._download(url, ydl_opts, limit)

    async def download_audio(self, url: str, max_size_mb: float | None = None) -> Path:
        """
        Download audio from URL (best quality, MP3).

        Returns path to the downloaded audio file.
        """
        limit = max_size_mb or self.max_size_mb
        output_template = self._make_output_path("audio")

        ydl_opts = {
            "format": f"bestaudio[filesize<? {int(limit)}M]/bestaudio/best",
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "max_filesize": int(limit * 1024 * 1024),
        }

        return await self._download(url, ydl_opts, limit)

    async def download_video(self, url: str, max_size_mb: float | None = None) -> Path:
        """
        Download video from URL (best quality, MP4).

        Returns path to the downloaded video file.
        """
        limit = max_size_mb or self.max_size_mb
        output_template = self._make_output_path("video")

        ydl_opts = {
            "format": (
                f"bestvideo[filesize<? {int(limit)}M]+bestaudio[filesize<? {int(limit)}M]"
                f"/best[filesize<? {int(limit)}M]"
                f"/bestvideo+bestaudio/best"
            ),
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
            "max_filesize": int(limit * 1024 * 1024),
        }

        return await self._download(url, ydl_opts, limit)

    async def _download(self, url: str, ydl_opts: dict, max_size_mb: float) -> Path:
        """Internal download method."""
        import yt_dlp

        downloaded_file = None

        def _run():
            nonlocal downloaded_file
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info:
                    filename = ydl.prepare_filename(info)
                    base = os.path.splitext(filename)[0]
                    for ext in [".mp3", ".m4a", ".mp4", ".webm", ".mkv", ".opus", ".ogg"]:
                        candidate = base + ext
                        if os.path.exists(candidate):
                            downloaded_file = candidate
                            return
                    if os.path.exists(filename):
                        downloaded_file = filename

        try:
            log_info(f"[DOWNLOADER] Starting download: {url}")
            await asyncio.to_thread(_run)
        except Exception as e:
            raise DownloadError(f"Download failed: {e}") from e

        if not downloaded_file or not os.path.exists(downloaded_file):
            raise DownloadError("Download completed but no file was found")

        file_size = os.path.getsize(downloaded_file)
        file_size_mb = file_size / (1024 * 1024)

        if file_size_mb > max_size_mb:
            self.cleanup(Path(downloaded_file))
            raise FileTooLargeError(file_size_mb, max_size_mb)

        log_info(f"[DOWNLOADER] Downloaded: {downloaded_file} ({file_size_mb:.1f} MB)")
        return Path(downloaded_file)

    def cleanup(self, filepath: Path) -> None:
        """Remove a downloaded file."""
        try:
            if filepath.exists():
                filepath.unlink()
                log_info(f"[DOWNLOADER] Cleaned up: {filepath}")
        except Exception as e:
            log_error(f"[DOWNLOADER] Cleanup failed: {e}")

    def cleanup_all(self) -> None:
        """Remove all files in the download directory."""
        try:
            if self.download_dir.exists():
                shutil.rmtree(self.download_dir)
                self.download_dir.mkdir(parents=True, exist_ok=True)
                log_info("[DOWNLOADER] Cleaned up all downloads")
        except Exception as e:
            log_error(f"[DOWNLOADER] Cleanup all failed: {e}")


downloader = Downloader()
