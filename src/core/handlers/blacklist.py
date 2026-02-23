"""
Blacklist handler - Deletes messages containing blacklisted words.
"""

from config.settings import features
from core.client import BotClient
from core.logger import log_info
from core.message import MessageHelper
from core.moderation import execute_moderation_action, is_admin
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

    if await is_admin(bot, msg.chat_jid, msg.sender_jid):
        return False

    text_lower = msg.text.lower()

    for word in blacklisted:
        if word.lower() in text_lower:
            try:
                await execute_moderation_action(bot, msg, "delete", "blacklist")
                await execute_moderation_action(bot, msg, "warn", "blacklist")
                return True
            except Exception as e:
                log_info(f"[BLACKLIST] Failed to handle blacklist: {e}")
                return False

    return False
