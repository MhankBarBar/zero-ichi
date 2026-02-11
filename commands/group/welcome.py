"""
Welcome command - Configure welcome messages for new members.
"""

from core import symbols as sym
from core.command import Command, CommandContext
from core.handlers.welcome import get_welcome_config, set_welcome_config


class WelcomeCommand(Command):
    name = "welcome"
    description = "Configure welcome messages for new group members"
    usage = "/welcome [on|off|set <message>]"
    category = "group"
    group_only = True
    admin_only = True
    examples = [
        "/welcome",
        "/welcome on",
        "/welcome off",
        "/welcome set Welcome {name}! Please follow our rules.",
    ]

    async def execute(self, ctx: CommandContext) -> None:
        """Configure welcome messages."""
        config = get_welcome_config(ctx.message.chat_jid)

        if not ctx.args:
            status = "Enabled ✅" if config.get("enabled", True) else "Disabled ❌"
            message = config.get("message", "Welcome, {name}!")

            await ctx.client.reply(
                ctx.message,
                f"{sym.INFO} *Welcome Message Settings*\n\n"
                f"*Status:* {status}\n\n"
                f"*Message:*\n{message}\n\n"
                f"*Available placeholders:*\n"
                f"• `{{name}}` - Member's name\n"
                f"• `{{mention}}` - @mention the member\n"
                f"• `{{group}}` - Group name\n\n"
                f"*Commands:*\n"
                f"• `/welcome on` - Enable\n"
                f"• `/welcome off` - Disable\n"
                f"• `/welcome set <message>` - Set custom message",
            )
            return

        action = ctx.args[0].lower()

        if action == "on":
            set_welcome_config(ctx.message.chat_jid, enabled=True)
            await ctx.client.reply(ctx.message, f"{sym.SUCCESS} Welcome messages *enabled*.")
        elif action == "off":
            set_welcome_config(ctx.message.chat_jid, enabled=False)
            await ctx.client.reply(ctx.message, f"{sym.SUCCESS} Welcome messages *disabled*.")
        elif action == "set":
            if len(ctx.args) < 2:
                await ctx.client.reply(
                    ctx.message,
                    f"{sym.ERROR} Provide a message.\n\nUsage: `/welcome set <message>`",
                )
                return

            new_message = " ".join(ctx.args[1:])
            set_welcome_config(ctx.message.chat_jid, message=new_message)
            await ctx.client.reply(
                ctx.message, f"{sym.SUCCESS} Welcome message updated:\n\n{new_message}"
            )
        else:
            await ctx.client.reply(
                ctx.message, f"{sym.ERROR} Unknown action. Use `on`, `off`, or `set <message>`."
            )
