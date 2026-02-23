"""
Shared state module for the bot.

This module holds shared references to the bot instance
that can be accessed by both main.py and dashboard_api.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.client import BotClient

_bot: BotClient | None = None


def set_bot(bot: BotClient) -> None:
    """Set the global bot instance."""
    global _bot
    _bot = bot


def get_bot() -> BotClient | None:
    """Get the global bot instance."""
    return _bot
