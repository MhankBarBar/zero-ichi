"""
PostgreSQL integration tests — run against a live PostgreSQL database.

These tests exercise all db.py operations against a real PostgreSQL instance
to verify dialect-specific branching (BIGSERIAL, RETURNING, etc.) works.

Requires DATABASE_URL env var pointing to a PostgreSQL database.
Skipped automatically if DATABASE_URL is not set or not postgresql.
"""

import os

import pytest
from dotenv import load_dotenv

load_dotenv()

import core.db as db_module  # noqa: E402

PG_URL = os.getenv("DATABASE_URL", "")
_is_pg = "postgresql" in PG_URL or "postgres" in PG_URL

pytestmark = pytest.mark.skipif(not _is_pg, reason="DATABASE_URL not set to PostgreSQL")


@pytest.fixture(autouse=True)
def _pg_engine():
    """Reset db module state and initialize against the real PostgreSQL."""
    db_module._engine = None
    db_module._ready = False
    db_module.ensure_database_ready()
    yield
    engine = db_module.get_engine()
    with engine.begin() as conn:
        from sqlalchemy import text

        conn.execute(text("DELETE FROM webhook_deliveries"))
        conn.execute(text("DELETE FROM webhooks"))
        conn.execute(text("DELETE FROM incoming_webhook_keys"))
        conn.execute(text("DELETE FROM kv_store WHERE scope LIKE 'test_%'"))
        conn.execute(text("DELETE FROM audit_logs"))


def test_pg_connection():
    """Verify we are actually connected to PostgreSQL."""
    engine = db_module.get_engine()
    assert engine.dialect.name == "postgresql"


def test_pg_kv_roundtrip():
    """KV store read/write on PostgreSQL."""
    payload = {"count": 42, "items": ["a", "b"]}
    db_module.kv_set_json("test_pg", "stats", payload)
    loaded = db_module.kv_get_json("test_pg", "stats", default={})
    assert loaded == payload

    db_module.kv_set_json("test_pg", "stats", {"count": 99})
    updated = db_module.kv_get_json("test_pg", "stats", default={})
    assert updated["count"] == 99

    db_module.kv_delete("test_pg", "stats")
    gone = db_module.kv_get_json("test_pg", "stats", default=None)
    assert gone is None


def test_pg_webhook_crud():
    """Webhook CRUD with BIGSERIAL id and RETURNING on PostgreSQL."""
    hook = db_module.create_webhook(
        name="PG Test",
        url="https://example.com/pg-hook",
        events=["command_executed", "message_received"],
        secret="pg_secret",
        enabled=True,
    )

    assert hook["id"] > 0
    assert hook["name"] == "PG Test"
    assert hook["enabled"] is True

    fetched = db_module.get_webhook(hook["id"])
    assert fetched is not None
    assert fetched["url"] == "https://example.com/pg-hook"

    updated = db_module.update_webhook(hook["id"], enabled=False)
    assert updated is not None
    assert updated["enabled"] is False

    matches = db_module.get_active_webhooks_for_event("command_executed")
    assert all(m["id"] != hook["id"] for m in matches)

    db_module.update_webhook(hook["id"], enabled=True)
    matches = db_module.get_active_webhooks_for_event("command_executed")
    assert any(m["id"] == hook["id"] for m in matches)

    assert db_module.delete_webhook(hook["id"])
    assert db_module.get_webhook(hook["id"]) is None


def test_pg_webhook_delivery_log():
    """Webhook delivery logging with BIGINT foreign key on PostgreSQL."""
    hook = db_module.create_webhook(
        name="Delivery Test",
        url="https://example.com/deliver",
        events=["*"],
        secret="s",
        enabled=True,
    )

    db_module.record_webhook_delivery(
        webhook_id=hook["id"],
        event_type="test_event",
        payload={"ok": True},
        success=True,
        attempt=1,
        status_code=200,
    )

    deliveries = db_module.list_webhook_deliveries(hook["id"], limit=10)
    assert len(deliveries) == 1
    assert deliveries[0]["success"] is True
    assert deliveries[0]["status_code"] == 200


def test_pg_webhook_auto_disable():
    """Auto-disable after max_failures on PostgreSQL."""
    hook = db_module.create_webhook(
        name="Auto Disable PG",
        url="https://example.com/fail",
        events=["*"],
        secret="s",
        enabled=True,
        max_failures=2,
    )

    db_module.mark_webhook_delivery_result(hook["id"], success=False, error="timeout")
    h1 = db_module.get_webhook(hook["id"])
    assert h1["enabled"] is True
    assert h1["failure_count"] == 1

    db_module.mark_webhook_delivery_result(hook["id"], success=False, error="timeout")
    h2 = db_module.get_webhook(hook["id"])
    assert h2["enabled"] is False
    assert h2["failure_count"] == 2
    assert h2["disabled_reason"] is not None


def test_pg_incoming_webhook_key_crud():
    """Incoming webhook key CRUD with RETURNING on PostgreSQL."""
    created = db_module.create_incoming_webhook_key(
        name="PG Incoming",
        allowed_actions=["send_message", "emit_event"],
        rate_limit_per_minute=30,
        enabled=True,
    )

    assert created["id"] > 0
    assert created["token"]

    resolved = db_module.resolve_incoming_webhook_key(created["token"])
    assert resolved is not None
    assert resolved["name"] == "PG Incoming"
    assert resolved["rate_limit_per_minute"] == 30

    new_token = db_module.rotate_incoming_webhook_key(created["id"])
    assert new_token
    assert db_module.resolve_incoming_webhook_key(created["token"]) is None
    assert db_module.resolve_incoming_webhook_key(new_token) is not None

    assert db_module.delete_incoming_webhook_key(created["id"])


def test_pg_idempotency():
    """Idempotency claim deduplication on PostgreSQL."""
    key = db_module.create_incoming_webhook_key(
        name="Idempotency PG",
        allowed_actions=["emit_event"],
        rate_limit_per_minute=10,
        enabled=True,
    )
    resolved = db_module.resolve_incoming_webhook_key(key["token"])
    assert resolved is not None

    first = db_module.claim_incoming_idempotency(int(resolved["id"]), "pg-dedup-123")
    second = db_module.claim_incoming_idempotency(int(resolved["id"]), "pg-dedup-123")

    assert first is True
    assert second is False

    third = db_module.claim_incoming_idempotency(int(resolved["id"]), "pg-dedup-456")
    assert third is True


def test_pg_audit_log():
    """Audit log write/read on PostgreSQL."""
    db_module.add_audit_log(
        action="test_action",
        actor="test_user@s.whatsapp.net",
        resource="test_resource",
        details={"note": "PG audit test"},
    )

    logs = db_module.list_audit_logs(limit=5)
    assert len(logs) >= 1
    latest = logs[0]
    assert latest["action"] == "test_action"
    assert latest["actor"] == "test_user@s.whatsapp.net"


def test_pg_secret_rotation():
    """Webhook secret rotation on PostgreSQL."""
    hook = db_module.create_webhook(
        name="Rotate PG",
        url="https://example.com/rotate",
        events=["*"],
        secret="old_secret",
        enabled=True,
    )

    new_secret = db_module.rotate_webhook_secret(hook["id"])
    assert new_secret
    assert new_secret != "old_secret"

    fetched = db_module.get_webhook(hook["id"])
    assert fetched["secret"] == new_secret
