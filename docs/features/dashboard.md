# Web Dashboard

Zero Ichi includes a web dashboard for monitoring and administration, built with **Next.js**.

## Setup

### 1. Start the Bot

The dashboard API starts automatically with the bot if enabled in `config.json`:

```json
"dashboard": {
  "enabled": true
}
```

Then start the bot:

```bash
uv run zero-ichi
# or, without editing config.json:
uv run zero-ichi --dashboard
```

The API runs on `http://localhost:8000`.

### 2. Start the Dashboard

In a separate terminal:

```bash
cd dashboard
bun install
bun dev
```

Open `http://localhost:3000` in your browser.

## Features

- **Live monitoring** — see messages, commands, and bot activity in real-time
- **Configuration** — manage bot settings from the web
- **Command management** — enable/disable commands
- **Group overview** — see all groups the bot is in
- **Reports Center** — inspect and resolve/dismiss moderation reports
- **Digest Manager** — configure daily/weekly group digests with preview + send-now
- **Automation Rules** — create no-code trigger/action moderation rules
- **Webhook Manager** — configure outbound event webhooks and inspect delivery logs
- **Incoming Keys** — create signed incoming webhook keys with allowed actions and rate limits
- **Audit Logs** — inspect security-sensitive config/webhook changes over time
- **Statistics** — message counts, command usage, and more

## Security Notes

- Set `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD` in `.env`.
- `admin/admin` is intentionally rejected for security.
- Dashboard CORS origins are controlled by `dashboard.cors_origins` (or `DASHBOARD_CORS_ORIGINS`).
- WebSocket live updates require short-lived auth tokens.

## API

The dashboard communicates with the bot through a REST API:

| Endpoint | Description |
|----------|-------------|
| `GET /api/status` | Bot status and uptime |
| `GET /api/config` | Current configuration |
| `PUT /api/config` | Update configuration |
| `GET /api/commands` | List all commands |
| `GET /api/groups` | List joined groups |
| `GET /api/webhooks` | List webhooks + supported event names |
| `POST /api/webhooks` | Create webhook endpoint |
| `PUT /api/webhooks/{id}` | Update webhook endpoint |
| `DELETE /api/webhooks/{id}` | Delete webhook endpoint |
| `POST /api/webhooks/{id}/test` | Send test event to endpoint |
| `POST /api/webhooks/{id}/rotate-secret` | Rotate webhook secret |
| `GET /api/webhooks/{id}/deliveries` | Recent delivery attempts |
| `POST /api/webhooks/{id}/deliveries/{delivery_id}/replay` | Replay one delivery |
| `GET /api/incoming-webhook-keys` | List incoming webhook keys |
| `POST /api/incoming-webhook-keys` | Create incoming webhook key |
| `PUT /api/incoming-webhook-keys/{id}` | Update incoming webhook key |
| `POST /api/incoming-webhook-keys/{id}/rotate` | Rotate incoming key token |
| `DELETE /api/incoming-webhook-keys/{id}` | Delete incoming webhook key |
| `POST /api/incoming-webhook/{token}` | Execute incoming webhook action |
| `GET /api/audit-logs` | Audit timeline entries |
| `GET /api/health` | API + DB + webhook worker health |
| `GET /api/groups/{group_id}/reports` | List report queue for a group |
| `PUT /api/groups/{group_id}/reports/{report_id}` | Update report status |
| `GET /api/groups/{group_id}/digest` | Get digest config + preview |
| `PUT /api/groups/{group_id}/digest` | Update digest schedule |
| `POST /api/groups/{group_id}/digest/now` | Trigger immediate digest |
| `GET /api/groups/{group_id}/automations` | List automation rules |
| `POST /api/groups/{group_id}/automations` | Create automation rule |
| `PUT /api/groups/{group_id}/automations/{rule_id}` | Update automation rule |
| `DELETE /api/groups/{group_id}/automations/{rule_id}` | Delete automation rule |
| `GET /api/stats` | Usage statistics |
