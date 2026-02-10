"""
AFK command - Set yourself as away from keyboard.
"""

from core import symbols as sym
from core.command import Command, CommandContext
from core.handlers.afk import set_afk
from core.i18n import t


class AfkCommand(Command):
    name = "afk"
    aliases = ["brb"]
    description = "Set yourself as AFK"
    usage = "/afk [reason]"
    category = "utility"
    examples = ["/afk", "/afk Sleeping", "/afk At work, be back later"]

    async def execute(self, ctx: CommandContext) -> None:
        """Set user as AFK."""
        reason = ctx.raw_args.strip() if ctx.raw_args else ""
        set_afk(ctx.message.sender_jid, reason)

        if reason:
            await ctx.client.reply(
                ctx.message, f"{sym.PENDING} {t('afk.set_reason', note=sym.NOTE, reason=reason)}"
            )
        else:
            await ctx.client.reply(ctx.message, f"{sym.PENDING} {t('afk.set')}")
