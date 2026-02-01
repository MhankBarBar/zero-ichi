"""
Setname command - Change group name.
"""

from core.command import Command, CommandContext
from core.i18n import t_error, t_info, t_success, t_warning


class SetnameCommand(Command):
    name = "setname"
    aliases = ["gname", "groupname"]
    description = "Change the group name"
    usage = "setname <new name>"
    group_only = True
    admin_only = True
    bot_admin_required = True

    async def execute(self, ctx: CommandContext) -> None:
        """Change group name."""
        if not ctx.raw_args:
            await ctx.client.reply(ctx.message, t_info("setname.usage", prefix=ctx.prefix))
            return

        new_name = ctx.raw_args.strip()
        if len(new_name) > 25:
            await ctx.client.reply(ctx.message, t_warning("setname.too_long"))
            return

        group_jid = ctx.message.chat_jid

        try:
            await ctx.client._client.set_group_name(ctx.client.to_jid(group_jid), new_name)
            await ctx.client.reply(ctx.message, t_success("setname.updated", name=new_name))
        except Exception as e:
            await ctx.client.reply(ctx.message, t_error("setname.failed", error=str(e)))
