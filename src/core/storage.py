"""Per-group and global data storage.

Runtime data now uses the shared database layer (`core.db`) instead of JSON files.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from core.constants import DATA_DIR
from core.db import kv_get_json, kv_set_json

DATA_DIR.mkdir(exist_ok=True)


def safe_jid(jid: str) -> str:
    """Sanitize a JID for compatibility with legacy folder naming."""
    return jid.replace(":", "_").replace("@", "_")


class GroupData:
    """Manages per-group structured data in database storage."""

    def __init__(self, group_jid: str) -> None:
        self.group_jid = group_jid
        self.scope = f"group:{group_jid}"

        self.group_dir = DATA_DIR / safe_jid(group_jid)
        self.group_dir.mkdir(exist_ok=True)

    def load(self, name: str, default: Any = None) -> Any:
        """Load data for a key from database."""
        fallback = default if default is not None else {}
        data = kv_get_json(self.scope, name, default=None)
        if data is None:
            return deepcopy(fallback)
        return data

    def save(self, name: str, data: Any) -> None:
        """Save data for a key in database."""
        kv_set_json(self.scope, name, data)

    @property
    def settings(self) -> dict:
        return self.load("settings", {})

    def save_settings(self, settings: dict) -> None:
        self.save("settings", settings)

    @property
    def notes(self) -> dict:
        return self.load("notes", {})

    def save_notes(self, notes: dict) -> None:
        self.save("notes", notes)

    @property
    def filters(self) -> dict:
        return self.load("filters", {})

    def save_filters(self, filters: dict) -> None:
        self.save("filters", filters)

    @property
    def blacklist(self) -> list:
        return self.load("blacklist", [])

    def save_blacklist(self, words: list) -> None:
        self.save("blacklist", words)

    @property
    def warnings(self) -> dict:
        return self.load("warnings", {})

    def save_warnings(self, warnings: dict) -> None:
        self.save("warnings", warnings)

    @property
    def welcome(self) -> dict:
        return self.load("welcome", {"enabled": False, "message": ""})

    def save_welcome(self, config: dict) -> None:
        self.save("welcome", config)

    @property
    def anti_link(self) -> dict:
        config = self.load(
            "anti_link",
            {
                "enabled": False,
                "action": "warn",
                "whitelist": [],
            },
        )
        action = str(config.get("action", "warn")).lower()
        if action in {"ban", "mute"}:
            config["action"] = "kick"
        elif action not in {"warn", "delete", "kick"}:
            config["action"] = "warn"
        return config

    def save_anti_link(self, config: dict) -> None:
        self.save("anti_link", config)

    @property
    def warnings_config(self) -> dict:
        config = self.load(
            "warnings_config",
            {
                "enabled": True,
                "limit": 3,
                "action": "kick",
            },
        )
        if str(config.get("action", "kick")).lower() != "kick":
            config["action"] = "kick"
        return config

    def save_warnings_config(self, config: dict) -> None:
        self.save("warnings_config", config)

    @property
    def reports(self) -> dict:
        return self.load("reports", {"counter": 0, "items": []})

    def save_reports(self, payload: dict) -> None:
        self.save("reports", payload)

    @property
    def digest(self) -> dict:
        return self.load(
            "digest",
            {
                "enabled": False,
                "period": "daily",
                "time": "20:00",
                "day": "sun",
                "task_id": "",
            },
        )

    def save_digest(self, config: dict) -> None:
        self.save("digest", config)

    @property
    def automations(self) -> list:
        rules = self.load("automations", [])
        return rules if isinstance(rules, list) else []

    def save_automations(self, rules: list) -> None:
        self.save("automations", rules)

    @property
    def muted(self) -> list:
        return self.load("muted", [])

    def save_muted(self, users: list) -> None:
        self.save("muted", users)


class Storage:
    """Global storage manager for dashboard/API counters and cached group metadata."""

    _SCOPE = "global"
    _STATS_KEY = "stats"
    _GROUPS_KEY = "groups"

    def get_all_groups(self) -> dict:
        data = kv_get_json(self._SCOPE, self._GROUPS_KEY, default={})
        return data if isinstance(data, dict) else {}

    def get_group_settings(self, group_id: str) -> dict | None:
        groups = self.get_all_groups()
        settings = groups.get(group_id)
        if isinstance(settings, dict):
            return deepcopy(settings)
        return settings

    def set_group_settings(self, group_id: str, settings: dict) -> None:
        groups = self.get_all_groups()
        existing = groups.get(group_id)
        if not isinstance(existing, dict):
            existing = {}
        existing.update(settings)
        groups[group_id] = existing
        kv_set_json(self._SCOPE, self._GROUPS_KEY, groups)

    def register_group(
        self, group_id: str, name: str, member_count: int = 0, is_admin: bool = False
    ) -> None:
        groups = self.get_all_groups()
        if group_id not in groups or not isinstance(groups[group_id], dict):
            groups[group_id] = {
                "name": name,
                "member_count": member_count,
                "is_admin": is_admin,
                "antilink": False,
                "welcome": True,
                "mute": False,
            }
        else:
            groups[group_id]["name"] = name
            groups[group_id]["member_count"] = member_count
            groups[group_id]["is_admin"] = is_admin

        kv_set_json(self._SCOPE, self._GROUPS_KEY, groups)

    def get_stat(self, key: str, default: Any = 0) -> Any:
        stats = kv_get_json(self._SCOPE, self._STATS_KEY, default={})
        if not isinstance(stats, dict):
            return default
        return stats.get(key, default)

    def set_stat(self, key: str, value: Any) -> None:
        stats = kv_get_json(self._SCOPE, self._STATS_KEY, default={})
        if not isinstance(stats, dict):
            stats = {}
        stats[key] = value
        kv_set_json(self._SCOPE, self._STATS_KEY, stats)

    def increment_stat(self, key: str, amount: int = 1) -> None:
        stats = kv_get_json(self._SCOPE, self._STATS_KEY, default={})
        if not isinstance(stats, dict):
            stats = {}
        stats[key] = int(stats.get(key, 0) or 0) + amount
        kv_set_json(self._SCOPE, self._STATS_KEY, stats)

    def flush(self, force: bool = True) -> None:
        """No-op kept for backward compatibility with previous buffered storage."""
        return
