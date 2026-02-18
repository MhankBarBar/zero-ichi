"""
Lang command - Change bot language per chat.

Users can set language in private chats.
Admins can set language in groups.
"""

from core import symbols as sym
from core.command import Command, CommandContext
from core.i18n import (
    get_available_languages,
    get_language,
    set_chat_language,
    t,
    t_error,
    t_success,
)
from core.permissions import check_admin_permission


class LangCommand(Command):
    """Change bot language for this chat."""

    name = "lang"
    aliases = ["language", "bahasa"]
    description = "Change bot language for this chat"
    usage = "lang [code]"

    async def execute(self, ctx: CommandContext) -> None:
        """Set or show current language."""
        chat_jid = ctx.message.chat_jid
        is_group = "@g.us" in chat_jid or "@lid" in chat_jid and ctx.message.is_group

        if is_group:
            if not await check_admin_permission(ctx.client, chat_jid, ctx.message.sender_jid):
                await ctx.client.reply(ctx.message, t_error("errors.admin_required", chat_jid))
                return

        if not ctx.args:
            await self._show_status(ctx, chat_jid)
            return

        lang_code = ctx.args[0].lower()
        available = get_available_languages()

        if lang_code not in available:
            codes = ", ".join(f"`{c}`" for c in available.keys())
            await ctx.client.reply(ctx.message, t_error("lang.invalid", chat_jid, codes=codes))
            return

        if set_chat_language(chat_jid, lang_code):
            lang_name = available[lang_code]
            await ctx.client.reply(ctx.message, t_success("lang.changed", chat_jid, lang=lang_name))
        else:
            await ctx.client.reply(ctx.message, t_error("lang.failed", chat_jid))

    async def _show_status(self, ctx: CommandContext, chat_jid: str) -> None:
        """Show current language and available options."""
        current = get_language(chat_jid)
        available = get_available_languages()
        current_name = available.get(current, current)

        lines = [
            f"{sym.STAR} *{t('lang.title', chat_jid)}*\n",
            f"{sym.BULLET} {t('lang.current', chat_jid)}: *{current_name}* (`{current}`)\n",
            f"{t('lang.available', chat_jid)}:",
        ]

        for code, name in available.items():
            marker = " ✓" if code == current else ""
            lines.append(f"  • `{code}` - {name}{marker}")

        lines.append(f"\n{t('lang.usage_hint', chat_jid, prefix=ctx.prefix)}")

        await ctx.client.reply(ctx.message, "\n".join(lines))
