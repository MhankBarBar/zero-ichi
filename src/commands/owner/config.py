"""
Owner config command - Manage bot configuration at runtime.
"""

from __future__ import annotations

from copy import deepcopy
from io import BytesIO
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from core import symbols as sym
from core.command import Command, CommandContext, command_loader
from core.config_ops import apply_config_operation
from core.i18n import t, t_error, t_info, t_success
from core.presentation import format_command_card
from core.runtime_config import DEFAULT_CONFIG, runtime_config

_SENSITIVE_KEYWORDS = {
    "api_key",
    "key",
    "token",
    "secret",
    "password",
    "pass",
    "auth",
    "credential",
}


def _is_sensitive_path(path: str) -> bool:
    lowered = path.lower()
    for part in lowered.replace("-", "_").split("."):
        if any(k in part for k in _SENSITIVE_KEYWORDS):
            return True
    return False


def _mask_value(path: str, value: Any) -> str:
    if _is_sensitive_path(path):
        return "[redacted]"
    text = str(value)
    return text if len(text) <= 120 else text[:117] + "..."


def _resolve_diff_mode(args: list[str] | None) -> str:
    """Resolve config diff mode (image by default, text if explicitly requested)."""
    if args and args[0].strip().lower() in {"text", "txt"}:
        return "text"
    return "image"


