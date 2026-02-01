"""
Notes command - List all saved notes.
"""

from config.settings import features
from core.command import Command, CommandContext
from core.i18n import t, t_error
from core.storage import GroupData


class NotesCommand(Command):
    name = "notes"
    description = "List all saved notes"
    usage = "/notes"
    group_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """List all notes."""
        if not features.notes:
            await ctx.client.reply(ctx.message, t_error("common.feature_disabled"))
            return

        group_jid = ctx.message.chat_jid
        data = GroupData(group_jid)
        notes = data.notes

        if not notes:
            await ctx.client.reply(ctx.message, t("notes.no_notes"))
            return

        lines = [f"{t('notes.list_title')}:"]
        for name in sorted(notes.keys()):
            lines.append(f"  - #{name}")

        await ctx.client.reply(ctx.message, "\n".join(lines))
