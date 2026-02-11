"""
Delete skill command - Remove an AI skill.
"""

from core import symbols as sym
from core.command import Command, CommandContext


class DelSkillCommand(Command):
    name = "delskill"
    aliases = ["rmskill", "removeskill"]
    description = "Remove an AI skill"
    usage = "/delskill <name>"
    category = "owner"
    owner_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Remove a skill from the AI."""
        from ai import agentic_ai
        from ai.skills import delete_skill_file

        if not ctx.args:
            await ctx.client.reply(
                ctx.message,
                f"{sym.ERROR} Please provide the skill name.\n\nUsage: `/delskill <name>`",
            )
            return

        name = ctx.args[0]

        removed_memory = agentic_ai.remove_skill(name)

        removed_file = delete_skill_file(name)

        if removed_memory or removed_file:
            await ctx.client.reply(ctx.message, f"{sym.SUCCESS} Skill `{name}` removed.")
        else:
            await ctx.client.reply(ctx.message, f"{sym.ERROR} Skill `{name}` not found.")
