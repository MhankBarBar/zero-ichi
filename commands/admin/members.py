"""
Group member management commands - Kick, Add, Promote, Demote.

All participant management commands consolidated in one file.
"""

from core.command import Command, CommandContext
from core.group_actions import update_participants
from core.i18n import t_error, t_info, t_success


class KickCommand(Command):
    """Remove members from the group."""

    name = "kick"
    aliases = ["ban"]
    description = "Remove one or more members from the group"
    usage = "/kick @user1 @user2 or reply with /kick"
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
    usage = "/add <number> or /add @user"
    group_only = True
    admin_only = True
    bot_admin_required = True

    async def execute(self, ctx: CommandContext) -> None:
        """Add users to the group."""
        if not ctx.args and not ctx.message.mentions:
            await ctx.client.reply(ctx.message, t_info("members.add_usage", prefix=ctx.prefix))
            return

        if ctx.message.mentions:
            await update_participants(ctx, "add", "add")
            return

        targets = []
        for arg in ctx.args:
            cleaned = arg.replace("@", "").replace("+", "").strip()
            if cleaned.isdigit():
                targets.append(f"{cleaned}@lid")

        if not targets:
            await ctx.client.reply(ctx.message, t_error("members.invalid_numbers"))
            return

        try:
            group_jid = ctx.message.chat_jid
            target_jids = [ctx.client.to_jid(t) for t in targets]
            await ctx.client._client.update_group_participants(
                ctx.client.to_jid(group_jid), target_jids, "add"
            )
            count = len(targets)
            await ctx.client.reply(
                ctx.message,
                t_success("members.added", count=count),
            )
        except Exception as e:
            await ctx.client.reply(ctx.message, t_error("members.add_failed", error=str(e)))


class PromoteCommand(Command):
    """Promote members to admin."""

    name = "promote"
    description = "Promote one or more members to admin"
    usage = "/promote @user1 @user2 or reply with /promote"
    group_only = True
    admin_only = True
    bot_admin_required = True

    async def execute(self, ctx: CommandContext) -> None:
        await update_participants(ctx, "promote", "promote")


class DemoteCommand(Command):
    """Demote admins to regular members."""

    name = "demote"
    description = "Demote one or more admins to regular members"
    usage = "/demote @user1 @user2 or reply with /demote"
    group_only = True
    admin_only = True
    bot_admin_required = True

    async def execute(self, ctx: CommandContext) -> None:
        await update_participants(ctx, "demote", "demote")
