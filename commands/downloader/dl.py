"""
Download command - Show media info and quality options.

Flow:
  /dl <url>  → show info + numbered quality options (with thumbnail)
  User replies to that message with a number → downloads that quality

  /dl <search query> → search YouTube → show results list
  /dl -n <count> <search query> → search with custom result count (max 20)
  User replies with number → show format options for that result
  User replies with format number → download

Supports YouTube, TikTok, Instagram, Twitter/X, and 1000+ sites via yt-dlp.
"""

import re

import httpx

from core import symbols as sym
from core.command import Command, CommandContext
from core.downloader import DownloadAbortedError, DownloadError, FileTooLargeError, downloader
from core.i18n import t, t_error
from core.logger import log_info, log_warning
from core.pending_store import (
    PendingDownload,
    PendingPlaylist,
    PendingSearch,
    SearchResult,
    pending_downloads,
)

URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)


class DlCommand(Command):
    name = "dl"
    aliases = ["download"]
    description = "Download media from URL or search YouTube"
    usage = "dl <url or search query> | dl -n <count> <query>"
    category = "downloader"
    cooldown = 10

    async def execute(self, ctx: CommandContext) -> None:
        """Download media from a URL or search YouTube."""
        if not ctx.args:
            await ctx.client.reply(
                ctx.message, t_error("errors.usage", usage=self.get_usage(ctx.prefix))
            )
            return

        raw_input = ctx.raw_args.strip()

        await ctx.client.send_reaction(ctx.message, "⏳")

        if URL_PATTERN.match(raw_input):
            await self._handle_url(ctx, ctx.args[0])
        else:
            await self._handle_search(ctx, raw_input)

    async def _handle_search(self, ctx: CommandContext, query: str) -> None:
        """Search YouTube and show results list."""
        count = 5
        if query.startswith("-n "):
            parts = query[3:].split(None, 1)
            if parts and parts[0].isdigit():
                count = min(int(parts[0]), 20)
                query = parts[1] if len(parts) > 1 else ""

        if not query:
            await ctx.client.reply(
                ctx.message, t_error("errors.usage", usage=f"{ctx.prefix}dl [-n count] <query>")
            )
            return

        try:
            results = await downloader.search_youtube(query, count=count)
        except DownloadError as e:
            await ctx.client.send_reaction(ctx.message, "❌")
            await ctx.client.reply(ctx.message, t_error("downloader.failed", error=str(e)))
            return

        if not results:
            await ctx.client.send_reaction(ctx.message, "❌")
            await ctx.client.reply(
                ctx.message,
                f"{sym.WARNING} {t('downloader.no_results', query=query)}",
            )
            return

        await ctx.client.send_reaction(ctx.message, "")

        search_results = [
            SearchResult(
                title=r["title"],
                url=r["url"],
                duration=r["duration"],
                uploader=r["uploader"],
            )
            for r in results
        ]

        text = self._build_search_text(query, search_results)
        response = await ctx.client.reply(ctx.message, text)

        pending_downloads.add(
            response.ID,
            PendingSearch(
                query=query,
                results=search_results,
                sender_jid=ctx.message.sender_jid,
                chat_jid=ctx.message.chat_jid,
            ),
        )

    async def _handle_url(self, ctx: CommandContext, url: str) -> None:
        """Handle a direct URL - show format options."""
        if "list=" in url and ("youtube.com" in url or "youtu.be" in url):
            await self._handle_playlist(ctx, url)
            return

        try:
            info = await downloader.get_info(url)
        except DownloadError as e:
            await ctx.client.send_reaction(ctx.message, "❌")
            await ctx.client.reply(ctx.message, t_error("downloader.failed", error=str(e)))
            return

        if info.is_playlist:
            await self._handle_playlist(ctx, url)
            return

        if not info.formats:
            await ctx.client.send_reaction(ctx.message, "❌")
            await ctx.client.reply(
                ctx.message,
                f"{sym.INFO} {t('downloader.no_formats')}\n"
                f"{sym.INFO} {t('downloader.use_audio_video_hint', prefix=ctx.prefix)}",
            )
            return

        if len(info.formats) == 1:
            await self._auto_download(ctx, info, info.formats[0])
            return

        await ctx.client.send_reaction(ctx.message, "")

        response = await self._show_options(ctx, info)

        pending_downloads.add(
            response.ID,
            PendingDownload(
                url=info.url,
                info=info,
                sender_jid=ctx.message.sender_jid,
                chat_jid=ctx.message.chat_jid,
            ),
        )

    async def _auto_download(self, ctx: CommandContext, info, fmt) -> None:
        """Auto-download when there's only one format available."""
        try:
            filepath = await downloader.download_format(
                info.url,
                fmt.format_id,
                merge_audio=not fmt.has_audio,
                is_audio=fmt.type == "audio",
                chat_jid=ctx.message.chat_jid,
                sender_jid=ctx.message.sender_jid,
            )

            media_type = "audio" if fmt.type == "audio" else "video"
            caption = f"{sym.SPARKLE} {info.title}"

            await ctx.client.send_media(
                ctx.message.chat_jid,
                media_type,
                str(filepath),
                caption=caption,
                quoted=ctx.message.event,
            )

            downloader.cleanup(filepath)
            await ctx.client.send_reaction(ctx.message, "✅")
            log_info(f"[DOWNLOADER] Auto-downloaded: {info.title}")

        except FileTooLargeError as e:
            await ctx.client.send_reaction(ctx.message, "❌")
            await ctx.client.reply(
                ctx.message,
                t_error("downloader.too_large", size=f"{e.size_mb:.1f}", max=f"{e.max_mb:.0f}"),
            )
        except DownloadAbortedError:
            await ctx.client.send_reaction(ctx.message, "🚫")
            await ctx.client.reply(ctx.message, f"{sym.INFO} {t('downloader.cancelled')}")
        except (DownloadError, Exception) as e:
            await ctx.client.send_reaction(ctx.message, "❌")
            await ctx.client.reply(ctx.message, t_error("downloader.failed", error=str(e)))

    async def _handle_playlist(self, ctx: CommandContext, url: str) -> None:
        """Handle a playlist URL - show tracks for selection."""
        try:
            playlist = await downloader.get_playlist_info(url)
        except DownloadError as e:
            await ctx.client.send_reaction(ctx.message, "❌")
            await ctx.client.reply(ctx.message, t_error("downloader.failed", error=str(e)))
            return

        if not playlist.entries:
            await ctx.client.send_reaction(ctx.message, "❌")
            await ctx.client.reply(
                ctx.message, t_error("downloader.no_results", query=playlist.title)
            )
            return

        await ctx.client.send_reaction(ctx.message, "")

        text = self._build_playlist_text(playlist)
        response = await ctx.client.reply(ctx.message, text)

        pending_downloads.add(
            response.ID,
            PendingPlaylist(
                title=playlist.title,
                entries=playlist.entries,
                sender_jid=ctx.message.sender_jid,
                chat_jid=ctx.message.chat_jid,
            ),
        )

    def _build_search_text(self, query: str, results: list[SearchResult]) -> str:
        """Build the search results display text."""
        lines = [
            f"{sym.SEARCH} *{t('downloader.search_results', query=query)}*",
            "",
        ]

        for idx, r in enumerate(results, 1):
            lines.append(f" `{idx}.` *{r.title}*")
            lines.append(f"     {sym.ARROW} {r.uploader} {sym.BULLET} {r.duration}")
            lines.append(f"     {sym.BULLET} {r.url}")
            lines.append("")

        lines.append(f"{sym.INFO} {t('downloader.choose_result_hint')}")

        return "\n".join(lines)

    def _build_options_text(self, info) -> str:
        """Build the numbered format options text."""
        lines = [
            f"{sym.SPARKLE} *{info.title}*",
            "",
            f"{sym.ARROW} {info.uploader}",
            f"{sym.BULLET} {info.platform} {sym.BULLET} {info.duration_str}",
        ]

        if info.filesize_approx:
            lines[-1] += f" {sym.BULLET} ~{info.filesize_str}"

        lines.append("")

        video_formats = [f for f in info.formats if f.type == "video"]
        audio_formats = [f for f in info.formats if f.type == "audio"]

        idx = 1

        if video_formats:
            lines.append(f"*{sym.VIDEO} {t('downloader.video_options')}*")
            for fmt in video_formats:
                size = f" ({fmt.filesize_str})" if fmt.filesize else ""
                lines.append(f" {sym.BULLET} `{idx}.` {fmt.quality} {fmt.ext.upper()}{size}")
                idx += 1
            lines.append("")

        if audio_formats:
            lines.append(f"*{sym.AUDIO} {t('downloader.audio_options')}*")
            for fmt in audio_formats:
                size = f" ({fmt.filesize_str})" if fmt.filesize else ""
                lines.append(f" {sym.BULLET} `{idx}.` {fmt.quality} {fmt.ext.upper()}{size}")
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
                log_warning(f"Failed to send thumbnail: {e}")

        return await ctx.client.reply(ctx.message, text)

    def _build_playlist_text(self, playlist) -> str:
        """Build the numbered playlist track list."""
        showing = len(playlist.entries)
        total = playlist.count

        lines = [
            f"{sym.SPARKLE} *{playlist.title}*",
            f"{sym.BULLET} {t('downloader.playlist_tracks', showing=showing, total=total)}",
            "",
        ]

        for entry in playlist.entries:
            lines.append(f" `{entry.index}.` *{entry.title}*")
            detail = f"     {sym.BULLET} {entry.duration}"
            if entry.uploader:
                detail += f" {sym.BULLET} {entry.uploader}"
            lines.append(detail)
            lines.append("")

        lines.append(f"{sym.INFO} {t('downloader.choose_result_hint')}")

        return "\n".join(lines)
