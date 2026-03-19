"""Time formatting helpers."""

from __future__ import annotations


def format_uptime(seconds: float, *, include_seconds: bool = False) -> str:
    """Format uptime seconds as a compact human-readable string."""
    total = max(0, int(seconds))
    days = total // 86400
    hours = (total % 86400) // 3600
    minutes = (total % 3600) // 60
    secs = total % 60

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if include_seconds or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)
