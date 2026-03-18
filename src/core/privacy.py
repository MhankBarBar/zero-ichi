"""Privacy settings helpers for retention and AI memory controls."""

from __future__ import annotations

from core.db import kv_get_json, kv_set_json
from core.runtime_config import runtime_config

_SCOPE = "privacy"
_MEMORY_OVERRIDES_KEY = "memory_chat_overrides"


def get_analytics_retention_days() -> int:
    """Get analytics retention in days from runtime config."""
    value = runtime_config.get_nested("privacy", "analytics_retention_days", default=30)
    try:
        days = int(value)
    except (TypeError, ValueError):
        return 30
    return max(1, min(365, days))


def get_ai_memory_ttl_hours() -> float:
    """Get AI memory TTL (hours) from runtime config."""
    value = runtime_config.get_nested("privacy", "ai_memory_ttl_hours", default=24)
    try:
        hours = float(value)
    except (TypeError, ValueError):
        return 24.0
    return max(1.0, min(720.0, hours))


def _load_memory_overrides() -> dict[str, bool]:
    """Load per-chat AI memory overrides from storage."""
    raw = kv_get_json(_SCOPE, _MEMORY_OVERRIDES_KEY, default={})
    if not isinstance(raw, dict):
        return {}
    result: dict[str, bool] = {}
    for chat_id, enabled in raw.items():
        result[str(chat_id)] = bool(enabled)
    return result


def _save_memory_overrides(overrides: dict[str, bool]) -> None:
    """Save per-chat AI memory overrides."""
    kv_set_json(_SCOPE, _MEMORY_OVERRIDES_KEY, overrides)


def set_chat_memory_enabled(chat_jid: str, enabled: bool) -> None:
    """Set per-chat AI memory enabled override."""
    chat = str(chat_jid).strip()
    if not chat:
        return
    overrides = _load_memory_overrides()
    overrides[chat] = bool(enabled)
    _save_memory_overrides(overrides)


def clear_chat_memory_override(chat_jid: str) -> bool:
    """Clear per-chat memory override. Returns True if removed."""
    chat = str(chat_jid).strip()
    if not chat:
        return False
    overrides = _load_memory_overrides()
    if chat not in overrides:
        return False
    overrides.pop(chat, None)
    _save_memory_overrides(overrides)
    return True


def get_chat_memory_override(chat_jid: str) -> bool | None:
    """Get per-chat memory override (None means inherit global setting)."""
    overrides = _load_memory_overrides()
    chat = str(chat_jid).strip()
    if not chat:
        return None
    if chat in overrides:
        return bool(overrides[chat])
    return None


def is_chat_memory_enabled(chat_jid: str) -> bool:
    """Resolve effective AI memory enabled value for a chat."""
    override = get_chat_memory_override(chat_jid)
    if override is not None:
        return override
    return bool(runtime_config.get_nested("privacy", "ai_memory_enabled", default=True))
