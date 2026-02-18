"""
Leave command - Make the bot leave a group.
"""

from core.command import Command, CommandContext
from core.i18n import t_error, t_success


class LeaveCommand(Command):
    name = "leave"
    description = "Make the bot leave a group"
    usage = "leave [group_jid]"
    category = "owner"
    cooldown = 5
    examples = [
        "leave",
        "leave 123456789@g.us",
    ]

    async def execute(self, ctx: CommandContext) -> None:
        """Handle leave command.

        - Owner: can leave current group or target a specific group by JID.
        - Group admin: can make the bot leave the current group.
        """
        from core.runtime_config import runtime_config

        is_owner = await runtime_config.is_owner_async(ctx.message.sender_jid)
        is_group = ctx.message.is_group

        args = ctx.args

        if is_owner and args:
            target_jid = args[0]
            if not target_jid.endswith("@g.us"):
                target_jid = f"{target_jid}@g.us"
            try:
                await ctx.client.leave_group(target_jid)
                await ctx.client.reply(ctx.message, t_success("leave.left", group=target_jid))
            except Exception as e:
                await ctx.client.reply(ctx.message, t_error("leave.failed", error=str(e)))
            return

        if not is_group:
            await ctx.client.reply(ctx.message, t_error("leave.not_group"))
            return

        if not is_owner:
            from core.permissions import check_admin_permission

            is_admin = await check_admin_permission(
                ctx.client, ctx.message.chat_jid, ctx.message.sender_jid
            )
            if not is_admin:
                await ctx.client.reply(ctx.message, t_error("leave.no_permission"))
                return

        group_jid = ctx.message.chat_jid
        try:
            await ctx.client.reply(ctx.message, t_success("leave.leaving"))
            await ctx.client.leave_group(group_jid)
        except Exception as e:
            await ctx.client.reply(ctx.message, t_error("leave.failed", error=str(e)))
