"""
Sticker command - Convert image to sticker.
"""

from io import BytesIO

from PIL import Image

from core.command import Command, CommandContext
from core.errors import report_error
from core.i18n import t_error, t_info, t_warning
from core.logger import log_error, log_info


class StickerCommand(Command):
    name = "sticker"
    aliases = ["s", "stiker"]
    description = "Convert image to sticker"
    usage = "/sticker (reply to image or with image)"

    async def execute(self, ctx: CommandContext) -> None:
        """Convert media to sticker."""
        msg_obj, media_type = ctx.message.get_media_message(ctx.client)

        if not msg_obj:
            await ctx.client.reply(ctx.message, t_info("sticker.reply_to_image"))
            return

        if media_type not in ["image", "sticker"]:
            await ctx.client.reply(ctx.message, t_warning("sticker.image_only"))
            return

        try:
            log_info(f"Downloading {media_type} for sticker...")
            media_bytes = await ctx.client._client.download_any(msg_obj)

            if not media_bytes:
                await ctx.client.reply(ctx.message, t_error("sticker.download_failed"))
                return

            webp_bytes = media_bytes

            if media_type == "image":
                try:
                    img = Image.open(BytesIO(media_bytes))

                    img.thumbnail((512, 512))

                    buff = BytesIO()
                    img.save(buff, format="WEBP", transparent=True)
                    webp_bytes = buff.getvalue()
                except Exception as e:
                    log_error(f"Image conversion failed: {e}")
                    await ctx.client.reply(ctx.message, t_error("sticker.convert_failed"))
                    return

            await ctx.client._client.send_sticker(
                ctx.client.to_jid(ctx.message.chat_jid), webp_bytes
            )

        except Exception as e:
            await report_error(ctx.client, ctx.message, self.name, e)
