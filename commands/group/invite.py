"""
Invite command - Get group invite link.
"""

from core.command import Command, CommandContext
from core.i18n import t_error, t_success, t_warning
from core.permissions import check_bot_admin


class InviteCommand(Command):
    name = "invite"
    description = "Get group invite link"
    usage = "/invite"
    group_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Get the group invite link."""
        group_jid = ctx.message.chat_jid

        if not await check_bot_admin(ctx.client, group_jid):
            await ctx.client.reply(ctx.message, t_warning("errors.bot_admin_required"))
            return

        try:
            result = await ctx.client._client.get_group_invite_link(
                ctx.client.to_jid(group_jid),
                False,
            )
            await ctx.client.reply(ctx.message, t_success("invite.link", link=result))
        except Exception as e:
            await ctx.client.reply(ctx.message, t_error("invite.failed", error=str(e)))
