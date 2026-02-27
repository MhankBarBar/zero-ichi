"""
Tagall command - Mention all group members.
"""

from core.command import Command, CommandContext
from core.errors import report_error
from core.i18n import t, t_error


class TagallCommand(Command):
    name = "tagall"
    aliases = ["all", "everyone"]
    description = "Mention all group members"
    usage = "tagall [message]"
    group_only = True
    admin_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Mention all group members."""
        group_jid = ctx.message.chat_jid

        try:
            group_info = await ctx.client._client.get_group_info(ctx.client.to_jid(group_jid))

            if not group_info.Participants:
                await ctx.client.reply(ctx.message, t_error("tagall.no_members"))
                return

            mention_text_parts = []
            for participant in group_info.Participants:
                user = participant.JID.User
                mention_text_parts.append(f"@{user}")

            custom_msg = ctx.raw_args.strip() if ctx.raw_args else t("tagall.attention")
            message = f"*{custom_msg}*\n\n" + " ".join(mention_text_parts)

            await ctx.client.send(group_jid, message, mentions_are_lids=True)
        except Exception as e:
            await report_error(ctx.client, ctx.message, self.name, e)
