"""
Revoke command - Revoke and get new group invite link.
"""

from core.command import Command, CommandContext
from core.i18n import t_error, t_success


class RevokeCommand(Command):
    name = "revoke"
    description = "Revoke and get new invite link"
    usage = "revoke"
    group_only = True
    admin_only = True
    bot_admin_required = True

    async def execute(self, ctx: CommandContext) -> None:
        """Revoke current invite link and get a new one."""
        group_jid = ctx.message.chat_jid

        try:
            result = await ctx.client._client.get_group_invite_link(
                ctx.client.to_jid(group_jid),
                True,
            )
            await ctx.client.reply(ctx.message, t_success("revoke.success", link=result))
        except Exception as e:
            await ctx.client.reply(ctx.message, t_error("revoke.failed", error=str(e)))
