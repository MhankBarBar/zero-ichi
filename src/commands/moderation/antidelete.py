"""
Antidelete command - Toggle anti-delete feature and configure settings.
Only works for bot owner.
"""

from core.command import Command, CommandContext
from core.i18n import t, t_success
from core.runtime_config import runtime_config


class AntideleteCommand(Command):
    name = "antidelete"
    description = "Toggle anti-delete feature and configure settings"
    usage = "antidelete [on|off|forward|status]"
    aliases = ["ad", "antirevoke"]
    owner_only = True

    async def execute(self, ctx: CommandContext) -> None:
        """Toggle the anti-delete feature or configure settings."""
        args = ctx.args

        if not args:
            await self._show_status(ctx)
            return

        action = args[0].lower()

        if action in ("on", "enable", "1", "true"):
            runtime_config.set_feature("anti_delete", True)
            await ctx.client.reply(ctx.message, t_success("antidelete.enabled"))
        elif action in ("off", "disable", "0", "false"):
            runtime_config.set_feature("anti_delete", False)
            await ctx.client.reply(ctx.message, t_success("antidelete.disabled"))
        elif action == "forward":
            await self._handle_forward(ctx, args[1:])
        elif action == "status":
            await self._show_status(ctx)
        elif action == "help":
            await self._show_help(ctx)
        else:
            await self._show_help(ctx)

    async def _show_status(self, ctx: CommandContext) -> None:
        """Show current anti-delete status and settings."""
        enabled = runtime_config.get_feature("anti_delete")
        forward_to = runtime_config.get_nested("anti_delete", "forward_to", default="")
        cache_ttl = runtime_config.get_nested("anti_delete", "cache_ttl", default=60)
        p = ctx.prefix

        status = t("common.on") if enabled else t("common.off")
        forward_status = (
            f"`{forward_to}`" if forward_to else f"_({t('antidelete.reply_in_place')})_"
        )

        await ctx.client.reply(
            ctx.message,
            f"*📋 {t('antidelete.status_title')}*\n\n"
            f"• {t('headers.status')}: {status}\n"
            f"• {t('antidelete.forward_to')}: {forward_status}\n"
            f"• {t('antidelete.cache_ttl')}: {cache_ttl} {t('antidelete.minutes')}\n\n"
            f"{t('antidelete.use_help', prefix=p)}",
        )

    async def _show_help(self, ctx: CommandContext) -> None:
        """Show anti-delete help."""
        p = ctx.prefix
        await ctx.client.reply(
            ctx.message,
            f"*📋 {t('antidelete.help_title')}*\n\n"
            f"• `{p}antidelete on` - {t('antidelete.help_on')}\n"
            f"• `{p}antidelete off` - {t('antidelete.help_off')}\n"
            f"• `{p}antidelete forward <jid>` - {t('antidelete.help_forward_jid')}\n"
            f"• `{p}antidelete forward here` - {t('antidelete.help_forward_here')}\n"
            f"• `{p}antidelete forward off` - {t('antidelete.help_forward_off')}\n"
            f"• `{p}antidelete status` - {t('antidelete.help_status')}\n\n"
            f"*{t('antidelete.what_it_does_title')}*\n"
            f"{t('antidelete.what_it_does')}",
        )

    async def _handle_forward(self, ctx: CommandContext, args: list[str]) -> None:
        """Handle forward_to setting."""
        p = ctx.prefix

        if not args:
            forward_to = runtime_config.get_nested("anti_delete", "forward_to", default="")
            if forward_to:
                await ctx.client.reply(
                    ctx.message,
                    f"{t('antidelete.current_forward', jid=forward_to)}\n\n"
                    f"{t('antidelete.disable_hint', prefix=p)}",
                )
            else:
                await ctx.client.reply(
                    ctx.message,
                    f"{t('antidelete.forward_in_place')}\n\n"
                    f"{t('antidelete.forward_hint', prefix=p)}",
                )
            return

        target = args[0].lower()

        if target in ("off", "disable", "none", ""):
            runtime_config.set_nested("anti_delete", "forward_to", "")
            await ctx.client.reply(ctx.message, t_success("antidelete.forward_reply_in_place"))
        elif target == "here":
            runtime_config.set_nested("anti_delete", "forward_to", ctx.message.chat_jid)
            await ctx.client.reply(ctx.message, t_success("antidelete.forward_this_chat"))
        elif target == "me":
            runtime_config.set_nested("anti_delete", "forward_to", ctx.message.sender_jid)
            await ctx.client.reply(ctx.message, t_success("antidelete.forward_dm"))
        else:
            jid = args[0]
            if "@" not in jid:
                jid = f"{jid}@lid"

            runtime_config.set_nested("anti_delete", "forward_to", jid)
            await ctx.client.reply(ctx.message, t_success("antidelete.forward_set", jid=jid))
