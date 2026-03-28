"""Shared helpers for safe runtime config mutations in commands."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.i18n import t_error
from core.runtime_config import runtime_config


async def apply_config_operation(
    ctx: Any,
    operation: Callable[[], Any],
    *,
    preflight: bool = True,
) -> Any:
    """Run a config mutation with optional preflight schema validation and unified errors."""
    if preflight:
        ok, details = runtime_config.validate_current()
        if not ok:
            await ctx.client.reply(ctx.message, t_error("config.preflight_failed", details=details))
            return None

    try:
        result = operation()
        return True if result is None else result
    except ValueError as e:
        await ctx.client.reply(ctx.message, t_error("config.validation_failed", details=str(e)))
        return None
    except Exception as e:
        await ctx.client.reply(ctx.message, t_error("config.update_failed", error=str(e)))
        return None
