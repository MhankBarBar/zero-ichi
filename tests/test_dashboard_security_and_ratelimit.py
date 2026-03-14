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
