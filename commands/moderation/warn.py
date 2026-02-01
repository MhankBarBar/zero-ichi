"""
Warn command - Issue a warning to a user.
"""

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import t, t_error, t_success
from core.permissions import check_admin_permission, check_bot_admin
from core.storage import GroupData
from core.targets import extract_reason, parse_single_target


class WarnCommand(Command):
    name = "warn"
    description = "Issue a warning to a user"
    usage = "warn @user [reason]"
    group_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Warn a user."""
        sender_jid = ctx.message.sender_jid
        group_jid = ctx.message.chat_jid

        if not await check_admin_permission(ctx.client, group_jid, sender_jid):
            await ctx.client.reply(ctx.message, t_error("errors.admin_required"))
            return

        data = GroupData(group_jid)
        warn_config = data.warnings_config
        warn_limit = warn_config.get("limit", 3)
        warn_action = warn_config.get("action", "kick")

        target_jid = parse_single_target(ctx)
        reason = extract_reason(ctx, skip_first=not ctx.message.mentions) or t("warn.no_reason")

        if not target_jid:
            await ctx.client.reply(ctx.message, t_error("errors.no_target"))
            return

        user_id = target_jid.split("@")[0]

        warnings = data.warnings

        if user_id not in warnings:
            warnings[user_id] = []

        warnings[user_id].append(reason)
        data.save_warnings(warnings)

        warn_count = len(warnings[user_id])

        msg = (
            t("warn.warned", user=user_id, count=warn_count, limit=warn_limit)
            + f"\n{t('warn.reason')}: {reason}"
        )

        if warn_count >= warn_limit:
            if await check_bot_admin(ctx.client, group_jid):
                try:
                    await ctx.client._client.update_group_participants(
                        ctx.client.to_jid(group_jid),
                        [ctx.client.to_jid(target_jid)],
                        "remove",
                    )
                    msg += f"\n\n{t('warn.limit_reached', action=warn_action)}"
                    warnings[user_id] = []
                    data.save_warnings(warnings)
                except Exception as e:
                    msg += f"\n\n{t('warn.action_failed', action=warn_action, error=str(e))}"
            else:
                msg += f"\n\n{t('warn.not_admin', action=warn_action)}"

        await ctx.client.reply(ctx.message, msg)


class WarnConfigCommand(Command):
    """Configure warnings settings for the group."""

    name = "warnconfig"
    aliases = ["wc", "warnset"]
    description = "Configure warning settings for this group"
    usage = "warnconfig [limit|action] [value]"
    group_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Configure warning settings."""
        sender_jid = ctx.message.sender_jid
        group_jid = ctx.message.chat_jid

        if not await check_admin_permission(ctx.client, group_jid, sender_jid):
            await ctx.client.reply(ctx.message, t_error("errors.admin_required"))
            return

        data = GroupData(group_jid)
        args = ctx.args

        if not args:
            await self._show_status(ctx, data)
            return

        action = args[0].lower()

        if action == "limit":
            await self._set_limit(ctx, data, args[1:])
        elif action == "action":
            await self._set_action(ctx, data, args[1:])
        elif action in ("on", "enable"):
            config = data.warnings_config
            config["enabled"] = True
            data.save_warnings_config(config)
            await ctx.client.reply(ctx.message, t_success("warn.enabled"))
        elif action in ("off", "disable"):
            config = data.warnings_config
            config["enabled"] = False
            data.save_warnings_config(config)
            await ctx.client.reply(ctx.message, t_error("warn.disabled"))
        else:
            await self._show_status(ctx, data)

    async def _show_status(self, ctx: CommandContext, data: GroupData) -> None:
        """Show current warnings config."""
        config = data.warnings_config
        enabled = config.get("enabled", True)

        msg = sym.box(
            t("headers.settings"),
            [
                f"{t('common.enabled')}: {sym.ON if enabled else sym.OFF} {t('common.yes') if enabled else t('common.no')}",
                f"{t('warn.limit_label')}: {config.get('limit', 3)}",
                f"{t('warn.action_label')}: `{config.get('action', 'kick')}`",
            ],
        )
        await ctx.client.reply(ctx.message, msg)

    async def _set_limit(self, ctx: CommandContext, data: GroupData, args: list[str]) -> None:
        """Set warning limit."""
        if not args or not args[0].isdigit():
            await ctx.client.reply(ctx.message, t_error("warn.invalid_limit"))
            return

        limit = int(args[0])
        if limit < 1 or limit > 10:
            await ctx.client.reply(ctx.message, t_error("warn.limit_range"))
            return

        config = data.warnings_config
        config["limit"] = limit
        data.save_warnings_config(config)
        await ctx.client.reply(ctx.message, t_success("warn.limit_set", limit=limit))

    async def _set_action(self, ctx: CommandContext, data: GroupData, args: list[str]) -> None:
        """Set warning action."""
        valid = ["kick", "ban", "mute"]

        if not args or args[0].lower() not in valid:
            await ctx.client.reply(
                ctx.message,
                t_error("errors.invalid_action", options=", ".join(f"`{a}`" for a in valid)),
            )
            return

        action = args[0].lower()
        config = data.warnings_config
        config["action"] = action
        data.save_warnings_config(config)
        await ctx.client.reply(ctx.message, t_success("warn.action_set", action=action))
