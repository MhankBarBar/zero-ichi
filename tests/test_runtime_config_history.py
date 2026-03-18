from pathlib import Path

import pytest

import core.runtime_config as runtime_config_module


@pytest.fixture
def isolated_runtime_config(tmp_path, monkeypatch):
    schema_path = Path(__file__).resolve().parents[1] / "config.schema.json"

    monkeypatch.setattr(runtime_config_module, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(runtime_config_module, "SCHEMA_FILE", schema_path)
    monkeypatch.setattr(
        runtime_config_module, "OVERRIDES_FILE", tmp_path / "runtime_overrides.json"
    )
    monkeypatch.setattr(
        runtime_config_module,
        "OVERRIDES_MIGRATION_MARKER",
        tmp_path / ".runtime_overrides_migrated",
    )
    monkeypatch.setattr(runtime_config_module, "HISTORY_FILE", tmp_path / "config_history.json")
    runtime_config_module.RuntimeConfig._instance = None

    cfg = runtime_config_module.RuntimeConfig()
    yield cfg

    runtime_config_module.RuntimeConfig._instance = None


def test_history_records_on_config_updates(isolated_runtime_config):
    cfg = isolated_runtime_config

    cfg.set_nested("bot", "prefix", "!")

    entries = cfg.list_config_history(limit=5)
    assert entries
    assert entries[0]["id"].startswith("H")
    assert entries[0]["reason"] == "update"


def test_rollback_restores_snapshot_config(isolated_runtime_config):
    cfg = isolated_runtime_config

    cfg.set_nested("bot", "prefix", "!")
    cfg.set_nested("bot", "prefix", "#")
    assert cfg.get_nested("bot", "prefix") == "#"

    result = cfg.rollback_config("H0001")
    assert result is not None
    assert cfg.get_nested("bot", "prefix") == "/"


def test_rollback_unknown_id_returns_none(isolated_runtime_config):
    cfg = isolated_runtime_config

    cfg.set_nested("bot", "prefix", "!")
    result = cfg.rollback_config("H9999")
    assert result is None
