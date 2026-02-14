"""
Command usage analytics.

Tracks per-command usage with timestamps for dashboard charts.
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

from core.logger import log_debug

DATA_DIR = Path("data")
ANALYTICS_FILE = DATA_DIR / "analytics.json"

DEFAULT_RETENTION_DAYS = 30


class CommandAnalytics:
    """Track and query command usage analytics."""

    def __init__(self):
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        """Load analytics data from disk."""
        try:
            if ANALYTICS_FILE.exists():
                self._data = json.loads(ANALYTICS_FILE.read_text(encoding="utf-8"))
        except Exception:
            self._data = {}

        if "commands" not in self._data:
            self._data["commands"] = {}

    def _save(self) -> None:
        """Save analytics data to disk."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        ANALYTICS_FILE.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

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
        self._save()
        log_debug(f"Analytics: recorded {name}")

    def _prune(self) -> None:
        """Remove entries older than retention period."""
        cutoff = (datetime.now() - timedelta(days=DEFAULT_RETENTION_DAYS)).isoformat()

        for cmd_name in list(self._data.get("commands", {})):
            entries = self._data["commands"][cmd_name]
            self._data["commands"][cmd_name] = [e for e in entries if e.get("ts", "") >= cutoff]
            if not self._data["commands"][cmd_name]:
                del self._data["commands"][cmd_name]

    def get_top_commands(self, days: int = 7) -> list[dict]:
        """Get top commands by usage in the last N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        counts = {}
        for cmd_name, entries in self._data.get("commands", {}).items():
            count = sum(1 for e in entries if e.get("ts", "") >= cutoff)
            if count > 0:
                counts[cmd_name] = count

        sorted_cmds = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [{"command": name, "count": count} for name, count in sorted_cmds]

    def get_usage_timeline(self, command: str = "", days: int = 7) -> list[dict]:
        """Get daily usage timeline for a command (or all commands)."""
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

        for cmd_name, entries in cmds.items():
            for entry in entries:
                date = entry.get("ts", "")[:10]
                if date in daily:
                    daily[date] += 1

        return [{"date": date, "count": count} for date, count in sorted(daily.items())]

    def get_total_commands(self, days: int = 7) -> int:
        """Get total command count in the last N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        total = 0
        for entries in self._data.get("commands", {}).values():
            total += sum(1 for e in entries if e.get("ts", "") >= cutoff)
        return total


command_analytics = CommandAnalytics()
