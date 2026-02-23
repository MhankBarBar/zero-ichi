"""Anti-link middleware — block messages containing links if enabled."""

from core.handlers import antilink as antilink_handler


async def antilink_middleware(ctx, next):
    """Block messages containing links if anti-link is enabled."""
    if await antilink_handler.handle_anti_link(ctx.bot, ctx.msg):
        return
    await next()
