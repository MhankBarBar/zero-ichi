"""Mute middleware — skip messages from muted users."""

from core.handlers import mute as mute_handler


async def mute_middleware(ctx, next):
    """Skip messages from muted users."""
    if await mute_handler.handle_muted_users(ctx.bot, ctx.msg):
        return
    await next()
