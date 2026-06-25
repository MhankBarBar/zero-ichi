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
from core.jid_resolver import get_user_part, jids_match
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
        user_part = get_user_part(user_jid)
        for participant in group_info.Participants:
            if participant.JID.User == user_part:
                return participant
            participant_jid = f"{participant.JID.User}@{participant.JID.Server}"
            if await jids_match(participant_jid, user_jid, client):
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
        bot_jid = ""
        if me and me.JID:
            bot_jid = f"{me.JID.User}@{me.JID.Server}"
        elif me and hasattr(me, "LID") and me.LID and me.LID.User:
            bot_jid = f"{me.LID.User}@{me.LID.Server}"
        if bot_jid:
            return await check_admin_permission(client, group_jid, bot_jid)
    except Exception:
        pass
    return False


class PermissionResult:
    """Result of a permission check."""

    def __init__(
        self, allowed: bool, error_message: str | None = None, current_role: str = "member"
    ):
        self.allowed = allowed
        self.error_message = error_message
        self.current_role = current_role

    def __bool__(self) -> bool:
        return self.allowed


_ROLE_RANK = {
    "member": 0,
    "admin": 1,
    "owner": 2,
}


def _base_required_role(cmd: Command) -> str:
    """Get intrinsic role requirement from command flags."""
    if cmd.owner_only:
        return "owner"
    if cmd.admin_only:
        return "admin"
    return "member"


def _normalize_role(role: str | None) -> str | None:
    """Normalize a role string to member/admin/owner."""
    if not role:
        return None
    value = str(role).strip().lower()
    if value in _ROLE_RANK:
        return value
    return None


def _resolve_required_role(cmd: Command, chat_jid: str) -> str:
    """Resolve effective required role using overrides."""
    intrinsic = _base_required_role(cmd)
    override = _normalize_role(runtime_config.get_command_role_override(cmd.name, chat_jid))
    if override is None:
        return intrinsic

    if intrinsic == "owner" and override != "owner":
        return "owner"
    return override


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

    chat_jid = getattr(msg, "chat_jid", "")
    required_role = _resolve_required_role(cmd, chat_jid)

    owner = runtime_config.get_owner_jid().strip()
    if required_role == "owner" and not owner:
        if await _allow_owner_bootstrap(cmd, msg):
            return PermissionResult(True)
        return PermissionResult(False, t_error("errors.owner_only"))

    is_owner = False
    if owner:
        is_owner = await runtime_config.is_owner_async(msg.sender_jid, bot)

    is_admin = False
    if msg.is_group and not is_owner:
        is_admin = await check_admin_permission(bot, msg.chat_jid, msg.sender_jid)

    current_role = "owner" if is_owner else "admin" if is_admin else "member"
    if _ROLE_RANK[current_role] < _ROLE_RANK[required_role]:
        if required_role == "owner":
            return PermissionResult(False, t_error("errors.owner_only"))
        if required_role == "admin":
            return PermissionResult(False, t_error("errors.admin_required"))
        return PermissionResult(False, None)

    if cmd.bot_admin_required and msg.is_group:
        if not await check_bot_admin(bot, msg.chat_jid):
            return PermissionResult(False, t_error("errors.bot_admin_required"), current_role)

    if not runtime_config.is_command_enabled(cmd.name):
        return PermissionResult(False, None, current_role)

    return PermissionResult(True, current_role=current_role)


async def is_owner_for_bypass(msg: MessageHelper, bot: BotClient) -> bool:
    """
    Check if sender is owner (cached check for rate limit bypass).

    This uses the JID resolver for accurate PN/LID comparison.
    """
    return await runtime_config.is_owner_async(msg.sender_jid, bot)


async def _allow_owner_bootstrap(cmd: Command, msg: MessageHelper) -> bool:
    """Allow limited owner bootstrap commands when owner_jid is not configured.

    SECURITY NOTE: This allows anyone in a private chat to claim ownership
    when no owner is configured. This is intentional for first-time setup
    but should be logged for audit purposes.
    """
    if msg.is_group:
        return False

    text = (msg.text or "").strip().lower()
    if not text:
        return False

    parts = text.split()
    if len(parts) < 2:
        return False

    command_name = cmd.name.lower()
    allowed = False

    if command_name == "config":
        if len(parts) >= 3 and parts[1] == "owner":
            if parts[2] == "me":
                allowed = True
            elif parts[2] == "set" and len(parts) >= 4:
                allowed = True

    elif command_name == "setup":
        if parts[1] in {"status", "start"}:
            allowed = True
        elif len(parts) >= 3 and parts[1] == "owner":
            if parts[2] == "me":
                allowed = True
            elif parts[2] == "set" and len(parts) >= 4:
                allowed = True

    if allowed:
        from core.logger import log_warning

        log_warning(
            f"Owner bootstrap triggered by {msg.sender_jid} via /{command_name} "
            f"(no owner configured). Command: {text}"
        )

    return allowed
