"""
Simplified async client wrapper for neonize.

Provides easy-to-use methods for common WhatsApp operations.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from neonize.aioze.client import NewAClient
from neonize.proto.Neonize_pb2 import JID
from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import (
    ContextInfo,
    DeviceListMetadata,
    ExtendedTextMessage,
    InteractiveMessage,
    Message,
    MessageContextInfo,
)
from neonize.utils.enum import VoteType
from neonize.utils.jid import build_jid

from core.message import MessageHelper

if TYPE_CHECKING:
    from neonize.proto.Neonize_pb2 import SendResponse


class BotClient:
    """
    Simplified wrapper around NewAClient.

    Provides easy methods like reply() and send() that hide
    the complexity of the underlying neonize library.

    Example:
        client = BotClient(NewAClient("my_bot"))
        await client.reply(msg, "Hello!")
        await client.send("123456@lid", "Hi there!")
    """

    def __init__(self, neonize_client: NewAClient) -> None:
        """
        Create a BotClient wrapper.

        Args:
            neonize_client: The underlying neonize async client
        """
        self._client = neonize_client

    def to_jid(self, jid_str: str | JID) -> JID:
        """Convert a JID string to a JID object."""
        if isinstance(jid_str, JID):
            return jid_str

        if "@" in jid_str:
            user, server = jid_str.split("@", 1)
            return build_jid(user, server)
        else:
            return build_jid(jid_str, "s.whatsapp.net")

    @staticmethod
    def normalize_user_jid(user_input: str, use_lid: bool = True) -> str:
        """
        Normalize a user input (phone number or @mention) to a JID string.

        Args:
            user_input: Phone number, @mention, or raw number
            use_lid: If True, use @lid format (default). If False, use @s.whatsapp.net

        Returns:
            Normalized JID string like "123456@lid" or "123456@s.whatsapp.net"
        """
        cleaned = user_input.replace("@", "").strip()

        if cleaned.endswith("@lid") or cleaned.endswith("@s.whatsapp.net"):
            return cleaned

        suffix = "@lid" if use_lid else "@s.whatsapp.net"
        return f"{cleaned}{suffix}"

    @property
    def raw(self) -> NewAClient:
        """Get the underlying neonize client for advanced operations."""
        return self._client

    async def check_connected(self) -> bool:
        """
        Check if the client is connected to WhatsApp.

        This is async because neonize uses asyncio.to_thread() internally.
        """
        result = self._client.is_connected
        if hasattr(result, "__await__"):
            return await result
        return bool(result)

    async def check_logged_in(self) -> bool:
        """
        Check if the client is logged in.

        This is async because neonize uses asyncio.to_thread() internally.
        Use this instead of is_logged_in property to avoid coroutine warnings.
        """
        result = self._client.is_logged_in
        if hasattr(result, "__await__"):
            return await result
        return bool(result)

    async def resolve_jid_pair(self, jid: str) -> dict[str, str | None]:
        """
        Resolve both PN and LID formats for a JID.

        Uses neonize's get_lid_from_pn/get_pn_from_lid functions with caching.

        Args:
            jid: Any valid JID string (PN or LID format)

        Returns:
            Dict with keys "pn" and "lid", values may be None if resolution fails
            Example: {"pn": "1234567890@s.whatsapp.net", "lid": "123456@lid"}
        """
        from core.jid_resolver import resolve_pair

        return await resolve_pair(jid, self)

    async def match_jids(self, jid1: str, jid2: str) -> bool:
        """
        Check if two JIDs refer to the same user, regardless of format.

        Handles comparison between PN (@s.whatsapp.net) and LID (@lid) formats.

        Args:
            jid1: First JID to compare
            jid2: Second JID to compare

        Returns:
            True if both JIDs refer to the same user
        """
        from core.jid_resolver import jids_match

        return await jids_match(jid1, jid2, self)

    def _apply_forwarded(self, message: Message, score: int = 1) -> Message:
        """
        Apply forwarded context to a message.

        This marks the message as forwarded with a high score (999),
        which hides the original sender's identity.

        Args:
            message: The Message object to modify
            score: The forwarding score to apply

        Returns:
            The modified Message object
        """
        context = ContextInfo(isForwarded=True, forwardingScore=score)
        for field in [
            "extendedTextMessage",
            "imageMessage",
            "videoMessage",
            "audioMessage",
            "documentMessage",
            "stickerMessage",
            "interactiveMessage",
        ]:
            if message.HasField(field):
                getattr(message, field).contextInfo.MergeFrom(context)
                break
        return message

    async def forward_message(
        self,
        to: str | JID,
        message: Message,
        mark_forwarded: bool = True,
        score: int = 1,
    ) -> SendResponse:
        """
        Forward/resend a Message protobuf to a chat.

        Args:
            to: The JID to forward to
            message: The Message protobuf to forward
            mark_forwarded: If True, mark as forwarded (shows "Forwarded" label)

        Returns:
            SendResponse from the server
        """
        if mark_forwarded:
            self._apply_forwarded(message, score)
        return await self._client.send_message(self.to_jid(to), message)

    async def forward_message_with_quote(
        self,
        to: str | JID,
        message: Message,
        quoted_id: str,
        quoted_message: Message,
        quoted_participant: str | None = None,
        remote_jid: str | None = None,
        mark_forwarded: bool = True,
        score: int = 1,
    ) -> SendResponse:
        """
        Forward/resend a Message protobuf while also quoting another message.

        This sends the content of the message but with a quote reference
        to the original message, providing context.

        Args:
            to: The JID to forward to
            message: The Message protobuf to forward (the content)
            quoted_id: The ID of the message to quote
            quoted_message: The Message protobuf to show in the quote preview
            quoted_participant: JID of who sent the quoted message (for attribution)
            remote_jid: Original chat JID if quoting from a different chat (for cross-chat quotes)
            mark_forwarded: If True, mark as forwarded (shows "Forwarded" label)
            score: Forwarding score

        Returns:
            SendResponse from the server
        """
        quote_context = ContextInfo(
            stanzaID=quoted_id,
            quotedMessage=quoted_message,
        )

        if quoted_participant:
            quote_context.participant = quoted_participant

        if remote_jid:
            quote_context.remoteJID = remote_jid

        if mark_forwarded:
            quote_context.isForwarded = True
            quote_context.forwardingScore = score

        for field in [
            "extendedTextMessage",
            "imageMessage",
            "videoMessage",
            "audioMessage",
            "documentMessage",
            "stickerMessage",
            "interactiveMessage",
        ]:
            if message.HasField(field):
                getattr(message, field).contextInfo.MergeFrom(quote_context)
                break
        else:
            if message.HasField("conversation"):
                text = message.conversation
                message.ClearField("conversation")
                message.extendedTextMessage.text = text
                message.extendedTextMessage.contextInfo.MergeFrom(quote_context)

        return await self._client.send_message(self.to_jid(to), message)

    async def mark_read(self, msg: MessageHelper) -> None:
        """
        Mark a message as read.

        Args:
            msg: The MessageHelper of the message to mark as read
        """
        from neonize.utils.enum import ReceiptType

        try:
            await self._client.mark_read(
                msg.event.Info.ID,
                chat=self.to_jid(msg.chat_jid),
                sender=self.to_jid(msg.sender_jid),
                receipt=ReceiptType.READ,
            )
        except Exception:
            pass

    async def send_reaction(
        self,
        msg: MessageHelper,
        emoji: str,
    ) -> SendResponse:
        """
        Send a reaction to a message.

        Args:
            msg: The MessageHelper of the message to react to
            emoji: The emoji to react with (e.g., "👍", "❤️")

        Returns:
            SendResponse from the server
        """
        reaction_msg = await self._client.build_reaction(
            chat=self.to_jid(msg.chat_jid),
            sender=self.to_jid(msg.sender_jid),
            message_id=msg.event.Info.ID,
            reaction=emoji,
        )
        return await self._client.send_message(
            self.to_jid(msg.chat_jid),
            reaction_msg,
        )

    async def edit_message(
        self,
        chat_jid: str | JID,
        message_id: str,
        new_text: str,
    ) -> SendResponse:
        """
        Edit a previously sent text message.

        Args:
            chat_jid: The chat where the message was sent
            message_id: The ID of the message to edit
            new_text: The new text content

        Returns:
            SendResponse from the server
        """
        new_message = Message(conversation=new_text)
        return await self._client.edit_message(
            self.to_jid(chat_jid),
            message_id,
            new_message,
        )

    async def send_quoted(
        self,
        to: str | JID,
        text: str,
        quoted_id: str,
        quoted_text: str = "",
        participant: str | JID | None = None,
    ) -> SendResponse:
        """
        Send a message quoting another message by ID.

        Args:
            to: The JID to send to
            text: The text to send
            quoted_id: The ID of the message to quote
            quoted_text: The text of the quoted message (for display)
            participant: JID of the sender of the quoted message (for groups)

        Returns:
            SendResponse from the server
        """
        participant_str = None
        if participant:
            if isinstance(participant, str):
                participant_str = participant
            else:
                participant_str = f"{participant.User}@{participant.Server}"
        else:
            try:
                device = await self._client.get_me()
                if device and device.JID:
                    participant_str = f"{device.JID.User}@{device.JID.Server}"
            except Exception:
                pass

        context = ContextInfo(
            stanzaID=quoted_id,
            participant=participant_str,
            quotedMessage=Message(conversation=quoted_text) if quoted_text else None,
        )

        msg = Message(
            extendedTextMessage=ExtendedTextMessage(
                text=text,
                contextInfo=context,
            )
        )

        return await self._client.send_message(self.to_jid(to), msg)

    async def send_reply_to_message(
        self,
        to: str | JID,
        text: str,
        quoted_id: str,
        quoted_message: Message | None = None,
        quoted_participant: str | None = None,
        remote_jid: str | None = None,
    ) -> SendResponse:
        """
        Send a message that replies to/quotes another message by ID.

        Uses neonize's mention parsing for @mentions.

        Args:
            to: The JID to send to
            text: The text to send
            quoted_id: The ID of the message to quote
            quoted_message: The Message protobuf to quote (for preview)
            quoted_participant: JID of who sent the quoted message (for attribution)
            remote_jid: Original chat JID if quoting from a different chat

        Returns:
            SendResponse from the server
        """
        mentioned_jids = self._client._parse_mention(text, are_lids=True) or None

        context = ContextInfo(
            stanzaID=quoted_id,
            quotedMessage=quoted_message,
            mentionedJID=mentioned_jids,
        )

        if quoted_participant:
            context.participant = quoted_participant

        if remote_jid:
            context.remoteJID = remote_jid

        msg = Message(
            extendedTextMessage=ExtendedTextMessage(
                text=text,
                contextInfo=context,
            )
        )

        return await self._client.send_message(self.to_jid(to), msg)

    async def reply_privately_to(
        self,
        user_jid: str | JID,
        text: str,
        quoted_id: str,
        quoted_sender: str,
        quoted_chat: str,
        quoted_text: str = "",
    ) -> SendResponse:
        """
        Send a private message to a user quoting a group message.

        This sends a DM to the user with a quote bubble that references
        the original message from the group.

        Args:
            user_jid: The user's JID to send the private message to
            text: The text to send
            quoted_id: The ID of the message to quote
            quoted_sender: The sender JID of the quoted message
            quoted_chat: The chat JID where the quoted message was sent (group)
            quoted_text: The text of the quoted message (for display)

        Returns:
            SendResponse from the server
        """
        from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import (
            ContextInfo,
            ExtendedTextMessage,
        )

        context = ContextInfo(
            stanzaID=quoted_id,
            participant=quoted_sender,
            remoteJID=quoted_chat,
            quotedMessage=Message(conversation=quoted_text) if quoted_text else None,
        )

        msg = Message(
            extendedTextMessage=ExtendedTextMessage(
                text=text,
                contextInfo=context,
            )
        )

        return await self._client.send_message(self.to_jid(user_jid), msg)

    async def reply(
        self,
        msg: MessageHelper,
        text: str,
        privately: bool = False,
        forwarded: bool = False,
        score: int = 1,
        **kwargs: dict,
    ) -> SendResponse:
        """
        Reply to a message with text.

        This sends a message to the same chat where the original
        message was received.

        Args:
            msg: The MessageHelper of the message to reply to
            text: The text to send
            privately: Whether to reply privately
            forwarded: Whether to forward the message
            score: The forwarding score to apply

        Returns:
            SendResponse from the server
        """
        msge = await self._client.build_reply_message(
            text, msg.event, reply_privately=privately, **kwargs
        )
        if forwarded:
            self._apply_forwarded(msge, score)
        return await self._client.send_message(self.to_jid(msg.chat_jid), msge)

    async def send(
        self,
        to: str | JID,
        text: str,
        forwarded: bool = False,
        mentions_are_lids: bool = True,
        **kwargs: dict,
    ) -> SendResponse:
        """
        Send a text message to a JID.

        Args:
            to: The JID to send to
            text: The text to send
            forwarded: Whether to mark the message as forwarded
            mentions_are_lids: If True (default), treat @mentions as LIDs
        """
        mention_pattern = r"@(\d+)"
        mentions = re.findall(mention_pattern, text)

        suffix = "@lid" if mentions_are_lids else "@s.whatsapp.net"
        mentioned_jid = [f"{m}{suffix}" for m in mentions] if mentions else None

        msg = Message(
            extendedTextMessage=ExtendedTextMessage(
                text=text,
                contextInfo=ContextInfo(
                    mentionedJID=mentioned_jid,
                ),
            )
        )

        if forwarded:
            self._apply_forwarded(msg)
        return await self._client.send_message(self.to_jid(to), msg)

    async def send_message(
        self,
        to: str | JID,
        message: Message | str,
        forwarded: bool = False,
        **kwargs,
    ) -> SendResponse:
        """
        Send a message with full control.

        This is a pass-through to the underlying neonize send_message
        for when you need more control.

        Args:
            to: The JID to send to
            message: Message object or text string
            forwarded: Whether to mark the message as forwarded
            **kwargs: Additional arguments for send_message

        Returns:
            SendResponse from the server
        """
        if forwarded and isinstance(message, Message):
            self._apply_forwarded(message)
        return await self._client.send_message(self.to_jid(to), message, **kwargs)

    async def send_buttons(
        self,
        to: str | JID,
        text: str,
        buttons: list[dict],
        footer: str = "",
        title: str = "",
        forwarded: bool = False,
    ) -> SendResponse:
        """
        Send a message with interactive buttons.

        Args:
            to: Recipient JID
            text: Body text
            buttons: List of button dicts. Supported types:
                - {"type": "copy", "text": "Copy Code", "code": "123"}
                - {"type": "url", "text": "Open Link", "url": "https://..."}
                - {"type": "call", "text": "Call Me", "phone": "+123456"}
            footer: Optional footer text
            title: Optional title text
            forwarded: Whether to mark the message as forwarded

        Returns:
            SendResponse
        """
        native_buttons = []

        for btn in buttons:
            b_type = btn.get("type", "").lower()
            b_text = btn.get("text", "Button")

            if b_type == "copy":
                native_buttons.append(
                    InteractiveMessage.NativeFlowMessage.NativeFlowButton(
                        name="cta_copy",
                        buttonParamsJSON=json.dumps(
                            {
                                "display_text": b_text,
                                "id": f"copy_{b_text}",
                                "copy_code": btn.get("code", ""),
                            },
                            separators=(",", ":"),
                        ),
                    )
                )
            elif b_type == "url":
                native_buttons.append(
                    InteractiveMessage.NativeFlowMessage.NativeFlowButton(
                        name="cta_url",
                        buttonParamsJSON=json.dumps(
                            {
                                "display_text": b_text,
                                "url": btn.get("url", ""),
                                "merchant_url": btn.get("url", ""),
                            },
                            separators=(",", ":"),
                        ),
                    )
                )
            elif b_type == "call":
                native_buttons.append(
                    InteractiveMessage.NativeFlowMessage.NativeFlowButton(
                        name="cta_call",
                        buttonParamsJSON=json.dumps(
                            {"display_text": b_text, "id": f"call_{b_text}"},
                            separators=(",", ":"),
                        ),
                    )
                )

        context_info = (
            ContextInfo(isForwarded=True, forwardingScore=999) if forwarded else ContextInfo()
        )

        message = Message(
            messageContextInfo=MessageContextInfo(
                deviceListMetadata=DeviceListMetadata(),
                deviceListMetadataVersion=2,
            ),
            interactiveMessage=InteractiveMessage(
                body=InteractiveMessage.Body(text=text),
                footer=InteractiveMessage.Footer(text=footer),
                header=InteractiveMessage.Header(title=title, hasMediaAttachment=False),
                nativeFlowMessage=InteractiveMessage.NativeFlowMessage(buttons=native_buttons),
                contextInfo=context_info,
            ),
        )

        return await self._client.send_message(self.to_jid(to), message)

    async def send_buttons_classic(
        self,
        to: str | JID,
        text: str,
        buttons: list[dict],
        footer: str = "",
        image: bytes | None = None,
        forwarded: bool = False,
    ) -> SendResponse:
        """
        Send a message with classic response buttons.

        This uses the older ButtonsMessage format which is more reliable.

        Args:
            to: Recipient JID
            text: Body/content text
            buttons: List of button dicts with format:
                - {"id": ".command", "text": "Button Label"}
            footer: Optional footer text
            image: Optional image bytes for header
            forwarded: Whether to mark as forwarded

        Returns:
            SendResponse
        """
        import json

        from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import (
            ButtonsMessage,
            DocumentMessage,
        )

        button_objects = []
        for btn in buttons:
            btn_id = btn.get("id", "")
            btn_text = btn.get("text", "Button")

            if btn.get("type") == "list" and btn.get("sections"):
                button_objects.append(
                    ButtonsMessage.Button(
                        buttonID="action",
                        buttonText=ButtonsMessage.Button.ButtonText(displayText=btn_text),
                        type=ButtonsMessage.Button.Type.NATIVE_FLOW,
                        nativeFlowInfo=ButtonsMessage.Button.NativeFlowInfo(
                            name="single_select",
                            paramsJSON=json.dumps(
                                {
                                    "title": btn.get("title", "Select"),
                                    "sections": btn.get("sections", []),
                                },
                                separators=(",", ":"),
                            ),
                        ),
                    )
                )
            else:
                button_objects.append(
                    ButtonsMessage.Button(
                        buttonID=btn_id,
                        buttonText=ButtonsMessage.Button.ButtonText(displayText=btn_text),
                        type=ButtonsMessage.Button.Type.RESPONSE,
                    )
                )

        if image:
            image_msg = await self._client.build_image_message(image, caption=text, viewonce=True)

            context = ContextInfo(
                isForwarded=True,
                forwardingScore=1,
                externalAdReply=ContextInfo.ExternalAdReplyInfo(
                    title="Zero Ichi Bot",
                    body="Menu",
                    mediaType=ContextInfo.ExternalAdReplyInfo.MediaType.IMAGE,
                    renderLargerThumbnail=True,
                ),
            )

            image_msg.imageMessage.contextInfo.MergeFrom(context)

            buttons_msg = ButtonsMessage(
                contentText=text,
                footerText=footer,
                headerType=ButtonsMessage.HeaderType.IMAGE,
                imageMessage=image_msg.imageMessage,
                buttons=button_objects,
            )
        else:
            xlsx_bytes = bytes(
                [
                    0x50,
                    0x4B,
                    0x03,
                    0x04,
                    0x14,
                    0x00,
                    0x00,
                    0x00,
                    0x08,
                    0x00,
                    0x00,
                    0x00,
                    0x21,
                    0x00,
                    0xB5,
                    0x55,
                    0x30,
                    0x23,
                    0xF4,
                    0x00,
                    0x00,
                    0x00,
                    0x4C,
                    0x01,
                    0x00,
                    0x00,
                    0x13,
                    0x00,
                    0x00,
                    0x00,
                ]
                + [0x00] * 200
            )

            upload = await self._client.upload(xlsx_bytes)

            doc_context = ContextInfo(
                isForwarded=True,
                forwardingScore=1,
                externalAdReply=ContextInfo.ExternalAdReplyInfo(
                    title="┈──┈──┈──┈──┈──┈──┈──┈──┈",
                    body="Zero Ichi",
                    mediaType=ContextInfo.ExternalAdReplyInfo.MediaType.IMAGE,
                    thumbnailURL="https://files.catbox.moe/cbmsvs.png",
                    renderLargerThumbnail=True,
                ),
            )

            doc_msg = DocumentMessage(
                URL=upload.url,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                fileSHA256=upload.FileSHA256,
                fileLength=len(xlsx_bytes),
                mediaKey=upload.MediaKey,
                fileName="─ ─┈⟢ Zero Ichi Bot ⟣┈─ ─",
                fileEncSHA256=upload.FileEncSHA256,
                directPath=upload.DirectPath,
                caption=text,
                contextInfo=doc_context,
            )

            buttons_msg = ButtonsMessage(
                documentMessage=doc_msg,
                contentText=text,
                footerText=footer,
                headerType=ButtonsMessage.HeaderType.DOCUMENT,
                buttons=button_objects,
            )

        message = Message(buttonsMessage=buttons_msg)

        return await self._client.send_message(self.to_jid(to), message)

    async def send_image(
        self,
        to: str | JID,
        file: str | bytes,
        caption: str = "",
        quoted: any = None,
        forwarded: bool = False,
    ) -> SendResponse:
        """
        Send an image.

        Args:
            to: Recipient JID
            file: Image file path or bytes
            caption: Optional caption
            quoted: Optional message to quote
            forwarded: Whether to mark the message as forwarded
        """
        msg = await self._client.build_image_message(file, caption=caption, quoted=quoted)
        if forwarded:
            self._apply_forwarded(msg)
        return await self._client.send_message(self.to_jid(to), msg)

    async def send_video(
        self,
        to: str | JID,
        file: str | bytes,
        caption: str = "",
        quoted: any = None,
        forwarded: bool = False,
    ) -> SendResponse:
        """
        Send a video.

        Args:
            to: Recipient JID
            file: Video file path or bytes
            caption: Optional caption
            quoted: Optional message to quote
            forwarded: Whether to mark the message as forwarded
        """
        msg = await self._client.build_video_message(file, caption=caption, quoted=quoted)
        if forwarded:
            self._apply_forwarded(msg)
        return await self._client.send_message(self.to_jid(to), msg)

    async def send_sticker(
        self,
        to: str | JID,
        file: str | bytes,
        quoted: any = None,
        forwarded: bool = False,
        **kwargs,
    ) -> SendResponse:
        """
        Send a sticker.

        Args:
            to: Recipient JID
            file: Sticker file path or bytes
            quoted: Optional message to quote
            forwarded: Whether to mark the message as forwarded
            **kwargs: Additional arguments to pass to build_sticker_message
        """
        msg = await self._client.build_sticker_message(file, quoted=quoted, **kwargs)
        if forwarded:
            self._apply_forwarded(msg)
        return await self._client.send_message(self.to_jid(to), msg)

    async def send_poll(
        self,
        to: str | JID,
        question: str,
        options: list[str],
        multi_select: bool = False,
    ) -> SendResponse:
        """
        Send a poll to a chat.

        Args:
            to: Recipient JID
            question: The poll question
            options: List of answer options (2-12)
            multi_select: Allow multiple selections (default: single select)
        """
        vote_type = VoteType.MULTIPLE if multi_select else VoteType.SINGLE
        poll_msg = await self._client.build_poll_vote_creation(question, options, vote_type)
        return await self._client.send_message(self.to_jid(to), poll_msg)

    async def send_document(
        self,
        to: str | JID,
        file: str | bytes,
        caption: str = "",
        filename: str = "document",
        quoted: any = None,
        forwarded: bool = False,
        **kwargs,
    ) -> SendResponse:
        """
        Send a document.

        Args:
            to: Recipient JID
            file: Document file path or bytes
            caption: Optional caption
            filename: Filename for the document
            quoted: Optional message to quote
            forwarded: Whether to mark the message as forwarded
        """
        msg = await self._client.build_document_message(
            file,
            caption=caption,
            filename=filename or caption,
            quoted=quoted,
        )
        if forwarded:
            self._apply_forwarded(msg)
        return await self._client.send_message(self.to_jid(to), msg)

    async def send_menu_document(
        self,
        to: str | JID,
        title: str,
        caption: str,
        forwarded: bool = True,
    ) -> SendResponse:
        """
        Send a fake document message that displays as a menu.

        This creates a minimal xlsx file to display a nice header title
        with the caption as the menu content.

        Args:
            to: Recipient JID
            title: The document title (displays as header)
            caption: The menu content/body text
            forwarded: Whether to mark as forwarded (default True)

        Returns:
            SendResponse
        """

        from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import DocumentMessage

        xlsx_bytes = bytes(
            [
                0x50,
                0x4B,
                0x03,
                0x04,
                0x14,
                0x00,
                0x00,
                0x00,
                0x08,
                0x00,
                0x00,
                0x00,
                0x21,
                0x00,
                0xB5,
                0x55,
                0x30,
                0x23,
                0xF4,
                0x00,
                0x00,
                0x00,
                0x4C,
                0x01,
                0x00,
                0x00,
                0x13,
                0x00,
                0x00,
                0x00,
                0x5B,
                0x43,
                0x6F,
                0x6E,
                0x74,
                0x65,
                0x6E,
                0x74,
                0x5F,
                0x54,
                0x79,
                0x70,
                0x65,
                0x73,
                0x5D,
                0x2E,
                0x78,
                0x6D,
                0x6C,
                0xB5,
            ]
            + [0x00] * 200
        )

        upload = await self._client.upload(xlsx_bytes)

        doc_msg = DocumentMessage(
            URL=upload.url,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            title=title,
            fileSHA256=upload.FileSHA256,
            fileLength=len(xlsx_bytes),
            mediaKey=upload.MediaKey,
            fileName=title,
            fileEncSHA256=upload.FileEncSHA256,
            directPath=upload.DirectPath,
            caption=caption,
            contactVcard=False,
        )

        message = Message(documentMessage=doc_msg)

        if forwarded:
            self._apply_forwarded(message)

        return await self._client.send_message(self.to_jid(to), message)

    async def send_audio(
        self,
        to: str | JID,
        file: str | bytes,
        quoted: any = None,
        caption: str = "",
        forwarded: bool = False,
        **kwargs,
    ) -> SendResponse:
        """
        Send an audio file.

        Args:
            to: Recipient JID
            file: Audio file path or bytes
            quoted: Optional message to quote
            caption: Optional caption (unused but kept for API consistency)
            forwarded: Whether to mark the message as forwarded
        """
        msg = await self._client.build_audio_message(file, quoted=quoted)
        if forwarded:
            self._apply_forwarded(msg)
        return await self._client.send_message(self.to_jid(to), msg)

    async def send_media(
        self,
        to: str | JID,
        media_type: str,
        data: str | bytes,
        caption: str = "",
        filename: str = "file",
        quoted: any = None,
        forwarded: bool = False,
        **kwargs,
    ) -> SendResponse:
        """
        Generic method to send media (path or bytes).
        Reduces boilerplace if/else checks in bot logic.

        Args:
            to: Recipient JID
            media_type: Type of media (image, video, sticker, audio, document)
            data: Media file path or bytes
            caption: Optional caption
            filename: Filename for documents
            quoted: Optional message to quote
            forwarded: Whether to mark the message as forwarded
            **kwargs: Additional arguments to pass to build_media_message
        """
        handlers = {
            "image": lambda: self.send_image(
                to, data, caption, quoted=quoted, forwarded=forwarded, **kwargs
            ),
            "video": lambda: self.send_video(
                to, data, caption, quoted=quoted, forwarded=forwarded, **kwargs
            ),
            "sticker": lambda: self.send_sticker(
                to, data, quoted=quoted, forwarded=forwarded, **kwargs
            ),
            "audio": lambda: self.send_audio(
                to, data, caption=caption, quoted=quoted, forwarded=forwarded, **kwargs
            ),
            "document": lambda: self.send_document(
                to, data, caption, filename=filename, quoted=quoted, forwarded=forwarded, **kwargs
            ),
        }

        handler = handlers.get(media_type.lower())
        if handler:
            return await handler()

        return await self.send_message(
            to, f"[{media_type}] {caption}", forwarded=forwarded, **kwargs
        )

    async def send_media_with_private_reply(
        self,
        to: str | JID,
        media_type: str,
        data: str | bytes,
        caption: str = "",
        quoted_id: str = "",
        quoted_sender: str = "",
        quoted_chat: str = "",
        quoted_text: str = "",
        forwarded: bool = False,
        **kwargs,
    ) -> SendResponse:
        """
        Send media with private reply context (quoting a message from another chat).

        Args:
            to: Recipient JID
            media_type: Type of media (image, video, sticker, audio, document)
            data: Media file path or bytes
            caption: Optional caption
            quoted_id: The ID of the message to quote
            quoted_sender: The sender JID of the quoted message
            quoted_chat: The chat JID where the quoted message was sent
            quoted_text: The text of the quoted message (for display)
            forwarded: Whether to mark the message as forwarded
        """
        msg = None
        media_type_lower = media_type.lower()

        if media_type_lower == "image":
            msg = await self._client.build_image_message(data, caption=caption)
        elif media_type_lower == "video":
            msg = await self._client.build_video_message(data, caption=caption)
        elif media_type_lower == "sticker":
            msg = await self._client.build_sticker_message(data, **kwargs)
        elif media_type_lower == "audio":
            msg = await self._client.build_audio_message(data)
        elif media_type_lower == "document":
            msg = await self._client.build_document_message(
                data, caption=caption, filename=kwargs.get("filename", "file")
            )
        else:
            return await self.reply_privately_to(
                to, f"[{media_type}] {caption}", quoted_id, quoted_sender, quoted_chat, quoted_text
            )

        if not msg:
            return await self.reply_privately_to(
                to, f"[{media_type}] {caption}", quoted_id, quoted_sender, quoted_chat, quoted_text
            )

        private_reply_context = ContextInfo(
            stanzaID=quoted_id,
            participant=quoted_sender,
            remoteJID=quoted_chat,
            quotedMessage=Message(conversation=quoted_text) if quoted_text else None,
        )

        for field in [
            "imageMessage",
            "videoMessage",
            "stickerMessage",
            "audioMessage",
            "documentMessage",
        ]:
            if msg.HasField(field):
                getattr(msg, field).contextInfo.MergeFrom(private_reply_context)
                break

        if forwarded:
            self._apply_forwarded(msg)

        return await self._client.send_message(self.to_jid(to), msg)

    async def get_group_name(self, group_jid: str | JID) -> str:
        """
        Get the subject/name of a group.

        Args:
            group_jid: The group's JID

        Returns:
            The group name string, or "Unknown Group" if fetch fails
        """
        jid = self.to_jid(group_jid)
        jid_str = f"{jid.User}@{jid.Server}"

        if not hasattr(self, "_group_name_cache"):
            self._group_name_cache = {}

        if jid_str in self._group_name_cache:
            return self._group_name_cache[jid_str]

        try:
            info = await self._client.get_group_info(jid)
            if info and hasattr(info, "GroupName") and info.GroupName:
                name = info.GroupName.Name
                self._group_name_cache[jid_str] = name
                return name
            elif info and hasattr(info, "Name"):
                name = info.Name
                self._group_name_cache[jid_str] = name
                return name
        except Exception:
            pass

        return "Group"

    async def get_joined_groups(self) -> list[dict]:
        """
        Get all groups the bot is currently in.

        Returns:
            List of dicts with group info:
            [{"id": "...", "name": "...", "member_count": N, "is_admin": bool}, ...]
        """
        try:
            groups = await self._client.get_joined_groups()
            me = await self._client.get_me()
            my_jid_str = f"{me.JID.User}@{me.JID.Server}"
            result = []

            for group in groups:
                jid_str = f"{group.JID.User}@{group.JID.Server}"
                name = group.GroupName.Name if group.GroupName else "Unknown"

                is_admin = False
                member_count = len(group.Participants) if group.Participants else 0

                for participant in group.Participants:
                    p_jid = f"{participant.JID.User}@{participant.JID.Server}"

                    if p_jid == my_jid_str:
                        is_admin = bool(participant.IsAdmin) or bool(participant.IsSuperAdmin)
                        print(
                            f"[DEBUG ADMIN] Group={name} my_jid={my_jid_str} p_jid={p_jid} IsAdmin={participant.IsAdmin} IsSuperAdmin={participant.IsSuperAdmin} result={is_admin}"
                        )
                        break

                result.append(
                    {
                        "id": jid_str,
                        "name": name,
                        "member_count": member_count,
                        "is_admin": is_admin,
                    }
                )

                if not hasattr(self, "_group_name_cache"):
                    self._group_name_cache = {}
                self._group_name_cache[jid_str] = name

            return result
        except Exception as e:
            from core.logger import log_warning

            log_warning(f"Failed to get joined groups: {e}")
            return []

    async def leave_group(self, group_jid: str) -> None:
        """Leave a WhatsApp group.

        Args:
            group_jid: The JID of the group to leave (e.g., '123456@g.us').
        """
        from neonize.utils import build_jid

        parts = group_jid.split("@")
        jid = build_jid(parts[0], parts[1] if len(parts) > 1 else "g.us")
        await self._client.leave_group(jid)

    async def connect(self) -> None:
        """Connect to WhatsApp."""
        await self._client.connect()

    async def disconnect(self) -> None:
        """Disconnect from WhatsApp."""
        await self._client.disconnect()
