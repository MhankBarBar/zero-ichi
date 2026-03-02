"""Automation command - manage no-code automation rules."""

from __future__ import annotations

from core.automations import load_rules, next_rule_id, save_rules
from core.command import Command, CommandContext
from core.event_bus import event_bus
from core.i18n import t, t_error, t_success
from core.permissions import check_admin_permission


class AutomationCommand(Command):
    name = "automation"
    aliases = ["automations", "rule", "ruleset"]
    description = "Manage automation rules"
    usage = "automation list|add|remove|toggle"
    group_only = True
    admin_only = True

    async def execute(self, ctx: CommandContext) -> None:
        if not await check_admin_permission(
            ctx.client, ctx.message.chat_jid, ctx.message.sender_jid
        ):
            await ctx.client.reply(ctx.message, t_error("errors.admin_required"))
            return

        args = ctx.args
        if not args:
            await ctx.client.reply(ctx.message, t_error("automation.usage", prefix=ctx.prefix))
            return

        action = args[0].lower()
        if action == "list":
            await self._list_rules(ctx)
            return

        if action == "remove" and len(args) >= 2:
            await self._remove_rule(ctx, args[1])
            return

        if action == "toggle" and len(args) >= 2:
            await self._toggle_rule(ctx, args[1])
            return

        if action == "add":
            await self._add_rule(ctx)
            return

        await ctx.client.reply(ctx.message, t_error("automation.usage", prefix=ctx.prefix))

    async def _list_rules(self, ctx: CommandContext) -> None:
        rules = load_rules(ctx.message.chat_jid)
        if not rules:
            await ctx.client.reply(ctx.message, t("automation.none"))
            return

        lines = [f"*{t('automation.title')}*", ""]
        for rule in rules:
            lines.append(
                t(
                    "automation.item",
                    id=rule["id"],
                    status=t("common.on") if rule.get("enabled", True) else t("common.off"),
                    trigger_type=rule.get("trigger_type", "contains"),
                    trigger_value=rule.get("trigger_value", ""),
                    action=rule.get("action_type", "reply"),
                )
            )
        await ctx.client.reply(ctx.message, "\n".join(lines))

    async def _add_rule(self, ctx: CommandContext) -> None:
        raw = ctx.raw_args[len("add") :].strip()
        if "=>" not in raw:
            await ctx.client.reply(ctx.message, t_error("automation.add_usage", prefix=ctx.prefix))
            return

        left, right = raw.split("=>", 1)
        left_parts = left.strip().split(maxsplit=1)
        if len(left_parts) < 2:
            await ctx.client.reply(ctx.message, t_error("automation.add_usage", prefix=ctx.prefix))
            return

        trigger_type = left_parts[0].lower()
        trigger_value = left_parts[1].strip()

        right_parts = right.strip().split(maxsplit=1)
        if not right_parts:
            await ctx.client.reply(ctx.message, t_error("automation.add_usage", prefix=ctx.prefix))
            return

        action_type = right_parts[0].lower()
        action_value = right_parts[1].strip() if len(right_parts) > 1 else ""

        valid_trigger = {"contains", "regex", "link"}
        valid_action = {"reply", "warn", "delete", "kick", "mute"}
        if trigger_type not in valid_trigger:
            await ctx.client.reply(ctx.message, t_error("automation.invalid_trigger"))
            return
        if action_type not in valid_action:
            await ctx.client.reply(ctx.message, t_error("automation.invalid_action"))
            return
        if trigger_type != "link" and not trigger_value:
            await ctx.client.reply(ctx.message, t_error("automation.missing_trigger_value"))
            return

        rules = load_rules(ctx.message.chat_jid)
        rid = next_rule_id(rules)
        rule = {
            "id": rid,
            "name": f"Rule {rid}",
            "enabled": True,
            "trigger_type": trigger_type,
            "trigger_value": trigger_value,
            "action_type": action_type,
            "action_value": action_value,
        }
        rules.append(rule)
        save_rules(ctx.message.chat_jid, rules)
        await event_bus.emit(
            "automation_update", {"group_id": ctx.message.chat_jid, "action": "created"}
        )
        await ctx.client.reply(ctx.message, t_success("automation.added", id=rid))

    async def _remove_rule(self, ctx: CommandContext, rule_id: str) -> None:
        rules = load_rules(ctx.message.chat_jid)
        rid = rule_id.strip().upper()
        updated = [r for r in rules if str(r.get("id", "")).upper() != rid]
        if len(updated) == len(rules):
            await ctx.client.reply(ctx.message, t_error("automation.not_found", id=rid))
            return

        save_rules(ctx.message.chat_jid, updated)
        await event_bus.emit(
            "automation_update", {"group_id": ctx.message.chat_jid, "action": "deleted"}
        )
        await ctx.client.reply(ctx.message, t_success("automation.removed", id=rid))

    async def _toggle_rule(self, ctx: CommandContext, rule_id: str) -> None:
        rules = load_rules(ctx.message.chat_jid)
        rid = rule_id.strip().upper()
        found = None
        for rule in rules:
            if str(rule.get("id", "")).upper() == rid:
                rule["enabled"] = not bool(rule.get("enabled", True))
                found = rule
                break

        if not found:
            await ctx.client.reply(ctx.message, t_error("automation.not_found", id=rid))
            return

        save_rules(ctx.message.chat_jid, rules)
        await event_bus.emit(
            "automation_update", {"group_id": ctx.message.chat_jid, "action": "updated"}
        )
        await ctx.client.reply(
            ctx.message,
            t_success(
                "automation.toggled",
                id=rid,
                status=t("common.on") if found.get("enabled") else t("common.off"),
            ),
        )
