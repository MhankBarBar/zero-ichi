"""
Reusable download progress bar utilities.

Provides a consistent progress bar format across all downloader commands.
"""

from core import symbols as sym

BAR_WIDTH = 15


def format_size(size_bytes: int | float) -> str:
    """Format bytes as human-readable string."""
    if not size_bytes or size_bytes <= 0:
        return "~"
    mb = size_bytes / (1024 * 1024)
    if mb >= 1:
        return f"{mb:.1f}MB"
    kb = size_bytes / 1024
    return f"{kb:.0f}KB"


def build_progress_bar(pct: float) -> str:
    """Build a progress bar string like `[███████░░░░░░░░]` 47%"""
    filled = int(pct / 100 * BAR_WIDTH)
    bar = "█" * filled + "░" * (BAR_WIDTH - filled)
    return f"`[{bar}]` {pct:.0f}%"


def build_progress_text(
    header: str,
    downloaded: int,
    total: int,
    speed: float | None = None,
    eta: float | None = None,
) -> str:
    """Build full progress message with bar, sizes, speed and ETA."""
    pct = (downloaded / total * 100) if total > 0 else 0
    bar = build_progress_bar(pct)

    dl_str = format_size(downloaded)
    total_str = format_size(total)

    lines = [header, bar, f"{sym.BULLET} {dl_str} / {total_str}"]

    extras = []
    if speed:
        extras.append(f"{format_size(speed)}/s")
    if eta:
        extras.append(f"ETA: {int(eta)}s")
    if extras:
        lines.append(f"{sym.BULLET} {' {sym.BULLET} '.join(extras)}")

    return "\n".join(lines)


def build_complete_bar(header: str, status_text: str) -> str:
    """Build a completed progress message (100% bar + status)."""
    bar = "█" * BAR_WIDTH
    return f"{header}`[{bar}]` 100%\n{sym.BULLET} {status_text}"
