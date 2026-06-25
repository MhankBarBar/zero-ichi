"""Shared database layer for runtime persistence.

Provides:
- SQLite default storage (`data/zeroichi.db`)
- Optional PostgreSQL via `DATABASE_URL`
- Generic key/value JSON store APIs
- Webhook and webhook delivery persistence
- One-time migration from legacy JSON files
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from core.constants import DATA_DIR, LOCALES_DIR, MEMORY_DIR, TASKS_FILE

_DEFAULT_DB_PATH = DATA_DIR / "zeroichi.db"
_MIGRATION_FLAG_KEY = "legacy_json_migration_v1_done"

_engine: Engine | None = None
_init_lock = threading.Lock()
_ready = False


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def _normalize_database_url(url: str) -> str:
    """Normalize env database URL for SQLAlchemy dialect handling."""
    normalized = url.strip()
    if normalized.startswith("postgres://"):
        return "postgresql+psycopg://" + normalized[len("postgres://") :]
    if normalized.startswith("postgresql://") and "+" not in normalized.split("://", 1)[0]:
        return "postgresql+psycopg://" + normalized[len("postgresql://") :]
    return normalized


def get_database_url() -> str:
    """Resolve database URL from environment with SQLite fallback."""
    env_url = os.getenv("DATABASE_URL", "").strip()
    if env_url:
        return _normalize_database_url(env_url)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{_DEFAULT_DB_PATH.as_posix()}"


def get_engine() -> Engine:
    """Get shared SQLAlchemy engine."""
    global _engine
    if _engine is not None:
        return _engine

    database_url = get_database_url()
    kwargs: dict[str, Any] = {"future": True, "pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}

    _engine = create_engine(database_url, **kwargs)
    return _engine


_SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _ensure_column(engine: Engine, table_name: str, column_name: str, column_sql: str) -> None:
    """Add a column if it does not exist. Table/column names are validated."""
    if not _SAFE_IDENTIFIER.match(table_name):
        raise ValueError(f"Invalid table name: {table_name}")
    if not _SAFE_IDENTIFIER.match(column_name):
        raise ValueError(f"Invalid column name: {column_name}")

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if table_name not in table_names:
        return

    existing = {col["name"] for col in inspector.get_columns(table_name)}
    if column_name in existing:
        return

    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}"))


def _ensure_tables(engine: Engine) -> None:
    """Create required runtime tables if they do not exist."""
    dialect = engine.dialect.name
    id_column = (
        "BIGSERIAL PRIMARY KEY" if dialect == "postgresql" else "INTEGER PRIMARY KEY AUTOINCREMENT"
    )
    webhook_fk_type = "BIGINT" if dialect == "postgresql" else "INTEGER"

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS kv_store (
                    scope TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (scope, key)
                )
                """
            )
        )

        conn.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS webhooks (
                    id {id_column},
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    events TEXT NOT NULL,
                    secret TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    failure_count INTEGER NOT NULL DEFAULT 0,
                    max_failures INTEGER NOT NULL DEFAULT 10,
                    last_success_at TEXT,
                    last_error TEXT,
                    disabled_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
        )

        conn.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS webhook_deliveries (
                    id {id_column},
                    webhook_id {webhook_fk_type} NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    status_code INTEGER,
                    error TEXT,
                    attempt INTEGER NOT NULL,
                    response_body TEXT,
                    request_headers TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(webhook_id) REFERENCES webhooks(id) ON DELETE CASCADE
                )
                """
            )
        )

        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_webhook ON webhook_deliveries(webhook_id, id DESC)"
            )
        )

        conn.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS incoming_webhook_keys (
                    id {id_column},
                    name TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    allowed_actions TEXT NOT NULL,
                    rate_limit_per_minute INTEGER NOT NULL DEFAULT 30,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_used_at TEXT
                )
                """
            )
        )

        conn.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id {id_column},
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
        )

        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(id DESC)")
        )

    _ensure_column(engine, "webhooks", "failure_count", "failure_count INTEGER NOT NULL DEFAULT 0")
    _ensure_column(engine, "webhooks", "max_failures", "max_failures INTEGER NOT NULL DEFAULT 10")
    _ensure_column(engine, "webhooks", "last_success_at", "last_success_at TEXT")
    _ensure_column(engine, "webhooks", "last_error", "last_error TEXT")
    _ensure_column(engine, "webhooks", "disabled_reason", "disabled_reason TEXT")
    _ensure_column(engine, "webhook_deliveries", "request_headers", "request_headers TEXT")


