from core import symbols as sym
from core.command import Command, CommandContext
from core.downloader import downloader
from core.i18n import t
from core.permissions import check_admin_permission
from core.runtime_config import runtime_config


class CancelCommand(Command):
    name = "cancel"
    description = "Cancel your active download in this chat"
    usage = "cancel [all]"
    category = "downloader"

    async def execute(self, ctx: CommandContext) -> None:
        """Cancel an active download."""
        chat_jid = ctx.message.chat_jid
        sender_jid = ctx.message.sender_jid

        if ctx.args and ctx.args[0].lower() == "all":
            is_owner = await runtime_config.is_owner_async(sender_jid, ctx.client)
            is_admin = False
            if ctx.message.is_group:
                is_admin = await check_admin_permission(ctx.client, chat_jid, sender_jid)

            if not (is_owner or is_admin):
                await ctx.client.reply(ctx.message, t("errors.admin_required"))
                return

            count = downloader.cancel_all_in_chat(chat_jid)
            if count > 0:
                await ctx.client.reply(
                    ctx.message, f"{sym.SUCCESS} {t('downloader.cancel_all_success', count=count)}"
                )
            else:
                await ctx.client.reply(ctx.message, f"{sym.INFO} {t('downloader.cancel_all_none')}")
            return

        cancelled = downloader.cancel_download(chat_jid, sender_jid)
        if cancelled:
            await ctx.client.reply(ctx.message, f"{sym.SUCCESS} {t('downloader.cancelled')}")
        else:
            await ctx.client.reply(ctx.message, f"{sym.INFO} {t('downloader.cancel_none')}")
