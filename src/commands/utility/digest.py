"""Digest command - configure and send group digest summaries."""

from __future__ import annotations

import re

from core.command import Command, CommandContext
from core.digest import apply_digest_schedule, send_digest_now
from core.i18n import t, t_error, t_success
from core.permissions import check_admin_permission
from core.storage import GroupData

TIME_RE = re.compile(r"^(?:[01]?\d|2[0-3]):[0-5]\d$")


class DigestCommand(Command):
    name = "digest"
    description = "Configure and send daily/weekly group digests"
    usage = "digest [status|now|off|on daily HH:MM|on weekly <day> HH:MM]"
    group_only = True
    admin_only = True

    async def execute(self, ctx: CommandContext) -> None:
        if not await check_admin_permission(
            ctx.client, ctx.message.chat_jid, ctx.message.sender_jid
        ):
            await ctx.client.reply(ctx.message, t_error("errors.admin_required"))
            return

        data = GroupData(ctx.message.chat_jid)
        args = ctx.args

        if not args or args[0].lower() == "status":
            cfg = data.digest
            await ctx.client.reply(
                ctx.message,
                t(
                    "digest.status",
                    enabled=t("common.on") if cfg.get("enabled") else t("common.off"),
                    period=cfg.get("period", "daily"),
                    day=cfg.get("day", "sun"),
                    time=cfg.get("time", "20:00"),
                ),
            )
            return

        action = args[0].lower()

        if action == "now":
            cfg = data.digest
            period = str(cfg.get("period", "daily"))
            if send_digest_now(ctx.message.chat_jid, period=period):
                await ctx.client.reply(ctx.message, t_success("digest.sent_now"))
            else:
                await ctx.client.reply(ctx.message, t_error("digest.scheduler_unavailable"))
            return

        if action == "off":
            cfg = data.digest
            cfg["enabled"] = False
            data.save_digest(cfg)
            apply_digest_schedule(ctx.message.chat_jid, creator_jid=ctx.message.sender_jid)
            await ctx.client.reply(ctx.message, t_success("digest.disabled"))
            return

        if action != "on":
            await ctx.client.reply(ctx.message, t_error("digest.usage", prefix=ctx.prefix))
            return

        if len(args) < 3:
            await ctx.client.reply(ctx.message, t_error("digest.usage", prefix=ctx.prefix))
            return

        period = args[1].lower()
        if period not in {"daily", "weekly"}:
            await ctx.client.reply(ctx.message, t_error("digest.invalid_period"))
            return

        day = "sun"
        time_arg_index = 2
        if period == "weekly":
            if len(args) < 4:
                await ctx.client.reply(ctx.message, t_error("digest.usage", prefix=ctx.prefix))
                return
            day = args[2].lower()[:3]
            if day not in {"sun", "mon", "tue", "wed", "thu", "fri", "sat"}:
                await ctx.client.reply(ctx.message, t_error("digest.invalid_day"))
                return
            time_arg_index = 3

        at = args[time_arg_index]
        if not TIME_RE.match(at):
            await ctx.client.reply(ctx.message, t_error("digest.invalid_time"))
            return

        cfg = data.digest
        cfg["enabled"] = True
        cfg["period"] = period
        cfg["day"] = day
        cfg["time"] = at
        data.save_digest(cfg)
        apply_digest_schedule(ctx.message.chat_jid, creator_jid=ctx.message.sender_jid)

        await ctx.client.reply(
            ctx.message,
            t_success("digest.enabled", period=period, day=day, time=at),
        )
