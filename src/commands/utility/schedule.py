"""
Schedule command - Manage recurring messages and auto-messages.
"""

import mimetypes
import uuid

from core import symbols as sym
from core.command import Command, CommandContext
from core.constants import MEDIA_DIR, MEDIA_FIELD_MAP
from core.i18n import t, t_error, t_info, t_success
from core.media import get_media_caption
from core.scheduler import TaskType, get_scheduler
from core.utils import parse_duration


class ScheduleCommand(Command):
    name = "schedule"
    description = "Manage recurring messages and auto-messages"
    usage = (
        "/schedule <cron|every <interval>> [message] | list | info <id> | cancel <id> | toggle <id>"
    )
    category = "utility"
    admin_only = True

    async def _download_media(self, ctx: CommandContext, msg_obj, media_type: str) -> str | None:
        """Download media to data/media/ and return the absolute path."""
        try:
            media_bytes = await ctx.client.raw.download_any(msg_obj)
            if not media_bytes:
                return None

            field = MEDIA_FIELD_MAP.get(media_type)
            mimetype = getattr(getattr(msg_obj, field, None), "mimetype", None) if field else None
            ext = mimetypes.guess_extension(mimetype) if mimetype else None

            MEDIA_DIR.mkdir(parents=True, exist_ok=True)
            file_path = MEDIA_DIR / f"{uuid.uuid4()}{ext or '.bin'}"
            file_path.write_bytes(media_bytes)
            return str(file_path.absolute())
        except Exception:
            return None

    async def _get_task_content(self, ctx: CommandContext, message_arg: str):
        """Extract (message, media_type, forward_msg, media_path) from context."""
        message = message_arg
        media_type = forward_msg = media_path = None

        quoted_raw = ctx.message.quoted_raw
        if quoted_raw:
            forward_msg = quoted_raw
            _, detected = ctx.message.get_media_message(ctx.client)
            if detected:
                media_type = detected
                if not message:
                    try:
                        message = get_media_caption(quoted_raw, media_type)
                    except Exception:
                        pass
        else:
            msg_obj, detected = ctx.message.get_media_message(ctx.client)
            if detected:
                media_type = detected
                media_path = await self._download_media(ctx, msg_obj, media_type)

        return message, media_type, forward_msg, media_path

    def _has_content(self, message, forward_msg, media_path):
        return bool(message) or bool(forward_msg) or bool(media_path)

    async def _add_cron(self, ctx, scheduler, chat_jid, cron_expr, message_raw):
        """Shared logic for adding a cron/recurring task."""
        message, media_type, forward_msg, media_path = await self._get_task_content(
            ctx, message_raw
        )

        if not self._has_content(message, forward_msg, media_path):
            await ctx.client.reply(ctx.message, t_error("schedule.no_message"))
            return None

        task = scheduler.add_recurring(
            chat_jid=chat_jid,
            message=message,
            cron_expression=cron_expr,
            creator_jid=ctx.message.sender_jid,
            media_type=media_type,
            media_path=media_path,
            forward_message=forward_msg,
        )

        tag = self._media_tag(media_type, forward_msg)
        await ctx.client.reply(
            ctx.message,
            t_success("schedule.set_cron", id=task.task_id, cron=cron_expr) + tag,
        )
        return task

    def _media_tag(self, media_type, forward_msg):
        if media_type:
            return f" ({media_type})"
        if forward_msg:
            return f" ({t('remind.message')})"
        return ""

    async def execute(self, ctx: CommandContext) -> None:
        """Manage scheduled tasks."""
        scheduler = get_scheduler()
        if not scheduler:
            await ctx.client.reply(ctx.message, t_error("schedule.scheduler_error"))
            return

        if not ctx.args:
            await ctx.client.reply(
                ctx.message, f"{sym.INFO} {t('schedule.usage', prefix=ctx.prefix)}"
            )
            return

        action = ctx.args[0].lower()
        chat_jid = ctx.message.chat_jid

        if action == "list":
            tasks = scheduler.get_tasks_for_chat(chat_jid)
            tasks = [t for t in tasks if t.task_type != TaskType.REMINDER]
            if not tasks:
                await ctx.client.reply(ctx.message, t_info("schedule.no_tasks"))
                return

            lines = [f"*{t('schedule.list_title')}*\n"]
            for task in tasks:
                status = "✅" if task.enabled else "❌"
                if task.task_type == TaskType.RECURRING:
                    trigger = f"Cron: `{task.cron_expression}`"
                else:
                    trigger = f"Every: `{task.interval_minutes}m`"

                preview = (
                    (task.message[:30] + "...")
                    if task.message and len(task.message) > 30
                    else (task.message or "")
                )
                media = f" [{task.media_type}]" if task.media_type else ""
                fwd = " [fwd]" if task.forward_message_data and not task.media_type else ""
                lines.append(f"{status} `{task.task_id}`{media}{fwd} — {trigger}\n   _{preview}_")

            await ctx.client.reply(ctx.message, "\n".join(lines))
            return

        if action == "info":
            if len(ctx.args) < 2:
                await ctx.client.reply(ctx.message, t_error("schedule.provide_id"))
                return

            task = scheduler.get_task(ctx.args[1])
            if not task or task.chat_jid != chat_jid:
                await ctx.client.reply(ctx.message, t_error("schedule.not_found", id=ctx.args[1]))
                return

            status = "✅ Enabled" if task.enabled else "❌ Disabled"
            if task.task_type == TaskType.RECURRING:
                trigger = f"Cron: `{task.cron_expression}`"
            elif task.task_type == TaskType.AUTO_MESSAGE:
                trigger = f"Every: `{task.interval_minutes}m`"
            else:
                trigger = task.task_type

            parts = [
                f"*📋 Task Info: `{task.task_id}`*\n",
                f"*Status:* {status}",
                f"*Type:* {trigger}",
                f"*Created:* {task.created_at.strftime('%Y-%m-%d %H:%M')}",
            ]
            if task.media_type:
                parts.append(f"*Media:* {task.media_type}")
            if task.forward_message_data:
                parts.append("*Forward:* Yes")
            if task.message:
                parts.append(f"*Message:*\n{task.message}")

            await ctx.client.reply(ctx.message, "\n".join(parts))
            return

        if action == "cancel":
            if len(ctx.args) < 2:
                await ctx.client.reply(ctx.message, t_error("schedule.provide_id"))
                return

            task_id = ctx.args[1]
            task = scheduler.get_task(task_id)
            if not task or task.chat_jid != chat_jid:
                await ctx.client.reply(ctx.message, t_error("schedule.not_found", id=task_id))
                return

            if scheduler.remove_task(task_id):
                await ctx.client.reply(ctx.message, t_success("schedule.cancelled", id=task_id))
            else:
                await ctx.client.reply(ctx.message, t_error("schedule.not_found", id=task_id))
            return

        if action == "toggle":
            if len(ctx.args) < 2:
                await ctx.client.reply(ctx.message, t_error("schedule.provide_id"))
                return

            task_id = ctx.args[1]
            task = scheduler.get_task(task_id)
            if not task or task.chat_jid != chat_jid:
                await ctx.client.reply(ctx.message, t_error("schedule.not_found", id=task_id))
                return

            new_state = not task.enabled
            scheduler.toggle_task(task_id, new_state)
            state_str = t("common.enabled") if new_state else t("common.disabled")
            await ctx.client.reply(
                ctx.message, t_success("schedule.toggled", id=task_id, state=state_str)
            )
            return

        if action == "every":
            if len(ctx.args) < 3:
                await ctx.client.reply(
                    ctx.message, t_error("schedule.usage_every", prefix=ctx.prefix)
                )
                return

            interval_str = ctx.args[1]
            message_raw = " ".join(ctx.args[2:])

            message, media_type, forward_msg, media_path = await self._get_task_content(
                ctx, message_raw
            )

            if not self._has_content(message, forward_msg, media_path):
                await ctx.client.reply(ctx.message, t_error("schedule.no_message"))
                return

            duration = parse_duration(interval_str)
            if not duration:
                await ctx.client.reply(ctx.message, t_error("schedule.invalid_interval"))
                return

            minutes = int(duration.total_seconds() / 60)
            if minutes < 1:
                await ctx.client.reply(ctx.message, t_error("schedule.min_interval"))
                return

            task = scheduler.add_auto_message(
                chat_jid=chat_jid,
                message=message,
                interval_minutes=minutes,
                creator_jid=ctx.message.sender_jid,
                media_type=media_type,
                media_path=media_path,
                forward_message=forward_msg,
            )

            tag = self._media_tag(media_type, forward_msg)
            await ctx.client.reply(
                ctx.message,
                t_success("schedule.set_interval", id=task.task_id, interval=f"{minutes}m") + tag,
            )
            return

        if action == "cron" and len(ctx.args) >= 6:
            cron_expr = " ".join(ctx.args[1:6])
            message_raw = " ".join(ctx.args[6:])
            try:
                await self._add_cron(ctx, scheduler, chat_jid, cron_expr, message_raw)
            except Exception as e:
                await ctx.client.reply(ctx.message, t_error("schedule.invalid_cron", error=str(e)))
            return

        if len(ctx.args) >= 5:
            cron_expr = " ".join(ctx.args[:5])
            message_raw = " ".join(ctx.args[5:])
            try:
                result = await self._add_cron(ctx, scheduler, chat_jid, cron_expr, message_raw)
                if result:
                    return
            except Exception:
                pass

        await ctx.client.reply(ctx.message, t_error("schedule.usage", prefix=ctx.prefix))
