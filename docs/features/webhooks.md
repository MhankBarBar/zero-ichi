# Webhooks

Zero Ichi can push bot and dashboard events to external services via HTTP webhooks.

## Where to Configure

Use the dashboard page:

- `Dashboard -> Webhooks`

Webhooks are stored in the runtime database (`SQLite` by default, or PostgreSQL when `DATABASE_URL` is set).

## Supported Events

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

You can subscribe to specific events or use `*` to receive all.

## Payload Format

Each delivery sends JSON:

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

## Security Headers

Every request includes:

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

Use your webhook secret to verify authenticity.

## Delivery Behavior

- Async queue worker (non-blocking for message pipeline)
- Retry with exponential backoff
- Delivery attempts are logged and visible in dashboard
