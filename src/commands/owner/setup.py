"""Owner setup wizard command - guided first-run configuration."""

from __future__ import annotations

from core import symbols as sym
from core.command import Command, CommandContext
from core.config_ops import apply_config_operation
from core.i18n import t, t_error, t_success
from core.presentation import format_command_card
from core.runtime_config import runtime_config


class SetupCommand(Command):
    name = "setup"
    description = "Guided setup wizard for common bot settings"
    usage = (
        "setup|start|status|done | setup owner me|<jid> | setup prefix <prefix> | "
        "setup anti-link <on|off> [warn|delete|kick] | "
        "setup anti-spam <on|off> [warn|mute|kick] | "
        "setup ai <on|off> | setup ai-key <key>"
    )
    owner_only = True

    async def execute(self, ctx: CommandContext) -> None:
        args = ctx.args
        if not args:
            await self._show_help(ctx)
            return

        action = args[0].lower()
        if action in {"start", "status"}:
            await self._show_status(ctx, started=action == "start")
            return
        if action == "owner":
            await self._set_owner(ctx, args[1:])
            return
        if action == "prefix":
            await self._set_prefix(ctx, args[1:])
            return
        if action == "anti-link":
            await self._set_anti_link(ctx, args[1:])
            return
        if action == "anti-spam":
            await self._set_anti_spam(ctx, args[1:])
            return
        if action == "ai":
            await self._set_ai(ctx, args[1:])
            return
        if action == "ai-key":
            await self._set_ai_key(ctx, args[1:])
            return
        if action == "done":
            await self._show_done(ctx)
            return

        await self._show_help(ctx)

    async def _show_help(self, ctx: CommandContext) -> None:
        """Show setup command help using command-card style."""
        card = format_command_card(
            ctx.prefix,
            self.name,
            self.description,
            self.get_usage(ctx.prefix),
            category="owner",
            restrictions=["Owner only"],
        )
        lines = [
            f"`{ctx.prefix}setup start`",
            f"`{ctx.prefix}setup status`",
            f"`{ctx.prefix}setup owner me`",
            f"`{ctx.prefix}setup prefix !`",
            f"`{ctx.prefix}setup anti-link on warn`",
            f"`{ctx.prefix}setup anti-spam on warn`",
            f"`{ctx.prefix}setup ai-key <key>`",
            f"`{ctx.prefix}setup ai on`",
            f"`{ctx.prefix}setup done`",
        ]
        await ctx.client.reply(
            ctx.message, card + "\n\n" + sym.section(t("setup.next_steps"), lines)
        )

    async def _apply_change(self, ctx: CommandContext, operation) -> bool:
        """Apply a setup mutation with validation-friendly errors."""
        return bool(await apply_config_operation(ctx, operation))

    async def _show_status(self, ctx: CommandContext, *, started: bool) -> None:
        owner = runtime_config.get_owner_jid()
        prefix = runtime_config.prefix
        anti_link = runtime_config.get_feature("anti_link")
        anti_spam = runtime_config.get_feature("anti_spam")
        ai_enabled = runtime_config.get_nested("agentic_ai", "enabled", default=False)
        ai_key = runtime_config.get_nested("agentic_ai", "api_key", default="")

        lines = [
            sym.status_line(t("setup.owner"), t("setup.set") if owner else t("setup.not_set")),
            sym.status_line(t("setup.prefix"), f"`{prefix}`"),
            sym.status_line(t("setup.anti_link"), t("common.on") if anti_link else t("common.off")),
            sym.status_line(t("setup.anti_spam"), t("common.on") if anti_spam else t("common.off")),
            sym.status_line(t("setup.ai"), t("common.on") if ai_enabled else t("common.off")),
            sym.status_line(t("setup.ai_key"), t("setup.set") if ai_key else t("setup.not_set")),
        ]

        commands = [
            f"`{ctx.prefix}setup owner me`",
            f"`{ctx.prefix}setup prefix !`",
            f"`{ctx.prefix}setup anti-link on warn`",
            f"`{ctx.prefix}setup anti-spam on warn`",
            f"`{ctx.prefix}setup ai-key <key>`",
            f"`{ctx.prefix}setup ai on`",
            f"`{ctx.prefix}setup done`",
        ]

        parts = []
        if started:
            parts.append(f"{sym.SPARKLE} {t('setup.started')}")
            parts.append("")

        parts.append(sym.box(t("setup.title"), lines))
        parts.append("")
        parts.append(sym.section(t("setup.next_steps"), commands))
        await ctx.client.reply(ctx.message, "\n".join(parts))

    async def _set_owner(self, ctx: CommandContext, args: list[str]) -> None:
        if not args:
            await ctx.client.reply(ctx.message, t_error("setup.owner_usage", prefix=ctx.prefix))
            return
        value = args[0]
        owner_jid = ctx.message.sender_jid if value.lower() == "me" else value
        if not await self._apply_change(ctx, lambda: runtime_config.set_owner_jid(owner_jid)):
            return
        await ctx.client.reply(ctx.message, t_success("setup.owner_set", owner=owner_jid))

    async def _set_prefix(self, ctx: CommandContext, args: list[str]) -> None:
        if not args:
            await ctx.client.reply(ctx.message, t_error("setup.prefix_usage", prefix=ctx.prefix))
            return
        prefix = args[0].strip()
        if not prefix:
            await ctx.client.reply(ctx.message, t_error("setup.prefix_usage", prefix=ctx.prefix))
            return
        if not await self._apply_change(
            ctx, lambda: runtime_config.set_nested("bot", "prefix", prefix)
        ):
            return
        await ctx.client.reply(ctx.message, t_success("setup.prefix_set", prefix=prefix))

    async def _set_anti_link(self, ctx: CommandContext, args: list[str]) -> None:
        if not args:
            await ctx.client.reply(
                ctx.message,
                t_error("setup.anti_link_usage", prefix=ctx.prefix),
            )
            return

        state = args[0].lower()
        if state not in {"on", "off"}:
            await ctx.client.reply(
                ctx.message,
                t_error("setup.anti_link_usage", prefix=ctx.prefix),
            )
            return

        if not await self._apply_change(
            ctx, lambda: runtime_config.set_feature("anti_link", state == "on")
        ):
            return

        if len(args) > 1:
            action = args[1].lower()
            if action not in {"warn", "delete", "kick"}:
                await ctx.client.reply(ctx.message, t_error("setup.anti_link_action_usage"))
                return
            if not await self._apply_change(
                ctx,
                lambda: runtime_config.set_nested("anti_link", "action", action),
            ):
                return
            await ctx.client.reply(
                ctx.message,
                t_success(
                    "setup.anti_link_set",
                    status=t("common.on") if state == "on" else t("common.off"),
                    action=action,
                ),
            )
            return

        await ctx.client.reply(
            ctx.message,
            t_success(
                "setup.anti_link_set",
                status=t("common.on") if state == "on" else t("common.off"),
                action=runtime_config.get_nested("anti_link", "action", default="warn"),
            ),
        )

    async def _set_anti_spam(self, ctx: CommandContext, args: list[str]) -> None:
        if not args:
            await ctx.client.reply(
                ctx.message,
                t_error("setup.anti_spam_usage", prefix=ctx.prefix),
            )
            return

        state = args[0].lower()
        if state not in {"on", "off"}:
            await ctx.client.reply(
                ctx.message,
                t_error("setup.anti_spam_usage", prefix=ctx.prefix),
            )
            return

        if not await self._apply_change(
            ctx, lambda: runtime_config.set_feature("anti_spam", state == "on")
        ):
            return

        if len(args) > 1:
            action = args[1].lower()
            if action not in {"warn", "mute", "kick"}:
                await ctx.client.reply(ctx.message, t_error("setup.anti_spam_action_usage"))
                return
            if not await self._apply_change(
                ctx,
                lambda: runtime_config.set_nested("anti_spam", "action", action),
            ):
                return
            await ctx.client.reply(
                ctx.message,
                t_success(
                    "setup.anti_spam_set",
                    status=t("common.on") if state == "on" else t("common.off"),
                    action=action,
                ),
            )
            return

        await ctx.client.reply(
            ctx.message,
            t_success(
                "setup.anti_spam_set",
                status=t("common.on") if state == "on" else t("common.off"),
                action=runtime_config.get_nested("anti_spam", "action", default="warn"),
            ),
        )

    async def _set_ai(self, ctx: CommandContext, args: list[str]) -> None:
        if not args:
            await ctx.client.reply(ctx.message, t_error("setup.ai_usage", prefix=ctx.prefix))
            return

        state = args[0].lower()
        if state not in {"on", "off"}:
            await ctx.client.reply(ctx.message, t_error("setup.ai_usage", prefix=ctx.prefix))
            return

        if state == "on":
            key = runtime_config.get_nested("agentic_ai", "api_key", default="")
            if not key:
                await ctx.client.reply(
                    ctx.message,
                    t_error("setup.ai_missing_key", prefix=ctx.prefix),
                )
                return

        if not await self._apply_change(
            ctx,
            lambda: runtime_config.set_nested("agentic_ai", "enabled", state == "on"),
        ):
            return
        await ctx.client.reply(
            ctx.message,
            t_success("setup.ai_set", status=t("common.on") if state == "on" else t("common.off")),
        )

    async def _set_ai_key(self, ctx: CommandContext, args: list[str]) -> None:
        if not args:
            await ctx.client.reply(ctx.message, t_error("setup.ai_key_usage", prefix=ctx.prefix))
            return

        key = " ".join(args).strip()
        if not key:
            await ctx.client.reply(ctx.message, t_error("setup.ai_key_usage", prefix=ctx.prefix))
            return

        if not await self._apply_change(
            ctx,
            lambda: runtime_config.set_nested("agentic_ai", "api_key", key),
        ):
            return
        await ctx.client.reply(ctx.message, t_success("setup.ai_key_set"))

    async def _show_done(self, ctx: CommandContext) -> None:
        owner = runtime_config.get_owner_jid()
        anti_spam = runtime_config.get_feature("anti_spam")
        anti_link = runtime_config.get_feature("anti_link")
        ai_enabled = runtime_config.get_nested("agentic_ai", "enabled", default=False)

        lines = [
            sym.status_line(t("setup.owner"), t("setup.set") if owner else t("setup.not_set")),
            sym.status_line(t("setup.anti_link"), t("common.on") if anti_link else t("common.off")),
            sym.status_line(t("setup.anti_spam"), t("common.on") if anti_spam else t("common.off")),
            sym.status_line(t("setup.ai"), t("common.on") if ai_enabled else t("common.off")),
        ]
        await ctx.client.reply(ctx.message, sym.box(t("setup.completed"), lines))
