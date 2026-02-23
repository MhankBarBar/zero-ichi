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
| `GET /api/stats` | Usage statistics |
