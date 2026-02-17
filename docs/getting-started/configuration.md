# Configuration

The bot is configured through `config.json` with [JSON Schema](https://json-schema.org/) validation — your editor will provide autocomplete and inline docs automatically.

## Quick Start

```json
{
  "$schema": "./config.schema.json",
  "bot": {
    "name": "my_bot",
    "prefix": "/",
    "login_method": "QR",
    "owner_jid": ""
  }
}
```

::: tip Editor Autocomplete
The `$schema` reference gives you full autocomplete and validation in VS Code, WebStorm, and other JSON-aware editors.
:::

---

## `bot` — Core Settings {#bot}

Core bot identity and behavior.

| Property | Type | Default | Required | Description |
|----------|------|---------|:--------:|-------------|
| `name` | `string` | `zero_ichi_bot` | ✅ | Session identifier — creates `<name>.session` database file |
| `prefix` | `string` | `(!\|/\|.)` | ✅ | Command prefix. Supports regex for multiple prefixes (e.g. `!`, `/`, or `.`) |
| `login_method` | `string` | `QR` | ✅ | Login method: `QR` or `PAIR_CODE` |
| `owner_jid` | `string` | — | ✅ | Bot owner's JID (e.g. `628xxx@s.whatsapp.net` or `4089xxx@lid`) |
| `phone_number` | `string` | — | | Phone number in international format without `+` (for `PAIR_CODE` login) |
| `auto_read` | `boolean` | `false` | | Automatically mark incoming messages as read |
| `auto_react` | `boolean` | `false` | | Automatically react to incoming messages |
| `auto_react_emoji` | `string` | `❤️` | | Emoji to use for auto-react |
| `auto_reload` | `boolean` | `false` | | Hot-reload commands when files change (for development) |
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
| `verbose` | `boolean` | `true` | Enable verbose/detailed logging output |

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
| `enabled` | `boolean` | `true` | Enable AI-powered responses |
| `provider` | `string` | `openai` | AI provider: `openai`, `anthropic`, `google` |
| `api_key` | `string` | `""` | API key (falls back to `AI_API_KEY` env var if empty) |
| `model` | `string` | `gpt-5-mini` | Model name for the selected provider |
| `trigger_mode` | `string` | `reply` | When AI responds: `always`, `mention`, `reply` |
| `allowed_actions` | `string[]` | `[]` | Allowed command actions for AI (empty = all non-blocked) |
| `blocked_actions` | `string[]` | `["aeval", "eval", ...]` | Commands blocked from AI use (security) |
| `owner_only` | `boolean` | `true` | Restrict AI to bot owner only |

```json
{
  "agentic_ai": {
    "enabled": true,
    "provider": "openai",
    "model": "gpt-4o-mini",
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

```json
{
  "features": {
    "anti_delete": true,
    "anti_link": false,
    "welcome": true,
    "notes": true,
    "filters": true,
    "blacklist": true,
    "warnings": true
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
| `action` | `string` | `warn` | Action on link detection: `warn`, `kick`, `ban` |
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
| `action` | `string` | `kick` | Action at limit: `warn`, `kick`, `ban` |

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
| `max_file_size_mb` | `number` | `180` | Maximum file size in MB for downloaded media |

::: tip
WhatsApp supports up to **180 MB** for media (images, videos, audio) and up to **2 GB** for documents. The default of 180 MB matches WhatsApp's media limit.
:::

```json
{
  "downloader": {
    "max_file_size_mb": 180
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

## Environment Variables

Store sensitive values in `.env` (never commit this file):

```bash
AI_API_KEY=your_api_key_here
```

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
    "model": "gpt-4o-mini",
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
    "warnings": true
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
    "max_file_size_mb": 180
  },
  "disabled_commands": []
}
```
