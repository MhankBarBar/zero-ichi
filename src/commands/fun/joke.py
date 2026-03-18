"""
Joke command - Get a random joke with live API fetch + static fallback.
"""

import random

import httpx

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t

_FALLBACK_JOKES = [
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

_JOKE_API = "https://v2.jokeapi.dev/joke/Any?blacklistFlags=nsfw,racist,sexist&type=twopart"


async def _fetch_live_joke() -> tuple[str, str] | None:
    """Fetch a joke from JokeAPI. Returns (setup, punchline) or None on failure."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(_JOKE_API)
            resp.raise_for_status()
            data = resp.json()
            if data.get("type") == "twopart":
                return data["setup"], data["delivery"]
    except Exception:
        pass
    return None


class JokeCommand(Command):
    name = "joke"
    description = "Get a random joke"
    usage = "joke"
    category = "fun"

    async def execute(self, ctx: CommandContext) -> None:
        """Send a random joke (live API with static fallback)."""
        result = await _fetch_live_joke()
        if result is None:
            result = random.choice(_FALLBACK_JOKES)

        setup, punchline = result
        await ctx.client.reply(
            ctx.message,
            f"{sym.SPARKLE} *{t('joke.title')}*\n\n"
            f"{sym.ARROW} *{setup}*\n\n{sym.DIAMOND} _{punchline}_",
        )
