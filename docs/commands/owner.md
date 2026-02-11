# Owner Commands

Commands restricted to the bot owner. Set yourself as owner with `/config owner me`.

::: danger Owner Only
These commands have full system access. Only the configured bot owner can use them.
:::

## /config

Manage bot configuration live from WhatsApp.

```
/config                      # Show current config overview
/config owner me             # Set yourself as owner
/config prefix <prefix>      # Change command prefix
/config ai                   # Show AI status
/config ai on                # Enable Agentic AI
/config ai off               # Disable Agentic AI
/config ai mode <mode>       # Set AI trigger mode
/config ai model <model>     # Change AI model
/config ai provider <name>   # Change AI provider
```

## /eval

Execute Python code directly.

```
/eval <code>
```

**Example:**
```
/eval 2 + 2
```

## /aeval

Execute async Python code.

```
/aeval <code>
```

**Example:**
```
/aeval await bot.reply(msg, "Hello from eval!")
```

::: warning
`/eval` and `/aeval` have full access to the bot's internals. Use with caution.
:::

## /addcommand

Create a new command dynamically via WhatsApp — no file needed.

```
/addcommand
<python code defining a Command class>
```

**Example:**
```
/addcommand
from core.command import Command, CommandContext

class GreetCommand(Command):
    name = "greet"
    description = "Greet someone"
    usage = "/greet"

    async def execute(self, ctx):
        await ctx.client.reply(ctx.message, "Greetings!")
```

## /delcommand

Delete a dynamically created command.

```
/delcommand <name>
```

## /listdynamic

List all dynamically created commands.

```
/listdynamic
```

## /addskill

Add an AI skill — custom instructions that the AI follows.

```
/addskill <name>
<instructions>
```

**Example:**
```
/addskill translator
Always translate messages to English when asked.
```

## /delskill

Remove an AI skill.

```
/delskill <name>
```

## /skills

List all loaded AI skills.

```
/skills
```
