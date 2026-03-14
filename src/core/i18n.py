"""
Internationalization (i18n) module for bot messages.

Provides translation support for bot messages with per-chat language settings.
"""

import json
from contextvars import ContextVar

from core import symbols as sym
from core.constants import LOCALES_DIR
from core.db import kv_get_json, kv_set_json
from core.runtime_config import runtime_config

_locales: dict[str, dict] = {}
_default_lang: str = "en"
_chat_languages: dict[str, str] = {}

_current_chat: ContextVar[str | None] = ContextVar("current_chat", default=None)

_available_languages: dict[str, str] = {}


def set_context(chat_jid: str) -> None:
    """Set the current chat context for translations."""
    _current_chat.set(chat_jid)


def get_context() -> str | None:
    """Get the current chat context."""
    return _current_chat.get()


def load_locale(lang: str = "en") -> dict:
    """
    Load a locale file into cache.

    Args:
        lang: Language code (e.g., "en", "id")

    Returns:
        Dictionary of translations
    """
    global _locales, _default_lang

    if lang in _locales:
        return _locales[lang]

    locale_file = LOCALES_DIR / f"{lang}.json"

    if not locale_file.exists():
        locale_file = LOCALES_DIR / "en.json"
        lang = "en"
        if not locale_file.exists():
            return {}

    try:
        with open(locale_file, encoding="utf-8") as f:
            _locales[lang] = json.load(f)
            return _locales[lang]
    except Exception:
        return {}


def get_language(chat_jid: str | None = None) -> str:
    """Get language for a specific chat or default."""
    jid = chat_jid or get_context()
    if jid and jid in _chat_languages:
        return _chat_languages[jid]
    return _default_lang


def set_chat_language(chat_jid: str, lang: str) -> bool:
    """
    Set language for a specific chat.

    Args:
        chat_jid: Chat JID (user or group)
        lang: Language code

    Returns:
        True if successful, False if language not available
    """
    if lang not in _available_languages:
        return False

    _chat_languages[chat_jid] = lang
    load_locale(lang)

    _save_chat_languages()

    return True


def _save_chat_languages() -> None:
    """Save chat language preferences to database."""
    kv_set_json("i18n", "chat_languages", _chat_languages)


def load_chat_languages() -> None:
    """Load saved chat language preferences from database."""
    global _chat_languages
    data = kv_get_json("i18n", "chat_languages", default={})
    _chat_languages = data if isinstance(data, dict) else {}


def t(key: str, chat_jid: str | None = None, **kwargs) -> str:
    """
    Get translated string by key.

    Args:
        key: Dot-notation key (e.g., "errors.group_only")
        chat_jid: Optional chat JID (auto-detected from context if not provided)
        **kwargs: Format arguments

    Returns:
        Translated string or key if not found

    Example:
        t("errors.cooldown", remaining=5.2)
        -> "Cooldown: 5.2s"
    """
    lang = get_language(chat_jid)

    if lang not in _locales:
        load_locale(lang)

    locale = _locales.get(lang, {})

    parts = key.split(".")
    value = locale

    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return key

    if not isinstance(value, str):
        return key

    if kwargs:
        try:
            return value.format(**kwargs)
        except KeyError:
            return value

    return value


def _load_available_languages() -> None:
    """Load available languages from locale files."""
    global _available_languages
    _available_languages = {}

    for file in LOCALES_DIR.glob("*.json"):
        try:
            with open(file, encoding="utf-8") as f:
                data = json.load(f)
                meta = data.get("_meta", {})
                label = meta.get("label", file.stem)
                _available_languages[file.stem] = label
        except Exception:
            _available_languages[file.stem] = file.stem


def init_i18n(lang: str | None = None) -> None:
    """
    Initialize i18n with language from config.

    Args:
        lang: Language code, or None to load from config
    """
    global _default_lang

    lang_value = (
        lang if lang is not None else runtime_config.get_nested("bot", "language", default="en")
    )
    lang_code = str(lang_value).strip() if isinstance(lang_value, str) else "en"
    if not lang_code:
        lang_code = "en"

    _default_lang = lang_code
    _load_available_languages()
    load_locale(lang_code)
    load_chat_languages()


def reload_locales(lang: str | None = None) -> None:
    """
    Reload locale data from disk.

    Args:
        lang: Optional language code to reload. If omitted, all locale
            caches are cleared and reloaded.
    """
    global _locales

    if lang:
        _locales.pop(lang, None)
        load_locale(lang)
        return

    _locales.clear()
    _load_available_languages()
    load_locale(_default_lang)


def get_available_languages() -> dict[str, str]:
    """Return dict of available language codes and names."""
    return _available_languages.copy()


def t_error(key: str, chat_jid: str | None = None, **kwargs) -> str:
    """Get translated error message with error symbol."""
    return sym.error(t(key, chat_jid, **kwargs))


def t_success(key: str, chat_jid: str | None = None, **kwargs) -> str:
    """Get translated success message with success symbol."""
    return sym.success(t(key, chat_jid, **kwargs))


def t_warning(key: str, chat_jid: str | None = None, **kwargs) -> str:
    """Get translated warning message with warning symbol."""
    return sym.warning(t(key, chat_jid, **kwargs))


def t_info(key: str, chat_jid: str | None = None, **kwargs) -> str:
    """Get translated info message with info symbol."""
    return f"{sym.INFO} {t(key, chat_jid, **kwargs)}"
