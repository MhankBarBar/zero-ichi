"""
8ball command - Magic 8-ball responses.
"""

import random

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t

RESPONSES = [
    ("It is certain.", "positive"),
    ("It is decidedly so.", "positive"),
    ("Without a doubt.", "positive"),
    ("Yes definitely.", "positive"),
    ("You may rely on it.", "positive"),
    ("As I see it, yes.", "positive"),
    ("Most likely.", "positive"),
    ("Outlook good.", "positive"),
    ("Yes.", "positive"),
    ("Signs point to yes.", "positive"),
    ("Reply hazy, try again.", "neutral"),
    ("Ask again later.", "neutral"),
    ("Better not tell you now.", "neutral"),
    ("Cannot predict now.", "neutral"),
    ("Concentrate and ask again.", "neutral"),
    ("Don't count on it.", "negative"),
    ("My reply is no.", "negative"),
    ("My sources say no.", "negative"),
    ("Outlook not so good.", "negative"),
    ("Very doubtful.", "negative"),
]


class EightBallCommand(Command):
    name = "8ball"
    aliases = ["magic8ball", "8b"]
    description = "Ask the magic 8-ball a question"
    usage = "/8ball <question>"
    category = "fun"
    examples = ["/8ball Will I be rich?", "/8ball Should I do it?"]

    async def execute(self, ctx: CommandContext) -> None:
        """Answer with magic 8-ball response."""
        if not ctx.raw_args:
            await ctx.client.reply(
                ctx.message, f"{sym.INFO} {t('eightball.ask_question', prefix=ctx.prefix)}"
            )
            return

        response, sentiment = random.choice(RESPONSES)

        if sentiment == "positive":
            indicator = sym.ON
        elif sentiment == "negative":
            indicator = sym.OFF
        else:
            indicator = sym.PENDING

        await ctx.client.reply(
            ctx.message,
            f"{sym.STAR} *{t('eightball.title')}*\n\n"
            f"{sym.QUOTE} _{ctx.raw_args}_\n\n"
            f"{indicator} *{response}*",
        )
