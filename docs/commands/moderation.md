# Moderation Commands

Tools for keeping groups safe and well-moderated.

## /warn

Warn a user. Reaching the warning limit triggers an automatic action.

```
/warn @user [reason]
```

**Example:**
```
/warn @user Spamming links
```

## /warns

Check a user's warning count and history.

```
/warns @user
```

## /resetwarns

Clear all warnings for a user.

```
/resetwarns @user
```

## /warnconfig

Configure warning behavior.

```
/warnconfig limit <number>    # Max warnings before action (default: 3)
/warnconfig action <action>   # Action on limit: kick, mute (default: kick)
```

## /blacklist

Add a word to the group blacklist. Messages containing blacklisted words are auto-deleted.

```
/blacklist <word>
```

## /unblacklist

Remove a word from the blacklist.

```
/unblacklist <word>
```

## /antilink

Configure anti-link protection. Automatically detects and handles links in group messages.

```
/antilink on                           # Enable anti-link
/antilink off                          # Disable anti-link
/antilink action <warn|delete|kick>    # Set action
/antilink whitelist add <domain>       # Whitelist a domain
/antilink whitelist remove <domain>    # Remove from whitelist
/antilink whitelist                    # List whitelisted domains
```

**Example:**
```
/antilink on
/antilink action warn
/antilink whitelist add youtube.com
/antilink whitelist add github.com
```

::: info
Admins are exempt from anti-link detection.
:::

## /antidelete

Reveal deleted messages by re-sending them. Owner only.

```
/antidelete on                  # Enable for current group
/antidelete off                 # Disable
/antidelete forward me          # Forward deleted messages to your DM
/antidelete forward here        # Re-send in the same group
```
