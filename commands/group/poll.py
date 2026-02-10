"""
Poll command - Create polls in groups.
"""

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t


class PollCommand(Command):
    name = "poll"
    description = "Create a poll in the group"
    usage = '/poll "Question" "Option 1" "Option 2" ...'
    category = "group"
    group_only = True
    examples = [
        '/poll "Favorite color?" "Red" "Blue" "Green"',
        '/poll "Meeting time?" "10 AM" "2 PM" "5 PM"',
    ]

    async def execute(self, ctx: CommandContext) -> None:
        """Create a poll."""
        import re

        text = ctx.raw_args
        if not text:
            await ctx.client.reply(
                ctx.message,
                f"{sym.INFO} *{t('poll.title')}*\n\n{t('poll.usage', prefix=ctx.prefix)}",
            )
            return

        parts = re.findall(r'"([^"]+)"', text)

        if len(parts) < 3:
            await ctx.client.reply(
                ctx.message, f"{sym.ERROR} {t('poll.need_options', prefix=ctx.prefix)}"
            )
            return

        if len(parts) > 13:
            await ctx.client.reply(ctx.message, f"{sym.ERROR} {t('poll.max_options')}")
            return

        question = parts[0]
        options = parts[1:]

        try:
            await ctx.client._client.send_poll(
                ctx.client.to_jid(ctx.message.chat_jid),
                question,
                options,
                False,
            )
        except Exception as e:
            await ctx.client.reply(ctx.message, f"{sym.ERROR} {t('poll.failed', error=e)}")
