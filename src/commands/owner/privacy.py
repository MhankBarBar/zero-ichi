"""Owner privacy command - retention and AI memory controls."""

from __future__ import annotations

from ai.memory import clear_memory
from core import symbols as sym
from core.analytics import command_analytics
from core.command import Command, CommandContext
from core.config_ops import apply_config_operation
from core.i18n import t, t_error, t_info, t_success
from core.presentation import format_command_card
from core.privacy import (
    clear_chat_memory_override,
    get_ai_memory_ttl_hours,
    get_analytics_retention_days,
    get_chat_memory_override,
    is_chat_memory_enabled,
    set_chat_memory_enabled,
)
from core.runtime_config import runtime_config


class PrivacyCommand(Command):
    name = "privacy"
    description = "Manage privacy and retention settings"
    usage = "privacy status|retention|memory"
    owner_only = True

    async def _apply_change(self, ctx: CommandContext, operation):
        return await apply_config_operation(ctx, operation)

    async def execute(self, ctx: CommandContext) -> None:
        args = ctx.args
        if not args:
            await self._show_help(ctx)
            return

        action = args[0].lower()
        if action == "status":
            await self._status(ctx, args[1:])
            return
        if action == "retention":
            await self._retention(ctx, args[1:])
            return
        if action == "memory":
            await self._memory(ctx, args[1:])
            return

        await self._show_help(ctx)

    async def _show_help(self, ctx: CommandContext) -> None:
        """Show privacy command usage in command-card style."""
        card = format_command_card(
            ctx.prefix,
            self.name,
            self.description,
            self.get_usage(ctx.prefix),
            category="owner",
            restrictions=["Owner only"],
        )
        actions = [
            f"`{ctx.prefix}privacy status`",
            f"`{ctx.prefix}privacy retention analytics 30`",
            f"`{ctx.prefix}privacy retention memory-ttl 24`",
            f"`{ctx.prefix}privacy memory global on`",
            f"`{ctx.prefix}privacy memory off here`",
            f"`{ctx.prefix}privacy memory inherit here`",
            f"`{ctx.prefix}privacy memory clear here`",
        ]
        await ctx.client.reply(
            ctx.message,
            card + "\n\n" + sym.section(t("headers.list"), actions),
        )

    async def _status(self, ctx: CommandContext, args: list[str]) -> None:
        chat_jid = self._scope_to_chat_jid(ctx, args[0] if args else "here")
        if not chat_jid:
            await ctx.client.reply(ctx.message, t_error("privacy.invalid_scope"))
            return

        override = get_chat_memory_override(chat_jid)
        override_label = (
            t("privacy.inherit")
            if override is None
            else t("common.on")
            if override
            else t("common.off")
        )
        lines = [
            sym.status_line(t("privacy.analytics_retention"), f"{get_analytics_retention_days()}d"),
            sym.status_line(
                t("privacy.ai_memory_global"),
                t("common.on")
                if runtime_config.get_nested("privacy", "ai_memory_enabled", default=True)
                else t("common.off"),
            ),
            sym.status_line(t("privacy.ai_memory_ttl"), f"{get_ai_memory_ttl_hours()}h"),
            sym.status_line(t("privacy.chat"), chat_jid),
            sym.status_line(
                t("privacy.chat_memory_effective"),
                t("common.on") if is_chat_memory_enabled(chat_jid) else t("common.off"),
            ),
            sym.status_line(t("privacy.chat_memory_override"), override_label),
        ]
        await ctx.client.reply(ctx.message, sym.box(t("privacy.title"), lines))

    async def _retention(self, ctx: CommandContext, args: list[str]) -> None:
        if len(args) < 2:
            await ctx.client.reply(
                ctx.message, t_error("privacy.retention_usage", prefix=ctx.prefix)
            )
            return

        target = args[0].lower()
        value_raw = args[1]
        if target == "analytics":
            if not value_raw.isdigit():
                await ctx.client.reply(ctx.message, t_error("privacy.retention_range"))
                return
            days = int(value_raw)
            if days < 1 or days > 365:
                await ctx.client.reply(ctx.message, t_error("privacy.retention_range"))
                return
            changed = await self._apply_change(
                ctx,
                lambda: runtime_config.set_nested("privacy", "analytics_retention_days", days),
            )
            if changed is None:
                return
            command_analytics.apply_retention_now()
            await ctx.client.reply(
                ctx.message,
                t_success("privacy.analytics_retention_set", days=str(days)),
            )
            return

        if target == "memory-ttl":
            try:
                hours = float(value_raw)
            except ValueError:
                await ctx.client.reply(ctx.message, t_error("privacy.memory_ttl_range"))
                return

            if hours < 1 or hours > 720:
                await ctx.client.reply(ctx.message, t_error("privacy.memory_ttl_range"))
                return

            changed = await self._apply_change(
                ctx,
                lambda: runtime_config.set_nested("privacy", "ai_memory_ttl_hours", hours),
            )
            if changed is None:
                return
            await ctx.client.reply(
                ctx.message,
                t_success("privacy.memory_ttl_set", hours=str(hours)),
            )
            return

        await ctx.client.reply(ctx.message, t_error("privacy.retention_usage", prefix=ctx.prefix))

    async def _memory(self, ctx: CommandContext, args: list[str]) -> None:
        if not args:
            await ctx.client.reply(ctx.message, t_error("privacy.memory_usage", prefix=ctx.prefix))
            return

        action = args[0].lower()

        if action in {"on", "off"}:
            scope = args[1] if len(args) > 1 else "here"
            chat_jid = self._scope_to_chat_jid(ctx, scope)
            if not chat_jid:
                await ctx.client.reply(ctx.message, t_error("privacy.invalid_scope"))
                return
            enabled = action == "on"
            set_chat_memory_enabled(chat_jid, enabled)
            await ctx.client.reply(
                ctx.message,
                t_success(
                    "privacy.memory_set",
                    status=t("common.on") if enabled else t("common.off"),
                    chat=chat_jid,
                ),
            )
            return

        if action == "clear":
            scope = args[1] if len(args) > 1 else "here"
            if scope.lower() == "all":
                clear_memory()
                await ctx.client.reply(ctx.message, t_success("privacy.memory_cleared_all"))
                return

            chat_jid = self._scope_to_chat_jid(ctx, scope)
            if not chat_jid:
                await ctx.client.reply(ctx.message, t_error("privacy.invalid_scope"))
                return
            clear_memory(chat_jid)
            await ctx.client.reply(ctx.message, t_success("privacy.memory_cleared", chat=chat_jid))
            return

        if action == "inherit":
            scope = args[1] if len(args) > 1 else "here"
            chat_jid = self._scope_to_chat_jid(ctx, scope)
            if not chat_jid:
                await ctx.client.reply(ctx.message, t_error("privacy.invalid_scope"))
                return
            removed = clear_chat_memory_override(chat_jid)
            if not removed:
                await ctx.client.reply(ctx.message, t_info("privacy.no_override", chat=chat_jid))
                return
            await ctx.client.reply(
                ctx.message, t_success("privacy.override_cleared", chat=chat_jid)
            )
            return

        if action == "global" and len(args) >= 2:
            mode = args[1].lower()
            if mode not in {"on", "off"}:
                await ctx.client.reply(
                    ctx.message, t_error("privacy.memory_global_usage", prefix=ctx.prefix)
                )
                return
            changed = await self._apply_change(
                ctx,
                lambda: runtime_config.set_nested("privacy", "ai_memory_enabled", mode == "on"),
            )
            if changed is None:
                return
            await ctx.client.reply(
                ctx.message,
                t_success(
                    "privacy.memory_global_set",
                    status=t("common.on") if mode == "on" else t("common.off"),
                ),
            )
            return

        await ctx.client.reply(ctx.message, t_error("privacy.memory_usage", prefix=ctx.prefix))

    def _scope_to_chat_jid(self, ctx: CommandContext, scope: str) -> str | None:
        token = str(scope).strip().lower()
        if token in {"", "here"}:
            return ctx.message.chat_jid
        if "@" in token:
            return token
        return None
