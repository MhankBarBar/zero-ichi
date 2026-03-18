# Webhooks

Zero Ichi has two webhook directions:

- **Outgoing webhooks**: Zero Ichi sends event payloads to your endpoint
- **Incoming webhooks**: your system calls Zero Ichi to execute allowed actions

## Quick View

| Type | Direction | Auth | Where to manage |
|------|-----------|------|-----------------|
| Outgoing | Zero Ichi -> your endpoint | HMAC signature (`X-ZeroIchi-Signature`) | `Dashboard -> Webhooks` |
| Incoming | your system -> Zero Ichi | token + HMAC + idempotency key | `Dashboard -> Webhooks` |

Webhooks are stored in the runtime database (SQLite by default, PostgreSQL if `DATABASE_URL` is set).

## Outgoing Webhooks

### 1) Create an outgoing webhook

In `Dashboard -> Webhooks`, define:

- `name`: label used in dashboard
- `url`: destination endpoint (HTTPS recommended)
- `events`: list of events or `*` for all events
- `secret`: shared secret for HMAC verification
- `max_failures`: consecutive failure limit before auto-disable
- `enabled`: on/off toggle

### 2) Subscribe to events

Current event names include:

- `new_message`
- `command_executed`
- `auto_download`
- `command_update`
- `config_update`
- `group_update`
- `report_update`
- `digest_update`
- `automation_update`
- `automation_triggered`

### 3) Handle payloads on your endpoint

Example payload:

```json
{
  "event": "command_executed",
  "timestamp": "2026-03-14T20:40:00+00:00",
  "data": {
    "command": "help",
    "user": "Alice",
    "chat": "123456@g.us"
  }
}
```

Every outgoing request includes:

- `X-ZeroIchi-Event`
- `X-ZeroIchi-Timestamp`
- `X-ZeroIchi-Signature`

Signature format:

```text
sha256=<hex-hmac>
```

HMAC input string:

```text
<timestamp>.<raw-json-body>
```

### 4) Verify signature (example)

```python
import hashlib
import hmac

def verify(secret: str, timestamp: str, raw_body: bytes, signature: str) -> bool:
    digest = hmac.new(secret.encode("utf-8"), f"{timestamp}.".encode() + raw_body, hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"
    return hmac.compare_digest(expected, signature)
```

## Incoming Webhooks

Incoming webhooks let external systems trigger safe, scoped actions in Zero Ichi.

### 1) Create incoming key

In `Dashboard -> Webhooks`, create an incoming key with:

- `name`
- `allowed_actions` (for example `send_message`, `emit_event`)
- `rate_limit_per_minute`
- `enabled`

You will get a token. Store it securely.

### 2) Call incoming endpoint

Endpoint:

```text
POST /api/incoming-webhook/{token}
```

If your API is local default, full URL is:

```text
http://localhost:8000/api/incoming-webhook/{token}
```

Required headers:

- `X-ZeroIchi-Incoming-Timestamp` (unix seconds)
- `X-ZeroIchi-Incoming-Signature` (`sha256=<hex-hmac>`)
- `X-ZeroIchi-Incoming-Idempotency-Key` (unique per request)

Signature HMAC input:

```text
<timestamp>.<raw-json-body>
```

### 3) Send payload

`send_message` example:

```json
{
  "action": "send_message",
  "data": {
    "to": "1234567890@s.whatsapp.net",
    "text": "Deploy complete"
  }
}
```

`emit_event` example:

```json
{
  "action": "emit_event",
  "data": {
    "event_type": "ci_pipeline_done",
    "event_data": {
      "project": "zero-ichi",
      "status": "success"
    }
  }
}
```

### 4) Generate incoming signature and send (Python example)

```python
import hashlib
import hmac
import json
import time
import uuid

token = "<incoming-token>"
timestamp = str(int(time.time()))
payload = {
    "action": "emit_event",
    "data": {"event_type": "ci_pipeline_done", "event_data": {"status": "success"}},
}
raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
digest = hmac.new(token.encode("utf-8"), f"{timestamp}.".encode() + raw, hashlib.sha256).hexdigest()
signature = f"sha256={digest}"
idempotency_key = str(uuid.uuid4())
```

Use `timestamp`, `signature`, and `idempotency_key` in request headers.

### 5) Reusable Python helper (recommended)

Use this helper to generate signed headers once, then send with either stdlib (`urllib`) or `httpx`.

```python
import hashlib
import hmac
import json
import time
import uuid


def build_incoming_request(token: str, payload: dict) -> tuple[str, bytes, dict[str, str]]:
    timestamp = str(int(time.time()))
    idempotency_key = str(uuid.uuid4())
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    digest = hmac.new(token.encode("utf-8"), f"{timestamp}.".encode() + raw, hashlib.sha256).hexdigest()
    signature = f"sha256={digest}"

    headers = {
        "Content-Type": "application/json",
        "X-ZeroIchi-Incoming-Timestamp": timestamp,
        "X-ZeroIchi-Incoming-Signature": signature,
        "X-ZeroIchi-Incoming-Idempotency-Key": idempotency_key,
    }
    return timestamp, raw, headers


token = "<incoming-token>"
payload = {
    "action": "emit_event",
    "data": {"event_type": "ci_pipeline_done", "event_data": {"status": "success"}},
}
_, raw, headers = build_incoming_request(token, payload)
url = f"http://localhost:8000/api/incoming-webhook/{token}"
```

### 6) Send using pure Python stdlib (`urllib`)

```python
import urllib.request

req = urllib.request.Request(url, data=raw, method="POST", headers=headers)
with urllib.request.urlopen(req, timeout=10) as resp:
    print(resp.status)
    print(resp.read().decode("utf-8"))
```

### 7) Send using `httpx`

```python
import httpx

response = httpx.post(url, content=raw, headers=headers, timeout=10)
print(response.status_code)
print(response.text)
```

Expected success response shape:

```json
{"success": true, "action": "emit_event", "event_type": "ci_pipeline_done"}
```

## Validation and Error Codes

Incoming requests are checked in this order:

1. key exists and is enabled
2. signature + timestamp drift window
3. idempotency key is present and not reused
4. per-key rate limit
5. action is allowed for that key

Common responses:

| Status | Meaning |
|--------|---------|
| `200` | action accepted and executed |
| `400` | invalid JSON/payload or missing required header |
| `401` | invalid key or invalid signature |
| `403` | action not allowed for this key |
| `409` | duplicate idempotency key |
| `429` | key rate limit exceeded |
| `503` | bot not connected (for `send_message`) |

## Reliability and Operations

Outgoing webhooks include:

- async dispatch queue (non-blocking)
- retry with exponential backoff
- delivery logs per webhook
- auto-disable after repeated failures (`max_failures`)
- rotate secret and replay selected deliveries from dashboard

Useful endpoints:

- `GET /api/webhooks/{id}/deliveries`
- `POST /api/webhooks/{id}/deliveries/{delivery_id}/replay`
- `GET /api/health` (authenticated API, DB, and webhook worker health)
- `GET /healthz` (public liveness)

## Troubleshooting

- `401 Invalid signature`: token/secret mismatch, wrong body bytes, or stale timestamp.
- `409 Duplicate idempotency key`: reuse detected; send a new unique key.
- `429 Incoming webhook rate limit exceeded`: increase limit for that key or reduce caller burst.
- Outgoing webhook disabled unexpectedly: review failure history and `max_failures`, then re-enable after fixing endpoint.
- No deliveries visible: verify webhook is enabled and event subscription matches emitted event names.
