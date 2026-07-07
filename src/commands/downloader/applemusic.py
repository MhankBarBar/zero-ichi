"""
Apple Music command - Download music from Apple Music URLs.

Flow:
  /am <url> -> choose quality (standard/ALAC/Atmos) -> fetch info ->
  single song: download -> send
  album: show track list -> user replies with number -> download
"""

import re
import shutil

from core import symbols as sym
from core.command import Command, CommandContext
from core.downloader_render import build_quality_sections, build_quality_text
from core.i18n import t, t_error
from core.pending_store import PendingAppleMusicQuality, pending_downloads
from core.selection_ui import send_selection

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
        """Validate the URL and show the quality picker (standard/ALAC/Atmos)."""
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

        atmos_available = shutil.which("mp4decrypt") is not None

        response = await send_selection(
            ctx.client,
            ctx.message,
            fallback_text=build_quality_text(atmos_available),
            sections=build_quality_sections(atmos_available),
            header=f"{sym.MUSIC} {t('applemusic.choose_quality_title')}",
            menu_title="Choose a quality",
            card_title=f"{sym.MUSIC} {t('applemusic.choose_quality_title')}",
        )

        pending_downloads.add(
            response.ID,
            PendingAppleMusicQuality(
                url=url,
                sender_jid=ctx.message.sender_jid,
                chat_jid=ctx.message.chat_jid,
            ),
        )
