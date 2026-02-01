"""
Save command - Save a note for the group (text or media).
"""

from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message

from config.settings import features
from core.command import Command, CommandContext
from core.i18n import t_error, t_success
from core.logger import log_error, log_info
from core.storage import DATA_DIR, GroupData


class SaveCommand(Command):
    name = "save"
    description = "Save a note for the group (text or media)"
    usage = "/save <name> [content] or reply to a message with /save <name>"
    group_only = True
    admin_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Save a note (text or media)."""
        if not features.notes:
            await ctx.client.reply(ctx.message, t_error("common.feature_disabled"))
            return

        group_jid = ctx.message.chat_jid

        if not ctx.args:
            await ctx.client.reply(ctx.message, t_error("notes.usage_save"))
            return

        note_name = ctx.args[0].lower()
        note_content = " ".join(ctx.args[1:]) if len(ctx.args) > 1 else ""

        msg_obj, media_type = ctx.message.get_media_message(ctx.client)

        note_type = "text"
        media_path = None

        if msg_obj and media_type:
            note_type = media_type

            if not note_content:
                if media_type == "image" and msg_obj.imageMessage.caption:
                    note_content = msg_obj.imageMessage.caption
                elif media_type == "video" and msg_obj.videoMessage.caption:
                    note_content = msg_obj.videoMessage.caption

            media_path = await self._save_media(ctx, group_jid, note_name, media_type, msg_obj)

        else:
            if not note_content:
                quoted = ctx.message.quoted_message
                if quoted and quoted.get("text"):
                    note_content = quoted["text"]
                else:
                    await ctx.client.reply(ctx.message, t_error("notes.no_content"))
                    return

        if note_type != "text" and not media_path:
            return

        data = GroupData(group_jid)
        notes = data.notes
        notes[note_name] = {
            "type": note_type,
            "content": note_content,
            "media_path": media_path,
        }
        data.save_notes(notes)

        await ctx.client.reply(
            ctx.message, t_success("notes.saved", name=note_name, type=note_type)
        )

    async def _save_media(
        self,
        ctx: CommandContext,
        group_jid: str,
        note_name: str,
        media_type: str,
        message: Message,
    ) -> str | None:
        """Download and save media file."""
        try:
            safe_jid = group_jid.replace(":", "_").replace("@", "_")
            media_dir = DATA_DIR / safe_jid / "media"
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

            log_info(f"Downloading {media_type} for note {note_name}...")
            media_bytes = await ctx.client._client.download_any(message)

            if media_bytes:
                file_path = media_dir / f"{note_name}{ext}"
                with open(file_path, "wb") as f:
                    f.write(media_bytes)
                log_info(f"Saved media to {file_path}")
                return str(file_path)
            else:
                log_error(f"Download returned empty bytes for {note_name}")
                await ctx.client.reply(ctx.message, t_error("notes.download_failed"))
        except Exception as e:
            log_error(f"Failed to save media: {e}")
            await ctx.client.reply(ctx.message, t_error("notes.save_failed", error=str(e)))

        return None
