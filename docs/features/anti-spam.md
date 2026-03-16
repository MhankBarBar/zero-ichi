# Anti-Spam

Automatic flood protection that detects and acts on users sending messages too quickly in groups.

## Overview

The anti-spam system uses a sliding time window to track message frequency per user. When a user exceeds the configured threshold, the bot takes an automatic action (warn, mute, or kick).

## Enable / Disable

Anti-spam is controlled by the `anti_spam` feature flag, which is **off by default**.

Toggle it with the existing config command:

```
/config toggle anti_spam
```

## Configuration

All settings live in the `anti_spam` section of `config.json`:

```jsonc
{
  "anti_spam": {
    "max_messages": 5,        // Messages allowed per window
    "window_seconds": 10,     // Sliding window duration
    "action": "warn",         // "warn", "mute", or "kick"
    "whitelist_admins": true  // Exempt group admins
  }
}
```

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `max_messages` | integer | `5` | Maximum messages a user can send within the time window before action triggers |
| `window_seconds` | number | `10` | Length of the sliding time window in seconds |
| `action` | string | `"warn"` | Action to take: `warn` (send warning), `mute` (mute + delete), `kick` (remove from group) |
| `whitelist_admins` | boolean | `true` | When enabled, group admins are exempt from spam detection |

You can also edit these values with:

```
/config set anti_spam.max_messages 8
/config set anti_spam.window_seconds 15
/config set anti_spam.action mute
```

## How It Works

1. Every incoming group message records a timestamp for the sender
2. Timestamps older than `window_seconds` are discarded
3. If the number of timestamps exceeds `max_messages`, the configured action fires
4. After an action triggers, the sender's window is reset to avoid repeated triggers

## Actions

| Action | Behavior |
|--------|----------|
| `warn` | Sends a public warning message mentioning the user |
| `mute` | Adds user to the mute list, deletes the spam message, and notifies the group |
| `kick` | Deletes the message and removes the user from the group |

::: tip
Start with `warn` to see how it affects your group before escalating to `mute` or `kick`.
:::

## Pipeline Position

Anti-spam runs in the middleware pipeline after **mute** and before **features**, so muted users are already filtered out before spam checking occurs.
