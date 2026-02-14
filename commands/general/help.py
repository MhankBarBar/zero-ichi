"""
Help command - Shows all available commands.
"""

from core import symbols as sym
from core.command import Command, CommandContext, command_loader
from core.i18n import t


def get_prefix() -> str:
    """Get the display-friendly prefix from runtime config."""
    from core.runtime_config import runtime_config

    return runtime_config.display_prefix


def fmt_cmd(cmd_name: str) -> str:
    """Format a command name with prefix (handles empty prefix)."""
    prefix = get_prefix()
    if prefix:
        return f"{prefix}{cmd_name}"
    return cmd_name


CATEGORY_ICONS = {
    "general": sym.INFO,
    "admin": sym.USER,
    "group": sym.GROUP,
    "owner": sym.SETTINGS,
    "moderation": sym.WARNING,
    "content": sym.SPARKLE,
    "utility": sym.COMMAND,
}


class HelpCommand(Command):
    """
    Display help information about available commands.
    """

    name = "help"
    aliases = ["h", "?"]
    description = "Show all available commands"

    @property
    def usage(self) -> str:
        return f"{fmt_cmd('help')} [command|category]"

    async def execute(self, ctx: CommandContext) -> None:
        """Show help message with all available commands."""

        if ctx.args:
            query = ctx.args[0].lower()
            grouped = command_loader.get_grouped_commands()

            matched_category = None
            for group_name in grouped:
                if group_name.lower() == query:
                    matched_category = group_name
                    break

            if matched_category:
                commands = grouped[matched_category]
                icon = CATEGORY_ICONS.get(matched_category.lower(), sym.DIAMOND)
                lines = [f"{icon} *{matched_category} Commands*\n"]
                for cmd in commands:
                    aliases_str = ""
                    if cmd.aliases:
                        aliases_str = f" ({', '.join(f'`{fmt_cmd(a)}`' for a in cmd.aliases)})"
                    lines.append(
                        f"  {sym.BULLET} `{fmt_cmd(cmd.name)}`{aliases_str} {sym.ARROW} {cmd.description}"
                    )

                    cooldown = getattr(cmd, "cooldown", 0)
                    if cooldown:
                        lines[-1] += f" ⏱{cooldown}s"

                lines.append(
                    f"\n{sym.INFO} {t('help.type_help', prefix=get_prefix())} `<command>` for details"
                )
                await ctx.client.reply(ctx.message, "\n".join(lines))
                return

            command_name = query
            cmd = command_loader.get(command_name)

            if cmd and cmd.enabled:
                icon = CATEGORY_ICONS.get(getattr(cmd, "category", "").lower(), sym.DIAMOND)
                help_text = (
                    f"{sym.HEADER_L} {fmt_cmd(cmd.name)} {sym.HEADER_R}\n\n"
                    f"{sym.QUOTE} {cmd.description}\n\n"
                    f"{sym.BULLET} *{t('help.usage')}:* `{cmd.usage if cmd.usage else fmt_cmd(cmd.name)}`\n"
                )

                if cmd.aliases:
                    aliases_str = ", ".join(f"`{fmt_cmd(a)}`" for a in cmd.aliases)
                    help_text += f"{sym.BULLET} *{t('help.aliases')}:* {aliases_str}\n"

                category_name = getattr(cmd, "category", None)
                if category_name:
                    help_text += (
                        f"{sym.BULLET} *{t('help.category')}:* {icon} {category_name.title()}\n"
                    )

                cooldown = getattr(cmd, "cooldown", 0)
                if cooldown:
                    help_text += f"{sym.BULLET} *{t('help.cooldown')}:* {cooldown}s\n"

                examples = getattr(cmd, "examples", [])
                if examples:
                    help_text += f"\n{sym.SPARKLE} *{t('help.examples')}:*\n"
                    for ex in examples:
                        help_text += f"  {sym.ARROW} `{ex}`\n"

                restrictions = []
                if cmd.private_only:
                    restrictions.append(t("help.private_only"))
                if cmd.group_only:
                    restrictions.append(t("help.group_only"))
                if cmd.owner_only:
                    restrictions.append(t("help.owner_only"))
                if cmd.admin_only:
                    restrictions.append(t("help.admin_only"))
                if restrictions:
                    help_text += (
                        f"\n{sym.WARNING} *{t('help.restrictions')}:* {', '.join(restrictions)}"
                    )
            else:
                similar = command_loader.find_similar(command_name)
                if similar:
                    suggestions = ", ".join(f"`{fmt_cmd(s)}`" for s in similar)
                    help_text = (
                        f"{sym.SEARCH} {t('help.not_found', command=command_name)}\n\n"
                        f"{sym.ARROW} *{t('help.did_you_mean')}:* {suggestions}"
                    )
                else:
                    help_text = f"{sym.ERROR} {t('help.not_found', command=command_name)}"

            await ctx.client.reply(ctx.message, help_text)
            return

        grouped = command_loader.get_grouped_commands()

        lines = [f"{sym.STAR} *{t('help.available_commands')}*\n"]

        for group_name, commands in grouped.items():
            icon = CATEGORY_ICONS.get(group_name.lower(), sym.DIAMOND)
            lines.append(f"\n{icon} *{group_name}*")
            for cmd in commands:
                lines.append(f"  {sym.BULLET} `{fmt_cmd(cmd.name)}` {sym.ARROW} {cmd.description}")

        lines.append(f"\n{sym.INFO} {t('help.type_help', prefix=get_prefix())}")
        lines.append(f"{sym.INFO} Use `{fmt_cmd('help')} <category>` for category details")

        await ctx.client.reply(ctx.message, "\n".join(lines))
