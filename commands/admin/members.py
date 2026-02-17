"""
Group member management commands - Kick, Add, Promote, Demote.

All participant management commands consolidated in one file.
"""

from core.command import Command, CommandContext
from core.group_actions import update_participants


class KickCommand(Command):
    """Remove members from the group."""

    name = "kick"
    aliases = ["ban"]
    description = "Remove one or more members from the group"
    usage = "kick @user1 @user2 or reply with kick"
    group_only = True
    admin_only = True
    bot_admin_required = True

    async def execute(self, ctx: CommandContext) -> None:
        await update_participants(ctx, "remove", "kick")


class AddCommand(Command):
    """Add members to the group."""

    name = "add"
    aliases = ["unban"]
    description = "Add one or more users to the group"
    usage = "add <number> or add @user"
    group_only = True
    admin_only = True
    bot_admin_required = True

    async def execute(self, ctx: CommandContext) -> None:
        """Add users to the group."""
        await update_participants(ctx, "add", "add", no_targets_key="members.add_usage")


class PromoteCommand(Command):
    """Promote members to admin."""

    name = "promote"
    description = "Promote one or more members to admin"
    usage = "promote @user1 @user2 or reply with promote"
    group_only = True
    admin_only = True
    bot_admin_required = True

    async def execute(self, ctx: CommandContext) -> None:
        await update_participants(ctx, "promote", "promote")


class DemoteCommand(Command):
    """Demote admins to regular members."""

    name = "demote"
    description = "Demote one or more admins to regular members"
    usage = "demote @user1 @user2 or reply with demote"
    group_only = True
    admin_only = True
    bot_admin_required = True

    async def execute(self, ctx: CommandContext) -> None:
        await update_participants(ctx, "demote", "demote")
