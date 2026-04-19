"""Anti-spam middleware — rate-limit messages per user to prevent flooding."""

from __future__ import annotations

import time

from core import symbols as sym
from core.i18n import t
from core.moderation import execute_moderation_action, is_admin
from core.runtime_config import runtime_config

_spam_windows: dict[str, list[float]] = {}


def _cleanup_window(timestamps: list[float], window: float, now: float) -> list[float]:
    """Remove timestamps outside the current window."""
    cutoff = now - window
    return [ts for ts in timestamps if ts > cutoff]


async def anti_spam_middleware(ctx, next):
    """Detect and act on message spam based on configurable thresholds."""
    if not runtime_config.get_feature("anti_spam"):
        await next()
        return

    if not ctx.msg.is_group or ctx.msg.is_from_me:
        await next()
        return

    sender = ctx.msg.sender_jid

    whitelist_admins = runtime_config.get_nested("anti_spam", "whitelist_admins", default=True)
    if whitelist_admins:
        try:
            if await is_admin(ctx.bot, ctx.msg.chat_jid, sender):
                await next()
                return
        except Exception:
            pass

    max_messages = runtime_config.get_nested("anti_spam", "max_messages", default=5)
    window_seconds = runtime_config.get_nested("anti_spam", "window_seconds", default=10)
    action = str(runtime_config.get_nested("anti_spam", "action", default="warn")).lower()

    now = time.time()

    # Prune stale entries to prevent unbounded memory growth
    if len(_spam_windows) > 1000:
        stale_keys = [
            k for k, v in _spam_windows.items() if not v or (now - v[-1]) > window_seconds * 2
        ]
        for k in stale_keys:
            del _spam_windows[k]

    timestamps = _spam_windows.get(sender, [])
    timestamps = _cleanup_window(timestamps, window_seconds, now)
    timestamps.append(now)
    _spam_windows[sender] = timestamps

    if len(timestamps) <= max_messages:
        await next()
        return

    user_id = sender.split("@")[0].split(":")[0]

    if action == "mute":
        from core.storage import GroupData

        data = GroupData(ctx.msg.chat_jid)
        muted = data.muted
        if user_id not in muted:
            muted.append(user_id)
            data.save_muted(muted)
        await execute_moderation_action(ctx.bot, ctx.msg, "delete", "anti_spam")
        await ctx.bot.send(ctx.msg.chat_jid, t("anti_spam.muted", user=user_id))
    elif action == "kick":
        await execute_moderation_action(ctx.bot, ctx.msg, "kick", "anti_spam")
    else:
        await ctx.bot.send(
            ctx.msg.chat_jid,
            f"{sym.WARNING} {t('anti_spam.warn_message', user=user_id)}",
        )

    _spam_windows[sender] = []
