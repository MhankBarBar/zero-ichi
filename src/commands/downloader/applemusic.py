"""
Apple Music command - Download music from Apple Music URLs.

Flow:
  Single song: /am <url> → fetch info → get download link → download → send
  Album: /am <url> → fetch tracks → show list → user replies with number → download
"""

import asyncio
import re
import time

from core import symbols as sym
from core.applemusic import AppleMusicError, applemusic_client
from core.command import Command, CommandContext
from core.errors import report_error
from core.i18n import t, t_error
from core.logger import log_info
from core.pending_store import PendingAppleMusic, pending_downloads
from core.progress import build_complete_bar, build_progress_text

APPLE_MUSIC_URL_PATTERN = re.compile(
    r"https?://(?:music\.apple\.com|embed\.music\.apple\.com)/", re.IGNORECASE
)


class AppleMusicCommand(Command):
    name = "applemusic"
    aliases = ["am", "apple"]
    description = "Download music from Apple Music URL"
    usage = "applemusic <apple music url>"
    category = "downloader"
    cooldown = 15

    async def execute(self, ctx: CommandContext) -> None:
        """Download audio from an Apple Music URL."""
        if not ctx.args:
            await ctx.client.reply(
                ctx.message, t_error("errors.usage", usage=self.get_usage(ctx.prefix))
            )
            return

        url = ctx.args[0].strip()

        if not APPLE_MUSIC_URL_PATTERN.match(url):
            await ctx.client.reply(
                ctx.message,
                f"{sym.WARNING} {t('applemusic.invalid_url')}",
            )
            return

        await ctx.client.send_reaction(ctx.message, "⏳")

        progress_msg = await ctx.client.reply(
            ctx.message,
            f"{sym.LOADING} {t('applemusic.fetching_info')}",
        )

        try:
            info = await applemusic_client.fetch_info(url)
        except AppleMusicError as e:
            await ctx.client.send_reaction(ctx.message, "❌")
            await ctx.client.reply(ctx.message, t_error("applemusic.failed", error=str(e)))
            return

        if not info.tracks:
            await ctx.client.send_reaction(ctx.message, "❌")
            await ctx.client.reply(
                ctx.message,
                f"{sym.WARNING} {t('applemusic.no_results', query=url)}",
            )
            return

        if len(info.tracks) == 1:
            track = info.tracks[0]
            await self._download_and_send(ctx, track, progress_msg)
            return

        await ctx.client.send_reaction(ctx.message, "")

        text = self._build_album_text(info)
        await ctx.client.edit_message(
            ctx.message.chat_jid,
            progress_msg.ID,
            text,
        )

        pending_downloads.add(
            progress_msg.ID,
            PendingAppleMusic(
                tracks=info.tracks,
                album_name=info.album,
                sender_jid=ctx.message.sender_jid,
                chat_jid=ctx.message.chat_jid,
            ),
        )

    async def _download_and_send(self, ctx, track, progress_msg) -> None:
        """Download a single track and send it."""
        header = f"{sym.MUSIC} *{track.name}*\n{sym.ARROW} {track.artist}"
        if track.album:
            header += f" {sym.BULLET} {track.album}"
        header += "\n"

        try:
            await ctx.client.edit_message(
                ctx.message.chat_jid,
                progress_msg.ID,
                f"{header}\n{sym.LOADING} {t('applemusic.fetching_link')}",
            )

            dlink = await applemusic_client.get_download_link(track)

            last_edit = [0.0]
            loop = asyncio.get_event_loop()
            msg_id = progress_msg.ID

            def _on_progress(downloaded: int, total: int):
                now = time.time()
                if now - last_edit[0] < 3:
                    return
                last_edit[0] = now
                text = build_progress_text(header, downloaded, total)
                asyncio.run_coroutine_threadsafe(
                    ctx.client.edit_message(ctx.message.chat_jid, msg_id, text),
                    loop,
                )

            safe_name = re.sub(r"[^\w\s-]", "", track.name)[:50] or "track"
            filename = f"am_{safe_name}"
            filepath = await applemusic_client.download_track(dlink, filename, _on_progress)

            await ctx.client.edit_message(
                ctx.message.chat_jid,
                msg_id,
                build_complete_bar(header, t("applemusic.sending")),
            )

            await ctx.client.send_media(
                ctx.message.chat_jid,
                "audio",
                str(filepath),
                quoted=ctx.message.event,
            )

            applemusic_client.cleanup(filepath)
            await ctx.client.edit_message(
                ctx.message.chat_jid,
                msg_id,
                build_complete_bar(header, t("applemusic.done")),
            )
            await ctx.client.send_reaction(ctx.message, "✅")
            log_info(f"[APPLEMUSIC] Sent: {track.name}")

        except AppleMusicError as e:
            await ctx.client.send_reaction(ctx.message, "❌")
            await ctx.client.reply(ctx.message, t_error("applemusic.failed", error=str(e)))
        except Exception as e:
            await ctx.client.send_reaction(ctx.message, "❌")
            await report_error(ctx.client, ctx.message, self.name, e)

    @staticmethod
    def _build_album_text(info) -> str:
        """Build the album track list display text."""
        lines = [
            f"{sym.MUSIC} *{info.album}*",
            f"{sym.ARROW} {info.artist} {sym.BULLET} {info.count} tracks",
            "",
        ]

        for idx, track in enumerate(info.tracks, 1):
            lines.append(f" `{idx}.` *{track.name}*")
            detail = f"     {sym.ARROW} {track.artist}"
            if track.duration:
                detail += f" {sym.BULLET} {track.duration}"
            lines.append(detail)

        lines.append("")
        lines.append(f"{sym.INFO} {t('applemusic.choose_hint')}")

        return "\n".join(lines)
