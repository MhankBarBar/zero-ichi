"""
Moderation utilities for handling user actions and permissions.
"""

from neonize.utils.enum import ParticipantChange

from core import symbols as sym
from core.client import BotClient
from core.i18n import t, t_warning
from core.logger import log_info
from core.message import MessageHelper


async def is_admin(bot: BotClient, chat_jid: str, user_jid: str) -> bool:
    """Check if a user is an admin in the group."""
    try:
        group_info = await bot.raw.get_group_info(bot.to_jid(chat_jid))
        user_id = user_jid.split("@")[0].split(":")[0]

        for participant in group_info.Participants:
            if participant.JID.User == user_id:
                return participant.IsAdmin or participant.IsSuperAdmin
    except Exception:
        pass
    return False


async def execute_moderation_action(
    bot: BotClient,
    msg: MessageHelper,
    action: str,
    reason_key: str,
    user_key: str = "user",
) -> None:
    """
    Execute a moderation action (warn, delete, kick).

    Args:
        bot: BotClient instance
        msg: MessageHelper instance
        action: Action to perform (warn, delete, kick)
        reason_key: I18n key prefix for messages (e.g. 'antilink', 'blacklist')
        user_key: I18n key for the user placeholder (default: 'user')
    """
    normalized_action = action.lower()
    if normalized_action in {"ban", "mute"}:
        normalized_action = "kick"

    user_id = msg.sender_jid.split("@")[0]
    chat_jid_obj = bot.to_jid(msg.chat_jid)
    sender_jid_obj = bot.to_jid(msg.sender_jid)
    message_id = msg.event.Info.ID

    if normalized_action == "warn":
        await bot.send(
            msg.chat_jid,
            t_warning(f"{reason_key}.warn_message", **{user_key: user_id}),
        )

    elif normalized_action == "delete":
        await bot.raw.revoke_message(chat_jid_obj, sender_jid_obj, message_id)
        log_info(f"[{reason_key.upper()}] Deleted message from {msg.sender_name}")

    elif normalized_action == "kick":
        await bot.raw.revoke_message(chat_jid_obj, sender_jid_obj, message_id)
        await bot.raw.update_group_participants(
            chat_jid_obj, [sender_jid_obj], ParticipantChange.REMOVE
        )

        await bot.send(
            msg.chat_jid,
            f"{sym.KICK} {t(f'{reason_key}.kicked', **{user_key: user_id})}",
        )
        log_info(f"[{reason_key.upper()}] Kicked {msg.sender_name}")