def _safe_jid(jid: str) -> str:
    return jid.replace(":", "_").replace("@", "_")


def _guess_jid_from_safe(safe_jid: str) -> str | None:
    """Best-effort reverse mapping from legacy safe folder name to jid."""
    if "_" not in safe_jid:
        return None
    left, right = safe_jid.rsplit("_", 1)
    if not left or not right:
        return None
    return f"{left}@{right}"


def _read_json_file(file_path: Path, default: Any) -> Any:
    if not file_path.exists():
        return default
    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _kv_upsert(conn, scope: str, key: str, value: Any) -> None:
    payload = json.dumps(value, ensure_ascii=False)
    conn.execute(
        text(
            """
            INSERT INTO kv_store(scope, key, value, updated_at)
            VALUES (:scope, :key, :value, :updated_at)
            ON CONFLICT(scope, key)
            DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """
        ),
        {
            "scope": scope,
            "key": key,
            "value": payload,
            "updated_at": _utcnow_iso(),
        },
    )


def _kv_get(conn, scope: str, key: str) -> Any | None:
    row = conn.execute(
        text("SELECT value FROM kv_store WHERE scope = :scope AND key = :key"),
        {"scope": scope, "key": key},
    ).fetchone()
    if not row:
        return None
    try:
        return json.loads(str(row[0]))
    except Exception:
        return None


def _migrate_legacy_json(engine: Engine) -> None:
    """One-time migration from legacy JSON files into database storage."""
    with engine.begin() as conn:
        migrated = _kv_get(conn, "meta", _MIGRATION_FLAG_KEY)
        if migrated:
            return

        stats = _read_json_file(DATA_DIR / "stats.json", {})
        groups = _read_json_file(DATA_DIR / "groups.json", {})
        scheduler_state = _read_json_file(TASKS_FILE, {"tasks": [], "counter": 0})
        analytics = _read_json_file(DATA_DIR / "analytics.json", {})
        ai_tokens = _read_json_file(DATA_DIR / "ai_tokens.json", {})
        afk_state = _read_json_file(DATA_DIR / "afk.json", {})

        chat_languages = _read_json_file(DATA_DIR / "chat_languages.json", {})
        if not chat_languages:
            chat_languages = _read_json_file(
                LOCALES_DIR.parent / "data" / "chat_languages.json", {}
            )

        if isinstance(stats, dict) and stats:
            _kv_upsert(conn, "global", "stats", stats)
        if isinstance(groups, dict) and groups:
            _kv_upsert(conn, "global", "groups", groups)
        if isinstance(scheduler_state, dict) and scheduler_state:
            _kv_upsert(conn, "scheduler", "state", scheduler_state)
        if isinstance(analytics, dict) and analytics:
            _kv_upsert(conn, "analytics", "payload", analytics)
        if isinstance(ai_tokens, dict) and ai_tokens:
            _kv_upsert(conn, "ai_tokens", "daily", ai_tokens)
        if isinstance(afk_state, dict) and afk_state:
            _kv_upsert(conn, "afk", "state", afk_state)
        if isinstance(chat_languages, dict) and chat_languages:
            _kv_upsert(conn, "i18n", "chat_languages", chat_languages)

        group_map: dict[str, str] = {}
        if isinstance(groups, dict):
            for group_jid in groups.keys():
                if isinstance(group_jid, str) and group_jid:
                    group_map[_safe_jid(group_jid)] = group_jid

        group_keys = [
            "settings",
            "notes",
            "filters",
            "blacklist",
            "warnings",
            "welcome",
            "goodbye",
            "anti_link",
            "warnings_config",
            "reports",
            "digest",
            "automations",
            "muted",
            "mute",
        ]

        if DATA_DIR.exists():
            for entry in DATA_DIR.iterdir():
                if not entry.is_dir():
                    continue
                group_jid = group_map.get(entry.name)
                if not group_jid:
                    group_jid = _guess_jid_from_safe(entry.name)
                if not group_jid:
                    continue

                scope = f"group:{group_jid}"
                for key in group_keys:
                    payload = _read_json_file(entry / f"{key}.json", None)
                    if payload is not None:
                        _kv_upsert(conn, scope, key, payload)

        if MEMORY_DIR.exists():
            for file_path in MEMORY_DIR.glob("*.json"):
                payload = _read_json_file(file_path, None)
                if payload is None:
                    continue
                _kv_upsert(conn, "ai_memory", file_path.stem, payload)

        _kv_upsert(conn, "meta", _MIGRATION_FLAG_KEY, True)
        _kv_upsert(conn, "meta", "legacy_json_migration_v1_at", _utcnow_iso())


