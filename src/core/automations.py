"""Automation rule helpers and executor."""

from __future__ import annotations

import re
from typing import Any

from core.event_bus import event_bus
from core.i18n import t
from core.moderation import execute_moderation_action
from core.storage import GroupData

URL_PATTERN = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE)


def load_rules(group_jid: str) -> list[dict[str, Any]]:
    """Load automation rules for group."""
    rules = GroupData(group_jid).automations
    normalized = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        normalized.append(
            {
                "id": str(rule.get("id", "")).strip() or "",
                "name": str(rule.get("name", "")).strip() or "Rule",
                "enabled": bool(rule.get("enabled", True)),
                "trigger_type": str(rule.get("trigger_type", "contains")).lower(),
                "trigger_value": str(rule.get("trigger_value", "")).strip(),
                "action_type": str(rule.get("action_type", "reply")).lower(),
                "action_value": str(rule.get("action_value", "")),
            }
        )
    return normalized


def save_rules(group_jid: str, rules: list[dict[str, Any]]) -> None:
    """Save automation rules for group."""
    GroupData(group_jid).save_automations(rules)


def next_rule_id(rules: list[dict[str, Any]]) -> str:
    """Generate next rule id like A001."""
    max_idx = 0
    for rule in rules:
        rid = str(rule.get("id", ""))
        if len(rid) == 4 and rid[0].upper() == "A" and rid[1:].isdigit():
            max_idx = max(max_idx, int(rid[1:]))
    return f"A{max_idx + 1:03d}"


def rule_matches(rule: dict[str, Any], text: str) -> bool:
    """Evaluate if a rule matches text."""
    trigger_type = str(rule.get("trigger_type", "contains")).lower()
    trigger_value = str(rule.get("trigger_value", ""))
    if not trigger_value and trigger_type != "link":
        return False

    lower_text = text.lower()
    if trigger_type == "contains":
        return trigger_value.lower() in lower_text
    if trigger_type == "regex":
        try:
            return re.search(trigger_value, text, re.IGNORECASE) is not None
        except re.error:
            return False
    if trigger_type == "link":
        return bool(URL_PATTERN.search(text))
    return False


async def execute_rule(rule: dict[str, Any], bot, msg) -> bool:
    """Execute one automation rule. Returns True if an action was executed."""
    action_type = str(rule.get("action_type", "reply")).lower()
    action_value = str(rule.get("action_value", "")).strip()

    if action_type == "reply":
        await bot.reply(msg, action_value or t("automation.default_reply"))
    elif action_type in {"warn", "delete", "kick", "ban"}:
        normalized = "kick" if action_type == "ban" else action_type
        await execute_moderation_action(bot, msg, normalized, "automation")
    elif action_type == "mute":
        data = GroupData(msg.chat_jid)
        muted = data.muted
        sender_id = msg.sender_jid.split("@")[0].split(":")[0]
        if sender_id not in muted:
            muted.append(sender_id)
            data.save_muted(muted)
        await execute_moderation_action(bot, msg, "delete", "automation")
        await bot.send(msg.chat_jid, t("automation.muted", user=sender_id))
    else:
        return False

    await event_bus.emit(
        "automation_triggered",
        {
            "group_id": msg.chat_jid,
            "rule_id": rule.get("id", ""),
            "action": action_type,
            "sender": msg.sender_jid,
        },
    )
    return True
