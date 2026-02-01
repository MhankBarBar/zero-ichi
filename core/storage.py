"""
Per-group data storage system.

Stores group-specific data (notes, filters, settings, etc.) in JSON files.
"""

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


class GroupData:
    """Manages per-group data storage."""

    def __init__(self, group_jid: str) -> None:
        """Initialize storage for a specific group."""
        safe_jid = group_jid.replace(":", "_").replace("@", "_")
        self.group_dir = DATA_DIR / safe_jid
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
        """Save data to a JSON file."""
        file = self._get_file(name)
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

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
        return self.load(
            "anti_link",
            {
                "enabled": False,
                "action": "warn",
                "whitelist": [],
            },
        )

    def save_anti_link(self, config: dict) -> None:
        """Save anti-link settings."""
        self.save("anti_link", config)

    @property
    def warnings_config(self) -> dict:
        """Get warnings configuration for this group."""
        return self.load(
            "warnings_config",
            {
                "enabled": True,
                "limit": 3,
                "action": "kick",
            },
        )

    def save_warnings_config(self, config: dict) -> None:
        """Save warnings configuration."""
        self.save("warnings_config", config)


class Storage:
    """Global storage manager for dashboard API."""

    def __init__(self) -> None:
        """Initialize storage manager."""
        self.stats_file = DATA_DIR / "stats.json"
        self.groups_file = DATA_DIR / "groups.json"

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
        """Save JSON file."""
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_all_groups(self) -> dict:
        """Get all groups and their settings."""
        return self._load_json(self.groups_file, {})

    def get_group_settings(self, group_id: str) -> dict | None:
        """Get settings for a specific group."""
        groups = self.get_all_groups()
        return groups.get(group_id)

    def set_group_settings(self, group_id: str, settings: dict) -> None:
        """Update settings for a group."""
        groups = self.get_all_groups()
        if group_id not in groups:
            groups[group_id] = {}
        groups[group_id].update(settings)
        self._save_json(self.groups_file, groups)

    def register_group(
        self, group_id: str, name: str, member_count: int = 0, is_admin: bool = False
    ) -> None:
        """Register a new group or update existing."""
        groups = self.get_all_groups()
        if group_id not in groups:
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
        self._save_json(self.groups_file, groups)

    def get_stat(self, key: str, default: Any = 0) -> Any:
        """Get a stat value."""
        stats = self._load_json(self.stats_file, {})
        return stats.get(key, default)

    def set_stat(self, key: str, value: Any) -> None:
        """Set a stat value."""
        stats = self._load_json(self.stats_file, {})
        stats[key] = value
        self._save_json(self.stats_file, stats)

    def increment_stat(self, key: str, amount: int = 1) -> None:
        """Increment a stat value."""
        stats = self._load_json(self.stats_file, {})
        stats[key] = stats.get(key, 0) + amount
        self._save_json(self.stats_file, stats)
