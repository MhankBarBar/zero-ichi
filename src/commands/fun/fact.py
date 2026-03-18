"""
Fact command - Random fun facts with live API fetch + static fallback.
"""

import random

import httpx

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t

_FALLBACK_FACTS = [
    "Honey never spoils. Archaeologists have found 3000-year-old honey in Egyptian tombs that was still edible.",
    "Octopuses have three hearts and blue blood.",
    "A group of flamingos is called a 'flamboyance'.",
    "Bananas are berries, but strawberries aren't.",
    "The shortest war in history lasted 38-45 minutes between Britain and Zanzibar.",
    "A jiffy is an actual unit of time: 1/100th of a second.",
    "Cows have best friends and get stressed when separated.",
    "The inventor of the Pringles can is buried in one.",
    "Dolphins have names for each other.",
    "Wombat poop is cube-shaped.",
    "There are more possible chess games than atoms in the observable universe.",
    "The heart of a shrimp is located in its head.",
    "A snail can sleep for three years.",
    "Elephants are the only animals that can't jump.",
    "Hot water freezes faster than cold water (Mpemba effect).",
    "The Eiffel Tower can grow up to 6 inches taller in summer due to heat expansion.",
    "Sharks have been around longer than trees.",
    "A day on Venus is longer than a year on Venus.",
    "Cleopatra lived closer in time to the Moon landing than to the construction of the Great Pyramid.",
    "There's a species of jellyfish that is immortal (Turritopsis dohrnii).",
    "Sloths can hold their breath longer than dolphins.",
    "The inventor of the frisbee was turned into a frisbee after he died.",
    "A group of owls is called a parliament.",
    "Humans share 60% of their DNA with bananas.",
    "The longest hiccuping spree lasted 68 years.",
]

_FACT_API = "https://uselessfacts.jsph.pl/random.json?language=en"


async def _fetch_live_fact() -> str | None:
    """Fetch a random fact from Useless Facts API. Returns fact text or None."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(_FACT_API)
            resp.raise_for_status()
            data = resp.json()
            text = data.get("text", "").strip()
            if text:
                return text
    except Exception:
        pass
    return None


class FactCommand(Command):
    name = "fact"
    aliases = ["funfact", "didyouknow"]
    description = "Get a random fun fact"
    usage = "fact"
    category = "fun"

    async def execute(self, ctx: CommandContext) -> None:
        """Send a random fun fact (live API with static fallback)."""
        fact = await _fetch_live_fact()
        if fact is None:
            fact = random.choice(_FALLBACK_FACTS)

        await ctx.client.reply(
            ctx.message, f"{sym.SEARCH} *{t('fact.title')}*\n\n{sym.ARROW} {fact}"
        )
