"""
Telegram → WhatsApp Auto-Forwarder.

Listens to configured Telegram channels via Pyrogram and forwards
messages (text, images, videos, audio, documents) to WhatsApp chats
or WhatsApp Channels (newsletters) via neonize.
"""

from __future__ import annotations

import os
from io import BytesIO
from typing import TYPE_CHECKING, Any

import magic as libmagic
from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import (
    AudioMessage,
    DocumentMessage,
    ImageMessage,
    Message,
    VideoMessage,
)
from neonize.utils.enum import MediaType
from PIL import Image

from core.logger import log_error, log_info, log_success, log_warning

if TYPE_CHECKING:
    from core.client import BotClient


class TelegramForwarder:
    """Bridges Telegram channels to WhatsApp chats/newsletters in real-time."""

    def __init__(self, bot_client: BotClient, config: dict[str, Any], *, max_mb: int = 50) -> None:
        self._bot = bot_client
        self._config = config
        self._max_bytes = max_mb * 1024 * 1024
        self._tg_app = None
        self._started = False

        self._rules_by_source: dict[int, list[dict]] = {}
        for rule in config.get("rules", []):
            if not rule.get("enabled", True):
                continue
            src = rule.get("source_chat_id")
            if src is not None:
                self._rules_by_source.setdefault(src, []).append(rule)

    @property
    def source_ids(self) -> list[int]:
        """All monitored Telegram chat IDs (includes normalized versions)."""
        ids = []
        for src in self._rules_by_source.keys():
            ids.append(src)
            if src > 0:
                try:
                    ids.append(int(f"-100{src}"))
                except ValueError:
                    pass
            elif str(src).startswith("-100"):
                try:
                    ids.append(int(str(src)[4:]))
                except ValueError:
                    pass
        return list(set(ids))

    @property
    def is_running(self) -> bool:
        return self._started

    @property
    def rules(self) -> list[dict]:
        return self._config.get("rules", [])

    def reload_rules(self, config: dict[str, Any]) -> None:
        """Hot-reload rules from updated config (does NOT restart Pyrogram)."""
        self._config = config
        self._rules_by_source.clear()
        for rule in config.get("rules", []):
            if not rule.get("enabled", True):
                continue
            src = rule.get("source_chat_id")
            if src is not None:
                self._rules_by_source.setdefault(src, []).append(rule)
        log_info(f"Telegram forwarder rules reloaded ({len(self._rules_by_source)} sources)")

    async def start(self) -> None:
        """Connect Pyrogram and register the message handler."""
        from pyrogram import Client, filters

        api_id = self._config.get("api_id", 0)
        api_hash = self._config.get("api_hash", "")
        phone = self._config.get("phone", "")
        session = self._config.get("session_name", "tg_forwarder")

        if not api_id or not api_hash:
            log_error("Telegram forwarder: api_id and api_hash are required")
            return

        session_file = f"{session}.session"
        if not os.path.exists(session_file):
            log_error(
                f"Telegram forwarder: Session file '{session_file}' not found. Please run the login script on your VPS or upload the file."
            )
            return

        self._tg_app = Client(
            session,
            api_id=api_id,
            api_hash=api_hash,
            phone_number=phone or None,
        )

        source_ids = self.source_ids
        if not source_ids:
            log_warning("Telegram forwarder: no enabled rules configured")
            return

        @self._tg_app.on_message(filters.chat(source_ids))
        async def _handler(client, message):
            await self._on_message(message)

        try:
            await self._tg_app.start()
            self._started = True
            log_success(
                f"Telegram forwarder connected (watching {len(source_ids)} sources: {source_ids})"
            )
        except Exception as e:
            log_error(f"Telegram forwarder failed to start: {e}")

    async def stop(self) -> None:
        """Disconnect Pyrogram gracefully."""
        if self._tg_app and self._started:
            try:
                await self._tg_app.stop()
            except Exception:
                pass
            self._started = False
            log_info("Telegram forwarder disconnected")

    async def test_forward_last(self, rule_index: int) -> dict[str, Any]:
        """Fetch the last message from a rule's source channel and forward it.

        Returns a dict with status info: chat_id, chat_type, chat_title,
        forwarded (bool), error (str or None).
        """
        rules = self._config.get("rules", [])
        if rule_index < 0 or rule_index >= len(rules):
            return {"error": f"Invalid rule index {rule_index + 1}"}

        rule = rules[rule_index]
        src = rule.get("source_chat_id")
        if src is None:
            return {"error": "Rule has no source_chat_id"}

        if not self._tg_app or not self._started:
            return {"error": "Pyrogram client is not connected"}

        chat_ids_to_try = [src]
        if src > 0:
            chat_ids_to_try.append(int(f"-100{src}"))
        elif str(src).startswith("-100"):
            try:
                chat_ids_to_try.append(int(str(src)[4:]))
            except ValueError:
                pass

        last_error = None
        for try_id in chat_ids_to_try:
            try:
                messages = []
                async for msg in self._tg_app.get_chat_history(try_id, limit=1):
                    messages.append(msg)

                if not messages:
                    last_error = f"No messages found in chat {try_id}"
                    continue

                message = messages[0]
                chat = message.chat
                chat_info = {
                    "chat_id": chat.id,
                    "chat_type": str(chat.type),
                    "chat_title": getattr(chat, "title", "") or "",
                    "message_text": (message.text or message.caption or "(media)")[:100],
                }

                try:
                    await self._dispatch(rule, message)
                    chat_info["forwarded"] = True
                    chat_info["error"] = None
                except Exception as e:
                    chat_info["forwarded"] = False
                    chat_info["error"] = str(e)

                return chat_info
            except Exception as e:
                last_error = f"chat_id={try_id}: {e}"
                continue

        return {"error": f"Could not fetch from source. {last_error}"}

    async def _on_message(self, message) -> None:
        """Handle an incoming Telegram message."""
        chat_id = message.chat.id
        chat_title = getattr(message.chat, "title", "") or ""

        rules = self._rules_by_source.get(chat_id, [])

        if not rules:
            if str(chat_id).startswith("-100"):
                try:
                    short_id = int(str(chat_id)[4:])
                    rules = self._rules_by_source.get(short_id, [])
                except ValueError:
                    pass
            elif chat_id > 0:
                try:
                    long_id = int(f"-100{chat_id}")
                    rules = self._rules_by_source.get(long_id, [])
                except ValueError:
                    pass

        if not rules:
            log_warning(
                f"TG forwarder: message from chat_id={chat_id} ({chat_title}) "
                f"but no rules match. Configured sources: {list(self._rules_by_source.keys())}"
            )
            return

        log_info(
            f"TG forwarder: forwarding message from chat_id={chat_id} ({chat_title}) "
            f"to {len(rules)} rule(s)"
        )

        for rule in rules:
            try:
                await self._dispatch(rule, message)
            except Exception as e:
                src = rule.get("source_chat_id", "?")
                log_error(f"Telegram forwarder error (source={src}): {e}")

    async def _dispatch(self, rule: dict, message) -> None:
        """Route a Telegram message to all target WhatsApp JIDs."""
        targets = rule.get("target_jids", [])
        prefix = rule.get("caption_prefix", "")

        if message.photo:
            data = await message.download(in_memory=True)
            data_bytes = data.getvalue()
            caption = self._build_caption(prefix, message.caption)
            for jid in targets:
                await self._send_photo(jid, data_bytes, caption)

        elif message.video or message.animation:
            data = await message.download(in_memory=True)
            data_bytes = data.getvalue()
            caption = self._build_caption(prefix, message.caption)
            for jid in targets:
                await self._send_video(jid, data_bytes, caption)

        elif message.audio or message.voice:
            data = await message.download(in_memory=True)
            data_bytes = data.getvalue()
            caption = self._build_caption(prefix, message.caption)
            for jid in targets:
                await self._send_audio(jid, data_bytes, caption)

        elif message.document:
            data = await message.download(in_memory=True)
            data_bytes = data.getvalue()
            caption = self._build_caption(prefix, message.caption)
            fname = message.document.file_name or "document"
            for jid in targets:
                await self._send_document(jid, data_bytes, fname, caption)

        elif message.text:
            text = self._build_caption(prefix, message.text)
            for jid in targets:
                await self._send_text(jid, text)

        else:
            return

    def _build_caption(self, prefix: str, text: str | None) -> str:
        """Combine prefix and text into a single caption string."""
        parts = []
        if prefix:
            parts.append(prefix)
        if text:
            parts.append(text)
        return " ".join(parts).strip() if parts else ""

    @staticmethod
    def _is_newsletter(jid: str) -> bool:
        return jid.endswith("@newsletter")

    async def _send_text(self, jid: str, text: str) -> None:
        """Send a plain text message."""
        if not text:
            return
        try:
            if self._is_newsletter(jid):
                msg = Message(conversation=text)
                await self._bot.raw.send_message(self._bot.to_jid(jid), msg)
            else:
                await self._bot.send(jid, text)
        except Exception as e:
            log_error(f"TG→WA text send failed ({jid}): {e}")

    async def _send_photo(self, jid: str, data: bytes, caption: str) -> None:
        """Send an image message."""
        if len(data) > self._max_bytes:
            log_warning(f"TG→WA skipping oversized image ({len(data)} bytes) to {jid}")
            return
        try:
            if self._is_newsletter(jid):
                await self._send_newsletter_media(jid, data, caption, "image")
            else:
                await self._bot.send_image(jid, data, caption=caption)
        except Exception as e:
            log_error(f"TG→WA photo send failed ({jid}): {e}")

    async def _send_video(self, jid: str, data: bytes, caption: str) -> None:
        """Send a video message."""
        if len(data) > self._max_bytes:
            log_warning(f"TG→WA skipping oversized video ({len(data)} bytes) to {jid}")
            return
        try:
            if self._is_newsletter(jid):
                await self._send_newsletter_media(jid, data, caption, "video")
            else:
                await self._bot.send_video(jid, data, caption=caption)
        except Exception as e:
            log_error(f"TG→WA video send failed ({jid}): {e}")

    async def _send_audio(self, jid: str, data: bytes, caption: str) -> None:
        """Send an audio message."""
        if len(data) > self._max_bytes:
            log_warning(f"TG→WA skipping oversized audio ({len(data)} bytes) to {jid}")
            return
        try:
            if self._is_newsletter(jid):
                await self._send_newsletter_media(jid, data, caption, "audio")
            else:
                msg = await self._bot.raw.build_audio_message(data, caption=caption)
                await self._bot.raw.send_message(self._bot.to_jid(jid), msg)
        except Exception as e:
            log_error(f"TG→WA audio send failed ({jid}): {e}")

    async def _send_document(self, jid: str, data: bytes, filename: str, caption: str) -> None:
        """Send a document message."""
        if len(data) > self._max_bytes:
            log_warning(f"TG→WA skipping oversized document ({len(data)} bytes) to {jid}")
            return
        try:
            if self._is_newsletter(jid):
                await self._send_newsletter_media(jid, data, caption, "document", filename=filename)
            else:
                await self._bot.send_document(jid, data, caption=caption, filename=filename)
        except Exception as e:
            log_error(f"TG→WA document send failed ({jid}): {e}")

    async def _send_newsletter_media(
        self,
        jid: str,
        data: bytes,
        caption: str,
        kind: str,
        *,
        filename: str = "",
    ) -> None:
        """
        Upload media through the newsletter CDN and send to a WhatsApp Channel.

        Newsletter JIDs require upload_newsletter() instead of the regular upload().
        We manually build the Message proto from the upload response.
        """
        media_type_map = {
            "image": MediaType.MediaImage,
            "video": MediaType.MediaVideo,
            "audio": MediaType.MediaAudio,
            "document": MediaType.MediaDocument,
        }
        media_type = media_type_map.get(kind, MediaType.MediaDocument)

        upload = await self._bot.raw.upload(data, media_type)
        mime = libmagic.from_buffer(data, mime=True)

        target_jid = self._bot.to_jid(jid)

        if kind == "image":
            try:
                img = Image.open(BytesIO(data))
                img.thumbnail((200, 200))
                thumb_buf = BytesIO()
                img_saveable = img if img.mode == "RGB" else img.convert("RGB")
                img_saveable.save(thumb_buf, format="JPEG")
                thumbnail = thumb_buf.getvalue()
            except Exception:
                thumbnail = b""

            msg = Message(
                imageMessage=ImageMessage(
                    URL=upload.url,
                    caption=caption or None,
                    directPath=upload.DirectPath,
                    fileEncSHA256=upload.FileEncSHA256,
                    fileLength=upload.FileLength,
                    fileSHA256=upload.FileSHA256,
                    mediaKey=upload.MediaKey,
                    mimetype=mime,
                    JPEGThumbnail=thumbnail,
                )
            )
        elif kind == "video":
            msg = Message(
                videoMessage=VideoMessage(
                    URL=upload.url,
                    caption=caption or None,
                    directPath=upload.DirectPath,
                    fileEncSHA256=upload.FileEncSHA256,
                    fileLength=upload.FileLength,
                    fileSHA256=upload.FileSHA256,
                    mediaKey=upload.MediaKey,
                    mimetype=mime,
                )
            )
        elif kind == "audio":
            msg = Message(
                audioMessage=AudioMessage(
                    URL=upload.url,
                    directPath=upload.DirectPath,
                    fileEncSHA256=upload.FileEncSHA256,
                    fileLength=upload.FileLength,
                    fileSHA256=upload.FileSHA256,
                    mediaKey=upload.MediaKey,
                    mimetype=mime,
                )
            )
        else:
            msg = Message(
                documentMessage=DocumentMessage(
                    URL=upload.url,
                    caption=caption or None,
                    directPath=upload.DirectPath,
                    fileEncSHA256=upload.FileEncSHA256,
                    fileLength=upload.FileLength,
                    fileSHA256=upload.FileSHA256,
                    mediaKey=upload.MediaKey,
                    mimetype=mime,
                    fileName=filename or "document",
                )
            )

        await self._bot.raw.send_message(target_jid, msg)
