"""
Owner config command - Manage bot configuration at runtime.
"""

from core import symbols as sym
from core.command import Command, CommandContext, command_loader
from core.i18n import t, t_error, t_info, t_success
from core.runtime_config import runtime_config


class ConfigCommand(Command):
    """Manage bot configuration at runtime."""

    name = "config"
    aliases = ["cfg", "settings"]
    description = "View or modify bot configuration"
    usage = "config [action] [key] [value]"
    owner_only = True

    async def execute(self, ctx: CommandContext) -> None:
        args = ctx.args

        if not args:
            await self._show_help(ctx)
            return

        action = args[0].lower()

        if action == "get":
            await self._handle_get(ctx, args[1:])
        elif action == "set":
            await self._handle_set(ctx, args[1:])
        elif action == "features":
            await self._show_features(ctx)
        elif action == "toggle":
            await self._toggle_feature(ctx, args[1:])
        elif action == "owner":
            await self._handle_owner(ctx, args[1:])
        elif action == "cmd":
            await self._handle_command(ctx, args[1:])
        elif action == "all":
            await self._show_all(ctx)
        elif action in ("autoread", "ar"):
            await self._handle_autoread(ctx, args[1:])
        elif action in ("autoreact", "react"):
            await self._handle_autoreact(ctx, args[1:])
        elif action in ("selfmode", "self"):
            await self._handle_selfmode(ctx, args[1:])
        elif action == "ai":
            await self._handle_ai(ctx, args[1:])
        else:
            await self._show_help(ctx)

    async def _show_help(self, ctx: CommandContext) -> None:
        """Show config command help."""
        p = ctx.prefix
        help_text = f"""*{t("config.title")}*

*{t("config.usage_label")}:*
- `{p}config features` - {t("config.show_features")}
- `{p}config toggle <feature>` - {t("config.toggle_feature")}
- `{p}config cmd list` - {t("config.list_commands")}
- `{p}config cmd enable <name>` - {t("config.enable_command")}
- `{p}config cmd disable <name>` - {t("config.disable_command")}
- `{p}config autoread [on/off]` - {t("config.autoread_desc")}
- `{p}config react [emoji/off]` - {t("config.react_desc")}
- `{p}config selfmode [on/off]` - {t("config.selfmode_desc")}
- `{p}config ai [on/off/key/mode]` - {t("config.ai_desc")}
- `{p}config owner` - {t("config.show_owner")}
- `{p}config all` - {t("config.show_all")}"""

        await ctx.client.reply(ctx.message, help_text)

    async def _show_features(self, ctx: CommandContext) -> None:
        """Show all feature flags."""
        features = runtime_config.get_all_features()

        lines = [f"{sym.HEADER_L} {t('config.feature_flags')} {sym.HEADER_R}", ""]
        for name, enabled in features.items():
            status = sym.ON if enabled else sym.OFF
            lines.append(
                f"{status} `{name}`: {t('common.enabled') if enabled else t('common.disabled')}"
            )

        await ctx.client.reply(ctx.message, "\n".join(lines))

    async def _toggle_feature(self, ctx: CommandContext, args: list[str]) -> None:
        """Toggle a feature on/off."""
        if not args:
            await ctx.client.reply(ctx.message, t_error("config.provide_feature"))
            return

        feature_name = args[0].lower()
        all_features = runtime_config.get_all_features()

        if feature_name not in all_features:
            available = ", ".join(f"`{f}`" for f in all_features.keys())
            await ctx.client.reply(
                ctx.message,
                t_error("config.unknown_feature", feature=feature_name, available=available),
            )
            return

        current = all_features[feature_name]
        new_value = not current
        runtime_config.set_feature(feature_name, new_value)

        status = (
            f"{sym.ON} {t('common.enabled')}" if new_value else f"{sym.OFF} {t('common.disabled')}"
        )
        await ctx.client.reply(
            ctx.message, t_success("config.feature_updated", feature=feature_name, status=status)
        )

    async def _handle_command(self, ctx: CommandContext, args: list[str]) -> None:
        """Handle command enable/disable subcommand."""
        if not args:
            await ctx.client.reply(ctx.message, t_error("config.cmd_usage"))
            return

        action = args[0].lower()

        if action == "list":
            await self._list_commands(ctx)
        elif action == "enable" and len(args) >= 2:
            cmd_name = args[1].lower()
            if runtime_config.enable_command(cmd_name):
                await ctx.client.reply(ctx.message, t_success("config.cmd_enabled", name=cmd_name))
            else:
                await ctx.client.reply(
                    ctx.message, t_info("config.cmd_already_enabled", name=cmd_name)
                )
        elif action == "disable" and len(args) >= 2:
            cmd_name = args[1].lower()
            if cmd_name in ["config", "cfg", "settings"]:
                await ctx.client.reply(ctx.message, t_error("config.cannot_disable_config"))
                return
            if runtime_config.disable_command(cmd_name):
                await ctx.client.reply(ctx.message, t_success("config.cmd_disabled", name=cmd_name))
            else:
                await ctx.client.reply(
                    ctx.message, t_info("config.cmd_already_disabled", name=cmd_name)
                )
        else:
            await ctx.client.reply(ctx.message, t_error("config.cmd_usage"))

    async def _list_commands(self, ctx: CommandContext) -> None:
        """List all commands with their status."""
        all_cmds = command_loader.all_commands
        disabled = runtime_config.get_disabled_commands()

        seen = set()
        lines = [f"*📋 {t('headers.commands')}*", ""]

        for _name, cmd in sorted(all_cmds.items()):
            if cmd.name in seen:
                continue
            seen.add(cmd.name)

            is_disabled = cmd.name in disabled
            status = "❌" if is_disabled else "✅"
            owner_tag = " 👑" if cmd.owner_only else ""
            lines.append(f"{status} `{cmd.name}`{owner_tag}")

        if disabled:
            lines.append(f"\n*{t('common.disabled')}:* {', '.join(f'`{c}`' for c in disabled)}")

        await ctx.client.reply(ctx.message, "\n".join(lines))

    async def _handle_get(self, ctx: CommandContext, args: list[str]) -> None:
        """Get a config value."""
        if not args:
            await ctx.client.reply(ctx.message, t_error("config.get_usage"))
            return

        key = args[0]
        value = runtime_config.get(key)

        if value is None:
            await ctx.client.reply(ctx.message, t_error("config.key_not_found", key=key))
        else:
            await ctx.client.reply(ctx.message, f"*{key}*: `{value}`")

    async def _handle_set(self, ctx: CommandContext, args: list[str]) -> None:
        """Set a config value."""
        if len(args) < 2:
            await ctx.client.reply(ctx.message, t_error("config.set_usage"))
            return

        key = args[0]
        value_str = " ".join(args[1:])

        if value_str.lower() == "true":
            value = True
        elif value_str.lower() == "false":
            value = False
        elif value_str.isdigit():
            value = int(value_str)
        else:
            value = value_str

        runtime_config.set(key, value)
        await ctx.client.reply(ctx.message, t_success("config.value_set", key=key, value=value))

    async def _handle_owner(self, ctx: CommandContext, args: list[str]) -> None:
        """Handle owner subcommand."""
        if not args:
            owner = runtime_config.get_owner_jid()
            if owner:
                await ctx.client.reply(ctx.message, t("config.current_owner", owner=owner))
            else:
                await ctx.client.reply(ctx.message, t_error("config.no_owner"))
            return

        if args[0].lower() == "set" and len(args) >= 2:
            new_owner = args[1]
            runtime_config.set_owner_jid(new_owner)
            await ctx.client.reply(ctx.message, t_success("config.owner_set", owner=new_owner))
        elif args[0].lower() == "me":
            runtime_config.set_owner_jid(ctx.message.sender_jid)
            await ctx.client.reply(ctx.message, t_success("config.owner_is_you"))
        else:
            await ctx.client.reply(ctx.message, t_error("config.owner_usage"))

    async def _show_all(self, ctx: CommandContext) -> None:
        """Show all configuration."""
        config = runtime_config.all_config()

        if not config:
            await ctx.client.reply(ctx.message, t("config.no_config"))
            return

        lines = [f"*{t('config.all_config')}*", ""]
        for key, value in config.items():
            if isinstance(value, dict):
                lines.append(f"*{key}:*")
                for k, v in value.items():
                    lines.append(f"  - `{k}`: `{v}`")
            elif isinstance(value, list):
                lines.append(
                    f"*{key}:* {', '.join(f'`{v}`' for v in value) if value else '(empty)'}"
                )
            else:
                lines.append(f"- `{key}`: `{value}`")

        await ctx.client.reply(ctx.message, "\n".join(lines))

    async def _handle_autoread(self, ctx: CommandContext, args: list[str]) -> None:
        """Handle auto-read configuration."""
        current = runtime_config.get_nested("bot", "auto_read", default=False)

        if not args:
            status = t("common.on") if current else t("common.off")
            await ctx.client.reply(ctx.message, t("config.autoread_status", status=status))
            return

        action = args[0].lower()

        if action in ("on", "enable", "1", "true"):
            runtime_config.set_nested("bot", "auto_read", True)
            await ctx.client.reply(ctx.message, t_success("config.autoread_enabled"))
        elif action in ("off", "disable", "0", "false"):
            runtime_config.set_nested("bot", "auto_read", False)
            await ctx.client.reply(ctx.message, t_success("config.autoread_disabled"))
        else:
            await ctx.client.reply(ctx.message, t_error("config.autoread_usage"))

    async def _handle_autoreact(self, ctx: CommandContext, args: list[str]) -> None:
        """Handle auto-react configuration."""
        current_enabled = runtime_config.get_nested("bot", "auto_react", default=False)
        current_emoji = runtime_config.get_nested("bot", "auto_react_emoji", default="")

        if not args:
            status = t("common.on") if current_enabled and current_emoji else t("common.off")
            emoji_display = f"`{current_emoji}`" if current_emoji else t("common.none")
            await ctx.client.reply(
                ctx.message, t("config.autoreact_status", status=status, emoji=emoji_display)
            )
            return

        action = args[0]

        if action.lower() in ("off", "disable", "0", "false"):
            runtime_config.set_nested("bot", "auto_react", False)
            await ctx.client.reply(ctx.message, t_success("config.autoreact_disabled"))
        else:
            emoji = action
            runtime_config.set_nested("bot", "auto_react_emoji", emoji)
            runtime_config.set_nested("bot", "auto_react", True)
            await ctx.client.reply(ctx.message, t_success("config.autoreact_enabled", emoji=emoji))

    async def _handle_selfmode(self, ctx: CommandContext, args: list[str]) -> None:
        """Handle self mode configuration."""
        current = runtime_config.self_mode

        if not args:
            status = f"{sym.ON} {t('common.on')}" if current else f"{sym.OFF} {t('common.off')}"
            await ctx.client.reply(ctx.message, t("config.selfmode_status", status=status))
            return

        action = args[0].lower()

        if action in ("on", "enable", "1", "true"):
            runtime_config.set_self_mode(True)
            await ctx.client.reply(ctx.message, t_success("config.selfmode_enabled"))
        elif action in ("off", "disable", "0", "false"):
            runtime_config.set_self_mode(False)
            await ctx.client.reply(ctx.message, t_success("config.selfmode_disabled"))
        else:
            await ctx.client.reply(ctx.message, t_error("config.selfmode_usage"))

    async def _handle_ai(self, ctx: CommandContext, args: list[str]) -> None:
        """Handle agentic AI configuration."""
        from ai import agentic_ai

        if not args:
            enabled = agentic_ai.enabled
            provider = agentic_ai.provider
            model = agentic_ai.model
            trigger = agentic_ai.trigger_mode
            has_key = bool(agentic_ai.api_key)
            owner_only = agentic_ai.owner_only

            status = f"{sym.ON} {t('common.on')}" if enabled else f"{sym.OFF} {t('common.off')}"
            key_status = t("config.key_set") if has_key else t("config.key_not_set")

            await ctx.client.reply(
                ctx.message,
                f"{sym.HEADER_L} {t('config.ai_title')} {sym.HEADER_R}\n\n"
                f"{sym.BULLET} *{t('headers.status')}:* {status}\n"
                f"{sym.BULLET} *Provider:* `{provider}`\n"
                f"{sym.BULLET} *Model:* `{model}`\n"
                f"{sym.BULLET} *Trigger:* `{trigger}`\n"
                f"{sym.BULLET} *API Key:* {key_status}\n"
                f"{sym.BULLET} *Owner Only:* {t('common.yes') if owner_only else t('common.no')}",
            )
            return

        action = args[0].lower()

        if action in ("on", "enable", "1", "true"):
            if not agentic_ai.api_key:
                await ctx.client.reply(ctx.message, t_error("config.ai_no_key"))
                return
            agentic_ai.set_enabled(True)
            await ctx.client.reply(
                ctx.message, t_success("config.ai_enabled", mode=agentic_ai.trigger_mode)
            )

        elif action in ("off", "disable", "0", "false"):
            agentic_ai.set_enabled(False)
            await ctx.client.reply(ctx.message, t_success("config.ai_disabled"))

        elif action == "key" and len(args) >= 2:
            key = args[1]
            agentic_ai.set_api_key(key)
            await ctx.client.reply(ctx.message, t_success("config.ai_key_updated"))

        elif action == "mode" and len(args) >= 2:
            mode = args[1].lower()
            if mode in ("always", "mention", "reply"):
                agentic_ai.set_trigger_mode(mode)
                await ctx.client.reply(ctx.message, t_success("config.ai_mode_set", mode=mode))
            else:
                await ctx.client.reply(ctx.message, t_error("config.ai_invalid_mode"))

        else:
            await ctx.client.reply(ctx.message, t_error("config.ai_unknown"))
