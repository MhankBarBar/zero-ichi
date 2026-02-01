"""
Runtime configuration manager.

This is the MAIN configuration system for the bot.
All settings are stored in a JSON file with JSON Schema validation.

See config.schema.json for the schema definition.
"""

from pathlib import Path
from typing import Any

from core import jsonc

CONFIG_FILE = Path(__file__).parent.parent / "config.json"

DEFAULT_CONFIG = {
    "bot": {
        "name": "Zero Ichi",
        "prefix": "/",
        "login_method": "qr",
        "phone_number": "",
        "owner_jid": "",
        "auto_read": False,
        "auto_react": False,
        "auto_react_emoji": "",
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
        """Write default config with comments."""
        config_content = """{
  // Bot Configuration
  // This file uses JSONC format - comments are supported!

  "bot": {
    // Bot session name (used for database file)
    "name": "Zero Ichi",

    // Command prefix (can be a single character or regex pattern)
    "prefix": "/",

    // Login method: "qr" or "pair_code"
    "login_method": "qr",

    // Phone number for pair_code login (with country code, e.g., "628123456789")
    "phone_number": "",

    // Bot owner JID (set via /config owner me, or manually here)
    // Format: "123456@lid" or "1234567890@s.whatsapp.net"
    "owner_jid": ""
  },

  "logging": {
    // Log incoming messages to console
    "log_messages": true,

    // Verbose debug logging
    "verbose": false,

    // Log level: DEBUG, INFO, WARNING, ERROR
    "level": "INFO",

    // Enable file logging to logs/ directory
    "file_logging": true
  },

  "features": {
    // Anti-delete: reveal deleted messages
    "anti_delete": true,

    // Anti-link: detect and handle links in groups
    "anti_link": false,

    // Welcome messages for new group members
    "welcome": true,

    // Notes system (
    "notes": true,

    // Auto-reply filters
    "filters": true,

    // Word blacklist with auto-delete
    "blacklist": true,

    // Warning system
    "warnings": true
  },

  "anti_delete": {
    // JID to forward deleted messages to (leave empty to reply in-place)
    "forward_to": "",

    // How long to cache messages (minutes)
    "cache_ttl": 60
  },

  "anti_link": {
    // Action when link detected: "warn", "delete", "kick", "ban"
    "action": "warn",

    // Whitelisted domains (e.g., ["youtube.com", "github.com"])
    "whitelist": []
  },

  "warnings": {
    // Max warnings before action
    "limit": 3,

    // Action at limit: "kick", "ban", "mute"
    "action": "kick"
  },

  // Commands disabled at runtime (managed via /config cmd disable)
  "disabled_commands": []
}"""
        CONFIG_FILE.write_text(config_content, encoding="utf-8")

    def _load(self) -> None:
        """
        Load configuration from JSON file + runtime overrides.

        - config.json: Base config with JSON Schema (user edits this)
        - data/runtime_overrides.json: Runtime changes (bot edits this)
        """
        self._ensure_config_file()

        try:
            base_config = jsonc.load(CONFIG_FILE)

            overrides_file = Path(__file__).parent.parent / "data" / "runtime_overrides.json"
            overrides = {}
            if overrides_file.exists():
                try:
                    import json

                    with open(overrides_file, encoding="utf-8") as f:
                        overrides = json.load(f)
                except Exception:
                    pass

            self._config = self._merge_defaults(base_config, DEFAULT_CONFIG)
            self._config = self._deep_merge(self._config, overrides)

        except Exception as e:
            print(f"[CONFIG] Error loading config: {e}")
            self._config = DEFAULT_CONFIG.copy()

    def _merge_defaults(self, config: dict, defaults: dict) -> dict:
        """Recursively merge defaults into config for missing keys."""
        result = defaults.copy()
        for key, value in config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_defaults(value, result[key])
            else:
                result[key] = value
        return result

    def _deep_merge(self, base: dict, overrides: dict) -> dict:
        """Deep merge overrides into base config."""
        result = base.copy()
        for key, value in overrides.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _save(self) -> None:
        """
        Save runtime overrides to a separate file.

        This keeps config.json clean by only saving
        the differences (overrides) to a separate JSON file.
        """
        import json

        try:
            base_config = jsonc.load(CONFIG_FILE)
            base_config = self._merge_defaults(base_config, DEFAULT_CONFIG)
        except Exception:
            base_config = DEFAULT_CONFIG.copy()

        overrides = self._calc_overrides(base_config, self._config)

        overrides_file = Path(__file__).parent.parent / "data" / "runtime_overrides.json"
        overrides_file.parent.mkdir(parents=True, exist_ok=True)

        with open(overrides_file, "w", encoding="utf-8") as f:
            json.dump(overrides, f, indent=2, ensure_ascii=False)

    def _calc_overrides(self, base: dict, current: dict) -> dict:
        """Calculate the differences between base and current config."""
        overrides = {}

        for key, value in current.items():
            if key not in base:
                overrides[key] = value
            elif isinstance(value, dict) and isinstance(base.get(key), dict):
                nested = self._calc_overrides(base[key], value)
                if nested:
                    overrides[key] = nested
            elif value != base.get(key):
                overrides[key] = value

        return overrides

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

        import re

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
        return self._config.get("bot", {}).get("login_method", "qr")

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
        """Check if the sender is the bot owner."""
        owner = self.get_owner_jid()
        if not owner:
            return False

        sender_user = sender_jid.split("@")[0].split(":")[0]
        owner_user = owner.split("@")[0].split(":")[0]

        return sender_user == owner_user

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
