"""
Skills command - List and manage AI skills.
"""

from core import symbols as sym
from core.command import Command, CommandContext


class SkillsCommand(Command):
    name = "skills"
    description = "List all loaded AI skills"
    usage = "skills"
    category = "owner"
    owner_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """List all loaded skills."""
        from ai import agentic_ai
        from ai.skills import list_skill_files

        skills = agentic_ai.skills
        skill_files = list_skill_files()

        if not skills and not skill_files:
            await ctx.client.reply(
                ctx.message, f"{sym.INFO} *No Skills Loaded*\n\nUse `/addskill` to add skills."
            )
            return

        lines = [f"{sym.INFO} *AI Skills*\n"]

        if skills:
            lines.append("*Loaded:*")
            for name, skill in skills.items():
                desc = skill.get("description", "No description")
                trigger = skill.get("trigger", "always")
                lines.append(f"• `{name}` - {desc} ({trigger})")

        if skill_files:
            lines.append("\n*Saved Files:*")
            for path in skill_files:
                lines.append(f"• `{path.stem}`")

        lines.append("\nUse `/delskill <name>` to remove.")
        lines.append("Use `/skillinfo <name>` for details.")

        await ctx.client.reply(ctx.message, "\n".join(lines))
