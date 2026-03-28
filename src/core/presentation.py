"""Presentation helpers for consistent command output formatting."""

from __future__ import annotations

from core import symbols as sym

CATEGORY_ICONS = {
    "general": sym.INFO,
    "admin": sym.USER,
    "group": sym.GROUP,
    "owner": sym.SETTINGS,
    "moderation": sym.WARNING,
    "content": sym.SPARKLE,
    "utility": sym.COMMAND,
}


def format_command_card(
    prefix: str,
    name: str,
    description: str,
    usage: str,
    *,
    aliases: list[str] | None = None,
    category: str | None = None,
    restrictions: list[str] | None = None,
) -> str:
    """Render a command information card using the house style."""
    safe_prefix = prefix or "/"
    aliases = aliases or []
    restrictions = restrictions or []

    lines = [
        f"{sym.HEADER_L} `{safe_prefix}{name}` {sym.HEADER_R}",
        "",
        f"{sym.QUOTE} {description}",
        "",
        f"{sym.BULLET} *Usage:* `{usage}`",
    ]

    if aliases:
        alias_text = ", ".join(f"`{safe_prefix}{alias}`" for alias in aliases)
        lines.append(f"{sym.BULLET} *Aliases:* {alias_text}")

    if category:
        icon = CATEGORY_ICONS.get(category.lower(), sym.DIAMOND)
        lines.append(f"{sym.BULLET} *Category:* {icon} {category.title()}")

    if restrictions:
        lines.append("")
        lines.append(f"{sym.WARNING} *Restrictions:* {', '.join(restrictions)}")

    return "\n".join(lines)
