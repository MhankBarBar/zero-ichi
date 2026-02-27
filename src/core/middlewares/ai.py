"""AI middleware — process messages with AI agent if applicable."""

from ai import agentic_ai
from core.command import command_loader
from core.logger import log_error


async def ai_middleware(ctx, next):
    """Process message with AI agent if applicable."""
    parsed_cmd = command_loader.parse_command(ctx.msg.text)[0]
    is_command = parsed_cmd is not None and command_loader.get(parsed_cmd) is not None

    if not is_command and await agentic_ai.should_respond(ctx.msg, ctx.bot):
        try:
            response = await agentic_ai.process(ctx.msg, ctx.bot)
            if response and response.strip():
                await ctx.bot.reply(ctx.msg, response)
            return
        except Exception as e:
            log_error(f"AI agent error: {e}")

    await next()
