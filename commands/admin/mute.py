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
    aliases = ["unmute", "muted", "mutelist"]
    description = "Mute a user (their messages will be auto-deleted)"
    usage = "mute <@user> | unmute <@user> | muted"
    group_only = True
    admin_only = True
    bot_admin_required = True

    async def execute(self, ctx: CommandContext) -> None:
        """Manage muted users."""
        command = ctx.command_name.lower()

        if command in ("muted", "mutelist") or (
            command == "mute" and ctx.args and ctx.args[0].lower() == "list"
        ):
            await self._list_muted(ctx)
            return

        target_jid = parse_single_target(ctx)
        if not target_jid:
            await ctx.client.reply(ctx.message, t_error("errors.no_target"))
            return

        user_id = target_jid.split("@")[0]
        group_jid = ctx.message.chat_jid
        data = GroupData(group_jid)
        muted = data.muted

        if command == "unmute":
            if user_id in muted:
                muted.remove(user_id)
                data.save_muted(muted)
                await ctx.client.reply(ctx.message, t_success("mute.unmuted", user=user_id))
            else:
                await ctx.client.reply(ctx.message, t_error("mute.not_muted", user=user_id))
            return

        if user_id in muted:
            await ctx.client.reply(ctx.message, t_error("mute.already_muted", user=user_id))
            return

        muted.append(user_id)
        data.save_muted(muted)
        await ctx.client.reply(ctx.message, t_success("mute.muted", user=user_id))

    async def _list_muted(self, ctx: CommandContext) -> None:
        """List all muted users."""
        data = GroupData(ctx.message.chat_jid)
        muted = data.muted

        if not muted:
            await ctx.client.reply(ctx.message, t_info("mute.no_muted"))
            return

        await ctx.client.reply(
            ctx.message, sym.section(t("mute.list_title"), [f"@{u}" for u in muted])
        )
