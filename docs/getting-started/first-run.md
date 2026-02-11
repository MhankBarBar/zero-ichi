# First Run

## Starting the Bot

```bash
uv run main.py
```

## QR Code Login

On first launch, the bot will display a QR code in the terminal:

1. Open **WhatsApp** on your phone
2. Go to **Settings → Linked Devices → Link a Device**
3. Scan the QR code displayed in the terminal

::: info
The session is saved to a `zero_ichi_bot.session` file so you only need to scan once. Subsequent launches will auto-connect.
:::

## What Happens Next

Once connected, the bot will:

1. **Load all commands** — you'll see `✓ Loaded 61 commands`
2. **Start the scheduler** — for reminders and scheduled tasks
3. **Start the dashboard API** — on `http://localhost:8000`
4. **Begin listening** — ready to process messages

```
╭──────────────────────────────────────────╮
│ Zero Ichi                                │
│ WhatsApp Bot built with 💖               │
╰──────────────────────────────────────────╯
✓  Dashboard API starting on http://localhost:8000
→  Starting bot...
  • Session: zero_ichi_bot
  • Login Method: QR
✓  Loaded 61 commands
✓  Bot is running! Press Ctrl+C to stop.
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

- [Explore all commands →](/commands/general)
- [Set up Agentic AI →](/features/ai)
- [Configure group moderation →](/commands/moderation)
