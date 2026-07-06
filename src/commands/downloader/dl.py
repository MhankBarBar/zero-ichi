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

from core import symbols as sym
from core.command import Command, CommandContext
from core.downloader import DownloadAbortedError, DownloadError, FileTooLargeError, downloader
from core.downloader_render import (
    build_format_sections,
    build_options_header,
    build_options_text,
    build_playlist_header,
    build_playlist_sections,
    build_playlist_text,
    build_search_header,
    build_search_sections,
    build_search_text,
)
from core.i18n import t, t_error
from core.logger import log_info
from core.pending_store import (
    PendingDownload,
    PendingPlaylist,
    PendingSearch,
    SearchResult,
    pending_downloads,
)
from core.selection_ui import send_selection

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

        response = await send_selection(
            ctx.client,
            ctx.message,
            fallback_text=build_search_text(query, search_results),
            sections=build_search_sections(search_results),
            header=build_search_header(query),
            menu_title="Choose a result",
            card_title=f"{sym.SEARCH} Search Results",
        )

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

        response = await send_selection(
            ctx.client,
            ctx.message,
            fallback_text=build_playlist_text(playlist),
            sections=build_playlist_sections(playlist.entries),
            header=build_playlist_header(playlist),
            menu_title="Choose a track",
            card_title=f"{sym.SPARKLE} {playlist.title}",
            allow_all=True,
        )

        pending_downloads.add(
            response.ID,
            PendingPlaylist(
                title=playlist.title,
                entries=playlist.entries,
                sender_jid=ctx.message.sender_jid,
                chat_jid=ctx.message.chat_jid,
            ),
        )

    async def _show_options(self, ctx: CommandContext, info):
        """Show media info and format options (buttons or numbered text). Returns SendResponse."""
        return await send_selection(
            ctx.client,
            ctx.message,
            fallback_text=build_options_text(info),
            sections=build_format_sections(info),
            header=build_options_header(info),
            menu_title="Choose a quality",
            card_title=f"{sym.SPARKLE} {info.title}",
            thumbnail=info.thumbnail or None,
        )
