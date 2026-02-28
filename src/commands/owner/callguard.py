"""Owner command to configure incoming call guard behavior."""

from __future__ import annotations

from core.command import Command, CommandContext
from core.i18n import t, t_error, t_success
from core.runtime_config import runtime_config


class CallGuardCommand(Command):
    name = "callguard"
    description = "Configure incoming call handling"
    usage = "callguard [status|on|off|delay|notify|ownernotify|whitelist]"
    owner_only = True

    async def execute(self, ctx: CommandContext) -> None:
        args = ctx.args

        if not args or args[0].lower() == "status":
            await self._show_status(ctx)
            return

        action = args[0].lower()

        if action == "on":
            runtime_config.set_nested("call_guard", "enabled", True)
            runtime_config.set_nested("call_guard", "action", "block")
            await ctx.client.reply(ctx.message, t_success("callguard.enabled"))
            return

        if action == "off":
            runtime_config.set_nested("call_guard", "enabled", False)
            runtime_config.set_nested("call_guard", "action", "off")
            await ctx.client.reply(ctx.message, t_success("callguard.disabled"))
            return

        if action == "delay":
            if len(args) < 2 or not args[1].isdigit():
                await ctx.client.reply(
                    ctx.message, t_error("callguard.delay_usage", prefix=ctx.prefix)
                )
                return

            delay = int(args[1])
            if delay < 0 or delay > 60:
                await ctx.client.reply(ctx.message, t_error("callguard.delay_range"))
                return

            runtime_config.set_nested("call_guard", "delay_seconds", delay)
            await ctx.client.reply(ctx.message, t_success("callguard.delay_set", seconds=delay))
            return

        if action == "notify":
            if len(args) < 2 or args[1].lower() not in {"on", "off"}:
                await ctx.client.reply(
                    ctx.message,
                    t_error("callguard.notify_usage", prefix=ctx.prefix),
                )
                return

            enabled = args[1].lower() == "on"
            runtime_config.set_nested("call_guard", "notify_caller", enabled)
            await ctx.client.reply(
                ctx.message,
                t_success(
                    "callguard.notify_set",
                    status=t("common.on") if enabled else t("common.off"),
                ),
            )
            return

        if action in {"ownernotify", "owner"}:
            if len(args) < 2 or args[1].lower() not in {"on", "off"}:
                await ctx.client.reply(
                    ctx.message,
                    t_error("callguard.ownernotify_usage", prefix=ctx.prefix),
                )
                return

            enabled = args[1].lower() == "on"
            runtime_config.set_nested("call_guard", "notify_owner", enabled)
            await ctx.client.reply(
                ctx.message,
                t_success(
                    "callguard.ownernotify_set",
                    status=t("common.on") if enabled else t("common.off"),
                ),
            )
            return

        if action == "whitelist":
            await self._handle_whitelist(ctx)
            return

        await ctx.client.reply(ctx.message, t_error("callguard.usage", prefix=ctx.prefix))

    async def _show_status(self, ctx: CommandContext) -> None:
        cfg = runtime_config.get("call_guard", {})
        if not isinstance(cfg, dict):
            cfg = {}

        whitelist = cfg.get("whitelist", [])
        if not isinstance(whitelist, list):
            whitelist = []

        text = t(
            "callguard.status",
            enabled=t("common.on") if cfg.get("enabled") else t("common.off"),
            action=cfg.get("action", "block"),
            delay=cfg.get("delay_seconds", 3),
            notify_caller=t("common.on") if cfg.get("notify_caller", True) else t("common.off"),
            notify_owner=t("common.on") if cfg.get("notify_owner", True) else t("common.off"),
            whitelist=len(whitelist),
        )

        if whitelist:
            shown = whitelist[:10]
            rows = "\n".join(f"- `{jid}`" for jid in shown)
            text = f"{text}\n\n{t('callguard.whitelist_title')}:\n{rows}"
            if len(whitelist) > len(shown):
                text = f"{text}\n{t('callguard.whitelist_more', count=len(whitelist) - len(shown))}"

        await ctx.client.reply(ctx.message, text)

    async def _handle_whitelist(self, ctx: CommandContext) -> None:
        args = ctx.args
        if len(args) < 2:
            await ctx.client.reply(
                ctx.message, t_error("callguard.whitelist_usage", prefix=ctx.prefix)
            )
            return

        sub = args[1].lower()
        cfg = runtime_config.get("call_guard", {})
        if not isinstance(cfg, dict):
            cfg = {}

        whitelist = cfg.get("whitelist", [])
        if not isinstance(whitelist, list):
            whitelist = []

        if sub == "list":
            if not whitelist:
                await ctx.client.reply(ctx.message, t("callguard.whitelist_empty"))
                return

            rows = "\n".join(f"- `{jid}`" for jid in whitelist)
            await ctx.client.reply(ctx.message, f"{t('callguard.whitelist_title')}:\n{rows}")
            return

        if len(args) < 3:
            await ctx.client.reply(
                ctx.message, t_error("callguard.whitelist_usage", prefix=ctx.prefix)
            )
            return

        raw_jid = args[2].strip()
        jid = self._normalize_jid(raw_jid)
        if not jid:
            await ctx.client.reply(ctx.message, t_error("callguard.invalid_jid"))
            return

        jid_user = jid.split("@")[0].split(":")[0]

        if sub == "add":
            for existing in whitelist:
                if not isinstance(existing, str):
                    continue
                existing_user = existing.split("@")[0].split(":")[0]
                if existing_user == jid_user:
                    await ctx.client.reply(
                        ctx.message, t_error("callguard.whitelist_exists", jid=jid)
                    )
                    return

            whitelist.append(jid)
            runtime_config.set_nested("call_guard", "whitelist", whitelist)
            await ctx.client.reply(ctx.message, t_success("callguard.whitelist_added", jid=jid))
            return

        if sub == "remove":
            filtered: list[str] = []
            removed = False
            for existing in whitelist:
                if not isinstance(existing, str):
                    continue
                existing_user = existing.split("@")[0].split(":")[0]
                if existing_user == jid_user:
                    removed = True
                    continue
                filtered.append(existing)

            if not removed:
                await ctx.client.reply(
                    ctx.message, t_error("callguard.whitelist_not_found", jid=jid)
                )
                return

            runtime_config.set_nested("call_guard", "whitelist", filtered)
            await ctx.client.reply(ctx.message, t_success("callguard.whitelist_removed", jid=jid))
            return

        await ctx.client.reply(ctx.message, t_error("callguard.whitelist_usage", prefix=ctx.prefix))

    def _normalize_jid(self, value: str) -> str:
        value = value.strip()
        if not value:
            return ""

        if "@" in value:
            return value

        digits = "".join(ch for ch in value if ch.isdigit())
        if not digits:
            return ""

        return f"{digits}@s.whatsapp.net"
