"""
Filters command - List all filters.
"""

from config.settings import features
from core.command import Command, CommandContext
from core.i18n import t, t_error
from core.storage import GroupData


class FiltersCommand(Command):
    name = "filters"
    description = "List all auto-reply filters"
    usage = "filters"
    group_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """List all filters."""
        if not features.filters:
            await ctx.client.reply(ctx.message, t_error("common.feature_disabled"))
            return

        group_jid = ctx.message.chat_jid
        data = GroupData(group_jid)
        filters = data.filters

        if not filters:
            await ctx.client.reply(ctx.message, t("filter.no_filters", prefix=ctx.prefix))
            return

        lines = [f"{t('filter.list_title')}:"]
        for trigger in sorted(filters.keys()):
            lines.append(f"  - {trigger}")

        await ctx.client.reply(ctx.message, "\n".join(lines))
