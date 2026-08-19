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
from pathlib import Path
from typing import Callable

import httpx

from core.logger import log_error, log_info, log_warning

ACTIVATE_URL = "https://store.steampowered.com/account/ajaxregisterkey"
REGISTER_URL = "https://store.steampowered.com/account/registerkey"


class SteamError(Exception):
    """Raised when Steam login/redeem cannot complete."""

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
        "username": os.getenv("STEAM_USERNAME", "") or cfg.get("username", "") or "",
        "password": os.getenv("STEAM_PASSWORD", "") or cfg.get("password", "") or "",
        "shared_secret": os.getenv("STEAM_SHARED_SECRET", "")
        or cfg.get("shared_secret", "")
        or "",
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
    """True when a Steam session source is configured (cookies OR auto-login)."""
    cfg = _steam_config()
    if cfg["username"] and cfg["password"] and cfg["shared_secret"]:
        return True
    return bool(cfg["sessionid"]) and bool(cfg["steam_login_secure"])


def _normalize_key(key: str) -> str:
    return str(key or "").strip().upper()


# --------------------------------------------------------------------------- #
# Auto-login (steamguard) — no browser cookie exports needed                   #
# --------------------------------------------------------------------------- #
_SESSION_CACHE: dict | None = None
_SESSION_CACHE_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "steam_session.json"


def _totp_code(shared_secret: str, steam_time: int) -> str:
    """Steam-style TOTP code (8 digits) from the account's shared_secret."""
    import base64
    import hashlib
    import hmac
    import struct

    key = base64.b64decode(shared_secret)
    msg = struct.pack(">Q", int(steam_time // 30))
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[19] & 0x0F
    code = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % 100000000
    return f"{code:08d}"


def _login_via_steamguard(cfg: dict) -> dict:
    """Full Steam web login: RSA password → auth session → 2FA → cookies."""
    import base64

    import rsa
    from steamguard.steam_api_web import (
        beginAuthSessionViaCredentials,
        finalizelogin,
        getPasswordRSAPublicKey,
        updateAuthSessionWithSteamGuardCode,
    )
    from steamguard.steam_session import SteamSession

    ss = SteamSession(cfg["username"], cfg["password"])
    ss.align_time()

    public_key, timestamp = getPasswordRSAPublicKey(ss.session, cfg["username"])
    encrypted = base64.b64encode(rsa.encrypt(cfg["password"].encode(), public_key)).decode()

    auth = beginAuthSessionViaCredentials(ss.session, cfg["username"], encrypted, timestamp)
    client_id = auth.get("client_id")
    steamid = auth.get("steamid")
    if not client_id or not steamid:
        raise SteamError(f"Steam login failed: unexpected auth response {str(auth)[:150]}")

    # If Steam asks for email confirmations instead of the 2FA app, surface it.
    confirmations = auth.get("allowed_confirmations") or []
    if auth.get("requires_twofactor") is not True and confirmations:
        types = [c.get("confirmation_type") for c in confirmations]
        raise SteamError(f"Steam login blocked: email guard required (confirmation types {types})")

    code = _totp_code(cfg["shared_secret"], ss.get_steam_time())
    upd = updateAuthSessionWithSteamGuardCode(ss.session, client_id, steamid, code)
    if upd.status_code != 200:
        raise SteamError(f"Steam 2FA rejected ({upd.status_code}): {upd.text[:150]}")

    try:
        refresh_token = upd.json()["response"]["refresh_token"]
    except (KeyError, ValueError) as e:
        raise SteamError(f"Steam 2FA response missing refresh_token: {upd.text[:150]}") from e

    finalizelogin(ss.session, refresh_token)

    cookies = {c.name: c.value for c in ss.session.cookies}
    sessionid = cookies.get("sessionid", "")
    steam_login_secure = cookies.get("steamLoginSecure", "")
    if not sessionid or not steam_login_secure:
        raise SteamError("Steam login completed but session cookies missing")

    # Persist the login so we don't need to re-login every redeem.
    payload = {
        "sessionid": sessionid,
        "steam_login_secure": steam_login_secure,
        "cookies": {k: v for k, v in cookies.items() if k not in ("sessionid", "steamLoginSecure")},
    }
    try:
        _SESSION_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SESSION_CACHE_FILE.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass
    return payload


def _get_session() -> dict:
    """Return session cookies: cached auto-login > static config cookies."""
    global _SESSION_CACHE
    if _SESSION_CACHE is not None:
        return _SESSION_CACHE

    cfg = _steam_config()
    if cfg["username"] and cfg["password"] and cfg["shared_secret"]:
        try:
            if _SESSION_CACHE_FILE.exists():
                cached = json.loads(_SESSION_CACHE_FILE.read_text(encoding="utf-8"))
                if cached.get("sessionid") and cached.get("steam_login_secure"):
                    _SESSION_CACHE = cached
                    return cached
        except (OSError, ValueError):
            pass
        _SESSION_CACHE = _login_via_steamguard(cfg)
        return _SESSION_CACHE

    # Static cookie fallback.
    payload = {
        "sessionid": cfg["sessionid"],
        "steam_login_secure": cfg["steam_login_secure"],
        "cookies": _parse_cookie_string(cfg["extra_cookies"]),
    }
    _SESSION_CACHE = payload
    return payload


def _reset_session() -> None:
    """Drop the cached session (forces a fresh login next redeem)."""
    global _SESSION_CACHE
    _SESSION_CACHE = None
    try:
        _SESSION_CACHE_FILE.unlink(missing_ok=True)
    except OSError:
        pass


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
            "message": (
                "Steam session not configured — set steam_redeem cookies or "
                "username/password/shared_secret in config.json"
            ),
            "action": "needs_login",
        }

    if on_status:
        on_status(f"Redeeming {key}...")

    # Two attempts: first with the current session; if Steam says the session
    # is dead, drop it and (when auto-login is configured) log in fresh.
    for attempt in range(2):
        try:
            session = _get_session()
        except SteamError as e:
            return {"ok": False, "key": key, "message": str(e), "action": "needs_login"}

        cookies = {
            "sessionid": session["sessionid"],
            "steamLoginSecure": session["steam_login_secure"],
            **session.get("cookies", {}),
        }

        try:
            async with httpx.AsyncClient(timeout=30, headers=_HEADERS, cookies=cookies) as client:
                resp = await client.post(
                    ACTIVATE_URL,
                    data={"product_key": key, "sessionid": session["sessionid"]},
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
                log_warning("[Steam] session rejected — re-login needed")
                _reset_session()
                if attempt == 0 and cfg["username"] and cfg["password"] and cfg["shared_secret"]:
                    log_info("[Steam] retrying with a fresh login...")
                    continue
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
    return {"ok": False, "key": key, "message": "Steam login retry failed", "action": "needs_login"}


def extract_steam_keys(text: str) -> list[str]:
    """Pull unique Steam keys from arbitrary text (discord message etc.)."""
    seen: list[str] = []
    for match in STEAM_KEY_RE.findall(str(text or "")):
        k = match.upper()
        if k not in seen:
            seen.append(k)
    return seen
