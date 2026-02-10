"""
Joke command - Get a random joke.
"""

import random

from core import symbols as sym
from core.command import Command, CommandContext

JOKES = [
    ("Why don't scientists trust atoms?", "Because they make up everything!"),
    ("Why did the scarecrow win an award?", "He was outstanding in his field!"),
    ("I told my wife she was drawing her eyebrows too high.", "She looked surprised."),
    ("Why don't eggs tell jokes?", "They'd crack each other up!"),
    ("What do you call a fake noodle?", "An impasta!"),
    ("Why did the bicycle fall over?", "Because it was two-tired!"),
    ("What do you call a bear with no teeth?", "A gummy bear!"),
    ("Why can't you give Elsa a balloon?", "Because she will let it go!"),
    ("What do you call a fish without eyes?", "A fsh!"),
    ("Why did the math book look so sad?", "Because it had too many problems!"),
    ("What do you call cheese that isn't yours?", "Nacho cheese!"),
    ("Why don't skeletons fight each other?", "They don't have the guts!"),
    ("What do you call a sleeping dinosaur?", "A dino-snore!"),
    ("Why did the golfer bring two pairs of pants?", "In case he got a hole in one!"),
    ("What's orange and sounds like a parrot?", "A carrot!"),
    ("Why did the cookie go to the doctor?", "Because it felt crummy!"),
    ("What do you call a dog that does magic tricks?", "A Labracadabrador!"),
    ("Why couldn't the bicycle stand up by itself?", "It was two-tired!"),
    ("What do you call a can opener that doesn't work?", "A can't opener!"),
    ("Why did the tomato turn red?", "Because it saw the salad dressing!"),
]


class JokeCommand(Command):
    name = "joke"
    description = "Get a random joke"
    usage = "/joke"
    category = "fun"

    async def execute(self, ctx: CommandContext) -> None:
        """Send a random joke."""
        setup, punchline = random.choice(JOKES)

        await ctx.client.reply(ctx.message, f"{sym.SPARKLE} *{setup}*\n\n{sym.ARROW} _{punchline}_")
