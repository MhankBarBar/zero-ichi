# Content Commands

Save, retrieve, and manage content like notes, filters, and stickers.

## /save

Save a note with text or media.

```
/save <name> <text>
```

You can also reply to a message (including images/videos) to save it:

```
/save meme
```

## /notes

List all saved notes in the group.

```
/notes
```

## Retrieving Notes

Use `#notename` anywhere in a message to retrieve a saved note:

```
#greeting
```

## /clear

Delete a saved note.

```
/clear <name>
```

## /filter

Create an auto-reply trigger. When the trigger word is detected in a message, the bot automatically responds.

```
/filter <trigger> <response>
```

**Example:**
```
/filter hello Hey there! Welcome to the group!
```

## /filters

List all active filters in the group.

```
/filters
```

## /stop

Remove a filter trigger.

```
/stop <trigger>
```

## /sticker

Convert an image to a WhatsApp sticker.

```
/sticker
```

Reply to an image or send an image with the `/sticker` caption.
