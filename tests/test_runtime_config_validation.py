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


def test_missing_schema_is_merged_and_preserved(tmp_path, monkeypatch):
    schema_path = Path(__file__).resolve().parents[1] / "config.schema.json"
    config_path = tmp_path / "config.json"
    config_path.write_text(
        """
{
  "bot": {
    "name": "Custom Bot",
    "owner_jid": "12345@s.whatsapp.net"
  },
  "features": {
    "notes": false
  }
}
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(runtime_config_module, "CONFIG_FILE", config_path)
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

    assert cfg.get_nested("bot", "name") == "Custom Bot"
    assert cfg.get_nested("bot", "owner_jid") == "12345@s.whatsapp.net"
    assert cfg.get_nested("features", "notes") is False
    assert cfg.get_nested("features", "anti_delete") is True

    persisted = runtime_config_module.jsonc.load(config_path)
    assert persisted.get("$schema") == runtime_config_module.DEFAULT_SCHEMA_PATH
    assert persisted.get("bot", {}).get("name") == "Custom Bot"
    assert persisted.get("features", {}).get("notes") is False

    runtime_config_module.RuntimeConfig._instance = None


def test_invalid_config_does_not_overwrite_file(tmp_path, monkeypatch):
    schema_path = Path(__file__).resolve().parents[1] / "config.schema.json"
    config_path = tmp_path / "config.json"
    invalid_content = """
{
  "bot": "not-an-object"
}
""".strip()
    config_path.write_text(invalid_content, encoding="utf-8")

    monkeypatch.setattr(runtime_config_module, "CONFIG_FILE", config_path)
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

    assert cfg.get_nested("bot", "name") == "Zero Ichi"
    assert config_path.read_text(encoding="utf-8").strip() == invalid_content

    runtime_config_module.RuntimeConfig._instance = None


def test_missing_default_keys_are_persisted_with_existing_schema(tmp_path, monkeypatch):
    schema_path = Path(__file__).resolve().parents[1] / "config.schema.json"
    config_path = tmp_path / "config.json"
    config_path.write_text(
        """
{
  "$schema": "./config.schema.json",
  "bot": {
    "name": "Custom Bot",
    "prefix": "/",
    "login_method": "QR",
    "phone_number": "",
    "owner_jid": "owner@s.whatsapp.net",
    "auto_read": false,
    "auto_reload": true,
    "auto_react": false,
    "auto_react_emoji": "",
    "ignore_self_messages": true,
    "self_mode": false
  },
  "features": {
    "anti_delete": true,
    "anti_link": true,
    "welcome": true,
    "notes": false,
    "filters": true,
    "blacklist": true,
    "warnings": true,
    "automation_rules": true
  }
}
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(runtime_config_module, "CONFIG_FILE", config_path)
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

    # Existing user values are preserved
    assert cfg.get_nested("bot", "name") == "Custom Bot"
    assert cfg.get_nested("features", "notes") is False

    # Newly added keys are merged and persisted
    assert cfg.get_nested("features", "anti_spam") is False
    persisted = runtime_config_module.jsonc.load(config_path)
    assert persisted.get("features", {}).get("anti_spam") is False

    runtime_config_module.RuntimeConfig._instance = None
