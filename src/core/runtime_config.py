"""
Runtime configuration manager.

This is the MAIN configuration system for the bot.
All settings are stored in a JSON file with JSON Schema validation.

See config.schema.json for the schema definition.
"""

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from core import jsonc

CONFIG_FILE = Path(__file__).parent.parent.parent / "config.json"
OVERRIDES_FILE = Path(__file__).parent.parent.parent / "data" / "runtime_overrides.json"
OVERRIDES_MIGRATION_MARKER = (
    Path(__file__).parent.parent.parent / "data" / ".runtime_overrides_migrated"
)
DEFAULT_SCHEMA_PATH = "./config.schema.json"

DEFAULT_CONFIG = {
    "bot": {
        "name": "Zero Ichi",
        "prefix": "/",
        "login_method": "QR",
        "phone_number": "",
        "owner_jid": "",
        "auto_read": False,
        "auto_reload": True,
        "auto_react": False,
        "auto_react_emoji": "",
        "ignore_self_messages": True,
        "self_mode": False,
    },
    "logging": {
        "log_messages": True,
        "verbose": False,
        "level": "INFO",
        "file_logging": True,
    },
    "features": {
        "anti_delete": True,
        "anti_link": True,
        "welcome": True,
        "notes": True,
        "filters": True,
        "blacklist": True,
        "warnings": True,
        "automation_rules": True,
    },
    "anti_delete": {
        "forward_to": "",
        "cache_ttl": 60,
    },
    "anti_link": {
        "action": "warn",
        "whitelist": [],
    },
    "warnings": {
        "limit": 3,
        "action": "kick",
    },
    "downloader": {
        "max_file_size_mb": 50,
        "auto_link_download": {
            "enabled": False,
            "mode": "auto",
            "cooldown_seconds": 30,
            "max_links_per_message": 1,
            "group_only": True,
        },
    },
    "call_guard": {
        "enabled": False,
        "action": "block",
        "delay_seconds": 3,
        "notify_caller": True,
        "notify_owner": True,
        "whitelist": [],
    },
    "agentic_ai": {
        "enabled": False,
        "provider": "openai",
        "api_key": "",
        "model": "gpt-4o-mini",
        "trigger_mode": "mention",
        "allowed_actions": [],
        "blocked_actions": ["eval", "aeval", "addcommand", "delcommand"],
        "owner_only": True,
    },
    "disabled_commands": [],
    "dashboard": {
        "enabled": False,
    },
}


