"""
Shared helper functions for group participant actions.

Provides common handlers for kick/ban/promote/demote to reduce code duplication.
"""

from core.command import CommandContext
from core.i18n import t_error, t_info, t_success
from core.targets import parse_targets


async def update_participants(
    ctx: CommandContext,
    action: str,
    action_key: str,
) -> None:
    """
    Common handler for kick/ban/promote/demote commands.

    Args:
        ctx: Command context
        action: WhatsApp action ("remove", "promote", "demote", "add")
        action_key: i18n key for action (e.g., "kick", "promote")
    """
    targets = parse_targets(ctx)
    if not targets:
        await ctx.client.reply(
            ctx.message, t_info("members.no_targets", prefix=ctx.prefix, command=ctx.command_name)
        )
        return

    try:
        group_jid = ctx.message.chat_jid
        target_jids = [ctx.client.to_jid(t) for t in targets]
        await ctx.client._client.update_group_participants(
            ctx.client.to_jid(group_jid), target_jids, action
        )
        count = len(targets)
        await ctx.client.reply(ctx.message, t_success(f"members.{action_key}_success", count=count))
    except Exception as e:
        await ctx.client.reply(ctx.message, t_error(f"members.{action_key}_failed", error=str(e)))
