"""Stats middleware — track message stats and resolve chat type."""

from config.settings import LOG_MESSAGES
from core.event_bus import event_bus
from core.logger import show_message
from core.storage import Storage


async def stats_middleware(ctx, next):
    """Track message stats and resolve chat type."""
    stats_storage = Storage()
    stats_storage.increment_stat("messages_total")

    if ctx.msg.is_group:
        group_name = await ctx.bot.get_group_name(ctx.msg.chat_jid)
        ctx.chat_type = f"Group ({group_name})"

    if LOG_MESSAGES:
        show_message(ctx.chat_type, ctx.msg.sender_name, ctx.msg.text)

    await event_bus.emit(
        "new_message",
        {
            "sender": ctx.msg.sender_name,
            "chat": ctx.msg.chat_jid,
            "chat_type": ctx.chat_type,
            "text": (ctx.msg.text or "")[:100],
        },
    )

    ctx.extras["stats_storage"] = stats_storage
    await next()

