"""
Steam key auto-redeemer.

Redeems Steam product keys programmatically via the Steam web activation
endpoint (the same one store.steampowered.com/account/registerkey uses):

    POST https://store.steampowered.com/account/activatesubkey
        form:  sessionid=<sessionid>&key=<KEY>
        cookie: sessionid=<sessionid>; steamLoginSecure=...; ...

Auth model (v1): a logged-in Steam session from a browser. Log into Steam
once in a browser, then copy the ``sessionid`` and ``steamLoginSecure``
cookie values into config.json (``steam_redeem`` section) or env vars.
No 2FA automation — the session is refreshed by the user re-logging in when
it expires (activation responses tell us when that happens).

Response handling (Steam web):
    {"success": 1}                          -> activated
    {"success": <n>, "message": "..."}      -> failed, message explains why
    non-JSON / "Please log in"              -> session expired / invalid
"""

from __future__ import annotations

import json
import os
import re
from typing import Callable

import httpx

from core.logger import log_error, log_info, log_warning

ACTIVATE_URL = "https://store.steampowered.com/account/ajaxregisterkey"
REGISTER_URL = "https://store.steampowered.com/account/registerkey"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": REGISTER_URL,
    "Origin": "https://store.steampowered.com",
    "Content-Type": "application/x-www-form-urlencoded",
}

# Matches classic (15-char) and extended (20-char) Steam keys.
STEAM_KEY_RE = re.compile(r"\b(?:[A-Z0-9]{5}-){2,4}[A-Z0-9]{5}\b", re.IGNORECASE)


def _steam_config() -> dict:
    """Resolve Steam redeem settings: config.json `steam_redeem`, env fallback."""
    try:
        from core.runtime_config import runtime_config

        cfg = runtime_config.get_nested("steam_redeem", default={}) or {}
    except Exception:
        cfg = {}
    return {
        "enabled": os.getenv("STEAM_AUTO_REDEEM", "") or str(cfg.get("enabled", False)),
        "sessionid": os.getenv("STEAM_SESSIONID", "") or cfg.get("sessionid", "") or "",
        "steam_login_secure": os.getenv("STEAM_LOGIN_SECURE", "")
        or cfg.get("steam_login_secure", "")
        or "",
        "extra_cookies": os.getenv("STEAM_COOKIES", "") or cfg.get("extra_cookies", "") or "",
    }


def _parse_cookie_string(cookie_str: str) -> dict:
    """Parse a 'name=value; name2=value2' cookie string into a dict."""
    cookies: dict[str, str] = {}
    for part in str(cookie_str or "").split(";"):
        part = part.strip()
        if "=" in part:
            k, _, v = part.partition("=")
            cookies[k.strip()] = v.strip().strip('"').strip("'")
    return cookies


def session_configured() -> bool:
    """True when a Steam session (sessionid + steamLoginSecure) is set."""
    cfg = _steam_config()
    return bool(cfg["sessionid"]) and bool(cfg["steam_login_secure"])


def _build_cookies(cfg: dict) -> dict:
    cookies = {"sessionid": cfg["sessionid"], "steamLoginSecure": cfg["steam_login_secure"]}
    cookies.update(_parse_cookie_string(cfg["extra_cookies"]))
    return cookies


def _normalize_key(key: str) -> str:
    return str(key or "").strip().upper()


# Steam purchase-result codes returned in `purchase_result_details`.
_PURCHASE_RESULT_MESSAGES = {
    9: "Invalid product code",
    13: "Something went wrong while activating this product",
    15: "This product code has already been activated by another account",
    29: "There have been too many activation attempts. Please wait and try again later",
    42: "Your account is restricted from using this product",
    45: "This product code has already been redeemed on this account",
}


def _result_message(data: dict) -> str:
    """Resolve the human-readable failure message from a Steam response."""
    raw = data.get("purchase_result_details") or data.get("message") or ""
    message = str(raw).strip()
    if not message:
        return ""
    if message.isdigit():
        return _PURCHASE_RESULT_MESSAGES.get(int(message), f"Steam error {message}")
    return message


async def redeem_steam_key(
    key: str,
    on_status: Callable[[str], None] | None = None,
) -> dict:
    """Attempt to redeem one Steam product key.

    Returns a dict:
        {"ok": bool, "key": str, "message": str, "action": str}
    where action is one of "redeemed", "duplicate", "invalid",
    "rate_limited", "needs_login", "error".
    """
    cfg = _steam_config()
    key = _normalize_key(key)

    if not session_configured():
        return {
            "ok": False,
            "key": key,
            "message": "Steam session not configured (steam_redeem in config.json)",
            "action": "needs_login",
        }

    cookies = _build_cookies(cfg)
    if on_status:
        on_status(f"Redeeming {key}...")

    try:
        async with httpx.AsyncClient(timeout=30, headers=_HEADERS, cookies=cookies) as client:
            resp = await client.post(
                ACTIVATE_URL,
                data={"product_key": key, "sessionid": cfg["sessionid"]},
            )
    except httpx.HTTPError as e:
        log_error(f"[Steam] redeem request failed for {key}: {e}")
        return {"ok": False, "key": key, "message": str(e), "action": "error"}

    text = resp.text or ""
    try:
        data = resp.json()
    except ValueError:
        data = None

    # Session gone -> Steam redirects to login (HTML, not JSON).
    if data is None:
        if "login" in text.lower() or resp.status_code in (301, 302, 303):
            log_warning("[Steam] session expired — re-login needed")
            return {
                "ok": False,
                "key": key,
                "message": "Steam session expired — please re-login",
                "action": "needs_login",
            }
        return {
            "ok": False,
            "key": key,
            "message": f"Unexpected response ({resp.status_code})",
            "action": "error",
        }

    success = data.get("success")
    message = _result_message(data)
    log_info(f"[Steam] {key} -> success={success} {message[:120]}")

    if success == 1:
        receipt = data.get("purchase_receipt_info") or {}
        games = []
        for item in (receipt.get("line_items") or [])[:3]:
            if item.get("line_item_description"):
                games.append(item["line_item_description"])
        detail = "Redeemed" + (f": {', '.join(games)}" if games else "")
        return {
            "ok": True,
            "key": key,
            "message": detail,
            "action": "redeemed",
        }

    low = message.lower()
    if "already" in low or "duplicate" in low:
        return {"ok": False, "key": key, "message": message, "action": "duplicate"}
    if "too many" in low or "rate" in low or "pending" in low:
        return {"ok": False, "key": key, "message": message, "action": "rate_limited"}
    if "log in" in low or "login" in low or "sign in" in low:
        return {"ok": False, "key": key, "message": message, "action": "needs_login"}
    if "invalid" in low or "not valid" in low or "restricted" in low:
        return {"ok": False, "key": key, "message": message, "action": "invalid"}
    return {
        "ok": False,
        "key": key,
        "message": message or "Invalid or unusable product code",
        "action": "invalid",
    }


def extract_steam_keys(text: str) -> list[str]:
    """Pull unique Steam keys from arbitrary text (discord message etc.)."""
    seen: list[str] = []
    for match in STEAM_KEY_RE.findall(str(text or "")):
        k = match.upper()
        if k not in seen:
            seen.append(k)
    return seen