def _load_mono_font(size: int = 16):
    candidates = [
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/Consolas.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def render_diff_image(title: str, rows: list[tuple[str, str]]) -> bytes:
    """Render colored diff lines into PNG bytes."""
    palette = {
        "header": (232, 234, 237),
        "meta": (156, 163, 175),
        "changed": (245, 158, 11),
        "added": (34, 197, 94),
        "missing": (239, 68, 68),
        "default": (229, 231, 235),
    }

    font = _load_mono_font(16)
    padding_x = 28
    padding_y = 24
    line_gap = 8
    bbox = font.getbbox("Ag")
    line_height = (bbox[3] - bbox[1]) + line_gap

    wrapped: list[tuple[str, str]] = []
    max_chars = 100
    for text, tone in rows:
        chunks = [text[i : i + max_chars] for i in range(0, len(text), max_chars)] or [""]
        for chunk in chunks:
            wrapped.append((chunk, tone))

    canvas_rows = [
        (title, "header"),
        ("Legend: ~ changed | + custom | - missing", "meta"),
        ("", "default"),
        *wrapped,
    ]

    max_width = 700
    for text, _ in canvas_rows:
        sample_w = int(font.getlength(text))
        if sample_w > max_width:
            max_width = sample_w

    width = max_width + (padding_x * 2)
    height = (len(canvas_rows) * line_height) + (padding_y * 2)

    bg_color: Any = (17, 24, 39)
    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)

    y = padding_y
    for text, tone in canvas_rows:
        color = palette.get(tone, palette["default"])
        draw.text((padding_x, y), text, fill=color, font=font)
        y += line_height

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


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
        elif action == "diff":
            await self._show_diff(ctx, args[1:])
        elif action == "validate":
            await self._validate_config(ctx)
        elif action == "history":
            await self._show_history(ctx, args[1:])
        elif action == "rollback":
            await self._rollback(ctx, args[1:])
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
        card = format_command_card(
            p,
            self.name,
            self.description,
            self.get_usage(p),
            aliases=self.aliases,
            category="owner",
            restrictions=["Owner only"],
        )
        actions = [
            f"`{p}config features` - {t('config.show_features')}",
            f"`{p}config toggle <feature>` - {t('config.toggle_feature')}",
            f"`{p}config cmd list` - {t('config.list_commands')}",
            f"`{p}config cmd enable <name>` - {t('config.enable_command')}",
            f"`{p}config cmd disable <name>` - {t('config.disable_command')}",
            f"`{p}config autoread [on/off]` - {t('config.autoread_desc')}",
            f"`{p}config react [emoji/off]` - {t('config.react_desc')}",
            f"`{p}config selfmode [on/off]` - {t('config.selfmode_desc')}",
            f"`{p}config ai [on/off/key/mode]` - {t('config.ai_desc')}",
            f"`{p}config owner` - {t('config.show_owner')}",
            f"`{p}config all` - {t('config.show_all')}",
            f"`{p}config diff [image|text]` - {t('config.show_diff')}",
            f"`{p}config validate` - {t('config.validate_desc')}",
            f"`{p}config history [limit]` - {t('config.history_desc')}",
            f"`{p}config rollback <id>` - {t('config.rollback_desc')}",
        ]
        await ctx.client.reply(
            ctx.message,
            card + "\n\n" + sym.section(t("config.usage_label"), actions),
        )

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
        if not await self._apply_change(
            ctx,
            lambda: runtime_config.set_feature(feature_name, new_value),
        ):
            return

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
            changed = await self._apply_change(
                ctx,
                lambda: runtime_config.enable_command(cmd_name),
            )
            if changed is None:
                return
            if changed:
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
            changed = await self._apply_change(
                ctx,
                lambda: runtime_config.disable_command(cmd_name),
            )
            if changed is None:
                return
            if changed:
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

        key_name = args[0]
        value = runtime_config.get(key_name)

        if value is None:
            await ctx.client.reply(
                ctx.message,
                t_error("config.key_not_found", **{"key": key_name}),
            )
        else:
            await ctx.client.reply(ctx.message, f"*{key_name}*: `{value}`")

    async def _handle_set(self, ctx: CommandContext, args: list[str]) -> None:
        """Set a config value."""
        if len(args) < 2:
            await ctx.client.reply(ctx.message, t_error("config.set_usage"))
            return

        key_name = args[0]
        value_str = " ".join(args[1:])

        if value_str.lower() == "true":
            value = True
        elif value_str.lower() == "false":
            value = False
        elif value_str.isdigit():
            value = int(value_str)
        else:
            value = value_str

        if not await self._apply_change(ctx, lambda: runtime_config.set(key_name, value)):
            return
        await ctx.client.reply(
            ctx.message,
            t_success("config.value_set", value=value, **{"key": key_name}),
        )

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
            if not await self._apply_change(ctx, lambda: runtime_config.set_owner_jid(new_owner)):
                return
            await ctx.client.reply(ctx.message, t_success("config.owner_set", owner=new_owner))
        elif args[0].lower() == "me":
            if not await self._apply_change(
                ctx,
                lambda: runtime_config.set_owner_jid(ctx.message.sender_jid),
            ):
                return
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

    async def _show_diff(self, ctx: CommandContext, args: list[str] | None = None) -> None:
        """Show diff between runtime config and defaults (image by default)."""
        current = deepcopy(runtime_config.all_config())
        current.pop("$schema", None)
        defaults = deepcopy(DEFAULT_CONFIG)

        mode = _resolve_diff_mode(args)

        diffs = self._collect_diff(defaults, current)
        if not diffs:
            await ctx.client.reply(ctx.message, t_info("config.diff_no_changes"))
            return

        rows: list[tuple[str, str]] = []
        text_lines = [f"*{t('config.diff_title')}*", ""]
        for item in diffs[:200]:
            kind = item["kind"]
            path = item["path"]
            if kind == "changed":
                default_val = _mask_value(path, item["default"])
                current_val = _mask_value(path, item["current"])
                text_lines.append(
                    f"{sym.BULLET} `~ {path}`: `{default_val}` {sym.ARROW} `{current_val}`"
                )
                rows.append((f"~ {path}: {default_val} -> {current_val}", "changed"))
            elif kind == "custom":
                current_val = _mask_value(path, item["current"])
                text_lines.append(f"{sym.BULLET} `+ {path}`: `{current_val}`")
                rows.append((f"+ {path}: {current_val}", "added"))
            elif kind == "missing":
                default_val = _mask_value(path, item["default"])
                text_lines.append(f"{sym.BULLET} `- {path}`: `{default_val}`")
                rows.append((f"- {path}: {default_val}", "missing"))

        if len(diffs) > 200:
            extra = len(diffs) - 200
            text_lines.append(t("config.diff_truncated", count=str(extra)))
            rows.append((f"... and {extra} more differences", "meta"))

        if mode == "text":
            await ctx.client.reply(ctx.message, "\n".join(text_lines))
            return

        try:
            image_bytes = render_diff_image(t("config.diff_title"), rows)
            await ctx.client.send_image(
                to=ctx.message.chat_jid,
                file=image_bytes,
                caption=t("config.diff_image_caption"),
                quoted=ctx.message.event,
            )
        except Exception:
            await ctx.client.reply(ctx.message, "\n".join(text_lines))

    async def _validate_config(self, ctx: CommandContext) -> None:
        """Validate current runtime config against schema."""
        ok, details = runtime_config.validate_current()
        if ok:
            await ctx.client.reply(ctx.message, t_success("config.validate_ok"))
            return
        await ctx.client.reply(ctx.message, t_error("config.validate_failed", details=details))

    async def _show_history(self, ctx: CommandContext, args: list[str] | None = None) -> None:
        """Show recent config history entries."""
        limit = 10
        if args:
            raw = str(args[0]).strip()
            if raw.isdigit():
                limit = max(1, min(50, int(raw)))

        entries = runtime_config.list_config_history(limit=limit)
        if not entries:
            await ctx.client.reply(ctx.message, t_info("config.history_empty"))
            return

        lines = [f"*{t('config.history_title')}*", ""]
        for item in entries:
            lines.append(
                t(
                    "config.history_item",
                    id=item.get("id", ""),
                    ts=item.get("ts", ""),
                    reason=item.get("reason", "update"),
                )
            )

        lines.append("")
        lines.append(t("config.rollback_hint", prefix=ctx.prefix))
        await ctx.client.reply(ctx.message, "\n".join(lines))

    async def _rollback(self, ctx: CommandContext, args: list[str]) -> None:
        """Rollback config to a snapshot id."""
        if not args:
            await ctx.client.reply(ctx.message, t_error("config.rollback_usage", prefix=ctx.prefix))
            return

        snapshot_id = args[0].strip().upper()
        if not snapshot_id:
            await ctx.client.reply(ctx.message, t_error("config.rollback_usage", prefix=ctx.prefix))
            return

        rolled_back = runtime_config.rollback_config(snapshot_id)
        if not rolled_back:
            await ctx.client.reply(
                ctx.message, t_error("config.rollback_not_found", id=snapshot_id)
            )
            return

        await ctx.client.reply(
            ctx.message,
            t_success(
                "config.rollback_done",
                id=rolled_back.get("id", snapshot_id),
                ts=rolled_back.get("ts", ""),
            ),
        )

    def _collect_diff(
        self,
        defaults: dict[str, Any],
        current: dict[str, Any],
        parent: str = "",
    ) -> list[dict[str, Any]]:
        """Collect nested config differences."""
        diffs: list[dict[str, Any]] = []
        keys = sorted(set(defaults.keys()) | set(current.keys()))

        for key in keys:
            path = f"{parent}.{key}" if parent else key
            in_defaults = key in defaults
            in_current = key in current

            if not in_defaults:
                diffs.append(
                    {"kind": "custom", "path": path, "default": None, "current": current[key]}
                )
                continue

            if not in_current:
                diffs.append(
                    {"kind": "missing", "path": path, "default": defaults[key], "current": None}
                )
                continue

            default_val = defaults[key]
            current_val = current[key]
            if isinstance(default_val, dict) and isinstance(current_val, dict):
                diffs.extend(self._collect_diff(default_val, current_val, path))
                continue

            if default_val != current_val:
                diffs.append(
                    {
                        "kind": "changed",
                        "path": path,
                        "default": default_val,
                        "current": current_val,
                    }
                )

        return diffs

    def _fmt(self, value: Any) -> str:
        """Format diff values for compact output."""
        text = str(value)
        return text if len(text) <= 80 else text[:77] + "..."

    async def _apply_change(self, ctx: CommandContext, operation) -> Any:
        """Run preflight validation then apply a config mutation safely."""
        return await apply_config_operation(ctx, operation)

    async def _handle_autoread(self, ctx: CommandContext, args: list[str]) -> None:
        """Handle auto-read configuration."""
        current = runtime_config.get_nested("bot", "auto_read", default=False)

        if not args:
            status = t("common.on") if current else t("common.off")
            await ctx.client.reply(ctx.message, t("config.autoread_status", status=status))
            return

        action = args[0].lower()

        if action in ("on", "enable", "1", "true"):
            if not await self._apply_change(
                ctx, lambda: runtime_config.set_nested("bot", "auto_read", True)
            ):
                return
            await ctx.client.reply(ctx.message, t_success("config.autoread_enabled"))
        elif action in ("off", "disable", "0", "false"):
            if not await self._apply_change(
                ctx,
                lambda: runtime_config.set_nested("bot", "auto_read", False),
            ):
                return
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
            if not await self._apply_change(
                ctx,
                lambda: runtime_config.set_nested("bot", "auto_react", False),
            ):
                return
            await ctx.client.reply(ctx.message, t_success("config.autoreact_disabled"))
        else:
            emoji = action
            if not await self._apply_change(
                ctx,
                lambda: (
                    runtime_config.set_nested("bot", "auto_react_emoji", emoji),
                    runtime_config.set_nested("bot", "auto_react", True),
                ),
            ):
                return
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
            if not await self._apply_change(ctx, lambda: runtime_config.set_self_mode(True)):
                return
            await ctx.client.reply(ctx.message, t_success("config.selfmode_enabled"))
        elif action in ("off", "disable", "0", "false"):
            if not await self._apply_change(ctx, lambda: runtime_config.set_self_mode(False)):
                return
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
            if not await self._apply_change(ctx, lambda: agentic_ai.set_enabled(True)):
                return
            await ctx.client.reply(
                ctx.message, t_success("config.ai_enabled", mode=agentic_ai.trigger_mode)
            )

        elif action in ("off", "disable", "0", "false"):
            if not await self._apply_change(ctx, lambda: agentic_ai.set_enabled(False)):
                return
            await ctx.client.reply(ctx.message, t_success("config.ai_disabled"))

        elif action == "key" and len(args) >= 2:
            key = args[1]
            if not await self._apply_change(ctx, lambda: agentic_ai.set_api_key(key)):
                return
            await ctx.client.reply(ctx.message, t_success("config.ai_key_updated"))

        elif action == "mode" and len(args) >= 2:
            mode = args[1].lower()
            if mode in ("always", "mention", "reply"):
                if not await self._apply_change(ctx, lambda: agentic_ai.set_trigger_mode(mode)):
                    return
                await ctx.client.reply(ctx.message, t_success("config.ai_mode_set", mode=mode))
            else:
                await ctx.client.reply(ctx.message, t_error("config.ai_invalid_mode"))

        else:
            await ctx.client.reply(ctx.message, t_error("config.ai_unknown"))
