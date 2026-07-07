"""AFK system handler.

Tracks users who are AFK and notifies when they're mentioned.
Uses database-backed storage so AFK state persists across restarts.
"""

from __future__ import annotations

import time
from datetime import timedelta

from core import symbols as sym
from core.db import kv_get_json, kv_set_json
from core.i18n import t
from core.utils import format_duration

_AFK_SCOPE = "afk"
_AFK_KEY = "state"


def _load_afk() -> dict:
    """Load AFK data from database."""
    data = kv_get_json(_AFK_SCOPE, _AFK_KEY, default={})
    return data if isinstance(data, dict) else {}


def _save_afk(data: dict) -> None:
    """Save AFK data to database."""
    kv_set_json(_AFK_SCOPE, _AFK_KEY, data)


def set_afk(user_jid: str, reason: str = "") -> None:
    """Set a user as AFK."""
    data = _load_afk()
    data[user_jid] = {
        "reason": reason,
        "time": time.time(),
    }
    _save_afk(data)


def remove_afk(user_jid: str) -> dict | None:
    """Remove a user from AFK. Returns the AFK data if they were AFK."""
    data = _load_afk()
    afk_info = data.pop(user_jid, None)
    if afk_info:
        _save_afk(data)
    return afk_info


def is_afk(user_jid: str) -> bool:
    """Check if a user is AFK."""
    return user_jid in _load_afk()


def get_afk(user_jid: str) -> dict | None:
    """Get AFK info for a user."""
    return _load_afk().get(user_jid)


async def handle_afk_mentions(bot, msg) -> None:
    """Check AFK mentions and clear sender AFK if needed."""
    afk_data = remove_afk(msg.sender_jid)
    if afk_data:
        duration = format_duration(timedelta(seconds=time.time() - afk_data["time"]))
        await bot.reply(msg, f"{sym.WAVE} {t('afk.welcome_back', duration=duration)}")

    if not msg.text:
        return

    afk_users = _load_afk()
    for user_jid, afk_info in afk_users.items():
        user_number = user_jid.split("@")[0]
        if f"@{user_number}" in msg.text:
            reason = afk_info.get("reason", "")
            duration = format_duration(timedelta(seconds=time.time() - afk_info["time"]))

            if reason:
                text = t(
                    "afk.is_afk_reason",
                    duration=duration,
                    note=sym.NOTE,
                    reason=reason,
                )
            else:
                text = t("afk.is_afk", duration=duration)

            await bot.reply(msg, f"{sym.INFO} {text}")
