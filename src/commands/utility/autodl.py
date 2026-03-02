"""Auto-download config command."""

from __future__ import annotations

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t, t_error, t_success
from core.runtime_config import runtime_config


class AutoDlCommand(Command):
    name = "autodl"
    description = "Configure automatic link download"
    usage = "autodl [status | on | off | mode <auto|audio|video|photo> | cooldown <seconds> | maxlinks <count> | album <count> | photolimit <count>]"
    owner_only = True

    async def execute(self, ctx: CommandContext) -> None:
        args = ctx.args
        cfg = runtime_config.get_nested("downloader", "auto_link_download", default={})
        if not isinstance(cfg, dict):
            cfg = {}
        photo_cfg = cfg.get("photo", {})
        if not isinstance(photo_cfg, dict):
            photo_cfg = {}

        if not args or args[0].lower() == "status":
            status_text = "\n".join(
                [
                    sym.header(t("autodl.title")),
                    "",
                    sym.status_line(
                        t("autodl.enabled_label"),
                        t("common.on") if cfg.get("enabled") else t("common.off"),
                    ),
                    sym.status_line(t("autodl.mode_label"), str(cfg.get("mode", "auto"))),
                    sym.status_line(
                        t("autodl.cooldown_label"),
                        t("autodl.seconds_value", seconds=cfg.get("cooldown_seconds", 30)),
                    ),
                    sym.status_line(
                        t("autodl.maxlinks_label"),
                        str(cfg.get("max_links_per_message", 1)),
                    ),
                    sym.status_line(
                        t("autodl.photo_limit_label"),
                        str(photo_cfg.get("max_images_per_link", 20)),
                    ),
                    sym.status_line(
                        t("autodl.photo_album_label"),
                        str(photo_cfg.get("max_images_per_album", 10)),
                    ),
                ]
            )
            await ctx.client.reply(
                ctx.message,
                status_text,
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
            if len(args) < 2 or args[1].lower() not in {"auto", "audio", "video", "photo"}:
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

        if action == "album":
            if len(args) < 2 or not args[1].isdigit():
                await ctx.client.reply(
                    ctx.message, t_error("autodl.album_usage", prefix=ctx.prefix)
                )
                return
            count = int(args[1])
            if count < 2 or count > 30:
                await ctx.client.reply(ctx.message, t_error("autodl.album_range"))
                return
            runtime_config.set_nested(
                "downloader", "auto_link_download", "photo", "max_images_per_album", count
            )
            await ctx.client.reply(ctx.message, t_success("autodl.album_set", count=count))
            return

        if action in {"photolimit", "photomax"}:
            if len(args) < 2 or not args[1].isdigit():
                await ctx.client.reply(
                    ctx.message, t_error("autodl.photolimit_usage", prefix=ctx.prefix)
                )
                return
            count = int(args[1])
            if count < 1 or count > 100:
                await ctx.client.reply(ctx.message, t_error("autodl.photolimit_range"))
                return
            runtime_config.set_nested(
                "downloader", "auto_link_download", "photo", "max_images_per_link", count
            )
            await ctx.client.reply(ctx.message, t_success("autodl.photolimit_set", count=count))
            return

        await ctx.client.reply(ctx.message, t_error("autodl.usage", prefix=ctx.prefix))
