"""
Middleware pipeline for processing incoming messages.

Each middleware is a callable that receives a MessageContext and a `next` function.
Calling `await next()` passes control to the next middleware in the chain.
If a middleware does NOT call `next()`, the pipeline stops (message is consumed).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.client import BotClient
    from core.message import MessageHelper


@dataclass
class MessageContext:
    """Shared context passed through the middleware pipeline."""

    bot: BotClient
    msg: MessageHelper
    event: Any
    chat_type: str = "Private"
    extras: dict = field(default_factory=dict)


MiddlewareFunc = Callable[[MessageContext, Callable[[], Awaitable[None]]], Awaitable[None]]


class MiddlewarePipeline:
    """Composable middleware pipeline for message handling."""

    def __init__(self) -> None:
        self._middlewares: list[tuple[str, MiddlewareFunc]] = []

    def use(self, name: str, middleware: MiddlewareFunc) -> MiddlewarePipeline:
        """Register a middleware. Returns self for chaining."""
        self._middlewares.append((name, middleware))
        return self

    async def execute(self, ctx: MessageContext) -> None:
        """Execute the pipeline in order."""
        index = 0

        async def next_middleware() -> None:
            nonlocal index
            if index < len(self._middlewares):
                _name, mw = self._middlewares[index]
                index += 1
                await mw(ctx, next_middleware)

        await next_middleware()

    @property
    def middlewares(self) -> list[str]:
        """List registered middleware names."""
        return [name for name, _ in self._middlewares]
