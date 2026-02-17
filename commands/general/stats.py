"""
Stats command - Bot usage statistics.
"""

import platform

from core import symbols as sym
from core.command import Command, CommandContext, command_loader
from core.i18n import t
from core.storage import Storage


class StatsCommand(Command):
    name = "stats"
    aliases = ["botstats"]
    description = "Show bot statistics"
    usage = "stats"
    category = "general"

    async def execute(self, ctx: CommandContext) -> None:
        """Show bot statistics."""
        storage = Storage()

        messages = storage.get_stat("messages_total", 0)
        commands = storage.get_stat("commands_used", 0)
        total_cmds = len(command_loader.enabled_commands)

        try:
            import time

            from commands.general.uptime import _start_time

            elapsed = time.time() - _start_time
            days = int(elapsed // 86400)
            hours = int((elapsed % 86400) // 3600)
            minutes = int((elapsed % 3600) // 60)
            parts = []
            if days:
                parts.append(f"{days}d")
            if hours:
                parts.append(f"{hours}h")
            parts.append(f"{minutes}m")
            uptime_str = " ".join(parts)
        except Exception:
            uptime_str = "N/A"

        try:
            groups = await ctx.client.get_joined_groups()
            group_count = len(groups)
        except Exception:
            group_count = "N/A"

        lines = [
            sym.header(t("stats.title")),
            "",
            sym.status_line(t("stats.uptime"), uptime_str),
            sym.status_line(t("stats.messages"), str(messages)),
            sym.status_line(t("stats.commands_used"), str(commands)),
            sym.status_line(t("stats.commands_loaded"), str(total_cmds)),
            sym.status_line(t("stats.groups"), str(group_count)),
            sym.status_line(t("stats.platform"), f"{platform.system()} {platform.machine()}"),
            sym.status_line(t("stats.python"), platform.python_version()),
        ]

        await ctx.client.reply(ctx.message, "\n".join(lines))
