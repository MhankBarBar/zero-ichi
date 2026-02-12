"""
Download command - Show media info and quality options.

Flow:
  /dl <url>  → show info + numbered quality options (with thumbnail)
  User replies to that message with a number → downloads that quality

Supports YouTube, TikTok, Instagram, Twitter/X, and 1000+ sites via yt-dlp.
"""

import httpx

from core import symbols as sym
from core.command import Command, CommandContext
from core.downloader import DownloadError, downloader
from core.i18n import t, t_error
from core.pending_store import PendingDownload, pending_downloads


class DlCommand(Command):
    name = "dl"
    aliases = ["download"]
    description = "Download media from URL"
    usage = "/dl <url>"
    category = "downloader"
    cooldown = 10

    async def execute(self, ctx: CommandContext) -> None:
        """Download media from a URL."""
        if not ctx.args:
            await ctx.client.reply(ctx.message, t_error("errors.usage", usage=self.usage))
            return

        url = ctx.args[0]

        await ctx.client.reply(
            ctx.message,
            f"{sym.LOADING} {t('downloader.fetching_info')}",
        )

        try:
            info = await downloader.get_info(url)
        except DownloadError as e:
            await ctx.client.reply(ctx.message, t_error("downloader.failed", error=str(e)))
            return

        if not info.formats:
            await ctx.client.reply(
                ctx.message,
                f"{sym.INFO} {t('downloader.no_formats')}\n"
                f"{sym.INFO} {t('downloader.use_audio_video_hint')}",
            )
            return

        response = await self._show_options(ctx, info)

        pending_downloads.add(
            response.ID,
            PendingDownload(
                url=url,
                info=info,
                sender_jid=ctx.message.sender_jid,
                chat_jid=ctx.message.chat_jid,
            ),
        )

    def _build_options_text(self, info) -> str:
        """Build the numbered format options text."""
        lines = [
            f"{sym.SPARKLE} *{info.title}*",
            f"{sym.ARROW} {info.uploader} {sym.BULLET} {info.platform}",
            f"{sym.CLOCK} {info.duration_str}",
            "",
        ]

        video_formats = [f for f in info.formats if f.type == "video"]
        audio_formats = [f for f in info.formats if f.type == "audio"]

        idx = 1

        if video_formats:
            lines.append(f"*{sym.VIDEO} {t('downloader.video_options')}*")
            for fmt in video_formats:
                lines.append(f"  {sym.BULLET} `{idx}` {sym.ARROW} {fmt.label}")
                idx += 1
            lines.append("")

        if audio_formats:
            lines.append(f"*{sym.AUDIO} {t('downloader.audio_options')}*")
            for fmt in audio_formats:
                lines.append(f"  {sym.BULLET} `{idx}` {sym.ARROW} {fmt.label}")
                idx += 1
            lines.append("")

        lines.append(f"{sym.INFO} {t('downloader.choose_hint')}")

        return "\n".join(lines)

    async def _show_options(self, ctx: CommandContext, info):
        """Show media info and numbered format options. Returns SendResponse."""
        text = self._build_options_text(info)

        if info.thumbnail:
            try:
                async with httpx.AsyncClient(timeout=5) as http:
                    resp = await http.get(info.thumbnail)
                    if resp.status_code == 200 and len(resp.content) > 0:
                        return await ctx.client.send_image(
                            ctx.message.chat_jid,
                            resp.content,
                            caption=text,
                            quoted=ctx.message.event,
                        )
            except Exception as e:
                from core.logger import log_warning

                log_warning(f"Failed to send thumbnail: {e}")

        return await ctx.client.reply(ctx.message, text)
