"""
Lock/Unlock commands - Toggle group message settings.
"""

from neonize.utils.jid import build_jid

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t


class LockCommand(Command):
    name = "lock"
    description = "Lock group - only admins can send messages"
    usage = "lock"
    category = "group"
    group_only = True
    admin_only = True
    bot_admin_required = True

    async def execute(self, ctx: CommandContext) -> None:
        """Lock the group."""
        await _toggle_group_lock(ctx, True)


class UnlockCommand(Command):
    name = "unlock"
    description = "Unlock group - everyone can send messages"
    usage = "unlock"
    category = "group"
    group_only = True
    admin_only = True
    bot_admin_required = True

    async def execute(self, ctx: CommandContext) -> None:
        """Unlock the group."""
        await _toggle_group_lock(ctx, False)


async def _toggle_group_lock(ctx: CommandContext, locked: bool) -> None:
    """Helper to toggle group lock state."""
    try:
        group_jid = build_jid(ctx.message.chat_jid)
        await ctx.client._client.set_group_announce(group_jid, locked)

        key = "lock.locked" if locked else "lock.unlocked"
        await ctx.client.reply(ctx.message, f"{sym.SUCCESS} {t(key)}")
    except Exception as e:
        fail_key = "lock.lock_failed" if locked else "lock.unlock_failed"
        await ctx.client.reply(ctx.message, f"{sym.ERROR} {t(fail_key, error=e)}")
