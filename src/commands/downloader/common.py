"""
Common utilities for downloader commands.
"""

import asyncio
import time
from collections.abc import Callable

from core import symbols as sym
from core.command import Command, CommandContext
from core.downloader import (
    DownloadAbortedError,
    DownloadError,
    FileTooLargeError,
    _format_size,
    downloader,
)
from core.errors import report_error
from core.i18n import t, t_error


class BaseMediaCommand(Command):
    """Base command for downloading media (audio/video)."""

    media_type: str = ""
    download_func: Callable = None

    @property
    def downloading_key(self) -> str:
        return f"downloader.downloading_{self.media_type}"

    async def execute(self, ctx: CommandContext) -> None:
        """Download media from a URL."""
        if not ctx.args:
            await ctx.client.reply(
                ctx.message, t_error("errors.usage", usage=self.get_usage(ctx.prefix))
            )
            return

        url = ctx.args[0]

        progress_msg = await ctx.client.reply(
            ctx.message,
            f"{sym.LOADING} {t(self.downloading_key)}",
        )

        try:
            info = await downloader.get_info(url)

            header = (
                f"{sym.MUSIC if self.media_type == 'audio' else sym.SPARKLE} *{info.title}*\n"
                f"{sym.ARROW} {info.uploader} • {info.duration_str}\n"
            )

            await ctx.client.edit_message(
                ctx.message.chat_jid,
                progress_msg.ID,
                f"{header}\n{sym.LOADING} {t(self.downloading_key)}",
            )

            progress_msg_id = progress_msg.ID
            last_edit_time = [0.0]
            loop = asyncio.get_event_loop()

            def _progress_hook(downloaded_bytes, total_bytes, speed, eta):
                now = time.time()
                if now - last_edit_time[0] < 5:
                    return
                last_edit_time[0] = now

                if not total_bytes or total_bytes <= 0:
                    return

                pct = (downloaded_bytes / total_bytes) * 100
                filled = int(pct / 5)
                bar = "█" * filled + "░" * (20 - filled)

                speed_str = _format_size(speed) + "/s" if speed else "?"
                eta_str = f"{int(eta)}s" if eta else "?"
                dl_str = _format_size(downloaded_bytes)
                total_str = _format_size(total_bytes)

                text = (
                    f"{header}"
                    f"`[{bar}]` {pct:.0f}%\n"
                    f"{sym.BULLET} {dl_str} / {total_str}\n"
                    f"{sym.BULLET} {speed_str} {sym.BULLET} ETA: {eta_str}"
                )

                asyncio.run_coroutine_threadsafe(
                    ctx.client.edit_message(ctx.message.chat_jid, progress_msg_id, text),
                    loop,
                )

            filepath = await self.download_func(
                url,
                progress_hook=_progress_hook,
                chat_jid=ctx.message.chat_jid,
                sender_jid=ctx.message.sender_jid,
            )

            await ctx.client.edit_message(
                ctx.message.chat_jid,
                progress_msg_id,
                f"{header}`[{'█' * 20}]` 100%\n{sym.BULLET} {t('downloader.sending')}",
            )

            caption = (
                f"{sym.MUSIC if self.media_type == 'audio' else sym.SPARKLE} {info.title}\n"
                f"{sym.ARROW} {info.uploader} • {info.duration_str}"
            )

            await ctx.client.send_media(
                ctx.message.chat_jid,
                self.media_type,
                str(filepath),
                caption=caption,
                quoted=ctx.message.event,
            )

            downloader.cleanup(filepath)
            await ctx.client.edit_message(
                ctx.message.chat_jid,
                progress_msg_id,
                f"{header}`[{'█' * 20}]` 100%\n{sym.BULLET} {t('downloader.done')}",
            )

        except FileTooLargeError as e:
            await ctx.client.reply(
                ctx.message,
                t_error("downloader.too_large", size=f"{e.size_mb:.1f}", max=f"{e.max_mb:.0f}"),
            )
        except DownloadAbortedError:
            await ctx.client.edit_message(
                ctx.message.chat_jid,
                progress_msg_id,
                f"{header}{sym.INFO} {t('downloader.cancelled')}",
            )
            await ctx.client.send_reaction(ctx.message, "🚫")
        except DownloadError as e:
            await ctx.client.reply(ctx.message, t_error("downloader.failed", error=str(e)))
        except Exception as e:
            await report_error(ctx.client, ctx.message, self.name, e)
