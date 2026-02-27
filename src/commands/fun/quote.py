"""
Quote command - Get an inspirational quote.
"""

import random

from core import symbols as sym
from core.command import Command, CommandContext

QUOTES = [
    ("The only way to do great work is to love what you do.", "Steve Jobs"),
    ("Innovation distinguishes between a leader and a follower.", "Steve Jobs"),
    ("Stay hungry, stay foolish.", "Steve Jobs"),
    ("Life is what happens when you're busy making other plans.", "John Lennon"),
    ("The future belongs to those who believe in the beauty of their dreams.", "Eleanor Roosevelt"),
    ("It is during our darkest moments that we must focus to see the light.", "Aristotle"),
    ("The only impossible journey is the one you never begin.", "Tony Robbins"),
    (
        "Success is not final, failure is not fatal: it is the courage to continue that counts.",
        "Winston Churchill",
    ),
    ("Believe you can and you're halfway there.", "Theodore Roosevelt"),
    (
        "The best time to plant a tree was 20 years ago. The second best time is now.",
        "Chinese Proverb",
    ),
    ("Your time is limited, don't waste it living someone else's life.", "Steve Jobs"),
    ("The only thing we have to fear is fear itself.", "Franklin D. Roosevelt"),
    ("In the middle of difficulty lies opportunity.", "Albert Einstein"),
    ("Whether you think you can or you think you can't, you're right.", "Henry Ford"),
    (
        "The greatest glory in living lies not in never falling, but in rising every time we fall.",
        "Nelson Mandela",
    ),
    ("If you want to lift yourself up, lift up someone else.", "Booker T. Washington"),
    ("The mind is everything. What you think you become.", "Buddha"),
    ("Strive not to be a success, but rather to be of value.", "Albert Einstein"),
    ("Be the change that you wish to see in the world.", "Mahatma Gandhi"),
    (
        "The only person you are destined to become is the person you decide to be.",
        "Ralph Waldo Emerson",
    ),
]


class QuoteCommand(Command):
    name = "quote"
    aliases = ["inspire", "motivation"]
    description = "Get an inspirational quote"
    usage = "quote"
    category = "fun"

    async def execute(self, ctx: CommandContext) -> None:
        """Send a random inspirational quote."""
        quote, author = random.choice(QUOTES)

        await ctx.client.reply(ctx.message, f"{sym.QUOTE} _{quote}_\n\n{sym.DIAMOND} *{author}*")
