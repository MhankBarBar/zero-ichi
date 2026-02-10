"""
Add skill command - Add AI skills from URL or file.
"""

from core import symbols as sym
from core.command import Command, CommandContext


class AddSkillCommand(Command):
    name = "addskill"
    aliases = ["skill"]
    description = "Add an AI skill from URL or attached file"
    usage = "/addskill <url> or attach .md file"
    category = "owner"
    owner_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Add a skill to the AI."""
        from ai import agentic_ai
        from ai.skills import (
            load_skill_from_url,
            parse_skill_markdown,
            save_skill_to_file,
        )

        if ctx.args:
            url = ctx.args[0]
            if url.startswith("http://") or url.startswith("https://"):
                skill = await load_skill_from_url(url)
                if skill:
                    save_skill_to_file(skill)
                    agentic_ai.add_skill(
                        skill["name"],
                        skill["content"],
                        skill["description"],
                        skill["trigger"],
                    )
                    await ctx.client.reply(
                        ctx.message,
                        f"{sym.SUCCESS} *Skill Added*\n\n"
                        f"*Name:* `{skill['name']}`\n"
                        f"*Description:* {skill['description']}\n"
                        f"*Trigger:* {skill['trigger']}",
                    )
                else:
                    await ctx.client.reply(
                        ctx.message,
                        f"{sym.ERROR} Failed to load skill from URL. Make sure it's a valid markdown file with frontmatter.",
                    )
                return

        msg_obj, media_type = ctx.message.get_media_message(ctx.client)
        if msg_obj and media_type == "document":
            try:
                media_data = await ctx.client._client.download_any(msg_obj)
                if media_data:
                    content = media_data.decode("utf-8")
                    skill = parse_skill_markdown(content)
                    if skill:
                        save_skill_to_file(skill)
                        agentic_ai.add_skill(
                            skill["name"],
                            skill["content"],
                            skill["description"],
                            skill["trigger"],
                        )
                        await ctx.client.reply(
                            ctx.message,
                            f"{sym.SUCCESS} *Skill Added*\n\n"
                            f"*Name:* `{skill['name']}`\n"
                            f"*Description:* {skill['description']}\n"
                            f"*Trigger:* {skill['trigger']}",
                        )
                    else:
                        await ctx.client.reply(
                            ctx.message,
                            f"{sym.ERROR} Invalid skill format. Make sure it has YAML frontmatter with 'name' field.",
                        )
                    return
            except Exception as e:
                await ctx.client.reply(
                    ctx.message, f"{sym.ERROR} Failed to read attached file: {e}"
                )
                return

        await ctx.client.reply(
            ctx.message,
            f"{sym.INFO} *Add AI Skill*\n\n"
            f"Usage:\n"
            f"• `/addskill <url>` - Load from URL\n"
            f"• Attach a `.md` file and send `/addskill`\n\n"
            f"*Skill Format:*\n"
            f"```\n"
            f"---\n"
            f"name: skill_name\n"
            f"description: What this skill does\n"
            f"trigger: always\n"
            f"---\n\n"
            f"# Instructions\n"
            f"Your AI instructions here...\n"
            f"```",
        )
