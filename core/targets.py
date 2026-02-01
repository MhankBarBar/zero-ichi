"""
Target parsing utilities for admin/moderation commands.

Provides helpers for extracting target JIDs from:
- Quoted/replied messages
- @mentions in message contextInfo
- Direct user IDs in arguments
"""

from core.command import CommandContext


def parse_targets(ctx: CommandContext) -> list[str]:
    """
    Parse target JIDs from a command context.

    Checks in order:
    1. Quoted message sender (single target)
    2. @mentions from message contextInfo (multiple targets)
    3. Numeric IDs in command arguments (multiple targets)

    Args:
        ctx: CommandContext with message and args

    Returns:
        List of target JID strings (may be empty)
    """
    targets = []

    quoted = ctx.message.quoted_message
    if quoted and quoted.get("sender"):
        targets.append(quoted["sender"])
        return targets

    mentions = ctx.message.mentions
    if mentions:
        return list(mentions)

    for arg in ctx.args:
        cleaned = arg.replace("@", "").strip()
        if cleaned.isdigit():
            targets.append(f"{cleaned}@lid")

    return targets


def parse_single_target(ctx: CommandContext) -> str | None:
    """
    Parse a single target JID from command context.

    Args:
        ctx: CommandContext with message and args

    Returns:
        Target JID string or None if no target found
    """
    targets = parse_targets(ctx)
    return targets[0] if targets else None


def extract_reason(ctx: CommandContext, skip_first: bool = False) -> str:
    """
    Extract reason text from command arguments.

    Args:
        ctx: CommandContext with args
        skip_first: If True, skip first arg (used when first arg is target)

    Returns:
        Reason string or empty string
    """
    mentions = ctx.message.mentions
    if mentions:
        return ctx.raw_args.strip()

    args = ctx.args[1:] if skip_first and ctx.args else ctx.args
    return " ".join(args) if args else ""
