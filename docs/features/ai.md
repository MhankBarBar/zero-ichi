# Agentic AI

Zero Ichi includes an AI assistant that can understand messages and execute bot commands on your behalf using tool calling.

## How It Works

The AI system uses [Pydantic AI](https://ai.pydantic.dev/) to connect to language models. It can:

- **Understand context** — knows the chat, sender, group info, and message history
- **Execute actions** — send messages, mention users, reply to messages
- **Use tools** — kick, mute, promote/demote members in groups
- **Remember** — maintains conversation memory per chat
- **Follow skills** — custom instructions you define

## Setup

### 1. Set API Key

Add your API key to `.env`:

```bash
AI_API_KEY=sk-your-api-key-here
```

### 2. Enable AI

Via WhatsApp:

```
/config ai on
```

Or in `config.json`:

```json
{
  "agentic_ai": {
    "enabled": true,
    "provider": "openai",
    "model": "gpt-5-mini"
  }
}
```

## Trigger Modes

Control when the AI responds:

| Mode | Command | Description |
|------|---------|-------------|
| **mention** | `/config ai mode mention` | Responds when @mentioned |
| **reply** | `/config ai mode reply` | Responds when replying to the bot |
| **always** | `/config ai mode always` | Responds to every message |

::: tip Recommended
Use `mention` or `reply` mode to avoid the AI responding to every message.
:::

## Providers

The bot supports multiple AI providers:

| Provider | Config Value | Example Models |
|----------|-------------|---------------|
| OpenAI | `openai` | `gpt-5-mini`, `gpt-5` |
| Google | `google` | `gemini-2.0-flash` |
| Groq | `groq` | `llama-3.3-70b` |

Change provider:

```
/config ai provider google
/config ai model gemini-2.0-flash
```

## AI Skills

Skills are custom instructions that the AI follows. They let you customize the AI's behavior without changing code.

### Adding a Skill

```
/addskill <name>
<instructions>
```

**Example:**

```
/addskill translator
When someone asks you to translate, translate the text
to the requested language. If no language is specified,
translate to English.
```

### Managing Skills

```
/skills              # List all skills
/delskill <name>     # Remove a skill
```

## Security

### Blocked Actions

By default, dangerous commands are blocked from AI execution:

```json
{
  "agentic_ai": {
    "blocked_actions": ["eval", "aeval", "addcommand", "delcommand"]
  }
}
```

### Owner Only Mode

Restrict AI to only respond to the bot owner:

```json
{
  "agentic_ai": {
    "owner_only": true
  }
}
```
