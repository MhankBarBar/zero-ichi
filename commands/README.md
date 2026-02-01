# Commands Directory

Place your bot commands here organized by category subdirectories.

## Directory Structure

```
commands/
  admin/           # Admin/moderation commands (kick, ban, promote, demote)
  content/         # Notes, filters, media commands
  general/         # Help, ping, menu
  group/           # Group management (invite, setname, tagall)
  moderation/      # Warn, blacklist, antilink
  owner/           # Owner-only commands (config, eval)
  utility/         # Utility commands (remind, etc.)
```

## Creating a Command

```python
from core.command import Command, CommandContext
from core import symbols as sym

class MyCommand(Command):
    name = "mycommand"
    aliases = ["mc", "mycmd"]     # Optional shortcuts
    description = "My custom command"
    usage = "/mycommand <arg>"
    category = "utility"          # For help grouping
    examples = ["/mycommand test"]

    # Restrictions
    group_only = False            # Only works in groups
    private_only = False          # Only works in DMs
    owner_only = False            # Only bot owner can use

    async def execute(self, ctx: CommandContext) -> None:
        # ctx.client - BotClient for sending messages
        # ctx.message - MessageHelper with message data
        # ctx.args - List of arguments
        # ctx.raw_args - Raw argument string
        # ctx.prefix - The prefix used to invoke the command

        await ctx.client.reply(ctx.message, f"{sym.SUCCESS} Hello!")
```

## Command Properties

| Property | Type | Description |
|----------|------|-------------|
| name | str | Command name (required) |
| aliases | list | Alternative names |
| description | str | Short description for help |
| usage | str | Usage example |
| category | str | Category for help grouping |
| examples | list | Usage examples |
| group_only | bool | Only works in groups |
| private_only | bool | Only works in DMs |
| owner_only | bool | Only bot owner can use |

## CommandContext

| Property | Type | Description |
|----------|------|-------------|
| client | BotClient | For sending messages |
| message | MessageHelper | Message data and helpers |
| args | list[str] | Parsed arguments |
| raw_args | str | Raw argument string |
| command_name | str | The invoked command name |
| prefix | str | The prefix used to invoke |

## Symbols

Use symbols from `core.symbols` for consistent message styling:

```python
from core import symbols as sym

# Available symbols
sym.SUCCESS   # Success indicator
sym.ERROR     # Error indicator
sym.WARNING   # Warning indicator
sym.INFO      # Info indicator
sym.ON        # Enabled state
sym.OFF       # Disabled state
sym.BULLET    # List bullet
sym.HEADER_L  # Header left bracket
sym.HEADER_R  # Header right bracket
```

## Features

- Auto-discovered from this directory and subdirectories
- Hot-reload support (changes picked up on restart)
- Permission checks (admin, owner)
- Consistent message styling with symbols