def ensure_database_ready() -> None:
    """Initialize database tables and run one-time migration."""
    global _ready
    if _ready:
        return

    with _init_lock:
        if _ready:
            return

        engine = get_engine()
        _ensure_tables(engine)
        _migrate_legacy_json(engine)
        _ready = True


def kv_get_json(scope: str, key: str, default: Any = None) -> Any:
    """Read JSON value from key-value storage."""
    ensure_database_ready()
    with get_engine().begin() as conn:
        value = _kv_get(conn, scope, key)
        if value is None:
            return default
        return value


def kv_set_json(scope: str, key: str, value: Any) -> None:
    """Write JSON value to key-value storage."""
    ensure_database_ready()
    with get_engine().begin() as conn:
        _kv_upsert(conn, scope, key, value)


def kv_delete(scope: str, key: str) -> None:
    """Delete one key from key-value storage."""
    ensure_database_ready()
    with get_engine().begin() as conn:
        conn.execute(
            text("DELETE FROM kv_store WHERE scope = :scope AND key = :key"),
            {"scope": scope, "key": key},
        )


def kv_list_scopes(prefix: str = "") -> list[str]:
    """List scopes from key-value store, optionally filtered by prefix."""
    ensure_database_ready()
    with get_engine().begin() as conn:
        if prefix:
            rows = conn.execute(
                text(
                    "SELECT DISTINCT scope FROM kv_store WHERE scope LIKE :prefix ORDER BY scope ASC"
                ),
                {"prefix": f"{prefix}%"},
            ).fetchall()
        else:
            rows = conn.execute(
                text("SELECT DISTINCT scope FROM kv_store ORDER BY scope ASC")
            ).fetchall()
    return [str(row[0]) for row in rows]


def kv_get_scope_keys(scope: str) -> list[str]:
    """List keys for a scope."""
    ensure_database_ready()
    with get_engine().begin() as conn:
        rows = conn.execute(
            text("SELECT key FROM kv_store WHERE scope = :scope ORDER BY key ASC"),
            {"scope": scope},
        ).fetchall()
    return [str(row[0]) for row in rows]


def create_pending_item(
    key: str,
    *,
    kind: str,
    payload: Any,
    expires_at: float,
    chat_jid: str = "",
    sender_jid: str = "",
) -> None:
    """Persist one pending interaction payload."""
    kv_set_json(
        "pending_items",
        key,
        {
            "key": key,
            "kind": str(kind),
            "payload": payload,
            "expires_at": float(expires_at),
            "chat_jid": str(chat_jid),
            "sender_jid": str(sender_jid),
            "created_at": time.time(),
        },
    )


def get_pending_item(key: str) -> dict[str, Any] | None:
    """Read one pending interaction payload by key."""
    row = kv_get_json("pending_items", key, default=None)
    if not isinstance(row, dict):
        return None
    return row


def delete_pending_item(key: str) -> None:
    """Delete one pending interaction payload."""
    kv_delete("pending_items", key)


def delete_expired_pending_items(now_ts: float) -> int:
    """Delete expired pending interaction payloads and return removed count."""
    removed = 0
    for key in kv_get_scope_keys("pending_items"):
        item = get_pending_item(key)
        if not isinstance(item, dict):
            continue
        try:
            expires_at = float(item.get("expires_at", 0.0))
        except (TypeError, ValueError):
            expires_at = 0.0
        if expires_at <= float(now_ts):
            delete_pending_item(key)
            removed += 1
    return removed


def _normalize_webhook_events(events: list[str]) -> list[str]:
    cleaned = [str(event).strip() for event in events if str(event).strip()]
    deduped: list[str] = []
    for event in cleaned:
        if event not in deduped:
            deduped.append(event)
    return deduped


