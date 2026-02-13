"""
Toimg command - Convert sticker to image.
"""

from io import BytesIO

from PIL import Image

from core.command import Command, CommandContext
from core.errors import report_error
from core.i18n import t_error, t_info
from core.logger import log_error, log_info


class ToimgCommand(Command):
    name = "toimg"
    aliases = ["toimage", "stickertoimg"]
    description = "Convert sticker to image"
    usage = "/toimg (reply to sticker)"
    category = "content"
    examples = ["/toimg"]

    async def execute(self, ctx: CommandContext) -> None:
        """Convert a sticker to a PNG image."""
        msg_obj, media_type = ctx.message.get_media_message(ctx.client)

        if not msg_obj:
            await ctx.client.reply(ctx.message, t_info("toimg.reply_to_sticker"))
            return

        if media_type != "sticker":
            await ctx.client.reply(ctx.message, t_error("toimg.sticker_only"))
            return

        try:
            log_info("Downloading sticker for toimg conversion...")
            media_bytes = await ctx.client._client.download_any(msg_obj)

            if not media_bytes:
                await ctx.client.reply(ctx.message, t_error("toimg.download_failed"))
                return

            try:
                img = Image.open(BytesIO(media_bytes))

                if getattr(img, "n_frames", 1) > 1:
                    img.seek(0)

                img = img.convert("RGBA")
                buff = BytesIO()
                img.save(buff, format="PNG")
                png_bytes = buff.getvalue()
            except Exception as e:
                log_error(f"Sticker to image conversion failed: {e}")
                await ctx.client.reply(ctx.message, t_error("toimg.convert_failed"))
                return

            await ctx.client.send_image(
                to=ctx.message.chat_jid,
                file=png_bytes,
                caption="",
                quoted=ctx.message,
            )

        except Exception as e:
            await report_error(ctx.client, ctx.message, self.name, e)
