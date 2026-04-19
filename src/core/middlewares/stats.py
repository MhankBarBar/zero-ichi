"""Stats middleware — track message stats and resolve chat type."""

from core.event_bus import event_bus
from core.logger import show_message
from core.runtime_config import runtime_config
from core.storage import Storage

_stats_storage = Storage()


async def stats_middleware(ctx, next):
    """Track message stats and resolve chat type."""
    _stats_storage.increment_stat("messages_total")

    group_name = ""
    if ctx.msg.is_group:
        group_name = await ctx.bot.get_group_name(ctx.msg.chat_jid)
        ctx.chat_type = "Group"

    if runtime_config.get_nested("logging", "log_messages", default=True):
        show_message(ctx.chat_type, ctx.msg.sender_name, ctx.msg.text)

    await event_bus.emit(
        "new_message",
        {
            "sender": ctx.msg.sender_name,
            "chat": ctx.msg.chat_jid,
            "chat_type": ctx.chat_type,
            "group_name": group_name,
            "text": (ctx.msg.text or "")[:100],
        },
    )

    ctx.extras["stats_storage"] = _stats_storage
    await next()
