"""
Blacklist handler - Deletes messages containing blacklisted words.
"""

from config.settings import features
from core.client import BotClient
from core.i18n import t_warning
from core.logger import log_info
from core.message import MessageHelper
from core.storage import GroupData


async def handle_blacklist(bot: BotClient, msg: MessageHelper) -> bool:
    """
    Check if message contains blacklisted words and delete if found.

    Returns:
        True if message was deleted (blocked), False otherwise
    """
    if not features.blacklist:
        return False

    if not msg.is_group or not msg.text:
        return False

    if msg.is_from_me:
        return False

    data = GroupData(msg.chat_jid)
    blacklisted = data.blacklist

    if not blacklisted:
        return False

    text_lower = msg.text.lower()

    for word in blacklisted:
        if word.lower() in text_lower:
            try:
                sender_jid = bot.to_jid(msg.sender_jid)
                chat_jid = bot.to_jid(msg.chat_jid)

                await bot.raw.revoke_message(chat_jid, sender_jid, msg.event.Info.ID)

                log_info(f"[BLACKLIST] Deleted message from {msg.sender_name} containing '{word}'")

                await bot.send(
                    msg.chat_jid,
                    t_warning("blacklist.warn_message", user=msg.sender_jid.split("@")[0]),
                )

                return True
            except Exception as e:
                log_info(f"[BLACKLIST] Failed to delete message: {e}")
                return False

    return False
