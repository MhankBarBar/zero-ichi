"""
Ping command - Check if bot is online.
"""

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t


class PingCommand(Command):
    """
    Simple ping/pong command to check bot status.
    """

    name = "ping"
    description = "Check if bot is online"
    usage = "ping"

    async def execute(self, ctx: CommandContext) -> None:
        """Reply with Pong to confirm bot is working."""
        await ctx.client.reply(ctx.message, f"{sym.SUCCESS} {t('ping.pong')}")
