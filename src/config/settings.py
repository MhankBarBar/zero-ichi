"""
Configuration settings loader.

This module provides backward-compatible access to settings.
The actual configuration is managed by core.runtime_config.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

_runtime_config = None


def _get_config():
    """Get the runtime config singleton."""
    global _runtime_config
    if _runtime_config is None:
        from core.runtime_config import runtime_config

        _runtime_config = runtime_config
    return _runtime_config


def _init_values():
    """Initialize values from config."""
    try:
        cfg = _get_config()
        return {
            "BOT_NAME": cfg.bot_name,
            "PREFIX": cfg.prefix,
            "LOGIN_METHOD": cfg.login_method,
            "PHONE_NUMBER": cfg.phone_number,
            "OWNER_JID": cfg.get_owner_jid(),
            "IGNORE_SELF_MESSAGES": cfg.get_nested("bot", "ignore_self_messages", default=True),
            "LOG_MESSAGES": cfg.get_nested("logging", "log_messages", default=True),
            "VERBOSE_LOGGING": cfg.get_nested("logging", "verbose", default=False),
            "LOG_LEVEL": cfg.get_nested("logging", "level", default="INFO"),
            "FILE_LOGGING": cfg.get_nested("logging", "file_logging", default=True),
            "AUTO_READ": cfg.get_nested("bot", "auto_read", default=True),
            "AUTO_RELOAD": cfg.get_nested("bot", "auto_reload", default=True),
        }
    except Exception:
        return {
            "BOT_NAME": "Zero Ichi",
            "PREFIX": "/",
            "LOGIN_METHOD": "QR",
            "PHONE_NUMBER": "",
            "OWNER_JID": "",
            "IGNORE_SELF_MESSAGES": True,
            "LOG_MESSAGES": True,
            "VERBOSE_LOGGING": False,
            "LOG_LEVEL": "INFO",
            "FILE_LOGGING": True,
            "AUTO_READ": True,
            "AUTO_RELOAD": True,
        }


_values = _init_values()
BOT_NAME = _values["BOT_NAME"]
PREFIX = _values["PREFIX"]
LOGIN_METHOD = _values["LOGIN_METHOD"]
PHONE_NUMBER = _values["PHONE_NUMBER"]
OWNER_JID = _values["OWNER_JID"]
IGNORE_SELF_MESSAGES = _values["IGNORE_SELF_MESSAGES"]
LOG_MESSAGES = _values["LOG_MESSAGES"]
VERBOSE_LOGGING = _values["VERBOSE_LOGGING"]
LOG_LEVEL = _values["LOG_LEVEL"]
FILE_LOGGING = _values["FILE_LOGGING"]
AUTO_READ = _values["AUTO_READ"]
AUTO_RELOAD = _values["AUTO_RELOAD"]


class FeatureFlags:
    """
    Mutable feature flags for runtime toggling.
    Reads from and syncs with runtime_config.
    """

    def __getattr__(self, name: str) -> bool:
        """Get feature flag from runtime config."""
        cfg = _get_config()
        return cfg.get_feature(name)

    def __setattr__(self, name: str, value: bool) -> None:
        """Set feature flag in runtime config."""
        cfg = _get_config()
        cfg.set_feature(name, value)


features = FeatureFlags()


def _get_anti_delete_settings():
    cfg = _get_config()
    return {
        "forward_to": cfg.get_nested("anti_delete", "forward_to", default=""),
        "cache_ttl": cfg.get_nested("anti_delete", "cache_ttl", default=60),
    }


def _get_anti_link_settings():
    cfg = _get_config()
    return {
        "action": cfg.get_nested("anti_link", "action", default="warn"),
        "whitelist": cfg.get_nested("anti_link", "whitelist", default=[]),
    }


def _get_warnings_settings():
    cfg = _get_config()
    return {
        "limit": cfg.get_nested("warnings", "limit", default=3),
        "action": cfg.get_nested("warnings", "action", default="kick"),
    }


_ad = _get_anti_delete_settings()
ANTI_DELETE_FORWARD_TO = _ad["forward_to"]
ANTI_DELETE_CACHE_TTL = _ad["cache_ttl"]

_al = _get_anti_link_settings()
ANTI_LINK_ACTION = _al["action"]
ANTI_LINK_WHITELIST = _al["whitelist"]

_w = _get_warnings_settings()
WARN_LIMIT = _w["limit"]
WARN_ACTION = _w["action"]
