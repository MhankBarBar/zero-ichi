"""Features middleware — handle notes, filters, and other group features."""

from core.handlers import afk as afk_handler
from core.handlers import features as features_handler
from core.i18n import set_context


async def features_middleware(ctx, next):
    """Handle notes, filters, and other group features."""
    set_context(ctx.msg.chat_jid)
    await features_handler.handle_features(ctx.bot, ctx.msg)
    await afk_handler.handle_afk_mentions(ctx.bot, ctx.msg)
    await next()
