"""
Permission checking utilities for commands.

Provides:
- Group admin/owner checks
- Unified command permission checking
- Owner cooldown bypass logic
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from neonize.proto.Neonize_pb2 import GroupParticipant

from core.i18n import t_error
from core.runtime_config import runtime_config

if TYPE_CHECKING:
    from core.client import BotClient
    from core.command import Command
    from core.message import MessageHelper


def is_group_admin(participant: GroupParticipant) -> bool:
    """Check if participant is a group admin."""
    return participant.IsAdmin or participant.IsSuperAdmin


def is_group_owner(participant: GroupParticipant) -> bool:
    """Check if participant is the group owner/superadmin."""
    return participant.IsSuperAdmin


async def get_participant(
    client: BotClient, group_jid: str, user_jid: str
) -> GroupParticipant | None:
    """Get participant info from a group."""
    try:
        group_info = await client._client.get_group_info(client.to_jid(group_jid))
        user_part = user_jid.split("@")[0].split(":")[0]
        for participant in group_info.Participants:
            if participant.JID.User == user_part:
                return participant
    except Exception:
        pass
    return None


async def check_admin_permission(client: BotClient, group_jid: str, user_jid: str) -> bool:
    """Check if user is admin in the group."""
    participant = await get_participant(client, group_jid, user_jid)
    if participant:
        return is_group_admin(participant)
    return False


async def check_bot_admin(client: BotClient, group_jid: str) -> bool:
    """Check if bot is admin in the group."""
    try:
        me = await client._client.get_me()
        if me and me.JID:
            bot_jid = f"{me.JID.User}@{me.JID.Server}"
            return await check_admin_permission(client, group_jid, bot_jid)
    except Exception:
        pass
    return False


class PermissionResult:
    """Result of a permission check."""

    def __init__(self, allowed: bool, error_message: str | None = None):
        self.allowed = allowed
        self.error_message = error_message

    def __bool__(self) -> bool:
        return self.allowed


async def check_command_permissions(
    cmd: Command, msg: MessageHelper, bot: BotClient
) -> PermissionResult:
    """
    Check all permissions for a command.

    Args:
        cmd: The command to check permissions for
        msg: The message that triggered the command
        bot: The bot client instance

    Returns:
        PermissionResult with allowed=True if all checks pass,
        or allowed=False with an error_message if any check fails.
    """
    if not cmd.can_execute(msg.chat_type):
        if cmd.group_only:
            return PermissionResult(False, t_error("errors.group_only"))
        elif cmd.private_only:
            return PermissionResult(False, t_error("errors.private_only"))
        return PermissionResult(False, None)

    if cmd.owner_only:
        is_owner = await runtime_config.is_owner_async(msg.sender_jid, bot)
        if not is_owner:
            return PermissionResult(False, None)

    if cmd.admin_only and msg.is_group:
        if not await check_admin_permission(bot, msg.chat_jid, msg.sender_jid):
            return PermissionResult(False, t_error("errors.admin_required"))

    if cmd.bot_admin_required and msg.is_group:
        if not await check_bot_admin(bot, msg.chat_jid):
            return PermissionResult(False, t_error("errors.bot_admin_required"))

    if not runtime_config.is_command_enabled(cmd.name):
        return PermissionResult(False, None)

    return PermissionResult(True)


async def is_owner_for_bypass(msg: MessageHelper, bot: BotClient) -> bool:
    """
    Check if sender is owner (cached check for rate limit bypass).

    This uses the JID resolver for accurate PN/LID comparison.
    """
    return await runtime_config.is_owner_async(msg.sender_jid, bot)
