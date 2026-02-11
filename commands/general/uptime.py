"""
Uptime command - Show bot uptime.
"""

import time

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t

_start_time = time.time()


def _format_uptime(seconds: float) -> str:
    """Format seconds to human-readable uptime."""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


class UptimeCommand(Command):
    name = "uptime"
    aliases = ["up"]
    description = "Show bot uptime"
    usage = "/uptime"
    category = "general"

    async def execute(self, ctx: CommandContext) -> None:
        """Show bot uptime."""
        elapsed = time.time() - _start_time
        uptime_str = _format_uptime(elapsed)

        await ctx.client.reply(ctx.message, f"{sym.CLOCK} *{t('uptime.title')}:* {uptime_str}")
