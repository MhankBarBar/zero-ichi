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
```

The API runs on `http://localhost:8000`.

### 2. Start the Dashboard

In a separate terminal:

```bash
cd dashboard
bun install    # or npm install
bun dev        # or npm run dev
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
- **Statistics** — message counts, command usage, and more

## API

The dashboard communicates with the bot through a REST API:

| Endpoint | Description |
|----------|-------------|
| `GET /api/status` | Bot status and uptime |
| `GET /api/config` | Current configuration |
| `POST /api/config` | Update configuration |
| `GET /api/commands` | List all commands |
| `GET /api/groups` | List joined groups |
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
