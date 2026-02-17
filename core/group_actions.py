"""
Shared helper functions for group participant actions.

Provides common handlers for kick/ban/promote/demote to reduce code duplication.
"""

from neonize.utils.enum import ParticipantChange

from core.command import CommandContext
from core.errors import report_error
from core.i18n import t_error, t_info, t_success
from core.targets import parse_targets

_ACTION_MAP = {
    "add": ParticipantChange.ADD,
    "remove": ParticipantChange.REMOVE,
    "promote": ParticipantChange.PROMOTE,
    "demote": ParticipantChange.DEMOTE,
}


async def update_participants(
    ctx: CommandContext,
    action: str,
    action_key: str,
    no_targets_key: str = "members.no_targets",
) -> None:
    """
    Common handler for kick/ban/promote/demote commands.

    Args:
        ctx: Command context
        action: WhatsApp action ("remove", "promote", "demote", "add")
        action_key: i18n key for action (e.g., "kick", "promote")
        no_targets_key: i18n key for no targets error
    """
    targets = parse_targets(ctx)
    if not targets:
        await ctx.client.reply(
            ctx.message, t_info(no_targets_key, prefix=ctx.prefix, command=ctx.command_name)
        )
        return

    neonize_action = _ACTION_MAP.get(action.lower())
    if not neonize_action:
        await ctx.client.reply(
            ctx.message, t_error("errors.invalid_action", options=", ".join(_ACTION_MAP.keys()))
        )
        return

    try:
        group_jid = ctx.message.chat_jid
        target_jids = [ctx.client.to_jid(t) for t in targets]
        await ctx.client._client.update_group_participants(
            ctx.client.to_jid(group_jid), target_jids, neonize_action
        )
        count = len(targets)
        await ctx.client.reply(ctx.message, t_success(f"members.{action_key}_success", count=count))
    except Exception as e:
        await ctx.client.reply(ctx.message, t_error(f"members.{action_key}_failed", error=str(e)))
        await report_error(ctx.client, ctx.message, "members", e)
