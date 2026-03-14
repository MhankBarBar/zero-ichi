<h1 align="center">Zero Ichi</h1>

<p align="center">
  <img src="docs/public/logo.png" alt="Zero Ichi Logo" width="128" height="128">
</p>

<p align="center">
  The WhatsApp bot that does it all (so you don't have to).<br>
  Built with <a href="https://github.com/krypton-byte/neonize">Neonize</a>.<br><br>
  <strong><a href="https://zeroichi.mhankbarbar.dev">📚 Read the Docs</a></strong>
</p>

---

## Why Zero Ichi?

Because life is too short for boring bots.

- **Agentic AI**: A smart assistant that remembers context, executes commands, and might just be your new best friend.
- **Universal Downloader**: Grab videos from YouTube, TikTok, Instagram, and 1000+ other sites. Yes, even that one.
- **Mod Toolkit**: Keep your groups clean with anti-link, anti-delete, warnings, reports, and blacklists.
- **Time Travel**: Okay, not really, but our **Scheduler** lets you send messages in the future (cron supported!).
- **Webhooks**: Stream bot events into your own apps, Discord, CI, or alerting stack.
- **Database-Backed State**: SQLite out of the box, PostgreSQL when you need it.
- **Polyglot**: Speaks English and Indonesian fluently. Add your own language if you're feeling adventurous.
- **Shiny Dashboard**: A web interface to manage everything because terminals are scary sometimes.

[See everything it can do →](https://zeroichi.mhankbarbar.dev)

---

## Get Started

### One-Line Install

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/MhankBarBar/zero-ichi/master/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/MhankBarBar/zero-ichi/master/install.ps1 | iex
```

### Manual Install

```bash
pip install uv
git clone https://github.com/MhankBarBar/zero-ichi
cd zero-ichi
uv sync
cp .env.example .env
```

### Launch

```bash
uv run zero-ichi
```

Common CLI options:

```bash
uv run zero-ichi --debug --auto-reload
uv run zero-ichi --qr
uv run zero-ichi --phone 6281234567890
uv run zero-ichi --dashboard
uv run zero-ichi --session my_session
uv run zero-ichi update
```

Scan the QR code and you're in business.

---

## Documentation

Everything you need to know, neatly organized:

👉 **[zeroichi.mhankbarbar.dev](https://zeroichi.mhankbarbar.dev)**

- [Commands List](https://zeroichi.mhankbarbar.dev/commands/general)
- [How to Configure](https://zeroichi.mhankbarbar.dev/getting-started/configuration)
- [The AI Stuff](https://zeroichi.mhankbarbar.dev/features/ai)
- [Downloading Media](https://zeroichi.mhankbarbar.dev/commands/downloader)

---

## Project Structure

- `src/commands/`: Where the magic happens
- `src/core/`: The brain
- `src/dashboard/`: The pretty face
- `src/locales/`: The dictionary

[Contributing Guide →](https://zeroichi.mhankbarbar.dev/development/contributing)

---

## License

[MIT](LICENSE)
