"""
Mute handler - Auto-deletes messages from muted users.
"""

from core.client import BotClient
from core.logger import log_info
from core.message import MessageHelper
from core.storage import GroupData


async def handle_muted_users(bot: BotClient, msg: MessageHelper) -> bool:
    """
    Check if sender is muted and delete their message.

    Returns:
        True if message was deleted, False otherwise
    """
    if not msg.is_group or not msg.text:
        return False

    if msg.is_from_me:
        return False

    data = GroupData(msg.chat_jid)
    muted = data.load("muted", [])

    if not muted:
        return False

    sender_id = msg.sender_jid.split("@")[0].split(":")[0]

    if sender_id in muted:
        try:
            await bot.raw.revoke_message(
                bot.to_jid(msg.chat_jid), bot.to_jid(msg.sender_jid), msg.event.Info.ID
            )
            log_info(f"[MUTE] Deleted message from muted user {msg.sender_name}")
            return True
        except Exception as e:
            log_info(f"[MUTE] Failed to delete message: {e}")
            return False

    return False
