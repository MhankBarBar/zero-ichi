"""
Uptime command - Show bot uptime.
"""

import time

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t
from core.timefmt import format_uptime

_start_time = time.time()


class UptimeCommand(Command):
    name = "uptime"
    aliases = ["up"]
    description = "Show bot uptime"
    usage = "uptime"
    category = "general"

    async def execute(self, ctx: CommandContext) -> None:
        """Show bot uptime."""
        elapsed = time.time() - _start_time
        uptime_str = format_uptime(elapsed, include_seconds=True)

        await ctx.client.reply(ctx.message, f"{sym.CLOCK} *{t('uptime.title')}:* {uptime_str}")
