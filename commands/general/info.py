"""
Info command - Show bot information.
"""

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t


class InfoCommand(Command):
    """
    Display information about the bot.
    """

    name = "info"
    description = "Show bot information"
    usage = "/info"

    async def execute(self, ctx: CommandContext) -> None:
        """Show bot info."""
        info_text = (
            f"{sym.STAR} *{t('info.title')}*\n\n"
            f"{t('info.description')}\n\n"
            f"{sym.BULLET} {t('info.version')}: 0.1.0\n"
            f"{sym.BULLET} {t('info.framework')}: Neonize (Async)\n"
            f"{sym.BULLET} {t('info.language')}: Python 3.11+\n"
        )
        await ctx.client.reply(ctx.message, info_text)
