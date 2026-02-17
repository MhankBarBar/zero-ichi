"""
Goodbye command - Configure goodbye messages for leaving members.
"""

from core.command import Command, CommandContext
from core.handlers.welcome import (
    get_goodbye_config,
    handle_welcome_goodbye_config,
    set_goodbye_config,
)


class GoodbyeCommand(Command):
    name = "goodbye"
    aliases = ["bye"]
    description = "Configure goodbye messages when members leave"
    usage = "goodbye [on|off|set <message>]"
    category = "group"
    group_only = True
    admin_only = True
    examples = [
        "goodbye",
        "goodbye on",
        "goodbye off",
        "goodbye set Goodbye {name}! We'll miss you.",
    ]

    async def execute(self, ctx: CommandContext) -> None:
        """Configure goodbye messages."""
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
            "goodbye",
            get_goodbye_config,
            set_goodbye_config,
            placeholders_help,
        )
