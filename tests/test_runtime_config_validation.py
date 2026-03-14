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
    runtime_config_module.RuntimeConfig._instance = None

    cfg = runtime_config_module.RuntimeConfig()
    yield cfg

    runtime_config_module.RuntimeConfig._instance = None


def test_invalid_schema_update_is_rejected(isolated_runtime_config):
    cfg = isolated_runtime_config

    before = cfg.get_nested("rate_limit", "burst_limit")

    with pytest.raises(ValueError):
        cfg.set_nested("rate_limit", "burst_limit", 0)

    assert cfg.get_nested("rate_limit", "burst_limit") == before


def test_valid_schema_update_is_persisted(isolated_runtime_config):
    cfg = isolated_runtime_config

    cfg.set_nested("rate_limit", "burst_limit", 9)

    assert cfg.get_nested("rate_limit", "burst_limit") == 9
