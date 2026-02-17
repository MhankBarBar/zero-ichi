"""
Warns command - Check warnings for a user.
"""

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t
from core.storage import GroupData
from core.targets import parse_single_target


class WarnsCommand(Command):
    name = "warns"
    description = "Check warnings for a user"
    usage = "warns [@user]"
    group_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Check user warnings."""
        target_jid = parse_single_target(ctx)
        if not target_jid:
            target_jid = ctx.message.sender_jid

        user_id = target_jid.split("@")[0]
        group_jid = ctx.message.chat_jid

        data = GroupData(group_jid)
        warnings = data.warnings
        user_warns = warnings.get(user_id, [])

        if not user_warns:
            await ctx.client.reply(ctx.message, t("warn.no_warns", user=user_id))
            return

        items = [f"{i}. {reason}" for i, reason in enumerate(user_warns, 1)]
        await ctx.client.reply(
            ctx.message,
            sym.section(t("warn.warns_title", user=user_id, count=len(user_warns)), items),
        )
