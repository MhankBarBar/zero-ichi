"""Command middleware — parse and execute bot commands."""

from core import symbols as sym
from core.analytics import command_analytics
from core.command import CommandContext, command_loader
from core.errors import report_error
from core.event_bus import event_bus
from core.i18n import t
from core.logger import log_command, log_command_execution, log_command_skip
from core.permissions import check_command_permissions, is_owner_for_bypass
from core.rate_limiter import rate_limiter


async def command_middleware(ctx, next):
    """Parse and execute bot commands."""
    command_name, raw_args, args = command_loader.parse_command(ctx.msg.text)
    if not command_name:
        return

    cmd = command_loader.get(command_name)
    if not cmd:
        return

    text = ctx.msg.text.strip()
    cmd_start = text.lower().find(command_name.lower())
    used_prefix = text[:cmd_start] if cmd_start > 0 else "/"

    perm_result = await check_command_permissions(cmd, ctx.msg, ctx.bot)
    if not perm_result:
        if perm_result.error_message:
            await ctx.bot.reply(ctx.msg, perm_result.error_message)
        log_command_skip(command_name, "permission denied", prefix=used_prefix)
        return

    is_owner = await is_owner_for_bypass(ctx.msg, ctx.bot)
    if not is_owner and rate_limiter.is_limited(ctx.msg.sender_jid, command_name):
        remaining = rate_limiter.get_remaining_cooldown(ctx.msg.sender_jid, command_name)
        log_command_skip(
            command_name, f"rate limited ({remaining:.1f}s remaining)", prefix=used_prefix
        )
        await ctx.bot.reply(
            ctx.msg, f"{sym.CLOCK} {t('errors.cooldown', remaining=f'{remaining:.1f}')}"
        )
        return

    rate_limiter.record(ctx.msg.sender_jid, command_name)

    stats_storage = ctx.extras.get("stats_storage")
    if stats_storage:
        stats_storage.increment_stat("commands_used")

    log_command(command_name, ctx.msg.sender_name, ctx.chat_type, prefix=used_prefix)

    try:
        cmd_ctx = CommandContext(
            client=ctx.bot,
            message=ctx.msg,
            args=args,
            raw_args=raw_args,
            command_name=command_name,
            prefix=used_prefix,
        )
        await cmd.execute(cmd_ctx)

        log_command_execution(
            command_name,
            ctx.msg.sender_name,
            ctx.chat_type,
            ctx.msg.chat_jid,
            success=True,
            prefix=used_prefix,
        )

        command_analytics.record_command(command_name, ctx.msg.sender_jid, ctx.msg.chat_jid)
        await event_bus.emit(
            "command_executed",
            {
                "command": command_name,
                "user": ctx.msg.sender_name,
                "chat": ctx.msg.chat_jid,
            },
        )
    except Exception as e:
        log_command_execution(
            command_name,
            ctx.msg.sender_name,
            ctx.chat_type,
            ctx.msg.chat_jid,
            success=False,
            error=str(e),
            prefix=used_prefix,
        )

        await report_error(cmd_ctx.client, cmd_ctx.message, command_name, e)

    await next()
