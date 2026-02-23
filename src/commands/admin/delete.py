"""
Delete command - Delete messages replied to.
"""

from core.command import Command, CommandContext
from core.i18n import t_error, t_info


class DeleteCommand(Command):
    """Delete a message by replying to it."""

    name = "delete"
    aliases = ["del", "d"]
    description = "Delete a message (reply to the message to delete)"
    usage = "delete or del (reply to message)"
    group_only = True
    admin_only = True
    bot_admin_required = True

    async def execute(self, ctx: CommandContext) -> None:
        """Delete the replied message."""
        quoted = ctx.message.quoted_message
        if not quoted:
            await ctx.client.reply(ctx.message, t_info("delete.reply_required"))
            return

        try:
            message_id = quoted.get("id", "")
            if not message_id:
                await ctx.client.reply(ctx.message, t_error("delete.no_id"))
                return

            chat_jid = ctx.client.to_jid(ctx.message.chat_jid)
            quoted_sender = quoted.get("sender", "")
            sender_jid = ctx.client.to_jid(quoted_sender) if quoted_sender else chat_jid

            await ctx.client._client.revoke_message(chat_jid, sender_jid, message_id)

            await ctx.client._client.revoke_message(
                chat_jid,
                ctx.client.to_jid(ctx.message.sender_jid),
                ctx.message.message_id,
            )

        except Exception as e:
            await ctx.client.reply(ctx.message, t_error("delete.failed", error=str(e)))