def list_webhooks(include_disabled: bool = True) -> list[dict[str, Any]]:
    """List configured webhooks."""
    ensure_database_ready()
    query = (
        "SELECT id, name, url, events, secret, enabled, failure_count, max_failures, "
        "last_success_at, last_error, disabled_reason, created_at, updated_at FROM webhooks"
        if include_disabled
        else "SELECT id, name, url, events, secret, enabled, failure_count, max_failures, "
        "last_success_at, last_error, disabled_reason, created_at, updated_at FROM webhooks WHERE enabled = 1"
    )
    query += " ORDER BY id DESC"

    with get_engine().begin() as conn:
        rows = conn.execute(text(query)).fetchall()

    hooks: list[dict[str, Any]] = []
    for row in rows:
        try:
            events = json.loads(str(row[3]))
        except Exception:
            events = []

        hooks.append(
            {
                "id": int(row[0]),
                "name": str(row[1]),
                "url": str(row[2]),
                "events": events if isinstance(events, list) else [],
                "secret": str(row[4]),
                "enabled": bool(row[5]),
                "failure_count": int(row[6]) if row[6] is not None else 0,
                "max_failures": int(row[7]) if row[7] is not None else 10,
                "last_success_at": str(row[8]) if row[8] is not None else None,
                "last_error": str(row[9]) if row[9] is not None else None,
                "disabled_reason": str(row[10]) if row[10] is not None else None,
                "created_at": str(row[11]),
                "updated_at": str(row[12]),
            }
        )
    return hooks


def get_webhook(webhook_id: int) -> dict[str, Any] | None:
    """Get one webhook by id."""
    for hook in list_webhooks(include_disabled=True):
        if int(hook["id"]) == int(webhook_id):
            return hook
    return None


def create_webhook(
    *,
    name: str,
    url: str,
    events: list[str],
    secret: str,
    enabled: bool,
    max_failures: int = 10,
) -> dict[str, Any]:
    """Create a webhook and return persisted object."""
    ensure_database_ready()
    now = _utcnow_iso()
    normalized_events = _normalize_webhook_events(events)

    with get_engine().begin() as conn:
        params = {
            "name": name.strip() or "Webhook",
            "url": url.strip(),
            "events": json.dumps(normalized_events, ensure_ascii=False),
            "secret": secret,
            "enabled": 1 if enabled else 0,
            "max_failures": max(1, int(max_failures)),
            "created_at": now,
            "updated_at": now,
        }

        if get_engine().dialect.name == "postgresql":
            result = conn.execute(
                text(
                    """
                    INSERT INTO webhooks(
                        name, url, events, secret, enabled, max_failures, created_at, updated_at
                    )
                    VALUES (
                        :name, :url, :events, :secret, :enabled, :max_failures, :created_at, :updated_at
                    )
                    RETURNING id
                    """
                ),
                params,
            )
            webhook_id = int(result.scalar_one())
        else:
            result = conn.execute(
                text(
                    """
                    INSERT INTO webhooks(
                        name, url, events, secret, enabled, max_failures, created_at, updated_at
                    )
                    VALUES (
                        :name, :url, :events, :secret, :enabled, :max_failures, :created_at, :updated_at
                    )
                    """
                ),
                params,
            )
            webhook_id = int(result.lastrowid)

    hook = get_webhook(webhook_id)
    if hook is None:
        raise RuntimeError("Failed to create webhook")
    return hook


