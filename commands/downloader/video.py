"""
Video command - Force download video from URLs.

Downloads video (MP4) from any supported site via yt-dlp.
"""

from core import symbols as sym
from core.command import Command, CommandContext
from core.downloader import DownloadError, FileTooLargeError, downloader
from core.errors import report_error
from core.i18n import t, t_error


class VideoCommand(Command):
    name = "video"
    aliases = ["vid", "mp4"]
    description = "Download video from URL"
    usage = "/video <url>"
    category = "downloader"
    cooldown = 15

    async def execute(self, ctx: CommandContext) -> None:
        """Download video from a URL."""
        if not ctx.args:
            await ctx.client.reply(ctx.message, t_error("errors.usage", usage=self.usage))
            return

        url = ctx.args[0]

        await ctx.client.reply(
            ctx.message,
            f"{sym.LOADING} {t('downloader.downloading_video')}",
        )

        try:
            info = await downloader.get_info(url)
            filepath = await downloader.download_video(url)

            caption = (
                f"{sym.SPARKLE} {info.title}\n{sym.ARROW} {info.uploader} • {info.duration_str}"
            )
            await ctx.client.send_media(
                ctx.message.chat_jid,
                "video",
                str(filepath),
                caption=caption,
                quoted=ctx.message.event,
            )

            downloader.cleanup(filepath)

        except FileTooLargeError as e:
            await ctx.client.reply(
                ctx.message,
                t_error("downloader.too_large", size=f"{e.size_mb:.1f}", max=f"{e.max_mb:.0f}"),
            )
        except DownloadError as e:
            await ctx.client.reply(ctx.message, t_error("downloader.failed", error=str(e)))
        except Exception as e:
            await report_error(ctx.client, ctx.message, self.name, e)
