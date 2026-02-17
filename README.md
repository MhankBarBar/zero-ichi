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
- **The Ban Hammer**: Keep your groups clean with anti-link, anti-delete, warnings, and blacklists.
- **Time Travel**: Okay, not really, but our **Scheduler** lets you send messages in the future (cron supported!).
- **Polyglot**: Speaks English and Indonesian fluently. Add your own language if you're feeling adventurous.
- **Shiny Dashboard**: A web interface to manage everything because terminals are scary sometimes.

[See everything it can do →](https://zeroichi.mhankbarbar.dev)

---

## Get Started

### 1. Install via pip & git

```bash
pip install uv
git clone https://github.com/MhankBarBar/zero-ichi
cd zero-ichi
uv sync  # magic happens here
```

### 2. Configure

Copy the example config and make it yours:

```json
{
  "$schema": "./config.schema.json",
  "bot": {
    "name": "my_super_bot",
    "prefix": "/",
    "login_method": "qr"
  }
}
```

(Check the [Config Guide](https://zeroichi.mhankbarbar.dev/getting-started/configuration) for the nerdy details)

### 3. Launch

```bash
uv run main.py
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

- `commands/`: Where the magic happens
- `core/`: The brain
- `dashboard/`: The pretty face
- `locales/`: The dictionary

[Contributing Guide →](https://zeroichi.mhankbarbar.dev/development/architecture)
