from pathlib import Path

import ai.memory as memory_module
import core.db as db_module
from ai.memory import clear_memory, get_memory
from core.privacy import (
    clear_chat_memory_override,
    get_analytics_retention_days,
    get_chat_memory_override,
    is_chat_memory_enabled,
    set_chat_memory_enabled,
)


def _reset_db(tmp_path: Path, monkeypatch) -> None:
    db_file = tmp_path / "privacy_controls.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    db_module._engine = None
    db_module._ready = False
    db_module.ensure_database_ready()


def test_chat_memory_override_roundtrip(tmp_path, monkeypatch):
    _reset_db(tmp_path, monkeypatch)

    chat = "123@g.us"
    assert get_chat_memory_override(chat) is None

    set_chat_memory_enabled(chat, False)
    assert get_chat_memory_override(chat) is False
    assert is_chat_memory_enabled(chat) is False

    set_chat_memory_enabled(chat, True)
    assert get_chat_memory_override(chat) is True
    assert is_chat_memory_enabled(chat) is True

    assert clear_chat_memory_override(chat) is True
    assert get_chat_memory_override(chat) is None


def test_analytics_retention_days_clamped(monkeypatch):
    monkeypatch.setattr(
        "core.privacy.runtime_config.get_nested",
        lambda *_args, **_kwargs: 999,
    )
    assert get_analytics_retention_days() == 365

    monkeypatch.setattr(
        "core.privacy.runtime_config.get_nested",
        lambda *_args, **_kwargs: -5,
    )
    assert get_analytics_retention_days() == 1


def test_clear_memory_for_uncached_chat(tmp_path, monkeypatch):
    _reset_db(tmp_path, monkeypatch)

    chat = "987@g.us"
    mem = get_memory(chat, ttl_hours=24)
    mem.add(role="user", content="hello")
    assert len(mem.get_history()) == 1

    # Simulate uncached chat memory object
    memory_module._memory_cache.pop(chat, None)

    clear_memory(chat)

    reloaded = get_memory(chat, ttl_hours=24)
    assert len(reloaded.get_history()) == 0
