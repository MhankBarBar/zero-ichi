"""
Anti-link handler - Detects and handles links in group messages.
"""

import re

from core import symbols as sym
from core.client import BotClient
from core.i18n import t, t_warning
from core.logger import log_info
from core.message import MessageHelper
from core.storage import GroupData

URL_PATTERN = re.compile(
    r'https?://[^\s<>"{}|\\^`\[\]]+'  # http:// or https:// URLs
    r"|"
    r'(?:www\.)?[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:/[^\s<>"{}|\\^`\[\]]*)?'  # domain.tld style
)


def extract_domains(text: str) -> list[str]:
    """Extract domain names from text."""
    urls = URL_PATTERN.findall(text)
    domains = []

    for url in urls:
        url = re.sub(r"^https?://", "", url)
        url = re.sub(r"^www\.", "", url)
        domain = url.split("/")[0].lower()
        if domain and "." in domain:
            domains.append(domain)

    return domains


async def handle_anti_link(bot: BotClient, msg: MessageHelper) -> bool:
    """
    Check if message contains links and handle according to group settings.

    Returns:
        True if message was blocked/handled, False otherwise
    """
    if not msg.is_group or not msg.text:
        return False

    if msg.is_from_me:
        return False

    data = GroupData(msg.chat_jid)
    config = data.anti_link

    if not config.get("enabled", False):
        return False

    domains = extract_domains(msg.text)

    if not domains:
        return False

    whitelist = config.get("whitelist", [])
    blocked_domains = []

    for domain in domains:
        is_whitelisted = False
        for wl_domain in whitelist:
            if domain == wl_domain or domain.endswith("." + wl_domain):
                is_whitelisted = True
                break

        if not is_whitelisted:
            blocked_domains.append(domain)

    if not blocked_domains:
        return False

    try:
        group_info = await bot.raw.get_group_info(bot.to_jid(msg.chat_jid))
        sender_user = msg.sender_jid.split("@")[0].split(":")[0]

        for participant in group_info.Participants:
            p_user = participant.JID.User
            if p_user == sender_user:
                if participant.IsAdmin or participant.IsSuperAdmin:
                    return False
                break
    except Exception:
        pass

    action = config.get("action", "warn")

    log_info(f"[ANTI-LINK] Link detected from {msg.sender_name}: {blocked_domains}")

    try:
        if action == "warn":
            await bot.send(
                msg.chat_jid,
                t_warning("antilink.warn_message", user=msg.sender_jid.split("@")[0]),
            )

        elif action == "delete":
            await bot.raw.revoke_message(
                bot.to_jid(msg.chat_jid), bot.to_jid(msg.sender_jid), msg.event.Info.ID
            )
            log_info(f"[ANTI-LINK] Deleted message from {msg.sender_name}")

        elif action == "kick":
            await bot.raw.revoke_message(
                bot.to_jid(msg.chat_jid), bot.to_jid(msg.sender_jid), msg.event.Info.ID
            )
            await bot.raw.update_group_participants(
                bot.to_jid(msg.chat_jid), [bot.to_jid(msg.sender_jid)], "remove"
            )
            await bot.send(
                msg.chat_jid,
                f"{sym.KICK} {t('antilink.kicked', user=msg.sender_jid.split('@')[0])}",
            )
            log_info(f"[ANTI-LINK] Kicked {msg.sender_name} for posting links")

        elif action == "ban":
            await bot.raw.revoke_message(
                bot.to_jid(msg.chat_jid), bot.to_jid(msg.sender_jid), msg.event.Info.ID
            )
            await bot.raw.update_group_participants(
                bot.to_jid(msg.chat_jid), [bot.to_jid(msg.sender_jid)], "remove"
            )
            await bot.send(
                msg.chat_jid, f"{sym.BAN} {t('antilink.banned', user=msg.sender_jid.split('@')[0])}"
            )
            log_info(f"[ANTI-LINK] Banned {msg.sender_name} for posting links")

        return True

    except Exception as e:
        log_info(f"[ANTI-LINK] Error handling link: {e}")
        return False
