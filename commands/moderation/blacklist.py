"""
Blacklist command - Add a word to the blacklist.
"""

from config.settings import features
from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t, t_error, t_info, t_success
from core.storage import GroupData


class BlacklistCommand(Command):
    name = "blacklist"
    description = "Add a word to the blacklist"
    usage = "/blacklist <word>"
    group_only = True
    admin_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Add word to blacklist."""
        if not features.blacklist:
            await ctx.client.reply(ctx.message, t_error("common.feature_disabled"))
            return

        group_jid = ctx.message.chat_jid

        if not ctx.args:
            data = GroupData(group_jid)
            words = data.blacklist
            if not words:
                await ctx.client.reply(ctx.message, t_info("blacklist.no_words"))
                return
            await ctx.client.reply(
                ctx.message, sym.section(t("headers.list"), [f"`{w}`" for w in words])
            )
            return

        word = ctx.args[0].lower()
        data = GroupData(group_jid)
        words = data.blacklist

        if word in words:
            await ctx.client.reply(ctx.message, t_error("blacklist.exists", word=word))
            return

        words.append(word)
        data.save_blacklist(words)
        await ctx.client.reply(ctx.message, t_success("blacklist.added", word=word))