def update_webhook(
    webhook_id: int,
    *,
    name: str | None = None,
    url: str | None = None,
    events: list[str] | None = None,
    secret: str | None = None,
    enabled: bool | None = None,
    max_failures: int | None = None,
) -> dict[str, Any] | None:
    """Update webhook fields and return updated object."""
    existing = get_webhook(webhook_id)
    if not existing:
        return None

    updates: dict[str, Any] = {
        "name": existing["name"],
        "url": existing["url"],
        "events": existing["events"],
        "secret": existing["secret"],
        "enabled": existing["enabled"],
        "max_failures": existing.get("max_failures", 10),
    }

    if name is not None:
        updates["name"] = name.strip() or "Webhook"
    if url is not None:
        updates["url"] = url.strip()
    if events is not None:
        updates["events"] = _normalize_webhook_events(events)
    if secret is not None:
        updates["secret"] = secret
    if enabled is not None:
        updates["enabled"] = bool(enabled)
    if max_failures is not None:
        updates["max_failures"] = max(1, int(max_failures))

    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE webhooks
                SET name = :name,
                    url = :url,
                    events = :events,
                    secret = :secret,
                    enabled = :enabled,
                    max_failures = :max_failures,
                    updated_at = :updated_at
                WHERE id = :id
                """
            ),
            {
                "id": int(webhook_id),
                "name": updates["name"],
                "url": updates["url"],
                "events": json.dumps(updates["events"], ensure_ascii=False),
                "secret": updates["secret"],
                "enabled": 1 if updates["enabled"] else 0,
                "max_failures": int(updates["max_failures"]),
                "updated_at": _utcnow_iso(),
            },
        )

    return get_webhook(webhook_id)


def delete_webhook(webhook_id: int) -> bool:
    """Delete webhook and associated deliveries."""
    ensure_database_ready()
    with get_engine().begin() as conn:
        conn.execute(
            text("DELETE FROM webhook_deliveries WHERE webhook_id = :id"),
            {"id": int(webhook_id)},
        )
        result = conn.execute(
            text("DELETE FROM webhooks WHERE id = :id"),
            {"id": int(webhook_id)},
        )
    return result.rowcount > 0


def get_active_webhooks_for_event(event_type: str) -> list[dict[str, Any]]:
    """Return enabled webhooks that subscribe to the given event."""
    active = list_webhooks(include_disabled=False)
    matched: list[dict[str, Any]] = []
    for hook in active:
        events = hook.get("events", [])
        if not isinstance(events, list):
            continue
        if "*" in events or event_type in events:
            matched.append(hook)
    return matched


def record_webhook_delivery(
    *,
    webhook_id: int,
    event_type: str,
    payload: dict[str, Any],
    success: bool,
    attempt: int,
    status_code: int | None = None,
    error: str | None = None,
    response_body: str | None = None,
    request_headers: dict[str, str] | None = None,
) -> int:
    """Persist webhook delivery attempt."""
    ensure_database_ready()
    params = {
        "webhook_id": int(webhook_id),
        "event_type": event_type,
        "payload": json.dumps(payload, ensure_ascii=False),
        "success": 1 if success else 0,
        "status_code": status_code,
        "error": (error or "")[:1000] or None,
        "attempt": int(attempt),
        "response_body": (response_body or "")[:2000] or None,
        "request_headers": (
            json.dumps(request_headers, ensure_ascii=False)
            if isinstance(request_headers, dict)
            else None
        ),
        "created_at": _utcnow_iso(),
    }

    if get_engine().dialect.name == "postgresql":
        with get_engine().begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO webhook_deliveries(
                        webhook_id, event_type, payload, success, status_code,
                        error, attempt, response_body, request_headers, created_at
                    )
                    VALUES (
                        :webhook_id, :event_type, :payload, :success, :status_code,
                        :error, :attempt, :response_body, :request_headers, :created_at
                    )
                    RETURNING id
                    """
                ),
                params,
            )
            return int(result.scalar_one())

    with get_engine().begin() as conn:
        result = conn.execute(
            text(
                """
                INSERT INTO webhook_deliveries(
                    webhook_id, event_type, payload, success, status_code,
                    error, attempt, response_body, request_headers, created_at
                )
                VALUES (
                    :webhook_id, :event_type, :payload, :success, :status_code,
                    :error, :attempt, :response_body, :request_headers, :created_at
                )
                """
            ),
            params,
        )
    return int(result.lastrowid) if result.lastrowid is not None else 0


def list_webhook_deliveries(webhook_id: int, limit: int = 50) -> list[dict[str, Any]]:
    """List recent webhook delivery attempts."""
    ensure_database_ready()
    with get_engine().begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, webhook_id, event_type, payload, success, status_code,
                       error, attempt, response_body, request_headers, created_at
                FROM webhook_deliveries
                WHERE webhook_id = :webhook_id
                ORDER BY id DESC
                LIMIT :limit
                """
            ),
            {"webhook_id": int(webhook_id), "limit": int(limit)},
        ).fetchall()

    deliveries: list[dict[str, Any]] = []
    for row in rows:
        try:
            payload = json.loads(str(row[3]))
        except Exception:
            payload = {}

        deliveries.append(
            {
                "id": int(row[0]),
                "webhook_id": int(row[1]),
                "event_type": str(row[2]),
                "payload": payload,
                "success": bool(row[4]),
                "status_code": int(row[5]) if row[5] is not None else None,
                "error": str(row[6]) if row[6] is not None else None,
                "attempt": int(row[7]),
                "response_body": str(row[8]) if row[8] is not None else None,
                "request_headers": (
                    json.loads(str(row[9])) if row[9] is not None and str(row[9]).strip() else {}
                ),
                "created_at": str(row[10]),
            }
        )
    return deliveries


def get_webhook_delivery(webhook_id: int, delivery_id: int) -> dict[str, Any] | None:
    """Get one webhook delivery row by id."""
    ensure_database_ready()
    with get_engine().begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, webhook_id, event_type, payload, success, status_code,
                       error, attempt, response_body, request_headers, created_at
                FROM webhook_deliveries
                WHERE webhook_id = :webhook_id AND id = :delivery_id
                """
            ),
            {"webhook_id": int(webhook_id), "delivery_id": int(delivery_id)},
        ).fetchone()

    if not row:
        return None

    try:
        payload = json.loads(str(row[3]))
    except Exception:
        payload = {}

    try:
        request_headers = json.loads(str(row[9])) if row[9] is not None else {}
    except Exception:
        request_headers = {}

    return {
        "id": int(row[0]),
        "webhook_id": int(row[1]),
        "event_type": str(row[2]),
        "payload": payload,
        "success": bool(row[4]),
        "status_code": int(row[5]) if row[5] is not None else None,
        "error": str(row[6]) if row[6] is not None else None,
        "attempt": int(row[7]),
        "response_body": str(row[8]) if row[8] is not None else None,
        "request_headers": request_headers if isinstance(request_headers, dict) else {},
        "created_at": str(row[10]),
    }


