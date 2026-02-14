"""Anti-delete middleware — cache messages and handle revocations."""

from core.handlers import antidelete


async def antidelete_middleware(ctx, next):
    """Cache messages and handle anti-delete revocations."""
    await antidelete.handle_anti_delete_cache(ctx.bot, ctx.event, ctx.msg)
    await antidelete.handle_anti_revoke(ctx.bot, ctx.event, ctx.msg)
    await next()
