"""
Command error handling utilities.

Provides centralized error reporting for commands that catches exceptions
and sends detailed reports to the owner instead of exposing errors to users.
"""

from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

from core import symbols as sym
from core.i18n import t_error
from core.logger import log_error, log_warning
from core.runtime_config import runtime_config

if TYPE_CHECKING:
    from core.client import BotClient
    from core.message import MessageHelper


async def report_error(
    client: BotClient,
    msg: MessageHelper,
    command_name: str,
    error: Exception,
    *,
    show_user_error: bool = True,
    user_message: str | None = None,
) -> None:
    """
    Report a command error to the owner and optionally show a generic message to the user.

    This is the centralized error handler for commands. Use it in your command's
    except block instead of directly sending errors to users.

    Args:
        client: The BotClient instance
        msg: The message that triggered the command
        command_name: Name of the command that failed
        error: The exception that was raised
        show_user_error: If True, send a generic error message to the user
        user_message: Custom message to show the user (defaults to generic error)

    Usage:
        try:
            # command logic
        except Exception as e:
            await report_error(ctx.client, ctx.message, "command_name", e)
    """
    error_details = traceback.format_exc()
    log_error(f"Error in command '{command_name}': {error}")

    is_owner = await runtime_config.is_owner_async(msg.sender_jid, client)

    await _send_error_to_owner(client, msg, command_name, error, error_details)

    if show_user_error:
        is_private_with_owner = not msg.is_group and is_owner

        if is_private_with_owner:
            await client.reply(msg, f"{sym.ERROR} `{type(error).__name__}: {error}`")
        else:
            await client.reply(msg, user_message or t_error("errors.generic"))


async def _send_error_to_owner(
    client: BotClient,
    msg: MessageHelper,
    command_name: str,
    error: Exception,
    error_details: str,
) -> None:
    """
    Send detailed error report to owner's DM.

    If owner JID is configured, sends to owner's DM.
    Otherwise, falls back to sending to bot's own chat.
    """
    try:
        from core.jid_resolver import get_user_part

        owner_jid = runtime_config.get_owner_jid()

        error_msg = (
            f"{sym.ERROR} *Command Error Report*\n\n"
            f"*Command:* `{command_name}`\n"
            f"*Sender:* {msg.sender_name} (`{get_user_part(msg.sender_jid)}`)\n"
            f"*Chat:* `{msg.chat_jid}`\n"
            f"*Error:* `{type(error).__name__}: {error}`\n\n"
            f"```\n{error_details[-1500:]}\n```"
        )

        if owner_jid:
            log_error(f"Sending error report to owner: {owner_jid}")
            await client.send(owner_jid, error_msg)
        else:
            me = await client._client.get_me()
            if me and me.JID:
                bot_jid = f"{me.JID.User}@{me.JID.Server}"
                log_error(f"No owner set, sending error report to bot self: {bot_jid}")
                await client.send(bot_jid, error_msg)
            else:
                log_warning("Could not get bot JID for self-note")

    except Exception as e:
        log_warning(f"Failed to send error report: {e}")