def mark_webhook_delivery_result(webhook_id: int, success: bool, error: str | None = None) -> None:
    """Update webhook health status after a delivery cycle."""
    ensure_database_ready()
    webhook = get_webhook(webhook_id)
    if not webhook:
        return

    failure_count = int(webhook.get("failure_count", 0) or 0)
    max_failures = max(1, int(webhook.get("max_failures", 10) or 10))

    with get_engine().begin() as conn:
        if success:
            conn.execute(
                text(
                    """
                    UPDATE webhooks
                    SET failure_count = 0,
                        last_success_at = :last_success_at,
                        last_error = NULL,
                        disabled_reason = NULL,
                        enabled = 1,
                        updated_at = :updated_at
                    WHERE id = :id
                    """
                ),
                {
                    "id": int(webhook_id),
                    "last_success_at": _utcnow_iso(),
                    "updated_at": _utcnow_iso(),
                },
            )
            return

        next_count = failure_count + 1
        should_disable = next_count >= max_failures
        conn.execute(
            text(
                """
                UPDATE webhooks
                SET failure_count = :failure_count,
                    last_error = :last_error,
                    disabled_reason = :disabled_reason,
                    enabled = :enabled,
                    updated_at = :updated_at
                WHERE id = :id
                """
            ),
            {
                "id": int(webhook_id),
                "failure_count": next_count,
                "last_error": (error or "delivery_failed")[:1000],
                "disabled_reason": (
                    f"auto_disabled_after_{next_count}_failures" if should_disable else None
                ),
                "enabled": 0 if should_disable else 1,
                "updated_at": _utcnow_iso(),
            },
        )


def rotate_webhook_secret(webhook_id: int) -> str | None:
    """Rotate webhook secret and return new value."""
    ensure_database_ready()
    hook = get_webhook(webhook_id)
    if not hook:
        return None

    secret = secrets.token_urlsafe(24)
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE webhooks
                SET secret = :secret, updated_at = :updated_at
                WHERE id = :id
                """
            ),
            {"id": int(webhook_id), "secret": secret, "updated_at": _utcnow_iso()},
        )
    return secret


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_incoming_webhook_key(
    *,
    name: str,
    allowed_actions: list[str],
    rate_limit_per_minute: int = 30,
    enabled: bool = True,
) -> dict[str, Any]:
    """Create incoming webhook key. Returns metadata + plain token once."""
    ensure_database_ready()
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    now = _utcnow_iso()
    allowed = [str(v).strip() for v in allowed_actions if str(v).strip()]
    if not allowed:
        allowed = ["send_message"]

    params = {
        "name": name.strip() or "Incoming Key",
        "token_hash": token_hash,
        "allowed_actions": json.dumps(allowed, ensure_ascii=False),
        "rate_limit_per_minute": max(1, int(rate_limit_per_minute)),
        "enabled": 1 if enabled else 0,
        "created_at": now,
        "updated_at": now,
    }

    if get_engine().dialect.name == "postgresql":
        with get_engine().begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO incoming_webhook_keys(
                        name, token_hash, allowed_actions, rate_limit_per_minute,
                        enabled, created_at, updated_at
                    )
                    VALUES(
                        :name, :token_hash, :allowed_actions, :rate_limit_per_minute,
                        :enabled, :created_at, :updated_at
                    )
                    RETURNING id
                    """
                ),
                params,
            )
            key_id = int(result.scalar_one())
    else:
        with get_engine().begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO incoming_webhook_keys(
                        name, token_hash, allowed_actions, rate_limit_per_minute,
                        enabled, created_at, updated_at
                    )
                    VALUES(
                        :name, :token_hash, :allowed_actions, :rate_limit_per_minute,
                        :enabled, :created_at, :updated_at
                    )
                    """
                ),
                params,
            )
            key_id = int(result.lastrowid) if result.lastrowid is not None else 0
    return {
        "id": key_id,
        "name": name.strip() or "Incoming Key",
        "allowed_actions": allowed,
        "rate_limit_per_minute": max(1, int(rate_limit_per_minute)),
        "enabled": bool(enabled),
        "created_at": now,
        "updated_at": now,
        "last_used_at": None,
        "token": token,
    }


def list_incoming_webhook_keys() -> list[dict[str, Any]]:
    """List incoming webhook key metadata (without token)."""
    ensure_database_ready()
    with get_engine().begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, name, allowed_actions, rate_limit_per_minute, enabled,
                       created_at, updated_at, last_used_at
                FROM incoming_webhook_keys
                ORDER BY id DESC
                """
            )
        ).fetchall()

    keys: list[dict[str, Any]] = []
    for row in rows:
        try:
            actions = json.loads(str(row[2]))
        except Exception:
            actions = []
        keys.append(
            {
                "id": int(row[0]),
                "name": str(row[1]),
                "allowed_actions": actions if isinstance(actions, list) else [],
                "rate_limit_per_minute": int(row[3]),
                "enabled": bool(row[4]),
                "created_at": str(row[5]),
                "updated_at": str(row[6]),
                "last_used_at": str(row[7]) if row[7] is not None else None,
            }
        )
    return keys


