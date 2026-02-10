"""
Lock/Unlock commands - Toggle group message settings.
"""

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t


class LockCommand(Command):
    name = "lock"
    description = "Lock group - only admins can send messages"
    usage = "/lock"
    category = "group"
    group_only = True
    admin_only = True
    bot_admin_required = True

    async def execute(self, ctx: CommandContext) -> None:
        """Lock the group (only admins can send)."""
        try:
            from neonize.utils.jid import build_jid

            group_jid = build_jid(ctx.message.chat_jid)
            await ctx.client._client.set_group_announce(group_jid, True)
            await ctx.client.reply(ctx.message, f"{sym.SUCCESS} {t('lock.locked')}")
        except Exception as e:
            await ctx.client.reply(ctx.message, f"{sym.ERROR} {t('lock.lock_failed', error=e)}")


class UnlockCommand(Command):
    name = "unlock"
    description = "Unlock group - everyone can send messages"
    usage = "/unlock"
    category = "group"
    group_only = True
    admin_only = True
    bot_admin_required = True

    async def execute(self, ctx: CommandContext) -> None:
        """Unlock the group (everyone can send)."""
        try:
            from neonize.utils.jid import build_jid

            group_jid = build_jid(ctx.message.chat_jid)
            await ctx.client._client.set_group_announce(group_jid, False)
            await ctx.client.reply(ctx.message, f"{sym.SUCCESS} {t('lock.unlocked')}")
        except Exception as e:
            await ctx.client.reply(ctx.message, f"{sym.ERROR} {t('lock.unlock_failed', error=e)}")
