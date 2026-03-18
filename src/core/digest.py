"""Digest generation and scheduling helpers."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

from core import symbols as sym
from core.analytics import command_analytics
from core.i18n import t
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


def _get_top_active_users(days: int, chat_jid: str, limit: int = 5) -> tuple[list[dict], int]:
    """Get top active users by command usage in the given time window."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    user_counts: Counter[str] = Counter()
    unique_users: set[str] = set()

    for entries in command_analytics._data.get("commands", {}).values():
        for entry in entries:
            if entry.get("ts", "") < cutoff:
                continue
            if chat_jid and entry.get("chat") != chat_jid:
                continue
            user = entry.get("user", "")
            if user:
                user_counts[user] += 1
                unique_users.add(user)

    top = user_counts.most_common(limit)
    return [{"user": u, "count": c} for u, c in top], len(unique_users)


def build_digest_message(group_jid: str, period: str = "daily") -> str:
    """Build rich digest text for a group using sym helpers."""
    days = 1 if period == "daily" else 7
    top_cmds = command_analytics.get_top_commands(days=days, chat_jid=group_jid)[:5]
    total = command_analytics.get_total_commands(days=days, chat_jid=group_jid)
    reports = list_reports(group_jid)
    open_reports = len([r for r in reports if str(r.get("status", "")).lower() == "open"])
    top_users, unique_count = _get_top_active_users(days, group_jid)

    period_label = t("digest.title") + " — " + ("Daily" if period == "daily" else "Weekly")

    summary_lines = [
        sym.status_line(t("stats.commands_used"), f"`{total}`"),
        sym.status_line("Open reports", f"`{open_reports}`"),
        sym.status_line("Active users", f"`{unique_count}`"),
    ]

    cmd_items = []
    if top_cmds:
        for i, item in enumerate(top_cmds, 1):
            cmd_items.append(f"{i}. `/{item['command']}` {sym.ARROW} {item['count']}")
    else:
        cmd_items.append("No command activity")

    user_items = []
    if top_users:
        for i, entry in enumerate(top_users, 1):
            user_items.append(f"{i}. @{entry['user']} {sym.ARROW} {entry['count']}")
    else:
        user_items.append("No user activity")

    parts = [
        sym.box(period_label, summary_lines),
        "",
        sym.section("Top Commands", cmd_items),
        "",
        sym.section("Top Active Users", user_items),
        "",
        f"{sym.TIME} {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    ]

    return "\n".join(parts)


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
