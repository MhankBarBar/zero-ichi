# Utility Commands

Helpful tools and productivity commands.

## /afk

Set yourself as Away From Keyboard. When someone mentions you, the bot notifies them that you're AFK.

```
/afk              # Set AFK with no reason
/afk <reason>     # Set AFK with a reason
```

**Example:**
```
/afk sleeping 💤
```

When you send any message, your AFK status is automatically cleared with a "Welcome back!" notification showing how long you were away.

## /remind

Set reminders that fire at a specific time.

```
/remind <duration> <message>
```

**Duration formats:**

| Format | Example | Description |
|--------|---------|-------------|
| `Xs` | `30s` | Seconds |
| `Xm` | `5m` | Minutes |
| `Xh` | `2h` | Hours |
| `Xd` | `1d` | Days |

**Examples:**
```
/remind 30m Check the oven
/remind 2h Call the client
/remind 1d Submit the report
```

## /echo

Repeat your message back.

```
/echo <text>
```

## /lang

Set the bot's language for the current chat.

```
/lang              # Show current language
/lang en           # Set to English
/lang id           # Set to Indonesian
```

See [Internationalization](/features/i18n) for more details.

## /time

Show the current time.

```
/time
```

## /schedule

Manage scheduled messages and reminders.

```
/schedule <cron|every <interval>> <message>
```

**Features:**
- **Cron**: Standard cron syntax (minute hour day month day-of-week)
- **Interval**: "Every X time" (e.g. `every 1h`)
- **Management**: List, cancel, toggle tasks

**Examples:**
```
/schedule 0 8 * * * Good morning!    # Daily at 8:00 AM
/schedule every 1h Drink water!      # Every hour
/schedule list                       # List active tasks
/schedule cancel <id>                # Cancel a task
/schedule toggle <id>                # Pause/Resume a task
/schedule info <id>                  # View task details
```

## /digest

Configure periodic group summaries (daily/weekly), or send one immediately.

```
/digest status
/digest now
/digest off
/digest on daily <HH:MM>
/digest on weekly <day> <HH:MM>
```

**Examples:**

```
/digest on daily 20:00
/digest on weekly sun 20:00
/digest now
```
