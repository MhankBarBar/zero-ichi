"""Self-mode middleware — skip messages not from self when in self mode."""

from core.runtime_config import runtime_config


async def self_mode_middleware(ctx, next):
    """Skip messages not from self when in self mode."""
    if runtime_config.self_mode:
        if not ctx.msg.is_from_me:
            return
    else:
        ignore_self_messages = runtime_config.get_nested(
            "bot", "ignore_self_messages", default=True
        )
        if ignore_self_messages and ctx.msg.is_from_me:
            return
    await next()
