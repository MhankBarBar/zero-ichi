"""Webhook dispatch service.

Consumes bot/dashboard events and delivers them to configured webhook endpoints.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any

import httpx

from core.db import (
    get_active_webhooks_for_event,
    get_webhook,
    record_webhook_delivery,
)
from core.logger import log_warning

MAX_ATTEMPTS = 3
BASE_RETRY_DELAY_SECONDS = 0.75
REQUEST_TIMEOUT_SECONDS = 8.0


@dataclass
class WebhookEvent:
    event_type: str
    data: dict[str, Any]
    timestamp: str


class WebhookDispatcher:
    """Asynchronous webhook delivery queue."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[WebhookEvent] = asyncio.Queue(maxsize=1000)
        self._worker_task: asyncio.Task | None = None
        self._client: httpx.AsyncClient | None = None
        self._lock = asyncio.Lock()

    async def _ensure_started(self) -> None:
        async with self._lock:
            if self._worker_task and not self._worker_task.done():
                return

            if self._client is None:
                self._client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS)

            self._worker_task = asyncio.create_task(self._worker(), name="webhook-dispatcher")

    async def enqueue(self, event: WebhookEvent) -> None:
        """Queue event for async webhook delivery."""
        await self._ensure_started()
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            log_warning("Webhook queue full; dropping event")

    def _build_signature(self, secret: str, timestamp: str, payload: str) -> str:
        message = f"{timestamp}.{payload}".encode()
        digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
        return f"sha256={digest}"

    async def _deliver_one(
        self,
        webhook: dict[str, Any],
        event: WebhookEvent,
        *,
        allow_retry: bool = True,
    ) -> dict[str, Any]:
        """Deliver an event to one webhook endpoint."""
        url = str(webhook.get("url", "")).strip()
        secret = str(webhook.get("secret", "")).strip() or secrets.token_hex(16)
        webhook_id = int(webhook["id"])

        body_payload = {
            "event": event.event_type,
            "timestamp": event.timestamp,
            "data": event.data,
        }
        body = json.dumps(body_payload, ensure_ascii=False)

        max_attempts = MAX_ATTEMPTS if allow_retry else 1

        for attempt in range(1, max_attempts + 1):
            ts = str(int(time.time()))
            signature = self._build_signature(secret, ts, body)
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "ZeroIchi-Webhook/1.0",
                "X-ZeroIchi-Event": event.event_type,
                "X-ZeroIchi-Timestamp": ts,
                "X-ZeroIchi-Signature": signature,
            }

            try:
                if self._client is None:
                    self._client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS)

                response = await self._client.post(
                    url, content=body.encode("utf-8"), headers=headers
                )
                ok = 200 <= response.status_code < 300

                record_webhook_delivery(
                    webhook_id=webhook_id,
                    event_type=event.event_type,
                    payload=body_payload,
                    success=ok,
                    attempt=attempt,
                    status_code=response.status_code,
                    response_body=response.text,
                    error=None if ok else f"HTTP {response.status_code}",
                )

                if ok:
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "attempt": attempt,
                    }

                if attempt < max_attempts:
                    await asyncio.sleep(BASE_RETRY_DELAY_SECONDS * (2 ** (attempt - 1)))
            except Exception as exc:
                record_webhook_delivery(
                    webhook_id=webhook_id,
                    event_type=event.event_type,
                    payload=body_payload,
                    success=False,
                    attempt=attempt,
                    status_code=None,
                    response_body=None,
                    error=str(exc),
                )
                if attempt < max_attempts:
                    await asyncio.sleep(BASE_RETRY_DELAY_SECONDS * (2 ** (attempt - 1)))
                else:
                    log_warning(f"Webhook delivery failed ({webhook_id}): {exc}")

        return {"success": False}

    async def _worker(self) -> None:
        """Background delivery worker."""
        while True:
            event = await self._queue.get()
            try:
                hooks = get_active_webhooks_for_event(event.event_type)
                for hook in hooks:
                    await self._deliver_one(hook, event, allow_retry=True)
            except Exception as exc:
                log_warning(f"Webhook worker error: {exc}")
            finally:
                self._queue.task_done()

    async def send_test(self, webhook_id: int) -> dict[str, Any]:
        """Send one immediate test event to a webhook."""
        hook = get_webhook(webhook_id)
        if not hook:
            return {"success": False, "error": "Webhook not found"}

        event = WebhookEvent(
            event_type="webhook_test",
            data={"message": "Zero Ichi test event"},
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )
        result = await self._deliver_one(hook, event, allow_retry=False)
        return result


_dispatcher = WebhookDispatcher()


async def dispatch_event(event_type: str, data: dict[str, Any], timestamp: str) -> None:
    """Queue an event for webhook delivery."""
    await _dispatcher.enqueue(WebhookEvent(event_type=event_type, data=data, timestamp=timestamp))


async def send_test_webhook(webhook_id: int) -> dict[str, Any]:
    """Trigger a one-shot webhook test delivery."""
    return await _dispatcher.send_test(webhook_id)


def list_known_events() -> list[str]:
    """Known event names exposed by current bot flows."""
    return [
        "new_message",
        "command_executed",
        "auto_download",
        "command_update",
        "config_update",
        "group_update",
        "report_update",
        "digest_update",
        "automation_update",
        "automation_triggered",
        "webhook_test",
    ]
