# First Run

## Starting the Bot

```bash
uv run zero-ichi
```

## QR Code Login

On first launch, the bot will display a QR code in the terminal:

1. Open **WhatsApp** on your phone
2. Go to **Settings → Linked Devices → Link a Device**
3. Scan the QR code displayed in the terminal

::: info
The session is saved to a `.session` file so you only need to scan once. Subsequent launches will auto-connect.
:::

## What Happens Next

Once connected, the bot will:

1. **Load all commands** — you'll see `OK  | Loaded 66 commands`
2. **Start the scheduler** — for reminders and scheduled tasks
3. **Start the dashboard API** — on `http://localhost:8000` (if enabled)
4. **Begin listening** — ready to process messages

```
20:36:31 INFO  | Message cache database initialized (WAL mode)
20:36:31  ->   | Validating environment...
20:36:31  OK   | Environment validation complete.
20:36:31  ->   | Starting bot...
               | * Session: zero_ichi_bot
               | * Login Method: QR
20:36:31  OK   | Loaded 66 commands
20:36:31  OK   | Bot is running! Press Ctrl+C to stop.
```

## Setting Yourself as Owner

Send this message from your WhatsApp:

```
/config owner me
```

This gives you access to [owner-only commands](/commands/owner) like `/eval`, `/config`, and `/addcommand`.

## Testing Commands

Try these commands to verify everything works:

| Command | What It Does |
|---------|-------------|
| `/ping` | Check if the bot is responding |
| `/help` | See all available commands |
| `/uptime` | Check how long the bot has been running |
| `/stats` | View bot statistics |

## Next Steps

- [Explore all commands](/commands/general)
- [Set up Agentic AI](/features/ai)
- [Configure group moderation](/commands/moderation)
