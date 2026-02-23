"""
Save command - Save a note for the group (text or media).
"""

from config.settings import features
from core.command import Command, CommandContext
from core.i18n import t_error, t_success
from core.media import get_media_caption, save_media_to_disk
from core.storage import GroupData


class SaveCommand(Command):
    name = "save"
    description = "Save a note for the group (text or media)"
    usage = "save <name> [content] or reply to a message with save <name>"
    group_only = True
    admin_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Save a note (text or media)."""
        if not features.notes:
            await ctx.client.reply(ctx.message, t_error("common.feature_disabled"))
            return

        group_jid = ctx.message.chat_jid

        if not ctx.args:
            await ctx.client.reply(ctx.message, t_error("notes.usage_save", prefix=ctx.prefix))
            return

        note_name = ctx.args[0].lower()
        note_content = " ".join(ctx.args[1:]) if len(ctx.args) > 1 else ""

        msg_obj, media_type = ctx.message.get_media_message(ctx.client)

        note_type = "text"
        media_path = None

        if msg_obj and media_type:
            note_type = media_type

            if not note_content:
                note_content = get_media_caption(msg_obj, media_type)

            media_path = await save_media_to_disk(
                ctx.client, msg_obj, media_type, group_jid, note_name
            )

        else:
            if not note_content:
                quoted = ctx.message.quoted_message
                if quoted and quoted.get("text"):
                    note_content = quoted["text"]
                else:
                    await ctx.client.reply(ctx.message, t_error("notes.no_content"))
                    return

        if note_type != "text" and not media_path:
            return

        data = GroupData(group_jid)
        notes = data.notes
        notes[note_name] = {
            "type": note_type,
            "content": note_content,
            "media_path": media_path,
        }
        data.save_notes(notes)

        await ctx.client.reply(
            ctx.message, t_success("notes.saved", name=note_name, type=note_type)
        )
