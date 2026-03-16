"""Automation middleware — evaluate and execute group automation rules."""

from core.automations import execute_rule, load_rules, rule_matches
from core.runtime_config import runtime_config


def _has_media_type_rules(rules: list[dict]) -> bool:
    """Check if any enabled rules use the media_type trigger."""
    return any(
        r.get("enabled", True) and str(r.get("trigger_type", "")).lower() == "media_type"
        for r in rules
    )


async def automations_middleware(ctx, next):
    """Evaluate automation rules for incoming group messages."""
    if not runtime_config.get_nested("features", "automation_rules", default=True):
        await next()
        return

    if not ctx.msg.is_group or ctx.msg.is_from_me:
        await next()
        return

    rules = load_rules(ctx.msg.chat_jid)
    if not rules:
        await next()
        return

    text = ctx.msg.text
    if not text and not _has_media_type_rules(rules):
        await next()
        return

    media_type = None
    if not text or _has_media_type_rules(rules):
        _, media_type = ctx.msg.get_media_message()

    for rule in rules:
        if not rule.get("enabled", True):
            continue
        if not rule_matches(rule, text or "", media_type=media_type):
            continue

        try:
            executed = await execute_rule(rule, ctx.bot, ctx.msg)
            if executed:
                return
        except Exception:
            continue

    await next()
