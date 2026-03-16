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


def test_webhook_auto_disable_after_failures(tmp_path, monkeypatch):
    _reset_db(tmp_path, monkeypatch)

    hook = db_module.create_webhook(
        name="Auto Disable",
        url="https://example.com/hook",
        events=["*"],
        secret="abc",
        enabled=True,
        max_failures=2,
    )

    db_module.mark_webhook_delivery_result(hook["id"], success=False, error="timeout")
    first = db_module.get_webhook(hook["id"])
    assert first is not None
    assert first["enabled"] is True
    assert first["failure_count"] == 1

    db_module.mark_webhook_delivery_result(hook["id"], success=False, error="timeout")
    second = db_module.get_webhook(hook["id"])
    assert second is not None
    assert second["enabled"] is False
    assert second["failure_count"] == 2
    assert second["disabled_reason"] is not None


def test_incoming_webhook_key_crud(tmp_path, monkeypatch):
    _reset_db(tmp_path, monkeypatch)

    created = db_module.create_incoming_webhook_key(
        name="CI Trigger",
        allowed_actions=["send_message", "emit_event"],
        rate_limit_per_minute=25,
        enabled=True,
    )

    assert created["id"] > 0
    assert created["token"]

    resolved = db_module.resolve_incoming_webhook_key(created["token"])
    assert resolved is not None
    assert resolved["name"] == "CI Trigger"
    assert resolved["rate_limit_per_minute"] == 25

    rotated = db_module.rotate_incoming_webhook_key(created["id"])
    assert rotated
    assert db_module.resolve_incoming_webhook_key(created["token"]) is None
    assert db_module.resolve_incoming_webhook_key(rotated) is not None

    assert db_module.delete_incoming_webhook_key(created["id"])


def test_claim_incoming_idempotency(tmp_path, monkeypatch):
    _reset_db(tmp_path, monkeypatch)

    key = db_module.create_incoming_webhook_key(
        name="CI Trigger",
        allowed_actions=["emit_event"],
        rate_limit_per_minute=10,
        enabled=True,
    )
    resolved = db_module.resolve_incoming_webhook_key(key["token"])
    assert resolved is not None

    first = db_module.claim_incoming_idempotency(int(resolved["id"]), "abc-123")
    second = db_module.claim_incoming_idempotency(int(resolved["id"]), "abc-123")

    assert first is True
    assert second is False
