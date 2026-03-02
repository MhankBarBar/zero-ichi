"""Photo command - Download image posts/albums via gallery-dl."""

from __future__ import annotations

from core import symbols as sym
from core.command import Command, CommandContext
from core.errors import report_error
from core.i18n import t, t_error
from core.photo_downloader import (
    PhotoDownloadError,
    build_photo_caption,
    is_auth_required_error,
    photo_downloader,
    send_photo_items,
)
from core.runtime_config import runtime_config


class PhotoCommand(Command):
    name = "photo"
    aliases = ["img", "images"]
    description = "Download photos from social links"
    usage = "photo <url>"
    category = "downloader"
    cooldown = 10

    async def execute(self, ctx: CommandContext) -> None:
        """Download and send images from a URL."""
        if not ctx.args:
            await ctx.client.reply(
                ctx.message, t_error("errors.usage", usage=self.get_usage(ctx.prefix))
            )
            return

        url = ctx.args[0].strip()
        photo_cfg = runtime_config.get_nested(
            "downloader",
            "auto_link_download",
            "photo",
            default={},
        )
        if not isinstance(photo_cfg, dict):
            photo_cfg = {}

        max_per_link = max(1, min(int(photo_cfg.get("max_images_per_link", 20) or 20), 100))
        max_per_album = max(2, min(int(photo_cfg.get("max_images_per_album", 10) or 10), 30))

        progress = await ctx.client.reply(ctx.message, f"{sym.LOADING} {t('photo.fetching')}")

        try:
            result = await photo_downloader.fetch(url, max_items=max_per_link)
            caption = build_photo_caption(
                result,
                title_fallback=t("photo.caption_fallback_title"),
                likes_label=t("photo.likes_label"),
                images_label=t("photo.images_label"),
                unknown_user=t("photo.unknown_user"),
            )
            sent = await send_photo_items(
                ctx.client,
                ctx.message.chat_jid,
                result.items,
                caption=caption,
                quoted=ctx.message.event,
                max_images_per_album=max_per_album,
            )

            await ctx.client.edit_message(
                ctx.message.chat_jid,
                progress.ID,
                t(
                    "photo.sent",
                    sent=sent,
                    found=result.total_urls,
                    converted=result.converted_count,
                ),
            )
            await ctx.client.send_reaction(ctx.message, "✅")

        except PhotoDownloadError as e:
            await ctx.client.send_reaction(ctx.message, "❌")
            error_text = str(e)
            message = (
                t("photo.auth_required")
                if is_auth_required_error(error_text)
                else t_error("photo.failed", error=error_text)
            )
            await ctx.client.edit_message(
                ctx.message.chat_jid,
                progress.ID,
                message,
            )
        except Exception as e:
            await ctx.client.send_reaction(ctx.message, "❌")
            await report_error(ctx.client, ctx.message, self.name, e)
