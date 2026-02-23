"""
Video command - Force download video from URLs.

Downloads video (MP4) from any supported site via yt-dlp.
"""

from commands.downloader.common import BaseMediaCommand
from core.downloader import downloader


class VideoCommand(BaseMediaCommand):
    name = "video"
    aliases = ["vid", "mp4"]
    description = "Download video from URL"
    usage = "video <url>"
    category = "downloader"
    cooldown = 15

    media_type = "video"

    download_func = downloader.download_video
