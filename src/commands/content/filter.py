"""
Filter command - Set auto-reply filter (text or media).
"""

from config.settings import features
from core.command import Command, CommandContext
from core.i18n import t_error, t_success
from core.media import get_media_caption, save_media_to_disk
from core.storage import GroupData


class FilterCommand(Command):
    name = "filter"
    description = "Set an auto-reply filter (text or media)"
    usage = "filter <trigger> [response] or reply to media with filter <trigger>"
    group_only = True
    admin_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Set an auto-reply filter (text or media)."""
        if not features.filters:
            await ctx.client.reply(ctx.message, t_error("common.feature_disabled"))
            return

        group_jid = ctx.message.chat_jid

        if not ctx.args:
            await ctx.client.reply(ctx.message, t_error("filter.usage", prefix=ctx.prefix))
            return

        trigger = ctx.args[0].lower()
        response_text = " ".join(ctx.args[1:]) if len(ctx.args) > 1 else ""

        msg_obj, media_type = ctx.message.get_media_message(ctx.client)

        filter_type = "text"
        media_path = None

        if msg_obj and media_type:
            filter_type = media_type

            if not response_text:
                response_text = get_media_caption(msg_obj, media_type)

            media_path = await save_media_to_disk(
                ctx.client,
                msg_obj,
                media_type,
                group_jid,
                trigger,
                subfolder="filter_media",
            )

            if not media_path:
                return
        else:
            if not response_text:
                quoted = ctx.message.quoted_message
                if quoted and quoted.get("text"):
                    response_text = quoted["text"]
                else:
                    await ctx.client.reply(ctx.message, t_error("filter.no_response"))
                    return

        data = GroupData(group_jid)
        filters = data.filters

        filters[trigger] = {
            "type": filter_type,
            "response": response_text,
            "media_path": media_path,
        }
        data.save_filters(filters)

        await ctx.client.reply(
            ctx.message, t_success("filter.set", trigger=trigger, type=filter_type)
        )
