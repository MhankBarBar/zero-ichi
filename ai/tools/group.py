"""
Group/feature AI tools - tools for group management and feature toggling.
"""

from __future__ import annotations

from pydantic_ai import RunContext

from ai.context import BotDependencies
from core.runtime_config import runtime_config


def register_group_tools(agent):
    """Register group/feature tools with the agent."""

    @agent.tool
    async def toggle_feature(ctx: RunContext[BotDependencies], feature: str, enabled: bool) -> str:
        """Toggle a bot feature on or off. Features: anti_delete, anti_link, welcome, notes, etc."""
        runtime_config.set_feature(feature, enabled)
        return f"Feature {feature} is now {'enabled' if enabled else 'disabled'}"

    @agent.tool
    async def get_group_info(ctx: RunContext[BotDependencies], group_jid: str = "") -> str:
        """Get information about a WhatsApp group."""
        jid = group_jid or ctx.deps.msg.chat_jid
        info = await ctx.deps.bot.get_group_info(jid)
        if info:
            return f"Group: {info.get('name', 'Unknown')}, Members: {len(info.get('participants', []))}"
        return "Could not get group info"
