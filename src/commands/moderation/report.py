"""Report command - member reporting and admin moderation queue."""

from __future__ import annotations

from neonize.utils.enum import ParticipantChange

from core.command import Command, CommandContext
from core.event_bus import event_bus
from core.i18n import t, t_error, t_success
from core.jid_resolver import get_user_part
from core.logger import log_warning
from core.permissions import check_admin_permission, check_bot_admin
from core.reports import (
    create_report,
    find_reports_by_id,
    get_report,
    list_reports,
    update_report_status,
)
from core.storage import GroupData
from core.targets import parse_single_target


class ReportCommand(Command):
    name = "report"
    aliases = ["reports"]
    description = "Report a message/user, and manage report queue"
    usage = (
        "report <reason> (reply/mention) | reports [open|all] | "
        "report <info|resolve|dismiss|warn|kick> <id> [note]"
    )

    async def execute(self, ctx: CommandContext) -> None:
        command = ctx.command_name.lower()
        args = ctx.args

        admin_actions = {
            "list",
            "open",
            "all",
            "info",
            "resolve",
            "dismiss",
            "warn",
            "kick",
        }
        is_admin_flow = command == "reports" or (args and args[0].lower() in admin_actions)

        if is_admin_flow:
            await self._handle_admin_flow(ctx)
            return

        await self._create_report(ctx)

    async def _create_report(self, ctx: CommandContext) -> None:
        if not ctx.message.is_group:
            await ctx.client.reply(ctx.message, t_error("errors.group_only"))
            return

        target_jid = parse_single_target(ctx)
        if not target_jid:
            await ctx.client.reply(
                ctx.message, t_error("report.target_required", prefix=ctx.prefix)
            )
            return

        reason = " ".join(ctx.args).strip() or t("report.no_reason")
        quoted = ctx.message.quoted_message or {}
        media_type, media_caption = self._extract_quoted_media(ctx)

        reporter_identity = await self._resolve_identity(
            ctx,
            ctx.message.sender_jid,
            display_name=ctx.message.sender_name,
        )
        target_identity = await self._resolve_identity(ctx, target_jid)

        evidence_text = str(quoted.get("text", "") or "").strip()
        evidence_id = str(quoted.get("id", "") or "").strip()
        evidence_sender = str(quoted.get("sender", "") or "").strip() or target_identity["jid"]
        if media_caption and not evidence_text:
            evidence_text = media_caption

        report = create_report(
            ctx.message.chat_jid,
            reporter_jid=reporter_identity["jid"],
            reporter_name=reporter_identity["name"],
            reporter_number=reporter_identity["number"],
            reporter_pn=reporter_identity["pn"],
            reporter_lid=reporter_identity["lid"],
            target_jid=target_identity["jid"],
            target_name=target_identity["name"],
            target_number=target_identity["number"],
            target_pn=target_identity["pn"],
            target_lid=target_identity["lid"],
            reason=reason,
            evidence_text=evidence_text,
            evidence_message_id=evidence_id,
            evidence_sender_jid=evidence_sender,
            evidence_chat_jid=ctx.message.chat_jid,
            evidence_media_type=media_type,
            evidence_caption=media_caption,
        )

        await event_bus.emit(
            "report_update", {"action": "created", "group_id": ctx.message.chat_jid}
        )
        await self._notify_admins(ctx, report)

        await ctx.client.reply(ctx.message, t_success("report.forwarded_admins"))

    async def _handle_admin_flow(self, ctx: CommandContext) -> None:
        args = ctx.args
        action = args[0].lower() if args else "open"

        if action in {"list", "open", "all"}:
            if not ctx.message.is_group:
                await ctx.client.reply(ctx.message, t_error("report.dm_usage", prefix=ctx.prefix))
                return

            if not await check_admin_permission(
                ctx.client, ctx.message.chat_jid, ctx.message.sender_jid
            ):
                await ctx.client.reply(ctx.message, t_error("errors.admin_required"))
                return

            await self._list_reports(ctx, ctx.message.chat_jid, action)
            return

        if action == "info":
            if len(args) < 2:
                await ctx.client.reply(ctx.message, t_error("report.info_usage", prefix=ctx.prefix))
                return

            group_jid, report = await self._resolve_report_scope(ctx, args[1])
            if not group_jid or not report:
                return

            await self._send_report_info(ctx, group_jid, report)
            return

        if action in {"resolve", "dismiss", "warn", "kick"}:
            if len(args) < 2:
                await ctx.client.reply(
                    ctx.message,
                    t_error("report.resolve_usage", action=action, prefix=ctx.prefix),
                )
                return

            group_jid, report = await self._resolve_report_scope(ctx, args[1])
            if not group_jid or not report:
                return

            note = " ".join(args[2:]).strip()

            if action in {"resolve", "dismiss"}:
                resolution = note or (
                    t("report.resolution_resolved")
                    if action == "resolve"
                    else t("report.resolution_dismissed")
                )
                updated = update_report_status(
                    group_jid,
                    report["id"],
                    status="resolved" if action == "resolve" else "dismissed",
                    resolved_by=ctx.message.sender_jid,
                    resolution=resolution,
                )
                if not updated:
                    await ctx.client.reply(ctx.message, t_error("report.not_found"))
                    return

                await event_bus.emit(
                    "report_update",
                    {
                        "action": "updated",
                        "group_id": group_jid,
                        "report_id": updated["id"],
                        "status": updated["status"],
                    },
                )
                await ctx.client.reply(
                    ctx.message,
                    t_success("report.updated", id=updated["id"], status=updated["status"]),
                )
                return

            await self._apply_moderation_action(ctx, group_jid, report, action, note)
            return

        await ctx.client.reply(ctx.message, t_error("report.usage", prefix=ctx.prefix))

    async def _list_reports(self, ctx: CommandContext, group_jid: str, action: str) -> None:
        status = "" if action in {"list", "all"} else "open"
        reports = list_reports(group_jid, status=status)
        if not reports:
            await ctx.client.reply(ctx.message, t("report.none"))
            return

        lines = [f"*{t('report.queue_title')}*", ""]
        for report in reports[:20]:
            target_number = get_user_part(
                str(report.get("target_pn", "")).strip()
                or str(report.get("target_number", "")).strip()
                or str(report.get("target_jid", ""))
            )
            target_name = str(report.get("target_name", "")).strip()
            target_label = (
                f"{target_name} ({target_number})"
                if target_name and target_name != target_number
                else target_number
            )

            reporter_number = get_user_part(
                str(report.get("reporter_pn", "")).strip()
                or str(report.get("reporter_number", "")).strip()
                or str(report.get("reporter_jid", ""))
            )
            reporter_name = str(report.get("reporter_name", "")).strip() or t("common.unknown")
            reporter_label = (
                f"{reporter_name} ({reporter_number})"
                if reporter_name and reporter_name != reporter_number
                else reporter_number
            )

            lines.append(
                t(
                    "report.queue_item",
                    id=report["id"],
                    status=report["status"],
                    target=target_label,
                    reporter=reporter_label,
                    reason=report["reason"],
                )
            )

        lines.append("")
        lines.append(t("report.info_hint", prefix=ctx.prefix))
        await ctx.client.reply(ctx.message, "\n".join(lines))

    async def _resolve_report_scope(
        self,
        ctx: CommandContext,
        report_id: str,
    ) -> tuple[str | None, dict | None]:
        if ctx.message.is_group:
            if not await check_admin_permission(
                ctx.client, ctx.message.chat_jid, ctx.message.sender_jid
            ):
                await ctx.client.reply(ctx.message, t_error("errors.admin_required"))
                return None, None

            report = get_report(ctx.message.chat_jid, report_id)
            if not report:
                await ctx.client.reply(ctx.message, t_error("report.not_found"))
                return None, None

            return ctx.message.chat_jid, report

        matches = find_reports_by_id(report_id)
        if not matches:
            await ctx.client.reply(ctx.message, t_error("report.not_found"))
            return None, None

        allowed: list[tuple[str, dict]] = []
        for group_jid, report in matches:
            if await check_admin_permission(ctx.client, group_jid, ctx.message.sender_jid):
                allowed.append((group_jid, report))

        if not allowed:
            await ctx.client.reply(ctx.message, t_error("errors.admin_required"))
            return None, None

        if len(allowed) > 1:
            await ctx.client.reply(
                ctx.message,
                t_error("report.ambiguous_id", id=report_id, count=len(allowed)),
            )
            return None, None

        return allowed[0]

    async def _send_report_info(self, ctx: CommandContext, group_jid: str, report: dict) -> None:
        target = (
            str(report.get("target_name", "")).strip()
            or str(report.get("target_number", "")).strip()
        )
        target_number = get_user_part(
            str(report.get("target_pn", "")).strip()
            or str(report.get("target_number", "")).strip()
            or str(report.get("target_jid", ""))
        )

        reporter = (
            str(report.get("reporter_name", "")).strip()
            or str(report.get("reporter_number", "")).strip()
        )
        reporter_number = get_user_part(
            str(report.get("reporter_pn", "")).strip()
            or str(report.get("reporter_number", "")).strip()
            or str(report.get("reporter_jid", ""))
        )

        evidence = report.get("evidence_text") or t("report.no_evidence")
        media_type = str(report.get("evidence_media_type", "")).strip() or "-"

        target_pn = str(report.get("target_pn", "")).strip() or "-"
        target_lid = str(report.get("target_lid", "")).strip() or "-"
        reporter_pn = str(report.get("reporter_pn", "")).strip() or "-"
        reporter_lid = str(report.get("reporter_lid", "")).strip() or "-"

        msg = (
            f"*{t('report.info_title', id=report['id'])}*\n"
            f"{t('report.group_label')}: `{group_jid}`\n"
            f"{t('report.status_label')}: `{report['status']}`\n"
            f"{t('report.target_label')}: {target} ({target_number})\n"
            f"{t('report.target_pn_label')}: `{target_pn}`\n"
            f"{t('report.target_lid_label')}: `{target_lid}`\n"
            f"{t('report.reporter_label')}: {reporter} ({reporter_number})\n"
            f"{t('report.reporter_pn_label')}: `{reporter_pn}`\n"
            f"{t('report.reporter_lid_label')}: `{reporter_lid}`\n"
            f"{t('report.media_type_label')}: `{media_type}`\n"
            f"{t('report.reason_label')}: {report.get('reason', '-')}\n"
            f"{t('report.created_label')}: {report.get('created_at', '-')}\n\n"
            f"*{t('report.evidence_label')}*\n{evidence}"
        )

        evidence_id = str(report.get("evidence_message_id", "")).strip()
        evidence_sender = (
            str(report.get("evidence_sender_jid", "")).strip()
            or str(report.get("target_jid", "")).strip()
        )
        evidence_chat = str(report.get("evidence_chat_jid", "")).strip() or group_jid
        evidence_text = (
            str(report.get("evidence_caption", "")).strip()
            or str(report.get("evidence_text", "")).strip()
        )

        if evidence_id and evidence_sender and evidence_chat:
            if ctx.message.is_group:
                await ctx.client.send_quoted(
                    ctx.message.chat_jid,
                    msg,
                    evidence_id,
                    evidence_text,
                    participant=evidence_sender,
                )
            else:
                await ctx.client.reply_privately_to(
                    ctx.message.sender_jid,
                    msg,
                    evidence_id,
                    evidence_sender,
                    evidence_chat,
                    evidence_text,
                )
            return

        await ctx.client.reply(ctx.message, msg)

    async def _apply_moderation_action(
        self,
        ctx: CommandContext,
        group_jid: str,
        report: dict,
        action: str,
        note: str,
    ) -> None:
        target_jid = (
            str(report.get("target_pn", "")).strip()
            or str(report.get("target_jid", "")).strip()
            or str(report.get("target_lid", "")).strip()
        )
        target_number = get_user_part(target_jid)

        if action == "warn":
            data = GroupData(group_jid)
            warnings = data.warnings
            reason = note or t("report.warn_default_reason", id=report["id"])

            warnings.setdefault(target_number, [])
            warnings[target_number].append(reason)
            data.save_warnings(warnings)
            warn_count = len(warnings[target_number])

            update_report_status(
                group_jid,
                report["id"],
                status="resolved",
                resolved_by=ctx.message.sender_jid,
                resolution=t("report.action_warn_resolution", count=warn_count),
            )
            await event_bus.emit(
                "report_update",
                {
                    "action": "updated",
                    "group_id": group_jid,
                    "report_id": report["id"],
                    "status": "resolved",
                },
            )
            await ctx.client.reply(
                ctx.message,
                t_success("report.action_warned", user=target_number, count=warn_count),
            )
            return

        if action == "kick":
            if not await check_bot_admin(ctx.client, group_jid):
                await ctx.client.reply(ctx.message, t_error("errors.bot_admin_required"))
                return

            try:
                await ctx.client._client.update_group_participants(
                    ctx.client.to_jid(group_jid),
                    [ctx.client.to_jid(target_jid)],
                    ParticipantChange.REMOVE,
                )
            except Exception as e:
                await ctx.client.reply(
                    ctx.message,
                    t_error("report.kick_failed", error=str(e)),
                )
                return

            update_report_status(
                group_jid,
                report["id"],
                status="resolved",
                resolved_by=ctx.message.sender_jid,
                resolution=note or t("report.action_kick_resolution"),
            )
            await event_bus.emit(
                "report_update",
                {
                    "action": "updated",
                    "group_id": group_jid,
                    "report_id": report["id"],
                    "status": "resolved",
                },
            )
            await ctx.client.reply(
                ctx.message, t_success("report.action_kicked", user=target_number)
            )
            return

    async def _notify_admins(self, ctx: CommandContext, report: dict) -> None:
        admin_jids = await self._get_group_admin_jids(ctx, ctx.message.chat_jid)
        if not admin_jids:
            return

        target_name = str(report.get("target_name", "")).strip()
        target_number = get_user_part(
            str(report.get("target_pn", "")).strip()
            or str(report.get("target_number", "")).strip()
            or str(report.get("target_jid", ""))
        )
        target_label = (
            f"{target_name} ({target_number})"
            if target_name and target_name != target_number
            else target_number
        )

        reporter_name = str(report.get("reporter_name", "")).strip()
        reporter_number = get_user_part(
            str(report.get("reporter_pn", "")).strip()
            or str(report.get("reporter_number", "")).strip()
            or str(report.get("reporter_jid", ""))
        )
        reporter_label = (
            f"{reporter_name} ({reporter_number})"
            if reporter_name and reporter_name != reporter_number
            else reporter_number
        )

        evidence_id = str(report.get("evidence_message_id", "")).strip()
        evidence_sender = (
            str(report.get("evidence_sender_jid", "")).strip()
            or str(report.get("target_jid", "")).strip()
        )
        evidence_chat = str(report.get("evidence_chat_jid", "")).strip() or ctx.message.chat_jid
        evidence_text = (
            str(report.get("evidence_caption", "")).strip()
            or str(report.get("evidence_text", "")).strip()
        )

        delivered_count = 0
        for admin_jid in admin_jids:
            notify_text = t(
                "report.admin_notification",
                id=report["id"],
                reporter=reporter_label,
                target=target_label,
                reason=report.get("reason", "-"),
                prefix=ctx.prefix,
            )

            candidates = await self._build_notification_targets(ctx, admin_jid)
            sent = False
            for candidate in candidates:
                try:
                    if evidence_id and evidence_sender and evidence_chat:
                        await ctx.client.reply_privately_to(
                            candidate,
                            notify_text,
                            evidence_id,
                            evidence_sender,
                            evidence_chat,
                            evidence_text,
                        )
                    else:
                        await ctx.client.send(candidate, notify_text)
                    sent = True
                    delivered_count += 1
                    break
                except Exception:
                    try:
                        await ctx.client.send(candidate, notify_text)
                        sent = True
                        delivered_count += 1
                        break
                    except Exception:
                        continue

            if not sent:
                log_warning(
                    f"[REPORT] Failed to notify admin {admin_jid} for {report.get('id', '-')}"
                )

        if delivered_count == 0:
            log_warning(f"[REPORT] No admin notifications delivered for {report.get('id', '-')}")

    async def _get_group_admin_jids(self, ctx: CommandContext, group_jid: str) -> list[str]:
        try:
            group_info = await ctx.client._client.get_group_info(ctx.client.to_jid(group_jid))
        except Exception:
            return []

        admins: list[str] = []
        for participant in group_info.Participants:
            if not (participant.IsAdmin or participant.IsSuperAdmin):
                continue
            admins.append(f"{participant.JID.User}@{participant.JID.Server}")
        return list(dict.fromkeys(admins))

    async def _build_notification_targets(self, ctx: CommandContext, admin_jid: str) -> list[str]:
        """Build best-effort target JIDs for admin DM delivery."""
        targets = [admin_jid]
        try:
            pair = await ctx.client.resolve_jid_pair(admin_jid)
            pn = str(pair.get("pn") or "").strip()
            lid = str(pair.get("lid") or "").strip()
            if pn:
                targets.append(pn)
            if lid:
                targets.append(lid)
        except Exception:
            pass

        ordered: list[str] = []
        for item in targets:
            if item and item not in ordered:
                ordered.append(item)
        return ordered

    def _extract_quoted_media(self, ctx: CommandContext) -> tuple[str, str]:
        quoted = ctx.message.quoted_raw
        if not quoted:
            return "", ""

        media_fields = (
            ("imageMessage", "image"),
            ("videoMessage", "video"),
            ("audioMessage", "audio"),
            ("documentMessage", "document"),
            ("stickerMessage", "sticker"),
        )

        for field_name, friendly in media_fields:
            has_field = False
            try:
                if field_name == "imageMessage":
                    has_field = quoted.HasField("imageMessage")
                elif field_name == "videoMessage":
                    has_field = quoted.HasField("videoMessage")
                elif field_name == "audioMessage":
                    has_field = quoted.HasField("audioMessage")
                elif field_name == "documentMessage":
                    has_field = quoted.HasField("documentMessage")
                elif field_name == "stickerMessage":
                    has_field = quoted.HasField("stickerMessage")
            except Exception:
                has_field = False

            if not has_field:
                continue

            caption = ""
            try:
                caption = str(getattr(getattr(quoted, field_name), "caption", "") or "").strip()
            except Exception:
                caption = ""
            return friendly, caption

        return "", ""

    async def _resolve_identity(
        self,
        ctx: CommandContext,
        jid: str,
        display_name: str = "",
    ) -> dict[str, str]:
        """Resolve PN/LID pair and normalized number for report identities."""
        pair = await ctx.client.resolve_jid_pair(jid)
        pn = str(pair.get("pn") or "")
        lid = str(pair.get("lid") or "")
        number = get_user_part(pn or lid or jid)
        name = display_name.strip() or number

        return {
            "jid": jid,
            "pn": pn,
            "lid": lid,
            "number": number,
            "name": name,
        }
