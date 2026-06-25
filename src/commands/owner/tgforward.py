"""
Telegram forwarder management commands (owner only).
"""

from core.command import Command, CommandContext
from core.runtime_config import runtime_config


class TgForwardCommand(Command):
    name = "tgforward"
    description = "Manage Telegram → WhatsApp auto-forwarder"
    usage = "tgforward <status|reload|test>"
    aliases = ["tgfwd"]
    owner_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Handle tgforward sub-commands."""
        if not ctx.args:
            await ctx.client.reply(
                ctx.message,
                f"*Telegram Forwarder*\n\n"
                f"Usage:\n"
                f"• `{ctx.prefix}tgforward status` — Show forwarder status\n"
                f"• `{ctx.prefix}tgforward reload` — Reload rules from config\n"
                f"• `{ctx.prefix}tgforward test <rule#>` — Send test message to a rule\n"
                f"• `{ctx.prefix}tgforward fetchlast <rule#>` — Fetch last TG message and forward it",
            )
            return

        action = ctx.args[0].lower()

        if action == "status":
            await self._status(ctx)
        elif action == "reload":
            await self._reload(ctx)
        elif action == "test":
            await self._test(ctx)
        elif action == "fetchlast":
            await self._fetchlast(ctx)
        else:
            await ctx.client.reply(
                ctx.message,
                f"Unknown action: `{action}`\nUse `{ctx.prefix}tgforward` for help.",
            )

    async def _status(self, ctx: CommandContext) -> None:
        """Show forwarder status and configured rules."""
        tg_cfg = runtime_config.get_telegram_forwarder()
        enabled = tg_cfg.get("enabled", False)
        rules = tg_cfg.get("rules", [])

        from core.shared import get_tg_forwarder

        forwarder = get_tg_forwarder()
        is_running = forwarder.is_running if forwarder else False

        lines = [
            "*📡 Telegram Forwarder Status*",
            "",
            f"• Enabled: {'✅ Yes' if enabled else '❌ No'}",
            f"• Connected: {'✅ Yes' if is_running else '❌ No'}",
            f"• API ID: `{tg_cfg.get('api_id', 0) or 'not set'}`",
            f"• Session: `{tg_cfg.get('session_name', 'tg_forwarder')}`",
            f"• Rules: {len(rules)}",
            "",
        ]

        for i, rule in enumerate(rules):
            rule_enabled = rule.get("enabled", True)
            src = rule.get("source_chat_id", "?")
            targets = rule.get("target_jids", [])
            prefix = rule.get("caption_prefix", "")
            status = "✅" if rule_enabled else "⏸️"
            lines.append(f"{status} *Rule #{i + 1}*")
            lines.append(f"  Source: `{src}`")
            for t in targets:
                t_type = "📢 Channel" if t.endswith("@newsletter") else "💬 Chat"
                lines.append(f"  → {t_type}: `{t}`")
            if prefix:
                lines.append(f"  Prefix: `{prefix}`")
            lines.append("")

        await ctx.client.reply(ctx.message, "\n".join(lines))

    async def _reload(self, ctx: CommandContext) -> None:
        """Reload rules from config without restarting."""
        from core.shared import get_tg_forwarder

        forwarder = get_tg_forwarder()
        if not forwarder:
            await ctx.client.reply(
                ctx.message,
                "❌ Telegram forwarder is not initialized.\n"
                "Enable it in config.json and restart the bot.",
            )
            return

        runtime_config.reload()
        new_cfg = runtime_config.get_telegram_forwarder()
        forwarder.reload_rules(new_cfg)

        rules = new_cfg.get("rules", [])
        active = sum(1 for r in rules if r.get("enabled", True))
        await ctx.client.reply(
            ctx.message,
            f"✅ Telegram forwarder rules reloaded!\n"
            f"• Total rules: {len(rules)}\n"
            f"• Active rules: {active}",
        )

    async def _test(self, ctx: CommandContext) -> None:
        """Send a test message through a specific rule."""
        from core.shared import get_tg_forwarder

        forwarder = get_tg_forwarder()
        if not forwarder:
            await ctx.client.reply(ctx.message, "❌ Telegram forwarder is not initialized.")
            return

        if not forwarder.is_running:
            await ctx.client.reply(ctx.message, "❌ Telegram forwarder is not connected.")
            return

        if len(ctx.args) < 2:
            await ctx.client.reply(
                ctx.message,
                f"Usage: `{ctx.prefix}tgforward test <rule#>`\n"
                f"Example: `{ctx.prefix}tgforward test 1`",
            )
            return

        try:
            rule_idx = int(ctx.args[1]) - 1
        except ValueError:
            await ctx.client.reply(ctx.message, "❌ Rule number must be a number.")
            return

        rules = forwarder.rules
        if rule_idx < 0 or rule_idx >= len(rules):
            await ctx.client.reply(
                ctx.message,
                f"❌ Invalid rule number. Available: 1-{len(rules)}",
            )
            return

        rule = rules[rule_idx]
        targets = rule.get("target_jids", [])
        prefix = rule.get("caption_prefix", "")
        test_text = f"{prefix}🧪 Telegram Forwarder Test Message".strip()

        success = 0
        fail = 0
        for jid in targets:
            try:
                await forwarder._send_text(jid, test_text)
                success += 1
            except Exception:
                fail += 1

        await ctx.client.reply(
            ctx.message,
            f"✅ Test complete for Rule #{rule_idx + 1}\n"
            f"• Sent: {success}/{len(targets)}\n"
            f"• Failed: {fail}",
        )

    async def _fetchlast(self, ctx: CommandContext) -> None:
        """Fetch the last message from a rule's source channel and forward it."""
        from core.shared import get_tg_forwarder

        forwarder = get_tg_forwarder()
        if not forwarder:
            await ctx.client.reply(ctx.message, "❌ Telegram forwarder is not initialized.")
            return

        if not forwarder.is_running:
            await ctx.client.reply(ctx.message, "❌ Telegram forwarder is not connected.")
            return

        if len(ctx.args) < 2:
            await ctx.client.reply(
                ctx.message,
                f"Usage: `{ctx.prefix}tgforward fetchlast <rule#>`\n"
                f"Example: `{ctx.prefix}tgforward fetchlast 1`",
            )
            return

        try:
            rule_idx = int(ctx.args[1]) - 1
        except ValueError:
            await ctx.client.reply(ctx.message, "❌ Rule number must be a number.")
            return

        await ctx.client.reply(ctx.message, "⏳ Fetching last message from Telegram channel...")

        result = await forwarder.test_forward_last(rule_idx)

        if result.get("error") and "forwarded" not in result:
            await ctx.client.reply(
                ctx.message,
                f"❌ Failed: {result['error']}",
            )
            return

        lines = [
            f"📡 *Fetch Last — Rule #{rule_idx + 1}*",
            "",
            f"• Chat ID: `{result.get('chat_id', '?')}`",
            f"• Type: `{result.get('chat_type', '?')}`",
            f"• Title: {result.get('chat_title', '?')}",
            f"• Message: _{result.get('message_text', '?')}_",
            "",
            f"• Forwarded: {'✅ Yes' if result.get('forwarded') else '❌ No'}",
        ]
        if result.get("error"):
            lines.append(f"• Error: {result['error']}")

        await ctx.client.reply(ctx.message, "\n".join(lines))
