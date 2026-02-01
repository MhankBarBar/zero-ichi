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
            note = notes[note_name]

            if isinstance(note, dict):
                note_type = note.get("type", "text")
                content = note.get("content", "")
                media_path = note.get("media_path")

                if note_type == "text" or not media_path:
                    await bot.reply(msg, content)
                else:
                    if Path(media_path).exists():
                        try:
                            await bot.send_media(
                                msg.chat_jid, note_type, media_path, content, quoted=msg.event
                            )
                        except Exception as e:
                            await bot.reply(msg, t_error("notes.send_failed", error=str(e)))
                    else:
                        await bot.reply(msg, content or t("notes.media_not_found"))
            else:
                await bot.reply(msg, note)
            return

    if features.filters:
        filters = data.filters
        text_lower = msg.text.lower()
        for trigger, filter_data in filters.items():
            if trigger in text_lower:
                if isinstance(filter_data, dict):
                    filter_type = filter_data.get("type", "text")
                    response = filter_data.get("response", "")
                    media_path = filter_data.get("media_path")

                    if filter_type == "text" or not media_path:
                        if response:
                            await bot.reply(msg, response)
                    else:
                        if Path(media_path).exists():
                            try:
                                await bot.send_media(
                                    msg.chat_jid, filter_type, media_path, response
                                )
                            except Exception as e:
                                await bot.reply(msg, t_error("filter.send_failed", error=str(e)))
                else:
                    await bot.reply(msg, filter_data)
                return
