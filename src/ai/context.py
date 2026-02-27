"""
AI Context module.

Defines dependencies and context building for AI tool calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.client import BotClient
    from core.message import MessageHelper


@dataclass
class BotDependencies:
    """Dependencies passed to AI tools during execution."""

    bot: BotClient
    msg: MessageHelper


def build_context_prompt(msg: MessageHelper, bot: BotClient) -> str:
    """
    Build context information for the AI from message data.

    Returns a formatted string with relevant message context.
    """
    context_parts = []

    context_parts.append(f"Sender: {msg.sender_name}")

    chat_type = "group" if msg.is_group else "private"
    context_parts.append(f"Chat type: {chat_type}")

    if msg.quoted_text:
        context_parts.append(f"Replied message: {msg.quoted_text[:500]}")

    if msg.quoted_sender_name:
        context_parts.append(f"Replied to: {msg.quoted_sender_name}")

    msg_obj, media_type = msg.get_media_message(bot)
    if media_type and media_type != "text":
        context_parts.append(f"Media attached: {media_type}")

    return "\n".join(context_parts)
