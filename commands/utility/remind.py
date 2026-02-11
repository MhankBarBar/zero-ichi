"""
Remind command - Set reminders for yourself or the group.

Usage:
    /remind 10m Check the oven     - Remind in 10 minutes
    /remind 2h Meeting starts      - Remind in 2 hours
    /remind 1d30m Daily standup    - Remind in 1 day and 30 minutes
    /remind list                   - List your reminders
    /remind cancel <id>            - Cancel a reminder

Reply to a media message with /remind <duration> to set a media reminder.
"""

import re
from datetime import datetime, timedelta

from core.command import Command, CommandContext
from core.i18n import t, t_error, t_info, t_success


def parse_duration(duration_str: str) -> timedelta | None:
    """
    Parse a duration string like "10m", "2h", "1d30m" into a timedelta.

    Supported units: d (days), h (hours), m (minutes), s (seconds)
    """
    pattern = r"(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?"
    match = re.fullmatch(pattern, duration_str.lower().strip())

    if not match:
        return None

    days = int(match.group(1) or 0)
    hours = int(match.group(2) or 0)
    minutes = int(match.group(3) or 0)
    seconds = int(match.group(4) or 0)

    if days == 0 and hours == 0 and minutes == 0 and seconds == 0:
        return None

    return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


def format_duration(td: timedelta) -> str:
    """Format a timedelta into a human-readable string."""
    total_seconds = int(td.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds and not (days or hours):
        parts.append(f"{seconds}s")

    return " ".join(parts) if parts else "0m"


def format_datetime(dt: datetime) -> str:
    """Format datetime for display."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


class RemindCommand(Command):
    """Set reminders for yourself or the group."""

    name = "remind"
    aliases = ["reminder", "remindme"]
    description = "Set a reminder (text or media)"
    usage = "/remind <duration> <message> or reply to media with /remind <duration>"
    cooldown = 3
    category = "utility"

    async def execute(self, ctx: CommandContext) -> None:
        """Handle remind command."""
        from core.scheduler import get_scheduler

        scheduler = get_scheduler()
        if not scheduler:
            await ctx.client.reply(ctx.message, t_error("remind.scheduler_error"))
            return

        if not ctx.args:
            await ctx.client.reply(ctx.message, t_info("remind.usage"))
            return

        action = ctx.args[0].lower()

        if action == "list":
            tasks = scheduler.get_tasks_for_chat(ctx.message.chat_jid)
            reminders = [t for t in tasks if t.task_type == "reminder"]

            if not reminders:
                await ctx.client.reply(ctx.message, t("remind.no_reminders"))
                return

            lines = [f"📋 *{t('remind.your_reminders')}:*\n"]
            for task in reminders:
                status = "✅" if task.enabled else "⏸️"
                time_str = (
                    format_datetime(task.trigger_time) if task.trigger_time else t("common.unknown")
                )
                msg_preview = task.message[:30] + "..." if len(task.message) > 30 else task.message
                media_tag = f" [{task.media_type}]" if task.media_type else ""
                lines.append(
                    f"{status} `{task.task_id}`{media_tag} - {time_str}\n   _{msg_preview}_"
                )

            await ctx.client.reply(ctx.message, "\n".join(lines))
            return

        if action == "cancel":
            if len(ctx.args) < 2:
                await ctx.client.reply(ctx.message, t_error("remind.provide_id"))
                return

            task_id = ctx.args[1]
            if scheduler.remove_task(task_id):
                await ctx.client.reply(ctx.message, t_success("remind.cancelled", id=task_id))
            else:
                await ctx.client.reply(ctx.message, t_error("remind.not_found", id=task_id))
            return

        duration = parse_duration(action)
        if not duration:
            await ctx.client.reply(ctx.message, t_error("remind.invalid_duration"))
            return

        message = " ".join(ctx.args[1:]) if len(ctx.args) > 1 else ""
        trigger_time = datetime.now() + duration

        forward_msg = None
        media_type = None

        quoted_raw = ctx.message.quoted_raw
        if quoted_raw:
            forward_msg = quoted_raw
            msg_obj, detected_media_type = ctx.message.get_media_message(ctx.client)
            if detected_media_type:
                media_type = detected_media_type
                if not message:
                    if media_type == "image" and msg_obj.imageMessage.caption:
                        message = msg_obj.imageMessage.caption
                    elif media_type == "video" and msg_obj.videoMessage.caption:
                        message = msg_obj.videoMessage.caption

        if not message and not forward_msg:
            await ctx.client.reply(ctx.message, t_error("remind.no_message"))
            return

        sender_id = ctx.message.sender_jid.split("@")[0]
        is_group = ctx.message.is_group

        media_labels = {
            "image": t("remind.media_image"),
            "video": t("remind.media_video"),
            "sticker": t("remind.media_sticker"),
            "document": t("remind.media_document"),
            "audio": t("remind.media_audio"),
        }

        if message:
            reminder_text = f"⏰ *{t('remind.reminder')}*\n\n{message}"
        elif media_type:
            label = media_labels.get(media_type, media_type)
            reminder_text = f"⏰ *{t('remind.reminder')}*\n\n_{label} {t('remind.attached')}_"
        elif forward_msg:
            reminder_text = f"⏰ *{t('remind.reminder')}*\n\n_{t('remind.message_attached')}_"
        else:
            reminder_text = f"⏰ *{t('remind.reminder')}*"

        if is_group:
            reminder_text += f"\n\n_{t('remind.set_by', user=sender_id)}_"

        task = scheduler.add_reminder(
            chat_jid=ctx.message.chat_jid,
            message=reminder_text,
            trigger_time=trigger_time,
            creator_jid=ctx.message.sender_jid,
            forward_message=forward_msg,
        )

        media_tag = f" ({media_type})" if media_type else ""
        if forward_msg and not media_type:
            media_tag = f" ({t('remind.message')})"
        msg_preview = f"_{message}_" if message else f"_[{t('remind.forwarded')}]_"

        await ctx.client.reply(
            ctx.message,
            f"✅ *{t('remind.set')}*{media_tag}\n\n"
            f"⏰ {t('remind.in_time')}: {format_duration(duration)}\n"
            f"📅 {t('remind.at_time')}: {format_datetime(trigger_time)}\n"
            f"📝 {t('remind.message')}: {msg_preview}\n\n"
            f"ID: `{task.task_id}`",
        )
