"""
Add skill command - Add AI skills from URL or file.
"""

from __future__ import annotations

from typing import Any

from core import symbols as sym
from core.command import Command, CommandContext


def build_inline_skill(raw_args: str, quoted_text: str = "") -> dict[str, Any] | None:
    """Build inline skill payload from command args/quoted text.

    Supports:
    - addskill <name> <instructions>
    - addskill <name>   (with quoted message text as instructions)
    """
    raw = (raw_args or "").strip()
    if not raw:
        return None

    parts = raw.split(maxsplit=1)
    if not parts:
        return None

    name = parts[0].strip().lower()
    if not name:
        return None

    content = parts[1].strip() if len(parts) > 1 else ""
    if not content:
        content = (quoted_text or "").strip()
    if not content:
        return None

    return {
        "name": name,
        "description": f"Inline skill: {name}",
        "trigger": "always",
        "priority": 10,
        "content": content,
    }


class AddSkillCommand(Command):
    name = "addskill"
    aliases = ["skill"]
    description = "Add an AI skill from inline text, URL, or attached file"
    usage = "addskill <name> <instructions> | addskill <url> | attach .md file"
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
            first_arg = ctx.args[0]
            if first_arg.startswith("http://") or first_arg.startswith("https://"):
                skill = await load_skill_from_url(first_arg)
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

        quoted_text = ""
        if ctx.message.quoted_message and ctx.message.quoted_message.get("text"):
            quoted_text = str(ctx.message.quoted_message.get("text") or "")

        inline_skill = build_inline_skill(ctx.raw_args, quoted_text)
        if inline_skill:
            save_skill_to_file(inline_skill)
            agentic_ai.add_skill(
                inline_skill["name"],
                inline_skill["content"],
                inline_skill["description"],
                inline_skill["trigger"],
            )
            await ctx.client.reply(
                ctx.message,
                f"{sym.SUCCESS} *Skill Added*\n\n"
                f"*Name:* `{inline_skill['name']}`\n"
                f"*Description:* {inline_skill['description']}\n"
                f"*Trigger:* {inline_skill['trigger']}",
            )
            return

        await ctx.client.reply(
            ctx.message,
            f"{sym.INFO} *Add AI Skill*\n\n"
            f"Usage:\n"
            f"• `/addskill <name> <instructions>` - Inline skill\n"
            f"• Reply to text with `/addskill <name>`\n"
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
