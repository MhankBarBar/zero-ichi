"""
Unblacklist command - Remove a word from the blacklist.
"""

from core.command import Command, CommandContext
from core.i18n import t_error, t_success
from core.storage import GroupData


class UnblacklistCommand(Command):
    name = "unblacklist"
    description = "Remove a word from the blacklist"
    usage = "/unblacklist <word>"
    aliases = ["unbl", "rmbl", "rmblacklist"]
    group_only = True
    admin_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Remove word from blacklist."""
        if not ctx.args:
            await ctx.client.reply(ctx.message, t_error("errors.no_target"))
            return

        word = ctx.args[0].lower()
        group_jid = ctx.message.chat_jid

        data = GroupData(group_jid)
        words = data.blacklist

        if word not in words:
            await ctx.client.reply(ctx.message, t_error("blacklist.not_found", word=word))
            return

        words.remove(word)
        data.save_blacklist(words)
        await ctx.client.reply(ctx.message, t_success("blacklist.removed", word=word))
