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

from core.constants import DOWNLOADS_DIR
from core.logger import log_error, log_info, log_warning
from core.runtime_config import runtime_config

MAX_FILE_SIZE_MB = runtime_config.get_nested("downloader", "max_file_size_mb", default=180)


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
    is_playlist: bool = False
    formats: list[FormatOption] = field(default_factory=list)

    @property
    def duration_str(self) -> str:
        """Format duration as mm:ss or hh:mm:ss."""
        if self.duration <= 0:
            return "Unknown"
        total = int(self.duration)
        hours, remainder = divmod(total, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    @property
    def filesize_str(self) -> str:
        return _format_size(self.filesize_approx)


@dataclass
class PlaylistEntry:
    """A single entry in a playlist."""

    title: str = ""
    url: str = ""
    duration: str = ""
    uploader: str = ""
    index: int = 0


@dataclass
class PlaylistInfo:
    """Extracted playlist metadata."""

    title: str = ""
    url: str = ""
    count: int = 0
    entries: list[PlaylistEntry] = field(default_factory=list)


class DownloadError(Exception):
    """Raised when a download fails."""

    pass


class FileTooLargeError(DownloadError):
    """Raised when the downloaded file exceeds the size limit."""

    def __init__(self, size_mb: float, max_mb: float):
        self.size_mb = size_mb
        self.max_mb = max_mb
        super().__init__(f"File too large: {size_mb:.1f} MB (max {max_mb:.0f} MB)")


class DownloadAbortedError(DownloadError):
    """Raised when a download is cancelled by the user."""

    pass


class Downloader:
    """yt-dlp wrapper for downloading media."""

    def __init__(self, download_dir: Path | None = None, max_size_mb: float = MAX_FILE_SIZE_MB):
        self.download_dir = download_dir or DOWNLOADS_DIR
        self.max_size_mb = max_size_mb
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self._active_downloads: dict[str, bool] = {}

    def _make_output_path(self, prefix: str = "dl") -> str:
        """Generate a unique output path template for yt-dlp."""
        ts = int(time.time() * 1000)
        return str(self.download_dir / f"{prefix}_{ts}_%(id)s.%(ext)s")

    def _add_cookies(self, ydl_opts: dict) -> None:
        """Inject cookiefile into ydl_opts if env var is set."""
        cookies_path_raw = os.getenv("YOUTUBE_COOKIES_PATH")
        if cookies_path_raw:
            project_root = Path(__file__).parent.parent
            cookies_path = project_root / cookies_path_raw

            if cookies_path.exists():
                ydl_opts["cookiefile"] = str(cookies_path.absolute())
                log_info(f"[DOWNLOADER] Using cookies: {cookies_path.name}")
            else:
                log_info(f"[DOWNLOADER] Cookie file not found at: {cookies_path}")

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
                    note="",
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

    async def search_youtube(self, query: str, count: int = 5) -> list[dict]:
        """
        Search YouTube and return a list of results.

        Args:
            query: Search query string
            count: Number of results to return (default 5)

        Returns:
            List of dicts with title, url, duration, uploader
        """
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
        }
        self._add_cookies(ydl_opts)

        search_url = f"ytsearch{count}:{query}"

        def _search():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(search_url, download=False)

        try:
            info = await asyncio.to_thread(_search)
        except Exception as e:
            raise DownloadError(f"Search failed: {e}") from e

        if not info or "entries" not in info:
            return []

        results = []
        for entry in info.get("entries", []):
            if not entry:
                continue
            duration = entry.get("duration", 0) or 0
            if duration > 0:
                total = int(duration)
                mins, secs = divmod(total, 60)
                dur_str = f"{mins}:{secs:02d}"
            else:
                dur_str = "?"

            results.append(
                {
                    "title": entry.get("title", "Unknown"),
                    "url": entry.get("url", entry.get("webpage_url", "")),
                    "duration": dur_str,
                    "uploader": entry.get("uploader", entry.get("channel", "Unknown")) or "Unknown",
                }
            )

        return results

    async def get_playlist_info(self, url: str, max_entries: int = 25) -> PlaylistInfo:
        """
        Extract playlist metadata using flat extraction.

        Args:
            url: Playlist URL
            max_entries: Maximum number of entries to fetch

        Returns:
            PlaylistInfo with title, count, and entry list
        """
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "ignoreerrors": True,
            "playlistend": max_entries,
        }
        self._add_cookies(ydl_opts)

        def _extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            info = await asyncio.to_thread(_extract)
        except Exception as e:
            raise DownloadError(f"Failed to extract playlist: {e}") from e

        if not info:
            raise DownloadError("No playlist info returned")

        raw_entries = info.get("entries", []) or []
        entries = []
        for i, entry in enumerate(raw_entries):
            if not entry:
                continue
            dur = entry.get("duration", 0) or 0
            if dur > 0:
                mins, secs = divmod(int(dur), 60)
                dur_str = f"{mins}:{secs:02d}"
            else:
                dur_str = "?"
            entries.append(
                PlaylistEntry(
                    title=entry.get("title", "Unknown"),
                    url=entry.get("url", entry.get("webpage_url", "")),
                    duration=dur_str,
                    uploader=entry.get("uploader", entry.get("channel", "")) or "",
                    index=i + 1,
                )
            )

        total_count = info.get("playlist_count", len(entries)) or len(entries)

        return PlaylistInfo(
            title=info.get("title", "Playlist"),
            url=url,
            count=total_count,
            entries=entries,
        )

    async def get_info(self, url: str) -> MediaInfo:
        """Extract media info without downloading."""
        import yt_dlp

        flat_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "ignoreerrors": True,
            "extractor_args": {"youtube": {"player_client": ["web", "android", "mweb", "tv"]}},
        }
        self._add_cookies(flat_opts)

        def _flat_extract():
            with yt_dlp.YoutubeDL(flat_opts) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            flat_info = await asyncio.to_thread(_flat_extract)
        except Exception as e:
            raise DownloadError(f"Failed to extract info: {e}") from e

        if not flat_info:
            raise DownloadError("No info returned for URL")

        if flat_info.get("_type") == "playlist" or (
            "entries" in flat_info and flat_info["entries"]
        ):
            return MediaInfo(
                title=flat_info.get("title", "Playlist"),
                is_playlist=True,
                url=url,
            )

        full_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "skip_download": True,
        }
        self._add_cookies(full_opts)

        def _full_extract():
            with yt_dlp.YoutubeDL(full_opts) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            info = await asyncio.to_thread(_full_extract)
        except Exception as e:
            raise DownloadError(f"Failed to extract info: {e}") from e

        if not info:
            raise DownloadError("No info returned for URL")

        raw_formats = info.get("formats", [])
        if not raw_formats:
            log_warning(f"[DOWNLOADER] No formats found for {url}. Info: {list(info.keys())}")
        format_options = self._parse_formats(raw_formats) if raw_formats else []

        actual_url = info.get("webpage_url", url)

        return MediaInfo(
            title=info.get("title", "Unknown"),
            duration=info.get("duration", 0) or 0,
            uploader=info.get("uploader", info.get("channel", "Unknown")),
            platform=info.get("extractor_key", info.get("extractor", "Unknown")),
            url=actual_url,
            thumbnail=info.get("thumbnail", ""),
            filesize_approx=info.get("filesize_approx", 0) or info.get("filesize", 0) or 0,
            formats=format_options,
        )

    async def download_format(
        self,
        url: str,
        format_id: str,
        max_size_mb: float | None = None,
        merge_audio: bool = False,
        is_audio: bool = False,
        progress_hook: callable | None = None,
        chat_jid: str | None = None,
        sender_jid: str | None = None,
    ) -> Path:
        """
        Download a specific format by its format_id.

        Args:
            merge_audio: If True, merge best audio into video-only streams.
            is_audio: If True, embed metadata and thumbnail into audio file.
            progress_hook: Optional callback(downloaded_bytes, total_bytes, speed, eta).

        Returns path to the downloaded file.
        """
        limit = max_size_mb or self.max_size_mb
        output_template = self._make_output_path("dl")

        if merge_audio:
            fmt = f"{format_id}+bestaudio/{format_id}/best"
        else:
            fmt = format_id

        ydl_opts = {
            "format": fmt,
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
            "extractor_args": {"youtube": {"player_client": ["ios", "android", "mweb", "tv", "web"]}},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        if limit:
            # Filesize filter at the format level with proper grouping
            ydl_opts["format"] = f"({fmt})[filesize<=?{int(limit)}M]"

        # No hard 'max_filesize' here; we check it after download or let yt-dlp estimate
        self._add_cookies(ydl_opts)

        if is_audio:
            ydl_opts["writethumbnail"] = True
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                },
                {
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                },
                {
                    "key": "EmbedThumbnail",
                },
            ]

        return await self._download(url, ydl_opts, limit, progress_hook, chat_jid, sender_jid)

    async def download_audio(
        self,
        url: str,
        max_size_mb: float | None = None,
        progress_hook: callable | None = None,
        chat_jid: str | None = None,
        sender_jid: str | None = None,
    ) -> Path:
        """
        Download audio from URL (best quality, MP3) with metadata + thumbnail.

        Returns path to the downloaded audio file.
        """
        limit = max_size_mb or self.max_size_mb
        output_template = self._make_output_path("audio")

        ydl_opts = {
            "format": f"bestaudio[filesize<=?{int(limit)}M]/bestaudio/best",
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "writethumbnail": True,
            "extractor_args": {"youtube": {"player_client": ["ios", "android", "mweb", "tv", "web"]}},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                },
                {
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                },
                {
                    "key": "EmbedThumbnail",
                },
            ],
        }
        self._add_cookies(ydl_opts)

        return await self._download(url, ydl_opts, limit, progress_hook, chat_jid, sender_jid)

    async def download_video(
        self,
        url: str,
        max_size_mb: float | None = None,
        progress_hook: callable | None = None,
        chat_jid: str | None = None,
        sender_jid: str | None = None,
    ) -> Path:
        """
        Download video from URL (best quality, MP4).

        Returns path to the downloaded video file.
        """
        limit = max_size_mb or self.max_size_mb
        output_template = self._make_output_path("video")

        ydl_opts = {
            "format": f"(bestvideo[ext=mp4][filesize<=?{int(limit)}M]+bestaudio[ext=m4a]/best[ext=mp4][filesize<=?{int(limit)}M]/bestvideo+bestaudio/best)",
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
            "max_filesize": int(limit * 1024 * 1024),
        }
        self._add_cookies(ydl_opts)

        return await self._download(url, ydl_opts, limit, progress_hook, chat_jid, sender_jid)

    async def _download(
        self,
        url: str,
        ydl_opts: dict,
        max_size_mb: float,
        progress_hook: callable | None = None,
        chat_jid: str | None = None,
        sender_jid: str | None = None,
    ) -> Path:
        """Internal download method."""
        import yt_dlp

        downloaded_file = None
        dl_key = f"{chat_jid}:{sender_jid}" if chat_jid and sender_jid else None

        base_output = ydl_opts.get("outtmpl", "")
        if isinstance(base_output, dict):
            base_output = base_output.get("default", "")
        base_output = str(base_output).replace(".%(ext)s", "")

        if dl_key:
            self._active_downloads[dl_key] = False

        def _progress(d):
            """yt-dlp progress hook."""
            if dl_key and self._active_downloads.get(dl_key):
                raise DownloadAbortedError("Download cancelled by user")

            if progress_hook and d.get("status") == "downloading":
                try:
                    progress_hook(
                        downloaded_bytes=d.get("downloaded_bytes", 0),
                        total_bytes=d.get("total_bytes") or d.get("total_bytes_estimate", 0),
                        speed=d.get("speed", 0),
                        eta=d.get("eta", 0),
                    )
                except Exception:
                    pass

        if progress_hook:
            ydl_opts["progress_hooks"] = [_progress]

        def _run():
            nonlocal downloaded_file
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    return

                if "requested_downloads" in info:
                    for rd in info["requested_downloads"]:
                        path = rd.get("filepath")
                        if path and os.path.exists(path):
                            downloaded_file = path
                            return

                filename = ydl.prepare_filename(info)
                base = os.path.splitext(filename)[0]
                for ext in [".mp3", ".m4a", ".mp4", ".webm", ".mkv", ".opus", ".ogg", ".ts"]:
                    candidate = base + ext
                    if os.path.exists(candidate):
                        downloaded_file = candidate
                        return

                if os.path.exists(filename):
                    downloaded_file = filename

        async def _cleanup_partial():
            import glob

            if base_output and base_output != "None":
                for f in glob.glob(f"{base_output}*"):
                    try:
                        if os.path.exists(f):
                            os.remove(f)
                            log_info(f"[DOWNLOADER] Cleaned up partial file: {f}")
                    except Exception:
                        log_warning(f"[DOWNLOADER] Failed to cleanup {f}")

        try:
            log_info(f"[DOWNLOADER] Starting download: {url}")
            await asyncio.to_thread(_run)
        except DownloadAbortedError:
            log_info(f"[DOWNLOADER] Download aborted locally: {url}")
            await _cleanup_partial()
            raise
        except Exception as e:
            await _cleanup_partial()
            if "Download cancelled by user" in str(e) or isinstance(e, DownloadAbortedError):
                raise DownloadAbortedError("Download cancelled by user") from e
            
            error_msg = str(e)
            if "Requested format is not available" in error_msg and os.getenv("YOUTUBE_COOKIES_PATH"):
                error_msg += f"\nTIP: This error is often caused by invalid/expired cookies in {os.getenv('YOUTUBE_COOKIES_PATH')}. Try updating them or disabling cookies."
            
            raise DownloadError(f"Download failed: {error_msg}") from e
        finally:
            if dl_key:
                self._active_downloads.pop(dl_key, None)

        if not downloaded_file or not os.path.exists(downloaded_file):
            raise DownloadError(
                f"Download failed: No file found after download. "
                f"This often happens if the file exceeds the size limit ({max_size_mb}MB) "
                f"or the format is temporary unavailable."
            )

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

    def cancel_download(self, chat_jid: str, sender_jid: str) -> bool:
        """
        Mark an active download as cancelled.
        Returns True if a matching download was found.
        """
        dl_key = f"{chat_jid}:{sender_jid}"
        if dl_key in self._active_downloads:
            self._active_downloads[dl_key] = True
            return True
        return False

    def cancel_all_in_chat(self, chat_jid: str) -> int:
        """
        Cancel all active downloads in a specific chat.
        Returns the number of downloads cancelled.
        """
        count = 0
        for key in list(self._active_downloads.keys()):
            if key.startswith(f"{chat_jid}:"):
                self._active_downloads[key] = True
                count += 1
        return count


downloader = Downloader()
