"""Self-mode middleware — skip messages not from self when in self mode."""

from config.settings import IGNORE_SELF_MESSAGES
from core.runtime_config import runtime_config


async def self_mode_middleware(ctx, next):
    """Skip messages not from self when in self mode."""
    if runtime_config.self_mode:
        if not ctx.msg.is_from_me:
            return
    elif IGNORE_SELF_MESSAGES and ctx.msg.is_from_me:
        return
    await next()
