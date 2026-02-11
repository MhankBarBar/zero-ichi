# Admin Commands

Group administration commands. Requires **admin** permissions in the group.

::: warning Permissions
These commands require the sender to be a group admin. Some also require the **bot** to be a group admin.
:::

## /kick

Kick a user from the group.

```
/kick @user
```

Mention the user or reply to their message. The bot must be a group admin.

**Aliases:** `remove`

## /add

Add a user to the group by phone number.

```
/add <number>
```

**Example:**
```
/add 6281234567890
```

## /mute

Mute a user in the group (prevents sending messages).

```
/mute @user
```

**Aliases:** `silence`

## /unmute

Unmute a previously muted user.

```
/unmute @user
```

## /promote

Promote a user to group admin.

```
/promote @user
```

## /demote

Demote a user from group admin.

```
/demote @user
```

## /admins

List all admins in the group.

```
/admins
```

## /delete

Delete a message. Reply to the message you want to delete.

```
/delete
```

**Aliases:** `del`, `d`

::: tip
Reply to the target message and send `/del` — both the target and your command message will be deleted.
:::
