"""Automation rule helpers and executor."""

from __future__ import annotations

import re
from typing import Any

from core.event_bus import event_bus
from core.i18n import t
from core.id_utils import next_prefixed_id
from core.moderation import execute_moderation_action
from core.storage import GroupData
from core.url_patterns import URL_PATTERN

TRIGGER_TYPES = {
    "contains",
    "starts_with",
    "exact_match",
    "regex",
    "link",
    "media_type",
}
ACTION_TYPES = {"reply", "warn", "delete", "kick", "mute"}
ACTION_ALIASES = {"ban": "kick"}


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


def get_automation_runtime(group_jid: str) -> dict[str, Any]:
    """Get per-group automation runtime settings."""
    data = GroupData(group_jid).load("automation_runtime", {"dry_run": False})
    if not isinstance(data, dict):
        data = {"dry_run": False}
    data.setdefault("dry_run", False)
    data["dry_run"] = bool(data.get("dry_run", False))
    return data


def set_automation_dry_run(group_jid: str, enabled: bool) -> None:
    """Set per-group automation dry-run mode."""
    runtime = get_automation_runtime(group_jid)
    runtime["dry_run"] = bool(enabled)
    GroupData(group_jid).save("automation_runtime", runtime)


def next_rule_id(rules: list[dict[str, Any]]) -> str:
    """Generate next rule id like A001."""
    return next_prefixed_id(rules, prefix="A", width=3)


def is_valid_trigger(trigger_type: str) -> bool:
    """Check if trigger type is supported."""
    return str(trigger_type).lower() in TRIGGER_TYPES


def normalize_action(action_type: str) -> str:
    """Normalize action aliases into canonical action type."""
    raw = str(action_type).lower().strip()
    return ACTION_ALIASES.get(raw, raw)


def is_valid_action(action_type: str) -> bool:
    """Check if action type is supported (including aliases)."""
    return normalize_action(action_type) in ACTION_TYPES


def rule_matches(rule: dict[str, Any], text: str, media_type: str | None = None) -> bool:
    """Evaluate if a rule matches text (or media type for media_type triggers)."""
    trigger_type = str(rule.get("trigger_type", "contains")).lower()
    trigger_value = str(rule.get("trigger_value", ""))

    if trigger_type == "media_type":
        if not trigger_value or not media_type:
            return False
        return media_type.lower() == trigger_value.lower()

    if not trigger_value and trigger_type != "link":
        return False

    if not text:
        return False

    lower_text = text.lower()
    if trigger_type == "contains":
        return trigger_value.lower() in lower_text
    if trigger_type == "exact_match":
        return lower_text.strip() == trigger_value.lower().strip()
    if trigger_type == "starts_with":
        return lower_text.startswith(trigger_value.lower())
    if trigger_type == "regex":
        if len(trigger_value) > 200:
            return False
        try:
            pattern = re.compile(trigger_value, re.IGNORECASE)
            # Limit input length to prevent ReDoS on pathological patterns
            safe_text = text[:5000] if len(text) > 5000 else text
            return pattern.search(safe_text) is not None
        except re.error:
            return False
    if trigger_type == "link":
        return bool(URL_PATTERN.search(text))
    return False


async def execute_rule(rule: dict[str, Any], bot, msg) -> bool:
    """Execute one automation rule. Returns True if an action was executed."""
    action_type = normalize_action(str(rule.get("action_type", "reply")).lower())
    action_value = str(rule.get("action_value", "")).strip()

    if action_type == "reply":
        await bot.reply(msg, action_value or t("automation.default_reply"))
    elif action_type in {"warn", "delete", "kick"}:
        await execute_moderation_action(bot, msg, action_type, "automation")
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
