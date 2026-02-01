"""
Welcome/Goodbye message handler.

Handles automatic messages when users join or leave groups.
"""

from core.storage import GroupData as GroupStorage


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
    message = message.replace("{name}", member_name)
    message = message.replace("{group}", "the group")

    mention = f"@{member_jid.split('@')[0]}"
    message = message.replace("{mention}", mention)

    try:
        await bot.send(group_jid, message)
    except Exception as e:
        from core.logger import log_warning

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
    message = message.replace("{name}", member_name)

    try:
        await bot.send(group_jid, message)
    except Exception as e:
        from core.logger import log_warning

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
