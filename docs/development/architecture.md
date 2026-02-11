# Architecture

Overview of Zero Ichi's internal architecture and project structure.

## Project Structure

```
zero-ichi/
├── main.py                 # Entry point, message handler
├── config.json             # Bot configuration
├── config.schema.json      # JSON Schema for validation
├── dashboard_api.py        # FastAPI dashboard backend
│
├── ai/                     # Agentic AI module
│   ├── agent.py            # Main AI agent logic
│   ├── config.py           # AI configuration
│   ├── context.py          # Message context builder
│   ├── memory.py           # Conversation memory
│   ├── skills.py           # Skill management
│   └── tools/              # AI tool definitions
│       ├── core.py         # Core tools (send, reply, mention)
│       └── group.py        # Group tools (kick, mute, promote)
│
├── commands/               # Command modules
│   ├── admin/              # Admin commands (kick, mute, etc.)
│   ├── content/            # Notes, filters, stickers
│   ├── fun/                # Entertainment commands
│   ├── general/            # Help, ping, stats
│   ├── group/              # Group management
│   ├── moderation/         # Warnings, blacklist, anti-link
│   ├── owner/              # Owner-only commands
│   └── utility/            # AFK, reminders, language
│
├── core/                   # Core modules
│   ├── client.py           # WhatsApp client wrapper
│   ├── command.py          # Command base class & loader
│   ├── errors.py           # Error handling utilities
│   ├── i18n.py             # Internationalization
│   ├── jid_resolver.py     # JID ↔ LID resolution
│   ├── message.py          # Message helper class
│   ├── permissions.py      # Permission checks
│   ├── rate_limiter.py     # Rate limiting
│   ├── runtime_config.py   # Live configuration manager
│   ├── scheduler.py        # Task scheduler (reminders)
│   ├── storage.py          # Per-group data storage
│   ├── symbols.py          # Unicode symbols
│   └── handlers/           # Event handlers
│       ├── afk.py          # AFK mention detection
│       ├── antidelete.py   # Deleted message recovery
│       ├── antilink.py     # Link detection
│       ├── blacklist.py    # Word filtering
│       ├── features.py     # Notes & filters handler
│       ├── mute.py         # Mute enforcement
│       └── welcome.py      # Welcome/goodbye handler
│
├── dashboard/              # Next.js admin dashboard
├── locales/                # Translation files (en, id)
├── data/                   # Per-group persistent data
└── logs/                   # Log files
```

## Core Modules

### Message Flow

```
WhatsApp → Neonize → main.py → Handlers → Command Loader → Command.execute()
```

1. **Neonize** receives the WhatsApp message
2. **`main.py`** wraps it in a `MessageHelper` and runs handlers
3. **Handlers** process features (anti-delete, anti-link, filters, etc.)
4. **Command Loader** matches the prefix + command name
5. **Permissions** are checked (admin, owner, bot-admin, rate limit)
6. **Command.execute()** runs the command logic

### Command System

Commands are Python classes that inherit from `Command`:

```python
class Command:
    name: str               # Command name
    aliases: list[str]      # Alternative names
    description: str        # Help text
    usage: str              # Usage example
    group_only: bool        # Group-only command
    private_only: bool      # DM-only command
    admin_only: bool        # Requires group admin
    owner_only: bool        # Requires bot owner
    bot_admin_required: bool  # Bot must be group admin
    cooldown: int           # Seconds between uses
```

Commands are auto-discovered from `commands/*/` directories.

### Storage

`core/storage.py` provides per-group persistent storage using JSON files in the `data/` directory:

```python
from core.storage import GroupData

storage = GroupData(chat_jid)
storage.save("rules", {"text": "Be kind!"})
rules = storage.load("rules", {"text": ""})
```

### JID Resolver

WhatsApp uses two ID formats: **PN** (phone number) and **LID** (linked ID). The JID resolver handles conversion between them:

```python
from core.jid_resolver import jids_match, resolve_pair

# Check if two JIDs are the same user
if await jids_match(jid1, jid2, client):
    print("Same user!")
```
