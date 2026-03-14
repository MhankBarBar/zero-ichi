from pathlib import Path

import core.db as db_module


def _reset_db(tmp_path: Path, monkeypatch) -> None:
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    db_module._engine = None
    db_module._ready = False
    db_module.ensure_database_ready()


def test_kv_roundtrip(tmp_path, monkeypatch):
    _reset_db(tmp_path, monkeypatch)

    payload = {"count": 42, "items": ["a", "b"]}
    db_module.kv_set_json("global", "stats", payload)

    loaded = db_module.kv_get_json("global", "stats", default={})
    assert loaded == payload


def test_webhook_crud_and_delivery_log(tmp_path, monkeypatch):
    _reset_db(tmp_path, monkeypatch)

    hook = db_module.create_webhook(
        name="CI",
        url="https://example.com/hook",
        events=["command_executed"],
        secret="abc",
        enabled=True,
    )

    assert hook["name"] == "CI"
    assert hook["enabled"] is True

    matches = db_module.get_active_webhooks_for_event("command_executed")
    assert len(matches) == 1
    assert matches[0]["id"] == hook["id"]

    db_module.record_webhook_delivery(
        webhook_id=hook["id"],
        event_type="command_executed",
        payload={"ok": True},
        success=True,
        attempt=1,
        status_code=204,
    )

    deliveries = db_module.list_webhook_deliveries(hook["id"], limit=10)
    assert len(deliveries) == 1
    assert deliveries[0]["success"] is True
    assert deliveries[0]["status_code"] == 204

    assert db_module.delete_webhook(hook["id"])
    assert db_module.get_webhook(hook["id"]) is None
