"""
Common utilities.
"""

from __future__ import annotations

import re
from datetime import timedelta


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
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0:
        parts.append(f"{seconds}s")

    if not parts:
        return "0s"

    return " ".join(parts)
