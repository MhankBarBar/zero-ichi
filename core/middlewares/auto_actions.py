"""Auto-actions middleware — handle auto-read and auto-react."""

from core.runtime_config import runtime_config


async def auto_actions_middleware(ctx, next):
    """Handle auto-read and auto-react."""
    if runtime_config.get_nested("bot", "auto_read", default=False):
        await ctx.bot.mark_read(ctx.msg)

    emoji = runtime_config.get_nested("bot", "auto_react_emoji", default="")
    if emoji and runtime_config.get_nested("bot", "auto_react", default=False):
        try:
            await ctx.bot.send_reaction(ctx.msg, emoji)
        except Exception:
            pass

    await next()
