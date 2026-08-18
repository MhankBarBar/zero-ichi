"""Discord link monitor -> WhatsApp forwarder via Zero Ichi API.

Use this when you only want one Discord token (listener) and want Zero Ichi
to deliver detected links and Steam product keys to WhatsApp.

Required env vars:
    LISTENER_TOKEN
    SOURCE_CHANNEL_URL
    WA_TARGET_JID
    DASHBOARD_USERNAME
    DASHBOARD_PASSWORD

Optional env vars:
    ZEROICHI_API_URL (default: http://localhost:8000)
    POLL_BASE_INTERVAL (default: 3)
    POLL_MAX_INTERVAL (default: 30)
    DISCORD_FETCH_LIMIT (default: 15)
"""

from __future__ import annotations

import asyncio
import base64
import os
import re
import time
from datetime import datetime

import httpx
from dotenv import load_dotenv

load_dotenv()


class Colors:
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"


def log(message: str, color: str = Colors.BLUE) -> None:
    print(f"{color}{message}{Colors.END}")


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _extract_channel_id(channel_url: str) -> str:
    parts = [p for p in channel_url.strip().split("/") if p]
    if not parts:
        raise ValueError("Invalid SOURCE_CHANNEL_URL")
    candidate = parts[-1]
    if not candidate.isdigit():
        raise ValueError("Could not parse channel id from SOURCE_CHANNEL_URL")
    return candidate


class DiscordListener:
    def __init__(self, token: str) -> None:
        self.base_url = "https://canary.discordapp.com/api/v9"
        auth = token.strip().replace('"', "").replace("'", "")
        if auth.startswith("yM"):
            auth = auth[1:]

        self.client = httpx.Client(
            timeout=10,
            headers={
                "Authorization": auth,
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0",
            },
        )

    def _request(self, method: str, endpoint: str, params: dict | None = None):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        while True:
            try:
                r = self.client.request(method, url, params=params)
                if r.status_code == 429:
                    retry = float(r.json().get("retry_after", 1))
                    log(f"[LISTENER] Rate limited. Waiting {retry:.2f}s...", Colors.YELLOW)
                    time.sleep(max(0.5, retry))
                    continue
                return r
            except httpx.RequestError as exc:
                log(f"[LISTENER] Network error: {exc}", Colors.RED)
                time.sleep(5)

    def validate_token(self):
        r = self._request("GET", "users/@me")
        if r.status_code != 200:
            return False
        data = r.json()
        log(f"[LISTENER] Logged in as: {data.get('username')}#{data.get('discriminator')}", Colors.GREEN)
        return True

    def fetch_messages(self, channel_id, limit, after=None):
        params = {"limit": limit}
        if after:
            params["after"] = after
        r = self._request("GET", f"channels/{channel_id}/messages", params=params)
        if r.status_code == 403:
            raise PermissionError("Discord listener token cannot access source channel")
        if r.status_code != 200:
            raise RuntimeError(f"Discord fetch failed: {r.status_code}")
        return r.json()


class ZeroIchiForwarder:
    def __init__(self, api_base, username, password, target_jid):
        auth = base64.b64encode(f"{username}:{password}".encode()).decode()
        self.api_base = api_base.rstrip("/")
        self.target_jid = target_jid
        self.client = httpx.Client(
            timeout=10,
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/json",
            },
        )

    def healthcheck(self):
        r = self.client.get(f"{self.api_base}/api/status")
        if r.status_code != 200:
            raise RuntimeError(r.text)

    def send_message(self, text):
        for chunk in [text[i:i+3500] for i in range(0, len(text), 3500)] or [text]:
            r = self.client.post(
                f"{self.api_base}/api/send-message",
                json={"to": self.target_jid, "text": chunk},
            )
            if r.status_code != 200:
                raise RuntimeError(r.text)


def run():
    listener = DiscordListener(_required_env("LISTENER_TOKEN"))
    if not listener.validate_token():
        return

    forwarder = ZeroIchiForwarder(
        os.getenv("ZEROICHI_API_URL", "http://localhost:8000"),
        _required_env("DASHBOARD_USERNAME"),
        _required_env("DASHBOARD_PASSWORD"),
        _required_env("WA_TARGET_JID"),
    )
    forwarder.healthcheck()

    channel_id = _extract_channel_id(_required_env("SOURCE_CHANNEL_URL"))
    base_interval = max(1, int(os.getenv("POLL_BASE_INTERVAL", "3")))
    max_interval = max(base_interval, int(os.getenv("POLL_MAX_INTERVAL", "30")))
    fetch_limit = max(1, min(100, int(os.getenv("DISCORD_FETCH_LIMIT", "15"))))

    url_pattern = re.compile(r"(https?://[^\s]+)")
    steam_key_pattern = re.compile(r"\b(?:[A-Z0-9]{5}-){2,4}[A-Z0-9]{5}\b", re.IGNORECASE)

    baseline = listener.fetch_messages(channel_id, 1)
    last_id = baseline[0]["id"] if baseline else None
    current_interval = base_interval

    while True:
        try:
            messages = listener.fetch_messages(channel_id, fetch_limit, last_id)
            if not messages:
                current_interval = min(current_interval + 2, max_interval)
                time.sleep(current_interval)
                continue

            current_interval = base_interval
            forward_lines = []
            steam_forward = []

            for msg in messages:
                content = str(msg.get("content", ""))
                author = msg.get("author", {}).get("username", "unknown")

                links = url_pattern.findall(content)
                steam_keys = steam_key_pattern.findall(content)

                if links or steam_keys:
                    now = datetime.now().strftime("%H:%M:%S")
                    log(f"[{now}] Match detected from {author}", Colors.GREEN)

                    text = [f"**From {author}**","", "Original Message:", content]

                    if steam_keys:
                        text.extend([
                            "",
                            "Redeem:",
                            "https://store.steampowered.com/account/registerkey",
                        ])
                        steam_forward.extend(steam_keys)

                    forward_lines.append("\n".join(text))

                last_id = str(msg.get("id", last_id))

            if forward_lines:
                forwarder.send_message("\n\n".join(forward_lines))

            if steam_forward:
                steam_forward = list(dict.fromkeys(steam_forward))

                # Auto-redeem when a Steam session is configured, so we don't
                # lose the race in giveaways. Results are sent to WhatsApp.
                from core.steam_redeemer import redeem_steam_key, session_configured

                if session_configured():
                    redeem_lines = []
                    for key in steam_forward:
                        try:
                            res = asyncio.run(redeem_steam_key(key))
                        except Exception as e:
                            res = {"ok": False, "key": key, "message": str(e), "action": "error"}
                        icon = "✅" if res["ok"] else "❌"
                        log(
                            f"[REDEEM] {icon} {key} -> {res['action']}: {res['message'][:90]}",
                            Colors.GREEN if res["ok"] else Colors.YELLOW,
                        )
                        redeem_lines.append(f"{icon} *{res['key']}* — {res['message']}")
                    forwarder.send_message("\n".join(redeem_lines))
                else:
                    forwarder.send_message("\n".join(steam_forward))

            time.sleep(current_interval)

        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f"Runtime error: {e}", Colors.RED)
            time.sleep(base_interval)


if __name__ == "__main__":
    run()

