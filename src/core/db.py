"""Shared database layer for runtime persistence.

Provides:
- SQLite default storage (`data/zeroichi.db`)
- Optional PostgreSQL via `DATABASE_URL`
- Generic key/value JSON store APIs
- Webhook and webhook delivery persistence
- One-time migration from legacy JSON files
"""

from __future__ import annotations

import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

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
        "SELECT id, name, url, events, secret, enabled, created_at, updated_at FROM webhooks"
        if include_disabled
        else "SELECT id, name, url, events, secret, enabled, created_at, updated_at FROM webhooks WHERE enabled = 1"
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
                "created_at": str(row[6]),
                "updated_at": str(row[7]),
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
            "created_at": now,
            "updated_at": now,
        }

        if get_engine().dialect.name == "postgresql":
            result = conn.execute(
                text(
                    """
                    INSERT INTO webhooks(name, url, events, secret, enabled, created_at, updated_at)
                    VALUES (:name, :url, :events, :secret, :enabled, :created_at, :updated_at)
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
                    INSERT INTO webhooks(name, url, events, secret, enabled, created_at, updated_at)
                    VALUES (:name, :url, :events, :secret, :enabled, :created_at, :updated_at)
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
) -> None:
    """Persist webhook delivery attempt."""
    ensure_database_ready()
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO webhook_deliveries(
                    webhook_id, event_type, payload, success, status_code,
                    error, attempt, response_body, created_at
                )
                VALUES (
                    :webhook_id, :event_type, :payload, :success, :status_code,
                    :error, :attempt, :response_body, :created_at
                )
                """
            ),
            {
                "webhook_id": int(webhook_id),
                "event_type": event_type,
                "payload": json.dumps(payload, ensure_ascii=False),
                "success": 1 if success else 0,
                "status_code": status_code,
                "error": (error or "")[:1000] or None,
                "attempt": int(attempt),
                "response_body": (response_body or "")[:2000] or None,
                "created_at": _utcnow_iso(),
            },
        )


def list_webhook_deliveries(webhook_id: int, limit: int = 50) -> list[dict[str, Any]]:
    """List recent webhook delivery attempts."""
    ensure_database_ready()
    with get_engine().begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, webhook_id, event_type, payload, success, status_code,
                       error, attempt, response_body, created_at
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
                "created_at": str(row[9]),
            }
        )
    return deliveries
