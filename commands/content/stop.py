"""
Stop command - Remove a filter (and its associated media if any).
"""

from pathlib import Path

from core.command import Command, CommandContext
from core.i18n import t_error, t_success
from core.logger import log_info
from core.storage import GroupData


class StopCommand(Command):
    name = "stop"
    description = "Remove an auto-reply filter"
    usage = "stop <trigger>"
    aliases = ["unfilter", "delfilter", "rmfilter"]
    group_only = True
    admin_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Remove a filter."""
        if not ctx.args:
            await ctx.client.reply(ctx.message, t_error("errors.no_target"))
            return

        trigger = ctx.args[0].lower()
        group_jid = ctx.message.chat_jid

        data = GroupData(group_jid)
        filters = data.filters

        if trigger not in filters:
            await ctx.client.reply(ctx.message, t_error("filter.not_found", trigger=trigger))
            return

        filter_data = filters[trigger]
        if isinstance(filter_data, dict) and filter_data.get("media_path"):
            media_path = Path(filter_data["media_path"])
            if media_path.exists():
                try:
                    media_path.unlink()
                    log_info(f"Deleted filter media: {media_path}")
                except Exception as e:
                    log_info(f"Could not delete filter media: {e}")

        del filters[trigger]
        data.save_filters(filters)
        await ctx.client.reply(ctx.message, t_success("filter.removed", trigger=trigger))
