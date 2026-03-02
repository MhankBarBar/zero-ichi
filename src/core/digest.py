"""Digest generation and scheduling helpers."""

from __future__ import annotations

from datetime import datetime, timedelta

from core.analytics import command_analytics
from core.reports import list_reports
from core.scheduler import get_scheduler
from core.storage import GroupData

DAY_TO_CRON = {
    "sun": 0,
    "mon": 1,
    "tue": 2,
    "wed": 3,
    "thu": 4,
    "fri": 5,
    "sat": 6,
}


def build_digest_message(group_jid: str, period: str = "daily") -> str:
    """Build digest text for a group."""
    days = 1 if period == "daily" else 7
    top = command_analytics.get_top_commands(days=days, chat_jid=group_jid)[:5]
    total = command_analytics.get_total_commands(days=days, chat_jid=group_jid)
    reports = list_reports(group_jid)
    open_reports = len([r for r in reports if str(r.get("status", "")).lower() == "open"])

    title = "Daily Digest" if period == "daily" else "Weekly Digest"
    lines = [f"*{title}*", ""]
    lines.append(f"Commands used: `{total}`")
    lines.append(f"Open reports: `{open_reports}`")
    lines.append("")
    lines.append("*Top commands*:")

    if top:
        for item in top:
            lines.append(f"- `/{item['command']}`: {item['count']}")
    else:
        lines.append("- No command activity")

    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    return "\n".join(lines)


def _cron_for(period: str, time_str: str, day: str = "sun") -> str:
    hour, minute = 20, 0
    try:
        hh, mm = time_str.split(":", 1)
        hour = max(0, min(23, int(hh)))
        minute = max(0, min(59, int(mm)))
    except Exception:
        pass

    if period == "weekly":
        dow = DAY_TO_CRON.get(day.lower()[:3], 0)
        return f"{minute} {hour} * * {dow}"
    return f"{minute} {hour} * * *"


def apply_digest_schedule(group_jid: str, creator_jid: str = "") -> dict:
    """Create/update digest task from group settings and return saved config."""
    data = GroupData(group_jid)
    config = data.digest
    scheduler = get_scheduler()
    if not scheduler:
        return config

    existing_task = str(config.get("task_id", "") or "")
    if existing_task:
        scheduler.remove_task(existing_task)

    if not config.get("enabled", False):
        config["task_id"] = ""
        data.save_digest(config)
        return config

    period = str(config.get("period", "daily")).lower()
    if period not in {"daily", "weekly"}:
        period = "daily"
    config["period"] = period

    cron = _cron_for(period, str(config.get("time", "20:00")), str(config.get("day", "sun")))
    task = scheduler.add_digest(
        chat_jid=group_jid,
        cron_expression=cron,
        period=period,
        creator_jid=creator_jid,
    )
    config["task_id"] = task.task_id
    data.save_digest(config)
    return config


def send_digest_now(group_jid: str, period: str = "daily") -> bool:
    """Queue an immediate digest by creating one-time reminder task."""
    scheduler = get_scheduler()
    if not scheduler:
        return False

    text = build_digest_message(group_jid, period=period)
    scheduler.add_reminder(
        chat_jid=group_jid,
        message=text,
        trigger_time=datetime.now() + timedelta(seconds=1),
        creator_jid="digest@system",
    )
    return True
