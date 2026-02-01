"""
Reset warnings command - Clear all warnings for a user.
"""

from core.command import Command, CommandContext
from core.i18n import t_error, t_success
from core.storage import GroupData
from core.targets import parse_single_target


class ResetWarnsCommand(Command):
    name = "resetwarns"
    description = "Clear all warnings for a user"
    usage = "/resetwarns @user"
    group_only = True
    admin_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Reset user warnings."""
        target_jid = parse_single_target(ctx)
        if not target_jid:
            await ctx.client.reply(ctx.message, t_error("errors.no_target"))
            return

        user_id = target_jid.split("@")[0]
        group_jid = ctx.message.chat_jid

        data = GroupData(group_jid)
        warnings = data.warnings

        if user_id in warnings:
            del warnings[user_id]
            data.save_warnings(warnings)

        await ctx.client.reply(ctx.message, t_success("warn.cleared", user=user_id))
