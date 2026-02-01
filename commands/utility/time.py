"""
Time command - Show current date and time.
"""

from datetime import datetime

from core.command import Command, CommandContext
from core.i18n import t


class TimeCommand(Command):
    """
    Display the current date and time.
    """

    name = "time"
    description = "Show current date and time"
    usage = "/time"

    async def execute(self, ctx: CommandContext) -> None:
        """Show current time."""
        now = datetime.now()

        time_text = (
            f"◷ *{t('time.title')}*\n\n"
            f"• {t('time.date')}: {now.strftime('%Y-%m-%d')}\n"
            f"• {t('time.time')}: {now.strftime('%H:%M:%S')}\n"
            f"• {t('time.day')}: {now.strftime('%A')}"
        )

        await ctx.client.reply(ctx.message, time_text)