class RuntimeConfig:
    """
    Manages bot configuration with runtime modification and persistence.

    All changes are automatically saved to the JSONC config file.
    """

    _instance = None

    def __new__(cls):
        """Singleton pattern - only one config instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._config: dict[str, Any] = {}
        self._load()

    def _ensure_config_file(self) -> None:
        """Ensure the config file exists with defaults."""
        if not CONFIG_FILE.exists():
            self._write_default_config()

    def _write_default_config(self) -> None:
        """Write default config file."""
        default_config = self._ensure_schema_key(deepcopy(DEFAULT_CONFIG))
        jsonc.dump(default_config, CONFIG_FILE, indent=2)

    def _ensure_schema_key(self, config: dict[str, Any]) -> dict[str, Any]:
        """Ensure config keeps top-level $schema key as the first field."""
        schema = config.get("$schema") or DEFAULT_SCHEMA_PATH
        rest = {k: v for k, v in config.items() if k != "$schema"}
        return {"$schema": schema, **rest}

    def _normalize_legacy_actions(self, config: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Normalize legacy moderation action values to supported ones."""
        changed = False

        bot = config.get("bot")
        if isinstance(bot, dict):
            login_method = str(bot.get("login_method", "QR")).upper()
            if login_method in {"PAIR_CODE", "QR"}:
                if bot.get("login_method") != login_method:
                    bot["login_method"] = login_method
                    changed = True
            else:
                bot["login_method"] = "QR"
                changed = True

        anti_link = config.get("anti_link")
        if isinstance(anti_link, dict):
            action = str(anti_link.get("action", "warn")).lower()
            if action in {"ban", "mute"}:
                anti_link["action"] = "kick"
                changed = True
            elif action not in {"warn", "delete", "kick"}:
                anti_link["action"] = "warn"
                changed = True

        warnings = config.get("warnings")
        if isinstance(warnings, dict):
            action = str(warnings.get("action", "kick")).lower()
            if action != "kick":
                warnings["action"] = "kick"
                changed = True

        call_guard = config.get("call_guard")
        if isinstance(call_guard, dict):
            action = str(call_guard.get("action", "block")).lower()
            if action not in {"off", "block"}:
                call_guard["action"] = "block"
                changed = True

            try:
                delay = int(call_guard.get("delay_seconds", 3))
            except (TypeError, ValueError):
                delay = 3
            delay = max(0, min(delay, 60))
            if call_guard.get("delay_seconds") != delay:
                call_guard["delay_seconds"] = delay
                changed = True

        return config, changed

    def _migrate_runtime_overrides(self, config: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """One-time migration from data/runtime_overrides.json into config.json."""
        if not OVERRIDES_FILE.exists() or OVERRIDES_MIGRATION_MARKER.exists():
            return config, False

        changed = False
        try:
            with open(OVERRIDES_FILE, encoding="utf-8") as f:
                overrides = json.load(f)
            if isinstance(overrides, dict) and overrides:
                config = self._deep_merge(config, overrides)
                changed = True
        except Exception:
            pass

        OVERRIDES_MIGRATION_MARKER.parent.mkdir(parents=True, exist_ok=True)
        OVERRIDES_MIGRATION_MARKER.write_text("migrated", encoding="utf-8")
        return config, changed

    def _load(self) -> None:
        """Load configuration from config.json and apply compatibility normalization."""
        self._ensure_config_file()

        try:
            loaded = jsonc.load(CONFIG_FILE)
            if not isinstance(loaded, dict):
                loaded = {}

            config = self._merge_defaults(loaded, DEFAULT_CONFIG)
            config, migrated = self._migrate_runtime_overrides(config)
            config, normalized = self._normalize_legacy_actions(config)
            config = self._ensure_schema_key(config)

            self._config = config

            if migrated or normalized or "$schema" not in loaded:
                self._save()

        except Exception as e:
            print(f"[CONFIG] Error loading config: {e}")
            self._config = self._ensure_schema_key(deepcopy(DEFAULT_CONFIG))
            self._save()

    def _merge_defaults(self, config: dict, defaults: dict) -> dict:
        """Recursively merge defaults into config for missing keys."""
        result = deepcopy(defaults)
        for key, value in config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_defaults(value, result[key])
            else:
                result[key] = value
        return result

    def _deep_merge(self, base: dict, overrides: dict) -> dict:
        """Deep merge overrides into base config."""
        result = deepcopy(base)
        for key, value in overrides.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _save(self) -> None:
        """Persist full runtime config into config.json."""
        self._config = self._ensure_schema_key(self._config)
        jsonc.dump(self._config, CONFIG_FILE, indent=2)

    def reload(self) -> None:
        """Reload configuration from file."""
        self._load()

    @property
    def bot_name(self) -> str:
        return self._config.get("bot", {}).get("name", "Zero Ichi")

    @property
    def prefix(self) -> str:
        return self._config.get("bot", {}).get("prefix", "/")

    @property
    def display_prefix(self) -> str:
        """
        Get a user-friendly display version of the prefix.

        For regex patterns, extracts a simple example:
        - "[!/.]" → "/" (first char in class)
        - "^[!/]" → "/" (first char in class after anchor)
        - "(?:!|/)" → "/" (first alternative)
        - Regular string → returns as-is
        """
        raw = self.prefix
        if not raw:
            return ""

        regex_chars = r"^$.*+?{}[]|()\\"
        is_regex = any(c in raw for c in regex_chars)

        if not is_regex:
            return raw

        pattern = raw.lstrip("^")

        char_class_match = re.search(r"\[([^\]]+)\]", pattern)
        if char_class_match:
            chars = char_class_match.group(1)
            for i, c in enumerate(chars):
                if c == "\\":
                    continue
                if i > 0 and chars[i - 1] == "\\":
                    return c
                return c

        alt_match = re.search(r"\(\?:([^)]+)\)", pattern)
        if alt_match:
            alts = alt_match.group(1).split("|")
            if alts:
                return alts[0]

        alt_match = re.search(r"\(([^)]+)\)", pattern)
        if alt_match:
            alts = alt_match.group(1).split("|")
            if alts:
                return alts[0]

        for c in pattern:
            if c not in regex_chars:
                return c

        return raw

    @property
    def self_mode(self) -> bool:
        """Check if self mode is enabled (only respond to self messages)."""
        return self._config.get("bot", {}).get("self_mode", False)

    def set_self_mode(self, enabled: bool) -> None:
        """Set self mode on or off."""
        if "bot" not in self._config:
            self._config["bot"] = {}
        self._config["bot"]["self_mode"] = enabled
        self._save()

    @property
    def login_method(self) -> str:
        return str(self._config.get("bot", {}).get("login_method", "QR")).upper()

    @property
    def phone_number(self) -> str:
        return self._config.get("bot", {}).get("phone_number", "")

    def get_owner_jid(self) -> str:
        """Get the owner JID."""
        return self._config.get("bot", {}).get("owner_jid", "")

    def set_owner_jid(self, jid: str) -> None:
        """Set the owner JID."""
        if "bot" not in self._config:
            self._config["bot"] = {}
        self._config["bot"]["owner_jid"] = jid
        self._save()

    def is_owner(self, sender_jid: str) -> bool:
        """Check if the sender is the bot owner (sync fallback, compares user parts only)."""
        owner = self.get_owner_jid()
        if not owner:
            return False

        sender_user = sender_jid.split("@")[0].split(":")[0]
        owner_user = owner.split("@")[0].split(":")[0]

        return sender_user == owner_user

    async def is_owner_async(self, sender_jid: str, client=None) -> bool:
        """
        Check if the sender is the bot owner (async with JID resolution).

        This method can compare JIDs across PN and LID formats by resolving
        them through the WhatsApp API.

        Args:
            sender_jid: The sender's JID to check
            client: Optional BotClient for API-based resolution

        Returns:
            True if sender is the owner
        """
        owner = self.get_owner_jid()
        if not owner:
            return False

        from core.jid_resolver import jids_match

        return await jids_match(sender_jid, owner, client)

    def get_feature(self, name: str) -> bool:
        """Get a feature flag value."""
        return self._config.get("features", {}).get(name, False)

    def set_feature(self, name: str, value: bool) -> None:
        """Set a feature flag value."""
        if "features" not in self._config:
            self._config["features"] = {}
        self._config["features"][name] = value
        self._save()

        try:
            from config.settings import features

            if hasattr(features, name):
                setattr(features, name, value)
        except ImportError:
            pass

    def get_all_features(self) -> dict[str, bool]:
        """Get all feature flags."""
        return self._config.get("features", {}).copy()

    def get_disabled_commands(self) -> list[str]:
        """Get list of disabled commands."""
        return self._config.get("disabled_commands", [])

    def is_command_enabled(self, command_name: str) -> bool:
        """Check if a command is enabled."""
        return command_name.lower() not in self.get_disabled_commands()

    def enable_command(self, command_name: str) -> bool:
        """Enable a command. Returns True if it was disabled."""
        disabled = self.get_disabled_commands()
        cmd = command_name.lower()
        if cmd in disabled:
            disabled.remove(cmd)
            self._config["disabled_commands"] = disabled
            self._save()
            return True
        return False

    def disable_command(self, command_name: str) -> bool:
        """Disable a command. Returns True if it was enabled."""
        disabled = self.get_disabled_commands()
        cmd = command_name.lower()
        if cmd not in disabled:
            disabled.append(cmd)
            self._config["disabled_commands"] = disabled
            self._save()
            return True
        return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a top-level config value."""
        return self._config.get(key, default)

    def get_nested(self, *keys, default: Any = None) -> Any:
        """Get a nested config value. E.g., get_nested('bot', 'name')"""
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set a top-level config value."""
        self._config[key] = value
        self._save()

    def set_nested(self, *keys_and_value) -> None:
        """Set a nested config value. Last argument is the value."""
        if len(keys_and_value) < 2:
            return

        keys = keys_and_value[:-1]
        value = keys_and_value[-1]

        current = self._config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value
        self._save()

    def all_config(self) -> dict[str, Any]:
        """Get all configuration."""
        return self._config.copy()


runtime_config = RuntimeConfig()
