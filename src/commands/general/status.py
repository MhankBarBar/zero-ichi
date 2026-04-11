"""Status command - quick bot health and runtime status."""

from __future__ import annotations

import asyncio
import time

from sqlalchemy import text

from core import symbols as sym
from core.command import Command, CommandContext, command_loader
from core.i18n import t
from core.presentation import format_command_card
from core.runtime_config import runtime_config
from core.timefmt import format_uptime
from core.webhooks import webhook_dispatcher_status


class StatusCommand(Command):
    name = "status"
    aliases = ["health"]
    description = "Show runtime health and key subsystem status"
    usage = "status"
    category = "general"

    def _ping_db(self) -> bool:
        """Run blocking DB ping outside event loop."""
        from core.db import get_engine

        try:
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    async def execute(self, ctx: CommandContext) -> None:
        from commands.general.uptime import _start_time

        uptime = format_uptime(time.time() - _start_time)

        try:
            db_ok = await asyncio.wait_for(asyncio.to_thread(self._ping_db), timeout=2.0)
        except TimeoutError:
            db_ok = False

        webhook = webhook_dispatcher_status()
        ai_enabled = runtime_config.get_nested("agentic_ai", "enabled", default=False)
        ai_provider = runtime_config.get_nested("agentic_ai", "provider", default="openai")
        ai_model = runtime_config.get_nested("agentic_ai", "model", default="gpt-5-mini")
        rate_limit_enabled = runtime_config.get_nested("rate_limit", "enabled", default=True)

        lines = [
            f"{sym.BULLET} *{t('status.uptime')}:* {uptime}",
            f"{sym.BULLET} *{t('status.db')}:* {t('common.on') if db_ok else t('common.off')}",
            f"{sym.BULLET} *{t('status.webhook_worker')}:* {t('common.on') if webhook.get('running') else t('common.off')}",
            f"{sym.BULLET} *{t('status.webhook_queue')}:* {webhook.get('queue_size', 0)}",
            f"{sym.BULLET} *{t('status.ai')}:* {t('common.on') if ai_enabled else t('common.off')}",
            f"{sym.BULLET} *{t('status.ai_model')}:* {ai_provider}:{ai_model}",
            f"{sym.BULLET} *{t('status.rate_limit')}:* {t('common.on') if rate_limit_enabled else t('common.off')}",
            f"{sym.BULLET} *{t('status.commands')}:* {len(command_loader.enabled_commands)}",
        ]

        header = format_command_card(
            ctx.prefix,
            self.name,
            self.description,
            self.get_usage(ctx.prefix),
            aliases=self.aliases,
            category=self.category,
        )
        await ctx.client.reply(ctx.message, header + "\n\n" + "\n".join(lines))
