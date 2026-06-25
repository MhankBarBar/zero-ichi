"""
Shared state module for the bot.

This module holds shared references to the bot instance
that can be accessed by both main.py and dashboard_api.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.client import BotClient
    from core.telegram_forwarder import TelegramForwarder

_bot: BotClient | None = None
_tg_forwarder: TelegramForwarder | None = None


def set_bot(bot: BotClient) -> None:
    """Set the global bot instance."""
    global _bot
    _bot = bot


def get_bot() -> BotClient | None:
    """Get the global bot instance."""
    return _bot


def set_tg_forwarder(forwarder: TelegramForwarder) -> None:
    """Set the global Telegram forwarder instance."""
    global _tg_forwarder
    _tg_forwarder = forwarder


def get_tg_forwarder() -> TelegramForwarder | None:
    """Get the global Telegram forwarder instance."""
    return _tg_forwarder
