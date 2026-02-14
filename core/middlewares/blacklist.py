"""Blacklist middleware — block messages containing blacklisted words."""

from core.handlers import blacklist as blacklist_handler


async def blacklist_middleware(ctx, next):
    """Block messages containing blacklisted words."""
    if await blacklist_handler.handle_blacklist(ctx.bot, ctx.msg):
        return
    await next()
