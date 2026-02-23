"""
Welcome/Goodbye message handler.

Handles automatic messages when users join or leave groups.
"""

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

from core.i18n import t
from core.logger import log_warning
from core.storage import GroupData as GroupStorage

if TYPE_CHECKING:
    from core.command import CommandContext


async def _resolve_placeholders(
    message: str, bot, group_jid: str, member_jid: str, member_name: str
) -> str:
    """Resolve all placeholders in a welcome/goodbye message."""
    message = message.replace("{name}", member_name)
    mention = f"@{member_jid.split('@')[0]}"
    message = message.replace("{mention}", mention)

    if "{group}" in message:
        try:
            group_name = await bot.get_group_name(group_jid)
            message = message.replace("{group}", group_name or "the group")
        except Exception:
            message = message.replace("{group}", "the group")

    if "{count}" in message:
        try:
            group_info = await bot._client.GetGroupInfo(bot._parse_jid(group_jid))
            count = len(group_info.Participants) if group_info and group_info.Participants else "?"
            message = message.replace("{count}", str(count))
        except Exception:
            message = message.replace("{count}", "?")

    now = datetime.now()
    if "{date}" in message:
        message = message.replace("{date}", now.strftime("%b %d, %Y"))
    if "{time}" in message:
        message = message.replace("{time}", now.strftime("%I:%M %p"))

    return message


async def handle_member_join(bot, group_jid: str, member_jid: str, member_name: str) -> None:
    """
    Handle a new member joining a group.

    Args:
        bot: The BotClient instance
        group_jid: The group's JID
        member_jid: The new member's JID
        member_name: The new member's name/push name
    """
    storage = GroupStorage(group_jid)

    welcome_config = storage.load(
        "welcome",
        {
            "enabled": True,
            "message": "Welcome to the group, {name}! 👋\n\nPlease read the group rules.",
        },
    )

    if not welcome_config.get("enabled", True):
        return

    message = welcome_config.get("message", "Welcome, {name}! 👋")
    message = await _resolve_placeholders(message, bot, group_jid, member_jid, member_name)

    try:
        await bot.send(group_jid, message)
    except Exception as e:
        log_warning(f"Failed to send welcome message: {e}")


async def handle_member_leave(bot, group_jid: str, member_jid: str, member_name: str) -> None:
    """
    Handle a member leaving a group.

    Args:
        bot: The BotClient instance
        group_jid: The group's JID
        member_jid: The leaving member's JID
        member_name: The leaving member's name
    """
    storage = GroupStorage(group_jid)

    goodbye_config = storage.load(
        "goodbye",
        {
            "enabled": False,
            "message": "Goodbye, {name}! 👋",
        },
    )

    if not goodbye_config.get("enabled", False):
        return

    message = goodbye_config.get("message", "Goodbye, {name}!")
    message = await _resolve_placeholders(message, bot, group_jid, member_jid, member_name)

    try:
        await bot.send(group_jid, message)
    except Exception as e:
        log_warning(f"Failed to send goodbye message: {e}")


def get_welcome_config(group_jid: str) -> dict:
    """Get welcome configuration for a group."""
    storage = GroupStorage(group_jid)
    return storage.load(
        "welcome",
        {
            "enabled": True,
            "message": "Welcome to the group, {name}! 👋\n\nPlease read the group rules.",
        },
    )


def set_welcome_config(group_jid: str, enabled: bool = None, message: str = None) -> None:
    """Update welcome configuration for a group."""
    storage = GroupStorage(group_jid)
    config = get_welcome_config(group_jid)

    if enabled is not None:
        config["enabled"] = enabled
    if message is not None:
        config["message"] = message

    storage.save("welcome", config)


def get_goodbye_config(group_jid: str) -> dict:
    """Get goodbye configuration for a group."""
    storage = GroupStorage(group_jid)
    return storage.load(
        "goodbye",
        {
            "enabled": False,
            "message": "Goodbye, {name}! 👋",
        },
    )


def set_goodbye_config(group_jid: str, enabled: bool = None, message: str = None) -> None:
    """Update goodbye configuration for a group."""
    storage = GroupStorage(group_jid)
    config = get_goodbye_config(group_jid)

    if enabled is not None:
        config["enabled"] = enabled
    if message is not None:
        config["message"] = message

    storage.save("goodbye", config)


async def handle_welcome_goodbye_config(
    ctx: "CommandContext",
    config_type: str,
    get_config_func: Callable[[str], dict],
    set_config_func: Callable[[str, bool, str], None],
    placeholders_help: str,
) -> None:
    """
    Handle configuration for welcome/goodbye commands.
    """
    if not ctx.args:
        config = get_config_func(ctx.message.chat_jid)
        status = t("common.on") if config.get("enabled", False) else t("common.off")
        msg = config.get("message", "-")

        reply = (
            f"*{config_type.capitalize()} Message Configuration*\n\n"
            f"Status: *{status}*\n"
            f"Message: {msg}\n\n"
            f"Usage:\n"
            f"• `{config_type} on` - Turn on\n"
            f"• `{config_type} off` - Turn off\n"
            f"• `{config_type} set <message>` - Set message\n\n"
            f"Placeholders: {placeholders_help}"
        )
        await ctx.client.reply(ctx.message, reply)
        return

    action = ctx.args[0].lower()
    chat_jid = ctx.message.chat_jid

    if action == "on":
        set_config_func(chat_jid, enabled=True)
        await ctx.client.reply(ctx.message, t(f"{config_type}.enabled", prefix=ctx.prefix))

    elif action == "off":
        set_config_func(chat_jid, enabled=False)
        await ctx.client.reply(ctx.message, t(f"{config_type}.disabled", prefix=ctx.prefix))

    elif action == "set":
        if len(ctx.args) < 2:
            await ctx.client.reply(ctx.message, t(f"{config_type}.provide_text", prefix=ctx.prefix))
            return

        message = " ".join(ctx.args[1:])
        set_config_func(chat_jid, message=message)
        await ctx.client.reply(ctx.message, t(f"{config_type}.updated", prefix=ctx.prefix))

    else:
        await ctx.client.reply(ctx.message, t(f"{config_type}.unknown_action", prefix=ctx.prefix))
