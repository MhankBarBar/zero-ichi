"""Automation middleware — evaluate and execute group automation rules."""

from core.automations import execute_rule, load_rules, rule_matches
from core.runtime_config import runtime_config


async def automations_middleware(ctx, next):
    """Evaluate automation rules for incoming group messages."""
    if not runtime_config.get_nested("features", "automation_rules", default=True):
        await next()
        return

    if not ctx.msg.is_group or not ctx.msg.text or ctx.msg.is_from_me:
        await next()
        return

    rules = load_rules(ctx.msg.chat_jid)
    if not rules:
        await next()
        return

    text = ctx.msg.text
    for rule in rules:
        if not rule.get("enabled", True):
            continue
        if not rule_matches(rule, text):
            continue

        try:
            executed = await execute_rule(rule, ctx.bot, ctx.msg)
            if executed:
                return
        except Exception:
            continue

    await next()
