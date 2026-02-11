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
