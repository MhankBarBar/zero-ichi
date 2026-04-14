"""
Help command - Shows all available commands.
"""

from core import symbols as sym
from core.command import Command, CommandContext, command_loader
from core.i18n import t

CATEGORY_ICONS = {
    "general": sym.INFO,
    "admin": sym.USER,
    "group": sym.GROUP,
    "owner": sym.SETTINGS,
    "moderation": sym.WARNING,
    "content": sym.SPARKLE,
    "utility": sym.COMMAND,
}


def _visible_commands_for_context(commands, *, msg, is_admin: bool, is_owner: bool):
    """Filter commands to those usable in the current chat and role context."""
    visible = []
    for cmd in commands:
        if not cmd.enabled:
            continue
        if msg.chat_type and not cmd.can_execute(msg.chat_type):
            continue
        if cmd.owner_only and not is_owner:
            continue
        if cmd.admin_only and not (is_admin or is_owner):
            continue
        visible.append(cmd)
    return visible


def _commands_for_help_mode(commands, *, mode: str, msg, is_admin: bool, is_owner: bool):
    """Return commands for a specific help mode."""
    normalized = str(mode or "").strip().lower()
    base_visible = _visible_commands_for_context(
        commands,
        msg=msg,
        is_admin=is_admin,
        is_owner=is_owner,
    )
    if normalized in {"", "default"}:
        return base_visible
    if normalized == "all":
        return [cmd for cmd in commands if cmd.enabled]
    if normalized == "admin":
        return [cmd for cmd in commands if cmd.enabled and not cmd.owner_only]
    if normalized == "owner":
        return [cmd for cmd in commands if cmd.enabled]
    if normalized == "group":
        return [cmd for cmd in commands if cmd.enabled and not cmd.private_only]
    if normalized == "private":
        return [cmd for cmd in commands if cmd.enabled and not cmd.group_only]
    return base_visible


class HelpCommand(Command):
    """
    Display help information about available commands.
    """

    name = "help"
    aliases = ["h", "?"]
    description = "Show all available commands"

    @property
    def usage(self) -> str:
        return "help [command|category]"

    async def execute(self, ctx: CommandContext) -> None:
        """Show help message with all available commands."""
        p = ctx.prefix

        def fmt(name):
            return f"{p}{name}"

        if ctx.args:
            query = ctx.args[0].lower()
            grouped = command_loader.get_grouped_commands()

            matched_category = None
            for group_name in grouped:
                if group_name.lower() == query:
                    matched_category = group_name
                    break

            help_mode = (
                query if query in {"all", "admin", "owner", "group", "private"} else "default"
            )

            if matched_category:
                commands = _commands_for_help_mode(
                    grouped[matched_category],
                    mode=help_mode,
                    msg=ctx.message,
                    is_admin=getattr(ctx, "is_admin", False),
                    is_owner=getattr(ctx, "is_owner", False),
                )
                icon = CATEGORY_ICONS.get(matched_category.lower(), sym.DIAMOND)
                lines = [f"{icon} *{matched_category} Commands*\n"]
                for cmd in commands:
                    aliases_str = ""
                    if cmd.aliases:
                        aliases_str = f" ({', '.join(f'`{fmt(a)}`' for a in cmd.aliases)})"
                    lines.append(
                        f"  {sym.BULLET} `{fmt(cmd.name)}`{aliases_str} {sym.ARROW} {cmd.description}"
                    )

                    cooldown = getattr(cmd, "cooldown", 0)
                    if cooldown:
                        lines[-1] += f" ⏱{cooldown}s"

                lines.append(
                    f"\n{sym.INFO} {t('help.type_help', prefix=p)} `<command>` for details"
                )
                await ctx.client.reply(ctx.message, "\n".join(lines))
                return

            if help_mode != "default":
                lines = [f"{sym.STAR} *{t('help.available_commands')}*\n"]
                for group_name, commands in grouped.items():
                    mode_commands = _commands_for_help_mode(
                        commands,
                        mode=help_mode,
                        msg=ctx.message,
                        is_admin=getattr(ctx, "is_admin", False),
                        is_owner=getattr(ctx, "is_owner", False),
                    )
                    if not mode_commands:
                        continue
                    icon = CATEGORY_ICONS.get(group_name.lower(), sym.DIAMOND)
                    lines.append(f"\n{icon} *{group_name}*")
                    for cmd in mode_commands:
                        lines.append(
                            f"  {sym.BULLET} `{fmt(cmd.name)}` {sym.ARROW} {cmd.description}"
                        )
                lines.append(f"\n{sym.INFO} {t('help.type_help', prefix=p)}")
                await ctx.client.reply(ctx.message, "\n".join(lines))
                return

            command_name = query
            cmd = command_loader.get(command_name)

            if cmd and cmd.enabled:
                icon = CATEGORY_ICONS.get(getattr(cmd, "category", "").lower(), sym.DIAMOND)
                help_text = (
                    f"{sym.HEADER_L} {fmt(cmd.name)} {sym.HEADER_R}\n\n"
                    f"{sym.QUOTE} {cmd.description}\n\n"
                    f"{sym.BULLET} *{t('help.usage')}:* `{cmd.get_usage(p)}`\n"
                )

                if cmd.aliases:
                    aliases_str = ", ".join(f"`{fmt(a)}`" for a in cmd.aliases)
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
                        help_text += f"  {sym.ARROW} `{p}{ex}`\n"

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
                    suggestions = ", ".join(f"`{fmt(s)}`" for s in similar)
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
            visible_commands = _visible_commands_for_context(
                commands,
                msg=ctx.message,
                is_admin=getattr(ctx, "is_admin", False),
                is_owner=getattr(ctx, "is_owner", False),
            )
            if not visible_commands:
                continue
            icon = CATEGORY_ICONS.get(group_name.lower(), sym.DIAMOND)
            lines.append(f"\n{icon} *{group_name}*")
            for cmd in visible_commands:
                lines.append(f"  {sym.BULLET} `{fmt(cmd.name)}` {sym.ARROW} {cmd.description}")

        lines.append(f"\n{sym.INFO} {t('help.type_help', prefix=p)}")
        lines.append(f"{sym.INFO} Use `{fmt('help')} <category>` for category details")

        await ctx.client.reply(ctx.message, "\n".join(lines))
