"""
Goodbye command - Configure goodbye messages for leaving members.
"""

from core import symbols as sym
from core.command import Command, CommandContext
from core.handlers.welcome import get_goodbye_config, set_goodbye_config


class GoodbyeCommand(Command):
    name = "goodbye"
    aliases = ["bye"]
    description = "Configure goodbye messages when members leave"
    usage = "/goodbye [on|off|set <message>]"
    category = "group"
    group_only = True
    admin_only = True
    examples = [
        "/goodbye",
        "/goodbye on",
        "/goodbye off",
        "/goodbye set Goodbye {name}! We'll miss you.",
    ]

    async def execute(self, ctx: CommandContext) -> None:
        """Configure goodbye messages."""
        config = get_goodbye_config(ctx.message.chat_jid)

        if not ctx.args:
            status = "Enabled ✅" if config.get("enabled", False) else "Disabled ❌"
            message = config.get("message", "Goodbye, {name}!")

            await ctx.client.reply(
                ctx.message,
                f"{sym.INFO} *Goodbye Message Settings*\n\n"
                f"*Status:* {status}\n\n"
                f"*Message:*\n{message}\n\n"
                f"*Available placeholders:*\n"
                f"• `{{name}}` - Member's name\n\n"
                f"*Commands:*\n"
                f"• `/goodbye on` - Enable\n"
                f"• `/goodbye off` - Disable\n"
                f"• `/goodbye set <message>` - Set custom message",
            )
            return

        action = ctx.args[0].lower()

        if action == "on":
            set_goodbye_config(ctx.message.chat_jid, enabled=True)
            await ctx.client.reply(ctx.message, f"{sym.SUCCESS} Goodbye messages *enabled*.")
        elif action == "off":
            set_goodbye_config(ctx.message.chat_jid, enabled=False)
            await ctx.client.reply(ctx.message, f"{sym.SUCCESS} Goodbye messages *disabled*.")
        elif action == "set":
            if len(ctx.args) < 2:
                await ctx.client.reply(
                    ctx.message,
                    f"{sym.ERROR} Provide a message.\n\nUsage: `/goodbye set <message>`",
                )
                return

            new_message = " ".join(ctx.args[1:])
            set_goodbye_config(ctx.message.chat_jid, message=new_message)
            await ctx.client.reply(
                ctx.message, f"{sym.SUCCESS} Goodbye message updated:\n\n{new_message}"
            )
        else:
            await ctx.client.reply(
                ctx.message, f"{sym.ERROR} Unknown action. Use `on`, `off`, or `set <message>`."
            )
