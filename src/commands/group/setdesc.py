"""
Setdesc command - Change group description.
"""

from core.command import Command, CommandContext
from core.i18n import t_error, t_info, t_success


class SetdescCommand(Command):
    name = "setdesc"
    aliases = ["gdesc", "groupdesc", "description"]
    description = "Change the group description"
    usage = "setdesc <new description>"
    group_only = True
    admin_only = True
    bot_admin_required = True

    async def execute(self, ctx: CommandContext) -> None:
        """Change group description."""
        if not ctx.raw_args:
            await ctx.client.reply(ctx.message, t_info("setdesc.usage"))
            return

        new_desc = ctx.raw_args.strip()
        group_jid = ctx.message.chat_jid

        try:
            await ctx.client._client.set_group_topic(ctx.client.to_jid(group_jid), new_desc)
            await ctx.client.reply(ctx.message, t_success("setdesc.updated"))
        except Exception as e:
            await ctx.client.reply(ctx.message, t_error("setdesc.failed", error=str(e)))