def update_incoming_webhook_key(
    key_id: int,
    *,
    name: str | None = None,
    allowed_actions: list[str] | None = None,
    rate_limit_per_minute: int | None = None,
    enabled: bool | None = None,
) -> dict[str, Any] | None:
    """Update incoming webhook key metadata."""
    existing = None
    for row in list_incoming_webhook_keys():
        if int(row["id"]) == int(key_id):
            existing = row
            break
    if not existing:
        return None

    next_name = name.strip() if isinstance(name, str) and name.strip() else existing["name"]
    next_actions = (
        [str(v).strip() for v in allowed_actions if str(v).strip()]
        if allowed_actions is not None
        else existing["allowed_actions"]
    )
    if not next_actions:
        next_actions = ["send_message"]
    next_rate = (
        max(1, int(rate_limit_per_minute))
        if rate_limit_per_minute is not None
        else int(existing["rate_limit_per_minute"])
    )
    next_enabled = bool(enabled) if enabled is not None else bool(existing["enabled"])

    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE incoming_webhook_keys
                SET name = :name,
                    allowed_actions = :allowed_actions,
                    rate_limit_per_minute = :rate,
                    enabled = :enabled,
                    updated_at = :updated_at
                WHERE id = :id
                """
            ),
            {
                "id": int(key_id),
                "name": next_name,
                "allowed_actions": json.dumps(next_actions, ensure_ascii=False),
                "rate": next_rate,
                "enabled": 1 if next_enabled else 0,
                "updated_at": _utcnow_iso(),
            },
        )

    for row in list_incoming_webhook_keys():
        if int(row["id"]) == int(key_id):
            return row
    return None


def rotate_incoming_webhook_key(key_id: int) -> str | None:
    """Rotate incoming webhook key token and return new token."""
    ensure_database_ready()
    exists = any(int(row["id"]) == int(key_id) for row in list_incoming_webhook_keys())
    if not exists:
        return None

    token = secrets.token_urlsafe(32)
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE incoming_webhook_keys
                SET token_hash = :token_hash,
                    updated_at = :updated_at
                WHERE id = :id
                """
            ),
            {
                "id": int(key_id),
                "token_hash": _hash_token(token),
                "updated_at": _utcnow_iso(),
            },
        )
    return token


def delete_incoming_webhook_key(key_id: int) -> bool:
    """Delete incoming webhook key."""
    ensure_database_ready()
    with get_engine().begin() as conn:
        result = conn.execute(
            text("DELETE FROM incoming_webhook_keys WHERE id = :id"),
            {"id": int(key_id)},
        )
    return result.rowcount > 0


