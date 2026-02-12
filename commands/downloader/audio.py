"""
Audio command - Force download audio from URLs.

Extracts audio (MP3) from any supported site via yt-dlp.
"""

from core import symbols as sym
from core.command import Command, CommandContext
from core.downloader import DownloadError, FileTooLargeError, downloader
from core.errors import report_error
from core.i18n import t, t_error


class AudioCommand(Command):
    name = "audio"
    aliases = ["mp3", "music"]
    description = "Download audio from URL"
    usage = "/audio <url>"
    category = "downloader"
    cooldown = 15

    async def execute(self, ctx: CommandContext) -> None:
        """Download audio from a URL."""
        if not ctx.args:
            await ctx.client.reply(ctx.message, t_error("errors.usage", usage=self.usage))
            return

        url = ctx.args[0]

        await ctx.client.reply(
            ctx.message,
            f"{sym.LOADING} {t('downloader.downloading_audio')}",
        )

        try:
            info = await downloader.get_info(url)
            filepath = await downloader.download_audio(url)

            caption = f"{sym.MUSIC} {info.title}\n{sym.ARROW} {info.uploader} • {info.duration_str}"
            await ctx.client.send_media(
                ctx.message.chat_jid,
                "audio",
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
