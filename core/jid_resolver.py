"""
JID Resolution Utilities.

Provides utilities for resolving and comparing JIDs across different formats:
- Phone Number (PN): 1234567890@s.whatsapp.net
- Linked ID (LID): 123456@lid

Uses neonize's get_lid_from_pn/get_pn_from_lid for conversion with caching.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from neonize.utils.jid import build_jid

from core.logger import log_debug, log_warning

if TYPE_CHECKING:
    from core.client import BotClient


_jid_cache: dict[str, dict[str, str | None]] = {}
_CACHE_MAX_SIZE = 500


def get_user_part(jid: str) -> str:
    """
    Extract the user part (number/id) from a JID string.

    Args:
        jid: Full JID like "123456@lid" or "1234567890@s.whatsapp.net"

    Returns:
        User part before @ symbol, stripped of device info (after :)
    """
    if not jid:
        return ""
    user_part = jid.split("@")[0]
    return user_part.split(":")[0]


def get_server(jid: str) -> str:
    """
    Get the server part of a JID.

    Args:
        jid: Full JID string

    Returns:
        Server part: "lid", "s.whatsapp.net", "g.us", etc.
    """
    if not jid or "@" not in jid:
        return ""
    return jid.split("@")[1]


def is_lid(jid: str) -> bool:
    """
    Check if a JID is in LID format.

    Args:
        jid: JID string to check

    Returns:
        True if JID ends with @lid
    """
    return jid.endswith("@lid") if jid else False


def is_pn(jid: str) -> bool:
    """
    Check if a JID is in PN (Phone Number) format.

    Args:
        jid: JID string to check

    Returns:
        True if JID ends with @s.whatsapp.net
    """
    return jid.endswith("@s.whatsapp.net") if jid else False


def is_group(jid: str) -> bool:
    """
    Check if a JID is a group JID.

    Args:
        jid: JID string to check

    Returns:
        True if JID ends with @g.us
    """
    return jid.endswith("@g.us") if jid else False


def normalize_jid(jid: str, to_lid: bool = True) -> str:
    """
    Normalize a JID to a consistent format (strips device info).

    Args:
        jid: Input JID string
        to_lid: If True, prefer LID format for individual JIDs

    Returns:
        Normalized JID string
    """
    if not jid:
        return ""

    user = get_user_part(jid)
    server = get_server(jid)

    if not user or not server:
        return jid

    if server == "g.us":
        return f"{user}@g.us"

    return f"{user}@{server}"


async def resolve_pair(jid: str, client: BotClient | None = None) -> dict[str, str | None]:
    """
    Resolve both PN and LID formats for a given JID.

    Uses neonize client's get_lid_from_pn/get_pn_from_lid to convert.
    Results are cached for performance.

    Args:
        jid: Any valid JID string (PN or LID format)
        client: BotClient instance for API calls (optional)

    Returns:
        Dict with keys "pn" and "lid", values may be None if resolution fails
        Example: {"pn": "1234567890@s.whatsapp.net", "lid": "123456@lid"}
    """
    if not jid:
        return {"pn": None, "lid": None}

    if is_group(jid):
        return {"pn": jid, "lid": jid}

    user = get_user_part(jid)
    server = get_server(jid)

    if user in _jid_cache:
        log_debug(f"JID cache hit for {user}")
        return _jid_cache[user]

    result: dict[str, str | None] = {"pn": None, "lid": None}

    if server == "lid":
        result["lid"] = f"{user}@lid"
    elif server == "s.whatsapp.net":
        result["pn"] = f"{user}@s.whatsapp.net"

    if client is None:
        log_debug(f"No client available for JID resolution of {jid}")
        return result

    try:
        neonize = client._client

        if server == "lid" and result["pn"] is None:
            lid_jid = build_jid(user, "lid")
            try:
                pn_jid = await neonize.get_pn_from_lid(lid_jid)
                if pn_jid and pn_jid.User:
                    result["pn"] = f"{pn_jid.User}@s.whatsapp.net"
                    log_debug(f"Resolved LID {jid} -> PN {result['pn']}")
            except Exception as e:
                log_debug(f"Could not resolve LID to PN: {e}")

        elif server == "s.whatsapp.net" and result["lid"] is None:
            pn_jid = build_jid(user, "s.whatsapp.net")
            try:
                lid_jid = await neonize.get_lid_from_pn(pn_jid)
                if lid_jid and lid_jid.User:
                    result["lid"] = f"{lid_jid.User}@lid"
                    log_debug(f"Resolved PN {jid} -> LID {result['lid']}")
            except Exception as e:
                log_debug(f"Could not resolve PN to LID: {e}")

        if len(_jid_cache) >= _CACHE_MAX_SIZE:
            keys_to_remove = list(_jid_cache.keys())[: _CACHE_MAX_SIZE // 2]
            for k in keys_to_remove:
                del _jid_cache[k]

        _jid_cache[user] = result
        if result["pn"]:
            pn_user = get_user_part(result["pn"])
            if pn_user != user:
                _jid_cache[pn_user] = result
        if result["lid"]:
            lid_user = get_user_part(result["lid"])
            if lid_user != user:
                _jid_cache[lid_user] = result

    except Exception as e:
        log_warning(f"JID resolution error for {jid}: {e}")

    return result


async def jids_match(jid1: str, jid2: str, client: BotClient | None = None) -> bool:
    """
    Check if two JIDs refer to the same user, regardless of format.

    This function handles the case where one JID is in PN format
    and the other is in LID format.

    Args:
        jid1: First JID to compare
        jid2: Second JID to compare
        client: BotClient instance for API calls (optional)

    Returns:
        True if both JIDs refer to the same user
    """
    if not jid1 or not jid2:
        return False

    if jid1 == jid2:
        return True

    user1 = get_user_part(jid1)
    user2 = get_user_part(jid2)

    if user1 == user2:
        return True

    if (is_lid(jid1) and is_pn(jid2)) or (is_pn(jid1) and is_lid(jid2)):
        pair1 = await resolve_pair(jid1, client)
        pair2 = await resolve_pair(jid2, client)

        if pair1["pn"] and pair2["pn"] and pair1["pn"] == pair2["pn"]:
            return True
        if pair1["lid"] and pair2["lid"] and pair1["lid"] == pair2["lid"]:
            return True
        if pair1["pn"] and pair1["pn"] == jid2:
            return True
        if pair1["lid"] and pair1["lid"] == jid2:
            return True
        if pair2["pn"] and pair2["pn"] == jid1:
            return True
        if pair2["lid"] and pair2["lid"] == jid1:
            return True

    return False


def jids_match_sync(jid1: str, jid2: str) -> bool:
    """
    Synchronous JID comparison (without API calls).

    This is a fallback that only compares user parts.
    It may return False for JIDs that actually match if they use
    different PN/LID numbers.

    Args:
        jid1: First JID to compare
        jid2: Second JID to compare

    Returns:
        True if user parts match
    """
    if not jid1 or not jid2:
        return False

    if jid1 == jid2:
        return True

    return get_user_part(jid1) == get_user_part(jid2)


def clear_cache() -> None:
    """Clear the JID resolution cache."""
    _jid_cache.clear()
    log_debug("JID cache cleared")


def get_cache_stats() -> dict:
    """Get cache statistics for debugging."""
    return {
        "size": len(_jid_cache),
        "max_size": _CACHE_MAX_SIZE,
    }
