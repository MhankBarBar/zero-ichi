"""Auto-download config command."""

from __future__ import annotations

from core.command import Command, CommandContext
from core.i18n import t, t_error, t_success
from core.runtime_config import runtime_config


class AutoDlCommand(Command):
    name = "autodl"
    description = "Configure automatic link download"
    usage = "autodl [status|on|off|mode|cooldown|maxlinks]"
    owner_only = True

    async def execute(self, ctx: CommandContext) -> None:
        args = ctx.args
        cfg = runtime_config.get_nested("downloader", "auto_link_download", default={})
        if not isinstance(cfg, dict):
            cfg = {}

        if not args or args[0].lower() == "status":
            await ctx.client.reply(
                ctx.message,
                t(
                    "autodl.status",
                    enabled=t("common.on") if cfg.get("enabled") else t("common.off"),
                    mode=cfg.get("mode", "auto"),
                    cooldown=cfg.get("cooldown_seconds", 30),
                    maxlinks=cfg.get("max_links_per_message", 1),
                ),
            )
            return

        action = args[0].lower()
        if action in {"on", "off"}:
            runtime_config.set_nested("downloader", "auto_link_download", "enabled", action == "on")
            await ctx.client.reply(
                ctx.message,
                t_success("autodl.enabled" if action == "on" else "autodl.disabled"),
            )
            return

        if action == "mode":
            if len(args) < 2 or args[1].lower() not in {"auto", "audio", "video"}:
                await ctx.client.reply(ctx.message, t_error("autodl.mode_usage", prefix=ctx.prefix))
                return
            runtime_config.set_nested("downloader", "auto_link_download", "mode", args[1].lower())
            await ctx.client.reply(ctx.message, t_success("autodl.mode_set", mode=args[1].lower()))
            return

        if action == "cooldown":
            if len(args) < 2 or not args[1].isdigit():
                await ctx.client.reply(
                    ctx.message, t_error("autodl.cooldown_usage", prefix=ctx.prefix)
                )
                return
            runtime_config.set_nested(
                "downloader", "auto_link_download", "cooldown_seconds", int(args[1])
            )
            await ctx.client.reply(ctx.message, t_success("autodl.cooldown_set", seconds=args[1]))
            return

        if action in {"maxlinks", "max"}:
            if len(args) < 2 or not args[1].isdigit() or int(args[1]) < 1:
                await ctx.client.reply(
                    ctx.message, t_error("autodl.maxlinks_usage", prefix=ctx.prefix)
                )
                return
            runtime_config.set_nested(
                "downloader", "auto_link_download", "max_links_per_message", int(args[1])
            )
            await ctx.client.reply(ctx.message, t_success("autodl.maxlinks_set", count=args[1]))
            return

        await ctx.client.reply(ctx.message, t_error("autodl.usage", prefix=ctx.prefix))
