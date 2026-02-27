"""
Shared media helpers for commands that save WhatsApp media to disk.

Consolidates the duplicated _save_media() logic from save.py and filter.py.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message

from core.logger import log_error, log_info
from core.storage import DATA_DIR, safe_jid

if TYPE_CHECKING:
    from core.client import BotClient


MEDIA_EXTENSIONS = {
    "image": ".jpg",
    "video": ".mp4",
    "sticker": ".webp",
    "document": "",
    "audio": ".ogg",
}


def get_media_caption(msg_obj: Message, media_type: str) -> str:
    """Extract caption from an image or video message, if present."""
    if media_type == "image" and msg_obj.imageMessage.caption:
        return msg_obj.imageMessage.caption
    elif media_type == "video" and msg_obj.videoMessage.caption:
        return msg_obj.videoMessage.caption
    return ""


async def save_media_to_disk(
    client: BotClient,
    message: Message,
    media_type: str,
    group_jid: str,
    filename: str,
    subfolder: str = "media",
) -> str | None:
    """Download and save a WhatsApp media message to disk.

    Args:
        client: The bot client (for downloading).
        message: The protobuf Message containing media.
        media_type: One of 'image', 'video', 'sticker', 'document', 'audio'.
        group_jid: The group JID (used for directory structure).
        filename: Base filename (without extension).
        subfolder: Subdirectory under the group folder (e.g. 'media', 'filter_media').

    Returns:
        The file path as a string, or None on failure.
    """
    try:
        media_dir = DATA_DIR / safe_jid(group_jid) / subfolder
        media_dir.mkdir(parents=True, exist_ok=True)

        ext = MEDIA_EXTENSIONS.get(media_type, "")

        if (
            media_type == "document"
            and message.documentMessage
            and message.documentMessage.fileName
        ):
            _, f_ext = os.path.splitext(message.documentMessage.fileName)
            if f_ext:
                ext = f_ext

        log_info(f"Downloading {media_type} for '{filename}'...")
        media_bytes = await client._client.download_any(message)

        if media_bytes:
            safe_name = filename.replace("/", "_").replace("\\", "_").replace(":", "_")
            file_path = media_dir / f"{safe_name}{ext}"
            with open(file_path, "wb") as f:
                f.write(media_bytes)
            log_info(f"Saved media to {file_path}")
            return str(file_path)
        else:
            log_error(f"Download returned empty bytes for '{filename}'")
    except Exception as e:
        log_error(f"Failed to save media: {e}")

    return None
