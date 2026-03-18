"""Status command - quick bot health and runtime status."""

from __future__ import annotations

import time

from sqlalchemy import text

from core import symbols as sym
from core.command import Command, CommandContext, command_loader
from core.i18n import t
from core.runtime_config import runtime_config
from core.webhooks import webhook_dispatcher_status


def _format_uptime(seconds: float) -> str:
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


class StatusCommand(Command):
    name = "status"
    aliases = ["health"]
    description = "Show runtime health and key subsystem status"
    usage = "status"
    category = "general"

    async def execute(self, ctx: CommandContext) -> None:
        from commands.general.uptime import _start_time
        from core.db import get_engine

        uptime = _format_uptime(time.time() - _start_time)

        db_ok = False
        try:
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            db_ok = False

        webhook = webhook_dispatcher_status()
        ai_enabled = runtime_config.get_nested("agentic_ai", "enabled", default=False)
        ai_provider = runtime_config.get_nested("agentic_ai", "provider", default="openai")
        ai_model = runtime_config.get_nested("agentic_ai", "model", default="gpt-5-mini")
        rate_limit_enabled = runtime_config.get_nested("rate_limit", "enabled", default=True)

        lines = [
            sym.status_line(t("status.uptime"), uptime),
            sym.status_line(t("status.db"), t("common.on") if db_ok else t("common.off")),
            sym.status_line(
                t("status.webhook_worker"),
                t("common.on") if webhook.get("running") else t("common.off"),
            ),
            sym.status_line(t("status.webhook_queue"), str(webhook.get("queue_size", 0))),
            sym.status_line(t("status.ai"), t("common.on") if ai_enabled else t("common.off")),
            sym.status_line(t("status.ai_model"), f"{ai_provider}:{ai_model}"),
            sym.status_line(
                t("status.rate_limit"),
                t("common.on") if rate_limit_enabled else t("common.off"),
            ),
            sym.status_line(t("status.commands"), str(len(command_loader.enabled_commands))),
        ]

        await ctx.client.reply(ctx.message, sym.box(t("status.title"), lines))
