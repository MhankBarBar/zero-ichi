"""
Welcome command - Configure welcome messages for new members.
"""

from core.command import Command, CommandContext
from core.handlers.welcome import (
    get_welcome_config,
    handle_welcome_goodbye_config,
    set_welcome_config,
)


class WelcomeCommand(Command):
    name = "welcome"
    description = "Configure welcome messages for new group members"
    usage = "welcome [on|off|set <message>]"
    category = "group"
    group_only = True
    admin_only = True
    examples = [
        "welcome",
        "welcome on",
        "welcome off",
        "welcome set Welcome {name}! Please follow our rules.",
    ]

    async def execute(self, ctx: CommandContext) -> None:
        """Configure welcome messages."""
        placeholders_help = (
            "• `{name}` - Member's name\n"
            "• `{mention}` - @mention the member\n"
            "• `{group}` - Group name\n"
            "• `{count}` - Member count\n"
            "• `{date}` - Current date\n"
            "• `{time}` - Current time"
        )

        await handle_welcome_goodbye_config(
            ctx,
            "welcome",
            get_welcome_config,
            set_welcome_config,
            placeholders_help,
        )
