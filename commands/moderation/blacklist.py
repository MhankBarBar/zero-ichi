"""
Blacklist command - Manage blacklisted words.
"""

from config.settings import features
from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t, t_error, t_info, t_success
from core.storage import GroupData


class BlacklistCommand(Command):
    name = "blacklist"
    description = "Manage blacklisted words"
    usage = "blacklist [add|remove|list] <word>"
    aliases = ["bl"]
    group_only = True
    admin_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Manage blacklist."""
        if not features.blacklist:
            await ctx.client.reply(ctx.message, t_error("common.feature_disabled"))
            return

        group_jid = ctx.message.chat_jid
        data = GroupData(group_jid)
        words = data.blacklist

        if not ctx.args or ctx.args[0].lower() == "list":
            if not words:
                await ctx.client.reply(ctx.message, t_info("blacklist.no_words"))
                return

            await ctx.client.reply(
                ctx.message, sym.section(t("headers.list"), [f"`{w}`" for w in words])
            )
            return

        action = ctx.args[0].lower()

        if action in ("add", "remove", "rm", "delete", "del"):
            if len(ctx.args) < 2:
                await ctx.client.reply(ctx.message, t_error("blacklist.no_word"))
                return
            word = ctx.args[1].lower()
        else:
            action = "add"
            word = ctx.args[0].lower()

        if action == "add":
            if word in words:
                await ctx.client.reply(ctx.message, t_error("blacklist.exists", word=word))
                return

            words.append(word)
            data.save_blacklist(words)
            await ctx.client.reply(ctx.message, t_success("blacklist.added", word=word))

        elif action in ("remove", "rm", "delete", "del"):
            if word not in words:
                await ctx.client.reply(ctx.message, t_error("blacklist.not_found", word=word))
                return

            words.remove(word)
            data.save_blacklist(words)
            await ctx.client.reply(ctx.message, t_success("blacklist.removed", word=word))
