"""
Message helper utilities.

Simplifies working with neonize message events by providing
easy-to-use functions for common operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from google.protobuf.json_format import MessageToDict
from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message

from core.constants import CONTEXT_FIELDS, MEDIA_FIELDS, TEXT_SOURCES
from core.logger import log_debug, log_warning
from core.types import ChatType

if TYPE_CHECKING:
    from neonize.proto.Neonize_pb2 import MessageEv


class MessageHelper:
    """
    Helper class that wraps a MessageEv to provide easy access to message data.

    Example:
        msg = MessageHelper(event)
        print(msg.text)        # Get message text
        print(msg.sender_jid)  # Get sender's JID
        print(msg.chat_type)   # ChatType.PRIVATE or ChatType.GROUP
    """

    def __init__(self, event: MessageEv) -> None:
        """
        Create a MessageHelper from a neonize MessageEv.

        Args:
            event: The message event from neonize
        """
        self._event = event
        self._message: Message = event.Message

    @property
    def event(self) -> MessageEv:
        """Get the raw neonize event."""
        return self._event

    @property
    def raw_message(self) -> Message:
        """Get the raw protobuf Message object."""
        return self._message

    @property
    def text(self) -> str:
        """
        Get the text content of the message.

        Works with plain text, extended text, and media captions.
        """
        for field_name, attr_name in TEXT_SOURCES:
            field = getattr(self._message, field_name, None)
            if field:
                if attr_name is None:
                    return field
                value = getattr(field, attr_name, None)
                if value:
                    return value
        return ""

    @property
    def sender_jid(self) -> str:
        """
        Get the sender's JID (Jabber ID / WhatsApp ID).

        Format: "123456@lid" or "1234567890@s.whatsapp.net"
        """
        source = self._event.Info.MessageSource
        if source.Sender.User:
            return f"{source.Sender.User}@{source.Sender.Server}"
        return f"{source.Chat.User}@{source.Chat.Server}"

    @property
    def sender_number(self) -> str:
        """
        Get just the phone number part of the sender's JID.

        Returns:
            User ID without @lid or @s.whatsapp.net suffix
        """
        source = self._event.Info.MessageSource
        if source.Sender.User:
            return source.Sender.User
        return source.Chat.User

    @property
    def sender_name(self) -> str:
        """
        Get the sender's push name (display name).

        Returns:
            Display name or phone number if not available
        """
        return self._event.Info.Pushname or self.sender_number

    @property
    def chat_jid(self) -> str:
        """
        Get the chat JID where the message was sent.

        For private: "123456@lid" or "1234567890@s.whatsapp.net"
        For group:   "1234567890-1234567890@g.us"
        """
        chat = self._event.Info.MessageSource.Chat
        return f"{chat.User}@{chat.Server}"

    @property
    def chat_type(self) -> ChatType:
        """
        Determine if this is a private or group message.

        Returns:
            ChatType.PRIVATE or ChatType.GROUP
        """
        return ChatType.GROUP if self.is_group else ChatType.PRIVATE

    @property
    def is_group(self) -> bool:
        """Check if message is from a group chat."""
        return "@g.us" in self.chat_jid

    @property
    def is_private(self) -> bool:
        """Check if message is from a private chat."""
        return self.chat_type == ChatType.PRIVATE

    @property
    def message_id(self) -> str:
        """Get the unique message ID."""
        return self._event.Info.ID

    @property
    def is_from_me(self) -> bool:
        """Check if this message was sent by the bot itself."""
        return self._event.Info.MessageSource.IsFromMe

    @property
    def timestamp(self) -> int:
        """Get the message timestamp (Unix epoch)."""
        return self._event.Info.Timestamp

    @property
    def mentions(self) -> list[str]:
        """
        Get list of mentioned JIDs from the message.

        Returns:
            List of JID strings that were @mentioned in this message
        """
        ctx = self._extract_context_info(self._message)
        if ctx:
            try:
                return list(ctx.mentionedJid) if ctx.mentionedJid else []
            except Exception:
                pass
        return []

    @property
    def quoted_message(self) -> dict | None:
        """
        Get the quoted/replied message info if this is a reply.

        Returns:
            Dict with 'sender', 'text', 'id' or None if not a reply
        """
        try:
            ctx = self._extract_context_info(self._message)
            if not ctx or not ctx.quotedMessage:
                return None

            quoted = ctx.quotedMessage
            quoted_text = self._extract_quoted_text(quoted)
            stanza_id = getattr(
                ctx,
                "stanzaId",
                getattr(ctx, "stanza_id", getattr(ctx, "stanzaID", "")),
            )

            return {
                "sender": getattr(ctx, "participant", "") or getattr(ctx, "remoteJid", ""),
                "text": quoted_text,
                "id": stanza_id,
            }
        except Exception:
            pass

        return None

    def is_quoted_from(self, jid: str) -> bool:
        """
        Check if the quoted message was sent by the specified JID.

        Args:
            jid: The JID to compare against (e.g., bot's JID)

        Returns:
            True if the quoted message sender matches the JID
        """
        try:
            ctx = self._extract_context_info(self._message)
            if not ctx or not ctx.quotedMessage:
                log_debug("is_quoted_from: no quoted message")
                return False

            participant = getattr(ctx, "participant", "")
            log_debug(f"is_quoted_from: participant='{participant}', checking jid='{jid}'")

            quoted_user = participant.split("@")[0]
            check_user = jid.split("@")[0]
            result = quoted_user == check_user
            log_debug(
                f"is_quoted_from: quoted_user={quoted_user}, check_user={check_user}, result={result}"
            )
            return result
        except Exception as e:
            log_debug(f"is_quoted_from: exception {e}")
            return False

    @property
    def quoted_raw(self) -> Message | None:
        """
        Get the raw Message protobuf object from the quoted message.

        Useful for downloading media from quoted messages.

        Returns:
            The quoted Message object, or None if not a reply
        """
        try:
            ctx = self._extract_context_info(self._message)
            if not ctx or not ctx.quotedMessage:
                return None

            quoted = ctx.quotedMessage

            try:
                if quoted.HasField("viewOnceMessage"):
                    return quoted.viewOnceMessage.message
            except Exception:
                pass

            return quoted
        except Exception:
            pass

        return None

    def _extract_quoted_text(self, quoted) -> str:
        """Extract text from quoted message."""
        for field_name, attr_name in TEXT_SOURCES:
            field = getattr(quoted, field_name, None)
            if field:
                if attr_name is None:
                    return field
                value = getattr(field, attr_name, None)
                if value:
                    return value
        return ""

    def _extract_context_info(self, raw_msg):
        """Extract contextInfo from any message type that has it."""
        for field_name in CONTEXT_FIELDS:
            try:
                if raw_msg.HasField(field_name):
                    field = getattr(raw_msg, field_name)
                    if field.HasField("contextInfo"):
                        return field.contextInfo
            except Exception:
                continue
        return None

    def get_media_message(self, client=None) -> tuple[Message | None, str | None]:
        """
        Get the Message object containing media (direct or quoted) available for download.
        Uses HasField for protobuf field detection.
        """
        try:
            msg_dict = MessageToDict(self._event.Message, preserving_proto_field_name=True)
            non_empty = {k: v for k, v in msg_dict.items() if v}
            log_debug(f"Raw message fields: {list(non_empty.keys())}")
        except Exception as e:
            log_warning(f"Failed to dump message: {e}")

        quoted = self.quoted_raw
        if quoted:
            media_type = self._detect_media_type(quoted)
            if media_type:
                log_debug(f"Detected quoted media: {media_type}")
                return quoted, media_type

        media_type = self._detect_media_type(self._event.Message)
        if media_type:
            log_debug(f"Detected direct media: {media_type}")
            return self._event.Message, media_type

        return None, None

    def _detect_media_type(self, msg) -> str | None:
        """Detect media type from a Message object."""
        for field_name, media_type in MEDIA_FIELDS:
            try:
                if msg.HasField(field_name):
                    return media_type
            except Exception:
                continue
        return None

    def __repr__(self) -> str:
        return f"MessageHelper(text={self.text!r}, sender={self.sender_name}, chat_type={self.chat_type.name})"
