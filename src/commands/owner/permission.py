"""Owner command - manage role-based command permission overrides."""

from __future__ import annotations

from core.command import Command, CommandContext, command_loader
from core.i18n import t, t_error, t_info, t_success
from core.runtime_config import runtime_config


class PermissionCommand(Command):
    name = "permission"
    aliases = ["permissions", "perm"]
    description = "Manage role overrides for command access"
    usage = "permission list|set|reset"
    owner_only = True

    async def execute(self, ctx: CommandContext) -> None:
        args = ctx.args
        if not args:
            await ctx.client.reply(ctx.message, t_error("permission.usage", prefix=ctx.prefix))
            return

        action = args[0].lower()
        if action == "list":
            await self._list_overrides(ctx, args[1:])
            return
        if action == "set":
            await self._set_override(ctx, args[1:])
            return
        if action == "reset":
            await self._reset_override(ctx, args[1:])
            return

        await ctx.client.reply(ctx.message, t_error("permission.usage", prefix=ctx.prefix))

    async def _list_overrides(self, ctx: CommandContext, args: list[str]) -> None:
        perms = runtime_config.get_command_permissions()
        global_map = perms.get("global", {})
        groups_map = perms.get("groups", {})

        scope = args[0].lower() if args else ""
        if scope and scope not in {"global", "here"} and "@g.us" not in scope:
            await ctx.client.reply(ctx.message, t_error("permission.invalid_scope"))
            return
        lines = [f"*{t('permission.title')}*", ""]

        if scope in {"", "global"}:
            lines.append(f"*{t('permission.global_scope')}*")
            if global_map:
                for cmd_name in sorted(global_map.keys()):
                    lines.append(
                        t(
                            "permission.item",
                            command=cmd_name,
                            role=global_map[cmd_name],
                        )
                    )
            else:
                lines.append(t("permission.none"))

        if scope == "global":
            await ctx.client.reply(ctx.message, "\n".join(lines))
            return

        group_jid = self._scope_to_group_jid(ctx, scope)
        if group_jid:
            lines.append("")
            lines.append(f"*{t('permission.group_scope', group=group_jid)}*")
            group_map = groups_map.get(group_jid, {})
            if group_map:
                for cmd_name in sorted(group_map.keys()):
                    lines.append(
                        t(
                            "permission.item",
                            command=cmd_name,
                            role=group_map[cmd_name],
                        )
                    )
            else:
                lines.append(t("permission.none"))

        await ctx.client.reply(ctx.message, "\n".join(lines))

    async def _set_override(self, ctx: CommandContext, args: list[str]) -> None:
        if len(args) < 2:
            await ctx.client.reply(ctx.message, t_error("permission.set_usage", prefix=ctx.prefix))
            return

        cmd_name = args[0].lower().strip()
        role = args[1].lower().strip()
        if role not in {"member", "admin", "owner"}:
            await ctx.client.reply(ctx.message, t_error("permission.invalid_role"))
            return

        cmd = command_loader.get(cmd_name)
        if not cmd:
            await ctx.client.reply(ctx.message, t_error("errors.not_found", command=cmd_name))
            return

        canonical = cmd.name.lower()
        scope = args[2].lower() if len(args) >= 3 else ""
        if scope and scope not in {"global", "here"} and "@g.us" not in scope:
            await ctx.client.reply(ctx.message, t_error("permission.invalid_scope"))
            return

        group_jid = self._scope_to_group_jid(ctx, scope)
        if scope == "here" and not ctx.message.is_group:
            await ctx.client.reply(ctx.message, t_error("permission.here_group_only"))
            return

        try:
            runtime_config.set_command_role_override(canonical, role, group_jid=group_jid)
        except ValueError as e:
            await ctx.client.reply(ctx.message, t_error("config.validation_failed", details=str(e)))
            return

        scope_text = (
            t("permission.scope_group", group=group_jid)
            if group_jid
            else t("permission.scope_global")
        )
        await ctx.client.reply(
            ctx.message,
            t_success(
                "permission.set_done",
                command=canonical,
                role=role,
                scope=scope_text,
            ),
        )

    async def _reset_override(self, ctx: CommandContext, args: list[str]) -> None:
        if not args:
            await ctx.client.reply(
                ctx.message, t_error("permission.reset_usage", prefix=ctx.prefix)
            )
            return

        cmd_name = args[0].lower().strip()
        cmd = command_loader.get(cmd_name)
        if not cmd:
            await ctx.client.reply(ctx.message, t_error("errors.not_found", command=cmd_name))
            return

        canonical = cmd.name.lower()
        scope = args[1].lower() if len(args) >= 2 else ""
        if scope and scope not in {"global", "here"} and "@g.us" not in scope:
            await ctx.client.reply(ctx.message, t_error("permission.invalid_scope"))
            return

        group_jid = self._scope_to_group_jid(ctx, scope)
        if scope == "here" and not ctx.message.is_group:
            await ctx.client.reply(ctx.message, t_error("permission.here_group_only"))
            return

        removed = runtime_config.reset_command_role_override(canonical, group_jid=group_jid)
        if not removed:
            await ctx.client.reply(ctx.message, t_info("permission.no_override", command=canonical))
            return

        scope_text = (
            t("permission.scope_group", group=group_jid)
            if group_jid
            else t("permission.scope_global")
        )
        await ctx.client.reply(
            ctx.message,
            t_success("permission.reset_done", command=canonical, scope=scope_text),
        )

    def _scope_to_group_jid(self, ctx: CommandContext, scope: str) -> str | None:
        """Resolve scope token into optional group JID."""
        if not scope or scope == "global":
            return None
        if scope == "here":
            return ctx.message.chat_jid if ctx.message.is_group else None
        return scope if "@g.us" in scope else None
