"""
Filter command - Set auto-reply filter (text or media).
"""

from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message

from config.settings import features
from core.command import Command, CommandContext
from core.i18n import t_error, t_success
from core.logger import log_error, log_info
from core.storage import DATA_DIR, GroupData


class FilterCommand(Command):
    name = "filter"
    description = "Set an auto-reply filter (text or media)"
    usage = "/filter <trigger> [response] or reply to media with /filter <trigger>"
    group_only = True
    admin_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Set an auto-reply filter (text or media)."""
        if not features.filters:
            await ctx.client.reply(ctx.message, t_error("common.feature_disabled"))
            return

        group_jid = ctx.message.chat_jid

        if not ctx.args:
            await ctx.client.reply(ctx.message, t_error("filter.usage"))
            return

        trigger = ctx.args[0].lower()
        response_text = " ".join(ctx.args[1:]) if len(ctx.args) > 1 else ""

        msg_obj, media_type = ctx.message.get_media_message(ctx.client)

        filter_type = "text"
        media_path = None

        if msg_obj and media_type:
            filter_type = media_type

            if not response_text:
                if media_type == "image" and msg_obj.imageMessage.caption:
                    response_text = msg_obj.imageMessage.caption
                elif media_type == "video" and msg_obj.videoMessage.caption:
                    response_text = msg_obj.videoMessage.caption

            media_path = await self._save_media(ctx, group_jid, trigger, media_type, msg_obj)

            if not media_path:
                return
        else:
            if not response_text:
                quoted = ctx.message.quoted_message
                if quoted and quoted.get("text"):
                    response_text = quoted["text"]
                else:
                    await ctx.client.reply(ctx.message, t_error("filter.no_response"))
                    return

        data = GroupData(group_jid)
        filters = data.filters

        filters[trigger] = {
            "type": filter_type,
            "response": response_text,
            "media_path": media_path,
        }
        data.save_filters(filters)

        await ctx.client.reply(
            ctx.message, t_success("filter.set", trigger=trigger, type=filter_type)
        )

    async def _save_media(
        self,
        ctx: CommandContext,
        group_jid: str,
        trigger: str,
        media_type: str,
        message: Message,
    ) -> str | None:
        """Download and save filter media file."""
        try:
            safe_jid = group_jid.replace(":", "_").replace("@", "_")
            media_dir = DATA_DIR / safe_jid / "filter_media"
            media_dir.mkdir(parents=True, exist_ok=True)

            extensions = {
                "image": ".jpg",
                "video": ".mp4",
                "sticker": ".webp",
                "document": "",
                "audio": ".ogg",
            }
            ext = extensions.get(media_type, "")

            if (
                media_type == "document"
                and message.documentMessage
                and message.documentMessage.fileName
            ):
                import os

                _, f_ext = os.path.splitext(message.documentMessage.fileName)
                if f_ext:
                    ext = f_ext

            log_info(f"Downloading {media_type} for filter '{trigger}'...")
            media_bytes = await ctx.client._client.download_any(message)

            if media_bytes:
                safe_trigger = trigger.replace("/", "_").replace("\\", "_").replace(":", "_")
                file_path = media_dir / f"{safe_trigger}{ext}"
                with open(file_path, "wb") as f:
                    f.write(media_bytes)
                log_info(f"Saved filter media to {file_path}")
                return str(file_path)
            else:
                log_error(f"Download returned empty bytes for filter '{trigger}'")
                await ctx.client.reply(ctx.message, t_error("filter.download_failed"))
        except Exception as e:
            log_error(f"Failed to save filter media: {e}")
            await ctx.client.reply(ctx.message, t_error("filter.save_failed", error=str(e)))

        return None
