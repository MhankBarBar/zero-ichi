"""Command usage analytics.

Tracks per-command usage with timestamps for dashboard charts.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta

from core.db import kv_get_json, kv_set_json
from core.logger import log_debug

DEFAULT_RETENTION_DAYS = 30
SAVE_INTERVAL_SECONDS = 2.0


class CommandAnalytics:
    """Track and query command usage analytics."""

    def __init__(self):
        self._scope = "analytics"
        self._key = "payload"
        self._data: dict = {}
        self._dirty = False
        self._last_save_ts = 0.0
        self._load()

    def _load(self) -> None:
        """Load analytics data from database."""
        data = kv_get_json(self._scope, self._key, default={})
        self._data = data if isinstance(data, dict) else {}
        if "commands" not in self._data:
            self._data["commands"] = {}

    def _save(self) -> None:
        """Persist analytics data to database."""
        kv_set_json(self._scope, self._key, self._data)
        self._dirty = False
        self._last_save_ts = time.time()

    def _schedule_save(self, force: bool = False) -> None:
        """Persist analytics on interval to reduce write volume."""
        self._dirty = True
        now = time.time()
        if force or now - self._last_save_ts >= SAVE_INTERVAL_SECONDS:
            self._save()

    def flush(self) -> None:
        """Flush pending analytics writes."""
        if self._dirty:
            self._save()

    def record_command(self, name: str, user_jid: str = "", chat_jid: str = "") -> None:
        """Record a command execution."""
        if "commands" not in self._data:
            self._data["commands"] = {}

        if name not in self._data["commands"]:
            self._data["commands"][name] = []

        self._data["commands"][name].append(
            {
                "ts": datetime.now().isoformat(),
                "user": user_jid.split("@")[0] if user_jid else "",
                "chat": chat_jid,
            }
        )

        self._prune()
        self._schedule_save()
        log_debug(f"Analytics: recorded {name}")

    def _prune(self) -> None:
        """Remove entries older than retention period."""
        cutoff = (datetime.now() - timedelta(days=DEFAULT_RETENTION_DAYS)).isoformat()

        for cmd_name in list(self._data.get("commands", {})):
            entries = self._data["commands"][cmd_name]
            self._data["commands"][cmd_name] = [e for e in entries if e.get("ts", "") >= cutoff]
            if not self._data["commands"][cmd_name]:
                del self._data["commands"][cmd_name]

    def get_top_commands(self, days: int = 7, chat_jid: str = "") -> list[dict]:
        """Get top commands by usage in the last N days, optionally filtered by chat."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        counts = {}
        for cmd_name, entries in self._data.get("commands", {}).items():
            count = 0
            for e in entries:
                if e.get("ts", "") >= cutoff:
                    if chat_jid and e.get("chat") != chat_jid:
                        continue
                    count += 1

            if count > 0:
                counts[cmd_name] = count

        sorted_cmds = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [{"command": name, "count": count} for name, count in sorted_cmds]

    def get_usage_timeline(
        self, command: str = "", days: int = 7, chat_jid: str = ""
    ) -> list[dict]:
        """Get daily usage timeline for a command (or all commands), optionally filtered by chat."""
        now = datetime.now()
        daily: dict[str, int] = {}

        for i in range(days):
            date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            daily[date] = 0

        cmds = (
            {command: self._data.get("commands", {}).get(command, [])}
            if command
            else self._data.get("commands", {})
        )

        for _cmd_name, entries in cmds.items():
            for entry in entries:
                if chat_jid and entry.get("chat") != chat_jid:
                    continue
                date = entry.get("ts", "")[:10]
                if date in daily:
                    daily[date] += 1

        return [{"date": date, "count": count} for date, count in sorted(daily.items())]

    def get_total_commands(self, days: int = 7, chat_jid: str = "") -> int:
        """Get total command count in the last N days, optionally filtered by chat."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        total = 0
        for entries in self._data.get("commands", {}).values():
            for e in entries:
                if e.get("ts", "") >= cutoff:
                    if chat_jid and e.get("chat") != chat_jid:
                        continue
                    total += 1
        return total


command_analytics = CommandAnalytics()
