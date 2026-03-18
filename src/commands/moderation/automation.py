"""Automation command - manage no-code automation rules."""

from __future__ import annotations

from core.automations import (
    get_automation_runtime,
    load_rules,
    next_rule_id,
    rule_matches,
    save_rules,
    set_automation_dry_run,
)
from core.command import Command, CommandContext
from core.event_bus import event_bus
from core.i18n import t, t_error, t_success
from core.permissions import check_admin_permission


class AutomationCommand(Command):
    name = "automation"
    aliases = ["automations", "rule", "ruleset"]
    description = "Manage automation rules"
    usage = "automation list|add|remove|toggle|simulate|dryrun"
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

        if action == "simulate":
            await self._simulate_rule(ctx, args[1:])
            return

        if action == "dryrun":
            await self._set_dry_run(ctx, args[1:])
            return

        await ctx.client.reply(ctx.message, t_error("automation.usage", prefix=ctx.prefix))

    async def _list_rules(self, ctx: CommandContext) -> None:
        rules = load_rules(ctx.message.chat_jid)
        runtime = get_automation_runtime(ctx.message.chat_jid)
        dry_run = bool(runtime.get("dry_run", False))

        if not rules:
            await ctx.client.reply(
                ctx.message,
                f"{t('automation.none')}\n{t('automation.dryrun_status', status=t('common.on') if dry_run else t('common.off'))}",
            )
            return

        lines = [
            f"*{t('automation.title')}*",
            t("automation.dryrun_status", status=t("common.on") if dry_run else t("common.off")),
            "",
        ]
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

        valid_trigger = {"contains", "starts_with", "exact_match", "regex", "link", "media_type"}
        valid_action = {"reply", "warn", "delete", "kick", "mute"}
        if trigger_type not in valid_trigger:
            await ctx.client.reply(ctx.message, t_error("automation.invalid_trigger"))
            return
        if action_type not in valid_action:
            await ctx.client.reply(ctx.message, t_error("automation.invalid_action"))
            return
        if trigger_type not in {"link"} and not trigger_value:
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

    async def _simulate_rule(self, ctx: CommandContext, args: list[str]) -> None:
        """Simulate whether a rule would match sample input."""
        if not args:
            await ctx.client.reply(
                ctx.message, t_error("automation.simulate_usage", prefix=ctx.prefix)
            )
            return

        rid = args[0].strip().upper()
        rule = None
        rules = load_rules(ctx.message.chat_jid)
        for item in rules:
            if str(item.get("id", "")).upper() == rid:
                rule = item
                break

        if not rule:
            await ctx.client.reply(ctx.message, t_error("automation.not_found", id=rid))
            return

        media_type = ""
        sample_tokens: list[str] = []
        idx = 1
        while idx < len(args):
            token = args[idx]
            if token.lower() == "--media" and idx + 1 < len(args):
                media_type = args[idx + 1].lower().strip()
                idx += 2
                continue
            sample_tokens.append(token)
            idx += 1

        sample_text = " ".join(sample_tokens).strip()
        trigger_type = str(rule.get("trigger_type", "contains"))
        if trigger_type != "media_type" and not sample_text:
            await ctx.client.reply(
                ctx.message, t_error("automation.simulate_usage", prefix=ctx.prefix)
            )
            return

        if trigger_type == "media_type" and not media_type:
            media_type = str(rule.get("trigger_value", "")).lower()

        matched = rule_matches(rule, sample_text, media_type=media_type or None)
        status = t("automation.simulate_match") if matched else t("automation.simulate_no_match")
        sample_display = sample_text or "(empty)"
        media_display = media_type or "-"

        lines = [
            t("automation.simulate_result", id=rid, status=status),
            t(
                "automation.simulate_rule",
                trigger_type=trigger_type,
                trigger_value=str(rule.get("trigger_value", "")),
                action=str(rule.get("action_type", "reply")),
            ),
            t("automation.simulate_input", text=sample_display, media=media_display),
        ]
        await ctx.client.reply(ctx.message, "\n".join(lines))

    async def _set_dry_run(self, ctx: CommandContext, args: list[str]) -> None:
        """Set or show automation dry-run mode for this group."""
        if not args:
            runtime = get_automation_runtime(ctx.message.chat_jid)
            await ctx.client.reply(
                ctx.message,
                t(
                    "automation.dryrun_status",
                    status=t("common.on") if runtime.get("dry_run") else t("common.off"),
                ),
            )
            return

        mode = args[0].lower()
        if mode not in {"on", "off"}:
            await ctx.client.reply(
                ctx.message, t_error("automation.dryrun_usage", prefix=ctx.prefix)
            )
            return

        enabled = mode == "on"
        set_automation_dry_run(ctx.message.chat_jid, enabled)
        await ctx.client.reply(
            ctx.message,
            t_success(
                "automation.dryrun_set", status=t("common.on") if enabled else t("common.off")
            ),
        )
