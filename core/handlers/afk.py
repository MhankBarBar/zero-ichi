"""
AFK system handler.

Tracks users who are AFK and notifies when they're mentioned.
Uses file-based storage so AFK state persists across bot restarts.
"""

import json
import time
from pathlib import Path

_AFK_FILE = Path(__file__).parent.parent.parent / "data" / "afk.json"
_AFK_FILE.parent.mkdir(exist_ok=True)


def _load_afk() -> dict:
    """Load AFK data from disk."""
    if not _AFK_FILE.exists():
        return {}
    try:
        with open(_AFK_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_afk(data: dict) -> None:
    """Save AFK data to disk."""
    with open(_AFK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def set_afk(user_jid: str, reason: str = "") -> None:
    """Set a user as AFK."""
    data = _load_afk()
    data[user_jid] = {
        "reason": reason,
        "time": time.time(),
    }
    _save_afk(data)


def remove_afk(user_jid: str) -> dict | None:
    """Remove a user from AFK. Returns the afk data if they were AFK."""
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


def _format_duration(seconds: float) -> str:
    """Format seconds to human-readable duration."""
    minutes = int(seconds // 60)
    hours = int(minutes // 60)
    days = int(hours // 24)

    if days > 0:
        return f"{days}d {hours % 24}h"
    elif hours > 0:
        return f"{hours}h {minutes % 60}m"
    elif minutes > 0:
        return f"{minutes}m"
    else:
        return f"{int(seconds)}s"


async def handle_afk_mentions(bot, msg) -> None:
    """
    Check if message mentions any AFK users and notify.
    Also check if sender is AFK and remove them.
    """
    from core import symbols as sym
    from core.i18n import t

    afk_data = remove_afk(msg.sender_jid)
    if afk_data:
        duration = _format_duration(time.time() - afk_data["time"])
        await bot.reply(msg, f"{sym.WAVE} {t('afk.welcome_back', duration=duration)}")

    if not msg.text:
        return

    afk_users = _load_afk()
    for user_jid, afk_info in afk_users.items():
        user_number = user_jid.split("@")[0]
        if f"@{user_number}" in msg.text:
            reason = afk_info.get("reason", "")
            duration = _format_duration(time.time() - afk_info["time"])

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
