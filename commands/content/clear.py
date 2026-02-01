"""
Clear command - Delete a saved note.
"""

from core.command import Command, CommandContext
from core.i18n import t_error, t_success
from core.storage import GroupData


class ClearCommand(Command):
    name = "clear"
    description = "Delete a saved note"
    usage = "/clear <name>"
    group_only = True
    admin_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Delete a note."""
        if not ctx.args:
            await ctx.client.reply(ctx.message, t_error("errors.no_target"))
            return

        note_name = ctx.args[0].lower().lstrip("#")
        group_jid = ctx.message.chat_jid

        data = GroupData(group_jid)
        notes = data.notes

        if note_name not in notes:
            await ctx.client.reply(ctx.message, t_error("notes.not_found", name=note_name))
            return

        del notes[note_name]
        data.save_notes(notes)
        await ctx.client.reply(ctx.message, t_success("notes.deleted", name=note_name))
