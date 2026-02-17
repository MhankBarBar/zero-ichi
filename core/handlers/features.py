from pathlib import Path

from config.settings import features
from core.client import BotClient
from core.i18n import t, t_error
from core.storage import GroupData


async def handle_features(bot: BotClient, msg: any):
    """
    Handle group features like Notes and Filters.
    """
    if not msg.is_group or not msg.text:
        return

    data = GroupData(msg.chat_jid)

    if features.notes and msg.text.startswith("#"):
        note_name = msg.text[1:].split()[0].lower()
        notes = data.notes
        if note_name in notes:
            await _send_feature_response(bot, msg, notes[note_name], content_key="content")
            return

    if features.filters:
        filters = data.filters
        text_lower = msg.text.lower()
        for trigger, filter_data in filters.items():
            if trigger in text_lower:
                await _send_feature_response(bot, msg, filter_data, content_key="response")
                return


async def _send_feature_response(
    bot: BotClient, msg: any, data: any, content_key: str = "content"
) -> None:
    """Send a response for a feature (note/filter)."""
    if isinstance(data, dict):
        msg_type = data.get("type", "text")
        content = data.get(content_key, "")
        media_path = data.get("media_path")

        if msg_type == "text" or not media_path:
            if content:
                await bot.reply(msg, content)
        else:
            if Path(media_path).exists():
                try:
                    await bot.send_media(
                        msg.chat_jid, msg_type, media_path, caption=content, quoted=msg.event
                    )
                except Exception as e:
                    await bot.reply(msg, t_error("notes.send_failed", error=str(e)))
            else:
                await bot.reply(msg, content or t("notes.media_not_found"))
    else:
        await bot.reply(msg, data)
