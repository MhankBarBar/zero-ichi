"""AI Token tracker.

Tracks token usage per user and per chat with configurable daily limits.
"""

from __future__ import annotations

import time
from datetime import datetime

from core.db import kv_get_json, kv_set_json
from core.logger import log_debug
from core.runtime_config import runtime_config

SAVE_INTERVAL_SECONDS = 2.0


class TokenTracker:
    """Track AI token usage per user and per chat with daily limits."""

    def __init__(self):
        self._scope = "ai_tokens"
        self._key = "daily"
        self._data: dict = {}
        self._dirty = False
        self._last_save_ts = 0.0
        self._load()

    def _load(self) -> None:
        """Load token data from database."""
        data = kv_get_json(self._scope, self._key, default={})
        self._data = data if isinstance(data, dict) else {}

        today = datetime.now().strftime("%Y-%m-%d")
        if self._data.get("date") != today:
            self._data = {"date": today, "users": {}, "chats": {}}
            self._schedule_save(force=True)

    def _save(self) -> None:
        """Persist token data to database."""
        kv_set_json(self._scope, self._key, self._data)
        self._dirty = False
        self._last_save_ts = time.time()

    def _schedule_save(self, force: bool = False) -> None:
        """Persist token usage on interval to reduce write volume."""
        self._dirty = True
        now = time.time()
        if force or now - self._last_save_ts >= SAVE_INTERVAL_SECONDS:
            self._save()

    def flush(self) -> None:
        """Flush pending token usage writes."""
        if self._dirty:
            self._save()

    @property
    def _user_limit(self) -> int:
        """Daily per-user token limit."""
        return runtime_config.get_nested("agentic_ai", "daily_token_limit_user", default=50_000)

    @property
    def _chat_limit(self) -> int:
        """Daily per-chat token limit."""
        return runtime_config.get_nested("agentic_ai", "daily_token_limit_chat", default=200_000)

    def _ensure_today(self) -> None:
        """Reset counters if it's a new day."""
        today = datetime.now().strftime("%Y-%m-%d")
        if self._data.get("date") != today:
            self._data = {"date": today, "users": {}, "chats": {}}
            self._schedule_save(force=True)

    def can_use(self, user_id: str, chat_id: str, estimated_tokens: int = 1000) -> bool:
        """Check if a user/chat can use more tokens."""
        self._ensure_today()

        user_used = self._data.get("users", {}).get(user_id, 0)
        chat_used = self._data.get("chats", {}).get(chat_id, 0)

        if self._user_limit > 0 and user_used + estimated_tokens > self._user_limit:
            log_debug(f"Token limit: user {user_id} at {user_used}/{self._user_limit}")
            return False

        if self._chat_limit > 0 and chat_used + estimated_tokens > self._chat_limit:
            log_debug(f"Token limit: chat {chat_id} at {chat_used}/{self._chat_limit}")
            return False

        return True

    def record(self, user_id: str, chat_id: str, tokens_used: int) -> None:
        """Record token usage for a user and chat."""
        self._ensure_today()

        if "users" not in self._data:
            self._data["users"] = {}
        if "chats" not in self._data:
            self._data["chats"] = {}

        self._data["users"][user_id] = self._data["users"].get(user_id, 0) + tokens_used
        self._data["chats"][chat_id] = self._data["chats"].get(chat_id, 0) + tokens_used

        self._schedule_save()
        log_debug(
            f"Token usage: user={user_id} +{tokens_used} "
            f"(total: {self._data['users'][user_id]}), "
            f"chat={chat_id} (total: {self._data['chats'][chat_id]})"
        )

    def get_usage(self, user_id: str) -> dict:
        """Get usage info for a user."""
        self._ensure_today()
        used = self._data.get("users", {}).get(user_id, 0)
        limit = self._user_limit
        remaining = max(0, limit - used) if limit > 0 else 0
        return {
            "used": used,
            "limit": limit,
            "remaining": remaining,
        }


token_tracker = TokenTracker()
