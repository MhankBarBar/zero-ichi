"""
Anti-link command - Configure anti-link settings for the group.
"""

import re

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t, t_error, t_success
from core.storage import GroupData


class AntilinkCommand(Command):
    name = "antilink"
    description = "Configure anti-link protection for the group"
    usage = "antilink [on|off|action|whitelist]"
    aliases = ["al"]
    group_only = True
    admin_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Configure anti-link settings."""
        args = ctx.args
        data = GroupData(ctx.message.chat_jid)

        if not args:
            await self._show_status(ctx, data)
            return

        action = args[0].lower()

        if action in ("on", "enable", "1", "true"):
            config = data.anti_link
            config["enabled"] = True
            data.save_anti_link(config)
            await ctx.client.reply(ctx.message, t_success("antilink.enabled"))
        elif action in ("off", "disable", "0", "false"):
            config = data.anti_link
            config["enabled"] = False
            data.save_anti_link(config)
            await ctx.client.reply(ctx.message, t_error("antilink.disabled"))
        elif action == "action":
            await self._handle_action(ctx, data, args[1:])
        elif action in ("whitelist", "wl"):
            await self._handle_whitelist(ctx, data, args[1:])
        elif action == "status":
            await self._show_status(ctx, data)
        elif action == "help":
            await self._show_help(ctx)
        else:
            await self._show_help(ctx)

    async def _show_status(self, ctx: CommandContext, data: GroupData) -> None:
        """Show current anti-link status."""
        config = data.anti_link
        enabled = config.get("enabled", False)
        action = str(config.get("action", "warn")).lower()
        if action in {"ban", "mute"}:
            action = "kick"
        whitelist = config.get("whitelist", [])
        p = ctx.prefix

        status = f"{sym.ON} ON" if enabled else f"{sym.OFF} OFF"
        wl_str = ", ".join(f"`{d}`" for d in whitelist) if whitelist else "_(none)_"

        msg = sym.box(
            "Anti-Link Settings",
            [
                f"Status: {status}",
                f"Action: `{action}`",
                f"Whitelist: {wl_str}",
                "",
                f"Use `{p}antilink help` for commands.",
            ],
        )
        await ctx.client.reply(ctx.message, msg)

    async def _show_help(self, ctx: CommandContext) -> None:
        """Show anti-link help."""
        p = ctx.prefix
        msg = sym.box(
            "Anti-Link Commands",
            [
                f"`{p}antilink on` - Enable for this group",
                f"`{p}antilink off` - Disable for this group",
                f"`{p}antilink action <type>` - Set action (warn/delete/kick)",
                f"`{p}antilink whitelist add <domain>` - Allow a domain",
                f"`{p}antilink whitelist remove <domain>` - Remove from whitelist",
                f"`{p}antilink whitelist list` - Show whitelist",
                f"`{p}antilink status` - Show current settings",
                "",
                "*Actions:*",
                "`warn` - Warn the user",
                "`delete` - Delete the message only",
                "`kick` - Delete + kick user",
            ],
        )
        await ctx.client.reply(ctx.message, msg)

    async def _handle_action(self, ctx: CommandContext, data: GroupData, args: list[str]) -> None:
        """Handle action setting."""
        valid_actions = ["warn", "delete", "kick"]

        if not args:
            config = data.anti_link
            current = config.get("action", "warn")
            await ctx.client.reply(
                ctx.message,
                f"Current action: `{current}`\n\n"
                f"Options: {', '.join(f'`{a}`' for a in valid_actions)}",
            )
            return

        new_action = args[0].lower()
        if new_action in {"ban", "mute"}:
            new_action = "kick"

        if new_action not in valid_actions:
            await ctx.client.reply(
                ctx.message,
                sym.error(f"Invalid action. Use: {', '.join(f'`{a}`' for a in valid_actions)}"),
            )
            return

        config = data.anti_link
        config["action"] = new_action
        data.save_anti_link(config)
        await ctx.client.reply(ctx.message, t_success("antilink.action_set", action=new_action))

    async def _handle_whitelist(
        self, ctx: CommandContext, data: GroupData, args: list[str]
    ) -> None:
        """Handle whitelist management."""
        config = data.anti_link
        whitelist = config.get("whitelist", [])
        p = ctx.prefix

        if not args or args[0].lower() == "list":
            if whitelist:
                await ctx.client.reply(
                    ctx.message,
                    sym.section(t("antilink.whitelist_title"), [f"`{d}`" for d in whitelist]),
                )
            else:
                await ctx.client.reply(ctx.message, t("antilink.whitelist_empty"))
            return

        action = args[0].lower()

        if action == "add" and len(args) >= 2:
            domain = args[1].lower()
            domain = re.sub(r"^https?://", "", domain)
            domain = re.sub(r"^www\.", "", domain)
            domain = domain.split("/")[0]

            if domain in whitelist:
                await ctx.client.reply(
                    ctx.message, t_error("antilink.whitelist_exists", domain=domain)
                )
                return

            whitelist.append(domain)
            config["whitelist"] = whitelist
            data.save_anti_link(config)
            await ctx.client.reply(
                ctx.message, t_success("antilink.whitelist_added", domain=domain)
            )

        elif action in ("remove", "del", "rm") and len(args) >= 2:
            domain = args[1].lower()
            if domain not in whitelist:
                await ctx.client.reply(
                    ctx.message, t_error("antilink.whitelist_not_found", domain=domain)
                )
                return

            whitelist.remove(domain)
            config["whitelist"] = whitelist
            data.save_anti_link(config)
            await ctx.client.reply(
                ctx.message, t_success("antilink.whitelist_removed", domain=domain)
            )

        elif action == "clear":
            config["whitelist"] = []
            data.save_anti_link(config)
            await ctx.client.reply(ctx.message, t_success("antilink.whitelist_cleared"))

        else:
            await ctx.client.reply(
                ctx.message,
                f"Usage:\n"
                f"• `{p}antilink whitelist add <domain>`\n"
                f"• `{p}antilink whitelist remove <domain>`\n"
                f"• `{p}antilink whitelist list`\n"
                f"• `{p}antilink whitelist clear`",
            )
