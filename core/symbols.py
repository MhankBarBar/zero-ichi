"""
Unicode symbols for bot messages.

Clean, minimal symbols that render well on WhatsApp.
Use these instead of emojis for a more professional look.
"""

SUCCESS = "✓"
ERROR = "✗"
WARNING = "⊘"
INFO = "ⓘ"

ARROW = "→"
ARROW_LEFT = "←"
BULLET = "•"
STAR = "★"
DIAMOND = "◆"

LINE = "─"
CORNER_UP = "╭"
CORNER_DOWN = "╰"
PIPE = "│"

ON = "●"
OFF = "○"
PENDING = "◐"

SETTINGS = "⛯"
USER = "◉"
GROUP = "⬡"
COMMAND = "❯"
SEARCH = "◎"
TIME = "◷"

HEADER_L = "「"
HEADER_R = "」"
SEP = "┄"
DIVIDER = "═"

QUOTE = "»"
DOT = "·"
SPARKLE = "✦"

TRASH = "⌫"
KICK = "⊗"
BAN = "⊘"
WAVE = "◠"
CLOCK = "⏱"
BELL = "◗"
NOTE = "≡"
LIST = "☰"

IMAGE = "▢"
VIDEO = "▷"
AUDIO = "♫"
DOC = "▤"
STICKER = "✧"
CALENDAR = "▦"
LOADING = "⏳"
MUSIC = "♪"


def header(text: str) -> str:
    """Format text as a header with decorative brackets."""
    return f"{HEADER_L} {text} {HEADER_R}"


def box(title: str, lines: list[str]) -> str:
    """
    Create a boxed message with title and content lines.

    Example:
        ╭─── Title
        │ Line 1
        │ Line 2
        ╰───────────────
    """
    result = [f"{CORNER_UP}{LINE * 3} {title}"]
    for line in lines:
        result.append(f"{PIPE} {line}")
    result.append(f"{CORNER_DOWN}{LINE * 15}")
    return "\n".join(result)


def section(title: str, items: list[str]) -> str:
    """
    Create a section with header and bullet points.

    Example:
        「 Title 」
        • Item 1
        • Item 2
    """
    lines = [header(title)]
    for item in items:
        lines.append(f"{BULLET} {item}")
    return "\n".join(lines)


def status_line(label: str, value: str, enabled: bool | None = None) -> str:
    """Format a status line with optional on/off indicator."""
    if enabled is not None:
        indicator = ON if enabled else OFF
        return f"{BULLET} {label}: {indicator} {value}"
    return f"{BULLET} {label}: {value}"


def success(text: str) -> str:
    """Format a success message."""
    return f"{SUCCESS} {text}"


def error(text: str) -> str:
    """Format an error message."""
    return f"{ERROR} {text}"


def warning(text: str) -> str:
    """Format a warning message."""
    return f"{WARNING} {text}"


def info(text: str) -> str:
    """Format an info message."""
    return f"{INFO} {text}"
