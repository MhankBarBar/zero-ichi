"""
Sticker command - Convert image or video to sticker.
"""

from core.command import Command, CommandContext
from core.errors import report_error
from core.i18n import t_error, t_info, t_warning
from core.logger import log_info


class StickerCommand(Command):
    name = "sticker"
    aliases = ["s", "stiker"]
    description = "Convert image or video to sticker"
    usage = "sticker (reply to image, short video, or sticker)"
    category = "content"
    examples = ["sticker", "s"]

    async def execute(self, ctx: CommandContext) -> None:
        """Convert media to sticker."""
        msg_obj, media_type = ctx.message.get_media_message(ctx.client)

        if not msg_obj:
            await ctx.client.reply(ctx.message, t_info("sticker.reply_to_image"))
            return

        if media_type not in ["image", "sticker", "video"]:
            await ctx.client.reply(ctx.message, t_warning("sticker.image_only"))
            return

        try:
            if media_type == "video":
                duration = msg_obj.videoMessage.seconds if msg_obj.HasField("videoMessage") else 0
                if duration > 7:
                    await ctx.client.reply(ctx.message, t_error("sticker.video_too_long"))
                    return
                await ctx.client.reply(ctx.message, t_info("sticker.processing_video"))

            log_info(f"Downloading {media_type} for sticker...")
            media_bytes = await ctx.client._client.download_any(msg_obj)

            if not media_bytes:
                await ctx.client.reply(ctx.message, t_error("sticker.download_failed"))
                return

            await ctx.client._client.send_sticker(
                ctx.client.to_jid(ctx.message.chat_jid),
                media_bytes,
                quoted=ctx.message.event,
            )

        except Exception as e:
            await report_error(ctx.client, ctx.message, self.name, e)
