"""
Echo command - Repeat message back to user.
"""

from core.command import Command, CommandContext
from core.i18n import t_info


class EchoCommand(Command):
    """
    Echo back whatever the user sends.
    """

    name = "echo"
    description = "Repeat your message back"
    usage = "/echo <message>"

    async def execute(self, ctx: CommandContext) -> None:
        """Echo the user's message."""
        if not ctx.raw_args:
            await ctx.client.reply(ctx.message, t_info("echo.usage"))
            return

        await ctx.client.reply(ctx.message, f"» {ctx.raw_args}")
