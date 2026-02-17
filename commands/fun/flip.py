"""
Flip command - Coin flip.
"""

import random

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t


class FlipCommand(Command):
    name = "flip"
    aliases = ["coin", "coinflip", "toss"]
    description = "Flip a coin"
    usage = "flip"
    category = "fun"

    async def execute(self, ctx: CommandContext) -> None:
        """Flip a coin."""
        result = random.choice(["Heads", "Tails"])

        await ctx.client.reply(
            ctx.message,
            f"{sym.SPARKLE} *{t('flip.title')}*\n\n{sym.ARROW} {t('flip.result')}: *{result}!*",
        )
