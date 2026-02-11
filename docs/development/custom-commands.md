# Custom Commands

There are two ways to add custom commands to Zero Ichi.

## Method 1: Create a File

Create a Python file in the appropriate `commands/<category>/` directory. The bot auto-discovers it on startup (or hot-reloads if `auto_reload` is enabled).

### Basic Command

```python
from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t


class HelloCommand(Command):
    name = "hello"
    description = "Say hello"
    usage = "hello"

    async def execute(self, ctx: CommandContext) -> None:
        await ctx.client.reply(ctx.message, f"{sym.WAVE} Hello, {ctx.message.sender_name}!")
```

### Command with Arguments

```python
class SayCommand(Command):
    name = "say"
    description = "Repeat your message"
    usage = "say <text>"

    async def execute(self, ctx: CommandContext) -> None:
        if not ctx.raw_args:
            await ctx.client.reply(ctx.message, "Please provide text to say!")
            return
        await ctx.client.reply(ctx.message, ctx.raw_args)
```

### Group-Only Admin Command

```python
class AnnounceCommand(Command):
    name = "announce"
    description = "Make an announcement"
    usage = "announce <message>"
    group_only = True
    admin_only = True

    async def execute(self, ctx: CommandContext) -> None:
        if not ctx.raw_args:
            return
        await ctx.client.reply(ctx.message, f"📢 *Announcement*\n\n{ctx.raw_args}")
```

## Method 2: Dynamic Command (Owner Only)

Create commands on the fly via WhatsApp with `/addcommand`:

```
/addcommand
from core.command import Command, CommandContext

class GreetCommand(Command):
    name = "greet"
    description = "Greet someone"
    usage = "greet"

    async def execute(self, ctx):
        await ctx.client.reply(ctx.message, "Greetings!")
```

Manage dynamic commands:

```
/listdynamic          # List all dynamic commands
/delcommand greet     # Delete a dynamic command
```

## Command Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `name` | `str` | _(required)_ | Command name |
| `aliases` | `list[str]` | `[]` | Alternative names |
| `description` | `str` | `""` | Help text |
| `usage` | `str` | `""` | Usage example |
| `group_only` | `bool` | `False` | Only in groups |
| `private_only` | `bool` | `False` | Only in DMs |
| `admin_only` | `bool` | `False` | Requires admin |
| `owner_only` | `bool` | `False` | Requires owner |
| `bot_admin_required` | `bool` | `False` | Bot must be admin |
| `cooldown` | `int` | `0` | Cooldown in seconds |

## CommandContext

The `ctx` object passed to `execute()` provides:

| Property | Type | Description |
|----------|------|-------------|
| `ctx.message` | `MessageHelper` | The incoming message |
| `ctx.client` | `BotClient` | The bot client for sending messages |
| `ctx.args` | `list[str]` | Parsed arguments |
| `ctx.raw_args` | `str` | Raw argument string |
| `ctx.command_name` | `str` | Command name used |
| `ctx.prefix` | `str` | Prefix used to invoke |

## Adding i18n Support

To make your command translatable:

1. Add keys to `locales/en.json` and `locales/id.json`
2. Use `t()` in your command

```python
from core.i18n import t

# In your execute method:
await ctx.client.reply(ctx.message, t("mycommand.greeting"))
```

See [Internationalization](/features/i18n) for more details.
