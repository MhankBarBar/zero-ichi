import hashlib
import hmac
import time

import pytest
from fastapi import HTTPException

import dashboard_api


def test_dashboard_credentials_require_env(monkeypatch):
    monkeypatch.delenv("DASHBOARD_USERNAME", raising=False)
    monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)

    with pytest.raises(HTTPException) as exc:
        dashboard_api._get_dashboard_credentials()

    assert exc.value.status_code == 503


def test_dashboard_credentials_reject_admin_defaults(monkeypatch):
    monkeypatch.setenv("DASHBOARD_USERNAME", "admin")
    monkeypatch.setenv("DASHBOARD_PASSWORD", "admin")

    with pytest.raises(HTTPException) as exc:
        dashboard_api._get_dashboard_credentials()

    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_rate_limit_update_persists(monkeypatch):
    captured = {}
    limiter = {}
    emitted = []

    def fake_set(key, value):
        captured[key] = value

    def fake_update(config):
        limiter.update(config.__dict__)

    async def fake_emit(event_type, payload):
        emitted.append((event_type, payload))

    monkeypatch.setattr(dashboard_api.runtime_config, "set", fake_set)
    monkeypatch.setattr(dashboard_api.rate_limiter, "update_config", fake_update)
    monkeypatch.setattr(dashboard_api.event_bus, "emit", fake_emit)

    result = await dashboard_api.update_rate_limit(
        dashboard_api.RateLimitSettings(
            enabled=True,
            user_cooldown=4.5,
            command_cooldown=3.0,
            burst_limit=9,
            burst_window=12.0,
        )
    )

    assert result == {"success": True}
    assert captured["rate_limit"]["burst_limit"] == 9
    assert limiter["burst_limit"] == 9
    assert emitted[0][0] == "config_update"


def test_incoming_signature_verification():
    token = "test-token"
    timestamp = str(int(time.time()))
    payload = b'{"action":"emit_event","data":{}}'
    digest = hmac.new(
        token.encode("utf-8"), f"{timestamp}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    signature = f"sha256={digest}"

    assert dashboard_api._verify_incoming_signature(token, timestamp, signature, payload)
    assert not dashboard_api._verify_incoming_signature(token, timestamp, "sha256=bad", payload)


def test_incoming_rate_limiter_window():
    key_id = 9999
    dashboard_api._incoming_rate_windows.pop(key_id, None)

    assert dashboard_api._consume_incoming_rate_limit(key_id, 2)
    assert dashboard_api._consume_incoming_rate_limit(key_id, 2)
    assert not dashboard_api._consume_incoming_rate_limit(key_id, 2)


class _FakeRequest:
    def __init__(self, headers: dict[str, str], payload: bytes):
        self.headers = headers
        self._payload = payload

    async def body(self) -> bytes:
        return self._payload


@pytest.mark.asyncio
async def test_incoming_webhook_duplicate_idempotency_returns_409(monkeypatch):
    payload = b'{"action":"emit_event","data":{"event_type":"ci_done","event_data":{}}}'
    request = _FakeRequest(
        headers={
            "X-ZeroIchi-Incoming-Timestamp": str(int(time.time())),
            "X-ZeroIchi-Incoming-Signature": "sha256=test",
            "X-ZeroIchi-Incoming-Idempotency-Key": "dup-1",
        },
        payload=payload,
    )

    monkeypatch.setattr(
        dashboard_api,
        "resolve_incoming_webhook_key",
        lambda _token: {
            "id": 1,
            "enabled": True,
            "allowed_actions": ["emit_event"],
            "rate_limit_per_minute": 30,
        },
    )
    monkeypatch.setattr(dashboard_api, "_verify_incoming_signature", lambda *_: True)
    monkeypatch.setattr(dashboard_api, "_consume_incoming_rate_limit", lambda *_: True)
    monkeypatch.setattr(dashboard_api, "claim_incoming_idempotency", lambda *_: False)

    with pytest.raises(HTTPException) as exc:
        await dashboard_api.incoming_webhook_endpoint("token", request)  # type: ignore[arg-type]

    assert exc.value.status_code == 409