def resolve_incoming_webhook_key(token: str) -> dict[str, Any] | None:
    """Resolve and return key metadata by plain token."""
    ensure_database_ready()
    token_hash = _hash_token(token)
    with get_engine().begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, name, allowed_actions, rate_limit_per_minute, enabled,
                       created_at, updated_at, last_used_at
                FROM incoming_webhook_keys
                WHERE token_hash = :token_hash
                """
            ),
            {"token_hash": token_hash},
        ).fetchone()

    if not row:
        return None

    try:
        actions = json.loads(str(row[2]))
    except Exception:
        actions = []

    return {
        "id": int(row[0]),
        "name": str(row[1]),
        "allowed_actions": actions if isinstance(actions, list) else [],
        "rate_limit_per_minute": int(row[3]),
        "enabled": bool(row[4]),
        "created_at": str(row[5]),
        "updated_at": str(row[6]),
        "last_used_at": str(row[7]) if row[7] is not None else None,
    }


def touch_incoming_webhook_key(key_id: int) -> None:
    """Update last_used_at for incoming webhook key."""
    ensure_database_ready()
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE incoming_webhook_keys
                SET last_used_at = :last_used_at,
                    updated_at = :updated_at
                WHERE id = :id
                """
            ),
            {
                "id": int(key_id),
                "last_used_at": _utcnow_iso(),
                "updated_at": _utcnow_iso(),
            },
        )


def claim_incoming_idempotency(
    key_id: int, idempotency_key: str, ttl_seconds: int = 86_400
) -> bool:
    """Atomically claim idempotency key usage for incoming webhooks.

    Returns True when key is first-seen within TTL window.
    Returns False when key was already claimed.
    """
    ensure_database_ready()

    raw = str(idempotency_key).strip()
    if not raw:
        return False

    now = time.time()
    cutoff = now - max(60, int(ttl_seconds))
    key_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    scope = f"incoming_idem:{int(key_id)}"

    with get_engine().begin() as conn:
        rows = conn.execute(
            text("SELECT key, value FROM kv_store WHERE scope = :scope"),
            {"scope": scope},
        ).fetchall()

        stale_keys: list[str] = []
        for row in rows:
            try:
                parsed = json.loads(str(row[1]))
                ts = float(parsed.get("ts", 0.0)) if isinstance(parsed, dict) else 0.0
            except Exception:
                ts = 0.0
            if ts < cutoff:
                stale_keys.append(str(row[0]))

        if stale_keys:
            for stale_key in stale_keys:
                conn.execute(
                    text("DELETE FROM kv_store WHERE scope = :scope AND key = :key"),
                    {"scope": scope, "key": stale_key},
                )

        try:
            conn.execute(
                text(
                    """
                    INSERT INTO kv_store(scope, key, value, updated_at)
                    VALUES (:scope, :key, :value, :updated_at)
                    """
                ),
                {
                    "scope": scope,
                    "key": key_hash,
                    "value": json.dumps({"ts": now}),
                    "updated_at": _utcnow_iso(),
                },
            )
            return True
        except IntegrityError:
            return False


def add_audit_log(
    *, actor: str, action: str, resource: str, details: dict[str, Any] | None = None
) -> None:
    """Persist audit log entry."""
    ensure_database_ready()
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO audit_logs(actor, action, resource, details, created_at)
                VALUES (:actor, :action, :resource, :details, :created_at)
                """
            ),
            {
                "actor": actor.strip() or "system",
                "action": action.strip() or "unknown",
                "resource": resource.strip() or "unknown",
                "details": json.dumps(details or {}, ensure_ascii=False),
                "created_at": _utcnow_iso(),
            },
        )


def list_audit_logs(limit: int = 100, action: str = "") -> list[dict[str, Any]]:
    """List recent audit logs."""
    ensure_database_ready()
    params: dict[str, Any] = {"limit": int(limit)}
    where = ""
    if action.strip():
        where = "WHERE action = :action"
        params["action"] = action.strip()

    with get_engine().begin() as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT id, actor, action, resource, details, created_at
                FROM audit_logs
                {where}
                ORDER BY id DESC
                LIMIT :limit
                """
            ),
            params,
        ).fetchall()

    out: list[dict[str, Any]] = []
    for row in rows:
        try:
            details = json.loads(str(row[4]))
        except Exception:
            details = {}
        out.append(
            {
                "id": int(row[0]),
                "actor": str(row[1]),
                "action": str(row[2]),
                "resource": str(row[3]),
                "details": details if isinstance(details, dict) else {},
                "created_at": str(row[5]),
            }
        )
    return out
