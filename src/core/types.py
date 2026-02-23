"""
Chat type definitions for WhatsApp messages.
"""

from enum import Enum, auto


class ChatType(Enum):
    """
    Type of chat where a message was received.

    PRIVATE = Direct message (one-on-one chat)
    GROUP   = Group chat message
    """

    PRIVATE = auto()
    GROUP = auto()


def get_chat_type_from_jid(jid_server: str) -> ChatType:
    """
    Determine chat type from JID server part.

    Args:
        jid_server: The server part of a JID (e.g., "s.whatsapp.net" or "g.us")

    Returns:
        ChatType.GROUP if it's a group, ChatType.PRIVATE otherwise
    """
    if jid_server == "g.us":
        return ChatType.GROUP
    return ChatType.PRIVATE
