"""
Mute command - Soft-mute a user by auto-deleting their messages.
"""

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t, t_error, t_info, t_success
from core.storage import GroupData
from core.targets import parse_single_target


class MuteCommand(Command):
    name = "mute"
    description = "Mute a user (their messages will be auto-deleted)"
    usage = "mute @user [duration in minutes]"
    group_only = True
    admin_only = True
    bot_admin_required = True

    async def execute(self, ctx: CommandContext) -> None:
        """Mute a user by adding them to muted list."""
        target_jid = parse_single_target(ctx)
        if not target_jid:
            await ctx.client.reply(ctx.message, t_error("errors.no_target"))
            return

        user_id = target_jid.split("@")[0]
        group_jid = ctx.message.chat_jid

        data = GroupData(group_jid)
        muted = data.load("muted", [])

        if user_id in muted:
            await ctx.client.reply(ctx.message, t_error("mute.already_muted", user=user_id))
            return

        muted.append(user_id)
        data.save("muted", muted)

        await ctx.client.reply(ctx.message, t_success("mute.muted", user=user_id))


class UnmuteCommand(Command):
    name = "unmute"
    description = "Unmute a user"
    usage = "unmute @user"
    group_only = True
    admin_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Unmute a user by removing them from muted list."""
        target_jid = parse_single_target(ctx)
        if not target_jid:
            await ctx.client.reply(ctx.message, t_error("errors.no_target"))
            return

        user_id = target_jid.split("@")[0]
        group_jid = ctx.message.chat_jid

        data = GroupData(group_jid)
        muted = data.load("muted", [])

        if user_id in muted:
            muted.remove(user_id)
            data.save("muted", muted)
            await ctx.client.reply(ctx.message, t_success("mute.unmuted", user=user_id))
        else:
            await ctx.client.reply(ctx.message, t_error("mute.not_muted", user=user_id))


class MutedCommand(Command):
    name = "muted"
    aliases = ["mutelist"]
    description = "List all muted users in the group"
    usage = "muted"
    group_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """List muted users."""
        data = GroupData(ctx.message.chat_jid)
        muted = data.load("muted", [])

        if not muted:
            await ctx.client.reply(ctx.message, t_info("mute.no_muted"))
            return

        await ctx.client.reply(
            ctx.message, sym.section(t("mute.list_title"), [f"@{u}" for u in muted])
        )
