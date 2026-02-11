# Group Commands

Group management and interaction commands.

## /invite

Get the group invite link.

```
/invite
```

## /revoke

Revoke the current group invite link and generate a new one.

```
/revoke
```

## /groupinfo

Show detailed information about the group.

```
/groupinfo
```

## /setname

Change the group name.

```
/setname <new name>
```

## /setdesc

Change the group description.

```
/setdesc <new description>
```

## /tagall

Mention all members in the group.

```
/tagall [message]
```

## /poll

Create a poll in the group.

```
/poll "Question" "Option 1" "Option 2" "Option 3"
```

::: tip
- Wrap the question and each option in double quotes
- Minimum 2 options, maximum 12
:::

**Example:**
```
/poll "Best programming language?" "Python" "JavaScript" "Rust" "Go"
```

## /rules

Manage group rules.

```
/rules              # View current rules
/rules set <text>   # Set group rules
/rules clear        # Clear group rules
```

## /lock

Lock the group — only admins can send messages.

```
/lock
```

## /unlock

Unlock the group — all members can send messages.

```
/unlock
```

## /welcome

Configure welcome messages for new members.

```
/welcome on                    # Enable welcome messages
/welcome off                   # Disable welcome messages
/welcome set <message>         # Set custom welcome message
/welcome                       # Show current settings
```

**Placeholders:**

| Placeholder | Description |
|-------------|-------------|
| `{user}` | New member's name |
| `{group}` | Group name |
| `{members}` | Member count |

## /goodbye

Configure goodbye messages for leaving members.

```
/goodbye on                    # Enable goodbye messages
/goodbye off                   # Disable goodbye messages
/goodbye set <message>         # Set custom goodbye message
/goodbye                       # Show current settings
```

Same placeholders as `/welcome`.
