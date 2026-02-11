"""
Core AI tools - essential tools for message handling and command execution.
"""

from __future__ import annotations

from pydantic_ai import RunContext

from ai.context import BotDependencies


def register_core_tools(agent):
    """Register core tools with the agent."""

    @agent.tool
    async def reply(
        ctx: RunContext[BotDependencies], message: str, with_mentions: bool = False
    ) -> str:
        """Send a message to the current chat. Set with_mentions=True if message contains @mentions like @123456789."""
        try:
            await ctx.deps.bot.reply(ctx.deps.msg, message, mentions_are_lids=with_mentions)
            return "Message sent"
        except Exception as e:
            return f"Failed to send message: {e}"

    @agent.tool
    async def get_commands(ctx: RunContext[BotDependencies], category: str = "") -> str:
        """Get list of available bot commands. ALWAYS use this before telling users about commands."""
        from core.command import command_loader

        grouped = command_loader.get_grouped_commands()
        result_lines = []

        for group_name, commands in grouped.items():
            if category and category.lower() not in group_name.lower():
                continue
            result_lines.append(f"\n{group_name}:")
            for cmd in commands:
                result_lines.append(f"  - {cmd.name}: {cmd.description}")

        return "\n".join(result_lines) if result_lines else "No commands found"

    @agent.tool
    async def run_command(ctx: RunContext[BotDependencies], command: str, args: str = "") -> str:
        """Execute a bot command. Use this to run commands for the user."""
        from core.command import CommandContext, command_loader

        cmd_name = command.lower()
        cmd = command_loader.get(cmd_name)

        if not cmd:
            return f"Command '{cmd_name}' not found"

        if not cmd.enabled:
            return f"Command '{cmd_name}' is disabled"

        args_list = args.split() if args else []
        cmd_ctx = CommandContext(
            client=ctx.deps.bot,
            message=ctx.deps.msg,
            args=args_list,
            raw_args=args,
            command_name=cmd_name,
        )

        try:
            await cmd.execute(cmd_ctx)
            return f"Executed command: {cmd_name}"
        except Exception as e:
            return f"Command error: {str(e)}"
