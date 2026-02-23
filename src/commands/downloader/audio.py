"""
Audio command - Force download audio from URLs.

Extracts audio (MP3) from any supported site via yt-dlp.
"""

from commands.downloader.common import BaseMediaCommand
from core.downloader import downloader


class AudioCommand(BaseMediaCommand):
    name = "audio"
    aliases = ["mp3", "music"]
    description = "Download audio from URL"
    usage = "audio <url>"
    category = "downloader"
    cooldown = 15

    media_type = "audio"

    download_func = downloader.download_audio
