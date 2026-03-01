# Configuration

The bot is configured through `config.json` with [JSON Schema](https://json-schema.org/) validation — your editor will provide autocomplete and inline docs automatically.

Runtime changes from WhatsApp commands or Dashboard are persisted back into `config.json` (single source of truth).

## Quick Start

```bash
cp config.json.example config.json
```

Then edit `config.json`.

`config.json.example` is committed to git; `config.json` is local-only.

::: tip Editor Autocomplete
The `$schema` reference gives you full autocomplete and validation in VS Code, WebStorm, and other JSON-aware editors.
:::

---

## `bot` — Core Settings {#bot}

Core bot identity and behavior.

| Property | Type | Default | Required | Description |
|----------|------|---------|:--------:|-------------|
| `name` | `string` | `zero_ichi_bot` | ✅ | Session identifier — creates `<name>.session` database file |
| `prefix` | `string` | `/` | ✅ | Command prefix. Supports regex for multiple prefixes (e.g. `!`, `/`, or `.`) |
| `login_method` | `string` | `QR` | ✅ | Login method: `QR` or `PAIR_CODE` |
| `owner_jid` | `string` | — | ✅ | Bot owner's JID (e.g. `628xxx@s.whatsapp.net` or `4089xxx@lid`) |
| `phone_number` | `string` | — | | Phone number in international format without `+` (for `PAIR_CODE` login) |
| `auto_read` | `boolean` | `false` | | Automatically mark incoming messages as read |
| `auto_react` | `boolean` | `false` | | Automatically react to incoming messages |
| `auto_react_emoji` | `string` | `""` | | Emoji to use for auto-react |
| `auto_reload` | `boolean` | `true` | | Hot-reload commands and locale files when files change (for development) |
| `ignore_self_messages` | `boolean` | `true` | | Ignore messages sent by the bot itself |

### Prefix Examples

```json
// Single prefix
"prefix": "/"

// Multiple prefixes (regex)
"prefix": "(/|!|.)"

// Exclamation mark only
"prefix": "!"
```

### Setting Owner

The easiest way to set yourself as the bot owner:

```
/config owner me
```

This auto-captures your JID and saves it to `config.json`.

---

## `logging` — Log Settings {#logging}

Control console and file logging output.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `log_messages` | `boolean` | `true` | Log incoming/outgoing messages to console |
| `level` | `string` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `file_logging` | `boolean` | `true` | Write logs to `logs/` directory |
| `verbose` | `boolean` | `false` | Enable verbose/detailed logging output |

```json
{
  "logging": {
    "log_messages": true,
    "level": "INFO",
    "file_logging": true,
    "verbose": false
  }
}
```

::: details Log Levels
| Level | Use Case |
|-------|----------|
| `DEBUG` | Everything — useful for development |
| `INFO` | General operational events |
| `WARNING` | Potential issues |
| `ERROR` | Failures that need attention |
| `CRITICAL` | Fatal errors |
:::

---

## `agentic_ai` — AI Settings {#agentic-ai}

Configure the AI assistant. See [Agentic AI](/features/ai) for full usage guide.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `enabled` | `boolean` | `false` | Enable AI-powered responses |
| `provider` | `string` | `openai` | AI provider: `openai`, `anthropic`, `google` |
| `api_key` | `string` | `""` | API key (falls back to `AI_API_KEY` env var if empty) |
| `model` | `string` | `gpt-5-mini` | Model name for the selected provider |
| `trigger_mode` | `string` | `mention` | When AI responds: `always`, `mention`, `reply` |
| `allowed_actions` | `string[]` | `[]` | Allowed command actions for AI (empty = all non-blocked) |
| `blocked_actions` | `string[]` | `["aeval", "eval", ...]` | Commands blocked from AI use (security) |
| `owner_only` | `boolean` | `true` | Restrict AI to bot owner only |

```json
{
  "agentic_ai": {
    "enabled": true,
    "provider": "openai",
    "model": "gpt-5-mini",
    "trigger_mode": "mention",
    "allowed_actions": [],
    "blocked_actions": ["aeval", "eval", "addcommand", "delcommand", "shutdown"],
    "owner_only": true
  }
}
```

::: warning Security
The `blocked_actions` list prevents the AI from running dangerous commands like `eval`. Don't remove these unless you know what you're doing.
:::

---

## `features` — Feature Toggles {#features}

Enable or disable built-in features globally.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `anti_delete` | `boolean` | `true` | Forward deleted messages to owner |
| `anti_link` | `boolean` | `false` | Detect and act on links in group chats |
| `welcome` | `boolean` | `true` | Send welcome messages for new group members |
| `notes` | `boolean` | `true` | Enable notes/saved replies (`/save`, `#notename`) |
| `filters` | `boolean` | `true` | Enable auto-reply filters (`/filter`) |
| `blacklist` | `boolean` | `true` | Enable word blacklist filtering |
| `warnings` | `boolean` | `true` | Enable user warning system |
| `automation_rules` | `boolean` | `true` | Enable no-code automation rule engine |

```json
{
  "features": {
    "anti_delete": true,
    "anti_link": false,
    "welcome": true,
    "notes": true,
    "filters": true,
    "blacklist": true,
    "warnings": true,
    "automation_rules": true
  }
}
```

---

## `anti_delete` — Anti-Delete Settings {#anti-delete}

Configure how deleted messages are recovered.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `forward_to` | `string` | — | JID to forward deleted messages to (usually your owner JID) |
| `cache_ttl` | `integer` | `60` | Message cache TTL in seconds (min: `1`) |

```json
{
  "anti_delete": {
    "forward_to": "628xxxx@s.whatsapp.net",
    "cache_ttl": 60
  }
}
```

---

## `anti_link` — Anti-Link Settings {#anti-link}

Configure link detection behavior in groups.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `action` | `string` | `warn` | Action on link detection: `warn`, `delete`, `kick` |
| `whitelist` | `string[]` | `[]` | Domains allowed to bypass anti-link |

```json
{
  "anti_link": {
    "action": "warn",
    "whitelist": ["youtube.com", "github.com"]
  }
}
```

---

## `warnings` — Warning System {#warnings}

Configure the user warning system.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `limit` | `integer` | `3` | Warnings before action is taken (min: `1`) |
| `action` | `string` | `kick` | Action at limit: `kick` |

```json
{
  "warnings": {
    "limit": 3,
    "action": "kick"
  }
}
```

---

## `downloader` — Download Settings {#downloader}

Configure the media downloader used by `/dl`, `/audio`, and `/video` commands.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `max_file_size_mb` | `number` | `50` | Maximum file size in MB for downloaded media |

### `downloader.gallery_dl`

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `config_file` | `string` | `""` | Optional path to gallery-dl config file |
| `config` | `object` | `{}` | Optional inline gallery-dl configuration object |
| `cookies_file` | `string` | `""` | Optional Netscape cookies file path (`--cookies`) |
| `cookies_from_browser` | `string` | `""` | Optional browser source (`--cookies-from-browser`) |
| `extra_args` | `string[]` | `[]` | Extra CLI args passed to gallery-dl |

You can use either `config_file` or inline `config` (or both). The inline `config` follows gallery-dl's official JSON structure (for example `extractor.*`, `downloader.*`, `output.*`).

```json
{
  "downloader": {
    "gallery_dl": {
      "config": {
        "extractor": {
          "instagram": {
            "cookies": "data/gallery-cookies.txt"
          }
        }
      }
    }
  }
}
```

### `downloader.auto_link_download`

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `enabled` | `boolean` | `false` | Enable automatic link downloads |
| `mode` | `string` | `auto` | Download mode: `auto`, `audio`, `video`, `photo` |
| `cooldown_seconds` | `integer` | `30` | Per-user cooldown to prevent spam |
| `max_links_per_message` | `integer` | `1` | Maximum links processed per message |
| `group_only` | `boolean` | `true` | Restrict auto-download to groups only |

### `downloader.auto_link_download.photo`

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `max_images_per_link` | `integer` | `20` | Max images extracted from one URL |
| `max_images_per_album` | `integer` | `10` | Max images sent per album batch |

::: tip
WhatsApp supports up to **180 MB** for media (images, videos, audio) and up to **2 GB** for documents.
The default limit is conservative (`50 MB`) to reduce failures on slower devices/networks.
:::

```json
{
  "downloader": {
    "max_file_size_mb": 50,
    "gallery_dl": {
      "config_file": "",
      "config": {},
      "cookies_file": "",
      "cookies_from_browser": "",
      "extra_args": []
    },
    "auto_link_download": {
      "enabled": false,
      "mode": "auto",
      "cooldown_seconds": 30,
      "max_links_per_message": 1,
      "group_only": true,
      "photo": {
        "max_images_per_link": 20,
        "max_images_per_album": 10
      }
    }
  }
}
```

---

## `call_guard` — Incoming Call Guard {#call-guard}

Handle incoming WhatsApp calls automatically.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `enabled` | `boolean` | `false` | Enable incoming call guard |
| `action` | `string` | `block` | Action mode: `off` or `block` |
| `delay_seconds` | `integer` | `3` | Delay before blocking caller (0-60) |
| `notify_caller` | `boolean` | `true` | Send DM warning to caller before block |
| `notify_owner` | `boolean` | `true` | Notify owner when a caller is blocked |
| `whitelist` | `string[]` | `[]` | Caller JIDs exempt from call guard |

```json
{
  "call_guard": {
    "enabled": false,
    "action": "block",
    "delay_seconds": 3,
    "notify_caller": true,
    "notify_owner": true,
    "whitelist": []
  }
}
```

---

## `disabled_commands` — Disable Commands {#disabled-commands}

Globally disable specific commands by name.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `disabled_commands` | `string[]` | `[]` | List of command names to disable |

```json
{
  "disabled_commands": ["joke", "flip", "8ball"]
}
```

---

## `dashboard` — Dashboard Settings {#dashboard}

Configure the web dashboard API.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `enabled` | `boolean` | `false` | Enable the dashboard API server on startup |

```json
{
  "dashboard": {
    "enabled": false
  }
}
```

::: note
The dashboard starts on port `8000` by default if enabled.
This dashboard api is required to enable if you want to use the dashboard.
:::

---

## Environment Variables

Store sensitive values in `.env` (never commit this file):

```bash
AI_API_KEY=your_api_key_here
YOUTUBE_COOKIES_PATH=data/cookies.txt
GALLERY_DL_CONFIG_FILE=data/gallery-dl.conf
GALLERY_DL_COOKIES_FILE=data/gallery-cookies.txt
GALLERY_DL_COOKIES_FROM_BROWSER=firefox
```

### YouTube Cookies

If you are running the bot on a VPS, YouTube may block your requests with "Sign in to confirm you're not a bot" errors. To fix this:

1.  Export your cookies from a logged-in browser (using an extension like [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/ccmgnabipihkhmhnoicpbihnkhnleogp)).
2.  Save them to `data/cookies.txt` (or whatever path you set in `.env`).
3.  Set the environment variable: `YOUTUBE_COOKIES_PATH=data/cookies.txt`.

### gallery-dl Cookies / Config

Use `downloader.gallery_dl` in `config.json`, or override with env vars above.

Examples:

- `downloader.gallery_dl.cookies_file`: pass Netscape cookies file via `--cookies`
- `downloader.gallery_dl.cookies_from_browser`: pass browser source via `--cookies-from-browser`
- `downloader.gallery_dl.config_file`: pass full gallery-dl config file via `--config`
- `downloader.gallery_dl.extra_args`: pass extra runtime arguments (array)

Copy the example file to get started:

```bash
cp .env.example .env
```

---

## Full Example

A complete `config.json` with all sections:

```json
{
  "$schema": "./config.schema.json",
  "bot": {
    "name": "zero_ichi_bot",
    "prefix": "(/|!|.)",
    "login_method": "QR",
    "owner_jid": "628xxxx@s.whatsapp.net",
    "auto_read": false,
    "auto_react": false,
    "auto_reload": true,
    "ignore_self_messages": true
  },
  "logging": {
    "log_messages": true,
    "level": "INFO",
    "file_logging": true,
    "verbose": false
  },
  "agentic_ai": {
    "enabled": true,
    "provider": "openai",
    "model": "gpt-5-mini",
    "trigger_mode": "mention",
    "blocked_actions": ["eval", "aeval", "addcommand", "delcommand"],
    "owner_only": true
  },
  "features": {
    "anti_delete": true,
    "anti_link": true,
    "welcome": true,
    "notes": true,
    "filters": true,
    "blacklist": true,
    "warnings": true,
    "automation_rules": true
  },
  "anti_delete": {
    "forward_to": "628xxxx@s.whatsapp.net",
    "cache_ttl": 60
  },
  "anti_link": {
    "action": "warn",
    "whitelist": ["youtube.com", "github.com"]
  },
  "warnings": {
    "limit": 3,
    "action": "kick"
  },
  "downloader": {
    "max_file_size_mb": 50,
    "gallery_dl": {
      "config_file": "",
      "config": {},
      "cookies_file": "",
      "cookies_from_browser": "",
      "extra_args": []
    },
    "auto_link_download": {
      "enabled": false,
      "mode": "auto",
      "cooldown_seconds": 30,
      "max_links_per_message": 1,
      "group_only": true,
      "photo": {
        "max_images_per_link": 20,
        "max_images_per_album": 10
      }
    }
  },
  "call_guard": {
    "enabled": false,
    "action": "block",
    "delay_seconds": 3,
    "notify_caller": true,
    "notify_owner": true,
    "whitelist": []
  },
  "disabled_commands": [],
  "dashboard": {
    "enabled": false
  }
}
```
