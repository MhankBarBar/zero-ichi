from pathlib import Path

import core.db as db_module
from core.automations import (
    get_automation_runtime,
    rule_matches,
    set_automation_dry_run,
)


def _reset_db(tmp_path: Path, monkeypatch) -> None:
    db_file = tmp_path / "automations.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    db_module._engine = None
    db_module._ready = False
    db_module.ensure_database_ready()


def test_rule_matches_text_variants():
    assert rule_matches({"trigger_type": "contains", "trigger_value": "hello"}, "hello world")
    assert rule_matches({"trigger_type": "starts_with", "trigger_value": "!promo"}, "!promo now")
    assert rule_matches({"trigger_type": "exact_match", "trigger_value": "Hello"}, " hello ")
    assert rule_matches({"trigger_type": "regex", "trigger_value": r"free\s+money"}, "FREE money")
    assert rule_matches({"trigger_type": "link", "trigger_value": ""}, "visit https://example.com")

    assert not rule_matches(
        {"trigger_type": "starts_with", "trigger_value": "!promo"},
        "check !promo",
    )
    assert not rule_matches(
        {"trigger_type": "exact_match", "trigger_value": "hello"},
        "hello world",
    )


def test_rule_matches_media_type():
    assert rule_matches(
        {"trigger_type": "media_type", "trigger_value": "image"},
        "",
        media_type="image",
    )
    assert not rule_matches(
        {"trigger_type": "media_type", "trigger_value": "image"},
        "",
        media_type="video",
    )


def test_automation_dry_run_runtime_roundtrip(tmp_path, monkeypatch):
    _reset_db(tmp_path, monkeypatch)
    group = "12345@g.us"

    runtime = get_automation_runtime(group)
    assert runtime["dry_run"] is False

    set_automation_dry_run(group, True)
    runtime = get_automation_runtime(group)
    assert runtime["dry_run"] is True

    set_automation_dry_run(group, False)
    runtime = get_automation_runtime(group)
    assert runtime["dry_run"] is False
