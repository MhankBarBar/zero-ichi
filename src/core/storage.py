"""
Per-group data storage system.

Stores group-specific data (notes, filters, settings, etc.) in JSON files.
"""

import json
import os
import tempfile
import threading
import time
from atexit import register as on_exit
from pathlib import Path
from typing import Any

from core.constants import DATA_DIR

DATA_DIR.mkdir(exist_ok=True)


def safe_jid(jid: str) -> str:
    """Sanitize a JID for use in file/directory names."""
    return jid.replace(":", "_").replace("@", "_")


def _atomic_write(file: Path, data: Any) -> None:
    """Write JSON data atomically using write-to-temp-then-rename.

    This prevents data corruption if the process crashes mid-write.
    """
    file.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=file.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, file)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


class GroupData:
    """Manages per-group data storage."""

    def __init__(self, group_jid: str) -> None:
        """Initialize storage for a specific group."""
        self.group_dir = DATA_DIR / safe_jid(group_jid)
        self.group_dir.mkdir(exist_ok=True)

    def _get_file(self, name: str) -> Path:
        """Get path to a data file."""
        return self.group_dir / f"{name}.json"

    def load(self, name: str, default: Any = None) -> Any:
        """Load data from a JSON file."""
        file = self._get_file(name)
        if not file.exists():
            return default if default is not None else {}

        try:
            with open(file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return default if default is not None else {}

    def save(self, name: str, data: Any) -> None:
        """Save data to a JSON file (atomic write)."""
        file = self._get_file(name)
        _atomic_write(file, data)

    @property
    def settings(self) -> dict:
        """Get group settings."""
        return self.load("settings", {})

    def save_settings(self, settings: dict) -> None:
        """Save group settings."""
        self.save("settings", settings)

    @property
    def notes(self) -> dict:
        """Get saved notes."""
        return self.load("notes", {})

    def save_notes(self, notes: dict) -> None:
        """Save notes."""
        self.save("notes", notes)

    @property
    def filters(self) -> dict:
        """Get auto-reply filters."""
        return self.load("filters", {})

    def save_filters(self, filters: dict) -> None:
        """Save filters."""
        self.save("filters", filters)

    @property
    def blacklist(self) -> list:
        """Get blacklisted words."""
        return self.load("blacklist", [])

    def save_blacklist(self, words: list) -> None:
        """Save blacklist."""
        self.save("blacklist", words)

    @property
    def warnings(self) -> dict:
        """Get user warnings."""
        return self.load("warnings", {})

    def save_warnings(self, warnings: dict) -> None:
        """Save warnings."""
        self.save("warnings", warnings)

    @property
    def welcome(self) -> dict:
        """Get welcome message config."""
        return self.load("welcome", {"enabled": False, "message": ""})

    def save_welcome(self, config: dict) -> None:
        """Save welcome config."""
        self.save("welcome", config)

    @property
    def anti_link(self) -> dict:
        """Get anti-link settings for this group."""
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
        """Save anti-link settings."""
        self.save("anti_link", config)

    @property
    def warnings_config(self) -> dict:
        """Get warnings configuration for this group."""
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
        """Save warnings configuration."""
        self.save("warnings_config", config)

    @property
    def reports(self) -> dict:
        """Get moderation reports payload."""
        return self.load("reports", {"counter": 0, "items": []})

    def save_reports(self, payload: dict) -> None:
        """Save moderation reports payload."""
        self.save("reports", payload)

    @property
    def digest(self) -> dict:
        """Get digest settings for this group."""
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
        """Save digest settings."""
        self.save("digest", config)

    @property
    def automations(self) -> list:
        """Get automation rules for this group."""
        rules = self.load("automations", [])
        return rules if isinstance(rules, list) else []

    def save_automations(self, rules: list) -> None:
        """Save automation rules for this group."""
        self.save("automations", rules)

    @property
    def muted(self) -> list:
        """Get list of muted users."""
        return self.load("muted", [])

    def save_muted(self, users: list) -> None:
        """Save muted users."""
        self.save("muted", users)


class Storage:
    """Global storage manager for dashboard API."""

    _cache_lock = threading.Lock()
    _stats_cache: dict[str, Any] | None = None
    _groups_cache: dict[str, Any] | None = None
    _stats_dirty = False
    _groups_dirty = False
    _last_flush_ts = 0.0
    _flush_interval_seconds = 2.0
    _atexit_registered = False

    def __init__(self) -> None:
        """Initialize storage manager."""
        self.stats_file = DATA_DIR / "stats.json"
        self.groups_file = DATA_DIR / "groups.json"
        if not Storage._atexit_registered:
            on_exit(self.flush)
            Storage._atexit_registered = True

    def _load_json(self, file: Path, default: Any = None) -> Any:
        """Load JSON file."""
        if not file.exists():
            return default if default is not None else {}
        try:
            with open(file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return default if default is not None else {}

    def _save_json(self, file: Path, data: Any) -> None:
        """Save JSON file (atomic write)."""
        _atomic_write(file, data)

    def _ensure_stats_cache(self) -> dict[str, Any]:
        """Ensure stats cache is loaded into memory."""
        if Storage._stats_cache is None:
            loaded = self._load_json(self.stats_file, {})
            Storage._stats_cache = loaded if isinstance(loaded, dict) else {}
        return Storage._stats_cache

    def _ensure_groups_cache(self) -> dict[str, Any]:
        """Ensure groups cache is loaded into memory."""
        if Storage._groups_cache is None:
            loaded = self._load_json(self.groups_file, {})
            Storage._groups_cache = loaded if isinstance(loaded, dict) else {}
        return Storage._groups_cache

    def _flush_if_needed(self, force: bool = False) -> None:
        """Flush dirty caches to disk on interval or force."""
        now = time.time()
        if not force and now - Storage._last_flush_ts < Storage._flush_interval_seconds:
            return

        if Storage._stats_dirty and Storage._stats_cache is not None:
            self._save_json(self.stats_file, Storage._stats_cache)
            Storage._stats_dirty = False

        if Storage._groups_dirty and Storage._groups_cache is not None:
            self._save_json(self.groups_file, Storage._groups_cache)
            Storage._groups_dirty = False

        Storage._last_flush_ts = now

    def flush(self, force: bool = True) -> None:
        """Flush in-memory dirty data to disk."""
        with Storage._cache_lock:
            self._flush_if_needed(force=force)

    def get_all_groups(self) -> dict:
        """Get all groups and their settings."""
        with Storage._cache_lock:
            groups = self._ensure_groups_cache()
            return groups.copy()

    def get_group_settings(self, group_id: str) -> dict | None:
        """Get settings for a specific group."""
        with Storage._cache_lock:
            groups = self._ensure_groups_cache()
            settings = groups.get(group_id)
            if isinstance(settings, dict):
                return settings.copy()
            return settings

    def set_group_settings(self, group_id: str, settings: dict) -> None:
        """Update settings for a group."""
        with Storage._cache_lock:
            groups = self._ensure_groups_cache()
            if group_id not in groups or not isinstance(groups[group_id], dict):
                groups[group_id] = {}
            groups[group_id].update(settings)
            Storage._groups_dirty = True
            self._flush_if_needed()

    def register_group(
        self, group_id: str, name: str, member_count: int = 0, is_admin: bool = False
    ) -> None:
        """Register a new group or update existing."""
        with Storage._cache_lock:
            groups = self._ensure_groups_cache()
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
            Storage._groups_dirty = True
            self._flush_if_needed()

    def get_stat(self, key: str, default: Any = 0) -> Any:
        """Get a stat value."""
        with Storage._cache_lock:
            stats = self._ensure_stats_cache()
            return stats.get(key, default)

    def set_stat(self, key: str, value: Any) -> None:
        """Set a stat value."""
        with Storage._cache_lock:
            stats = self._ensure_stats_cache()
            stats[key] = value
            Storage._stats_dirty = True
            self._flush_if_needed()

    def increment_stat(self, key: str, amount: int = 1) -> None:
        """Increment a stat value."""
        with Storage._cache_lock:
            stats = self._ensure_stats_cache()
            stats[key] = stats.get(key, 0) + amount
            Storage._stats_dirty = True
            self._flush_if_needed()
