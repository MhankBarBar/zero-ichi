"""
AI Token tracker.

Tracks token usage per user and per chat with configurable daily limits.
"""

import json
from datetime import datetime

from core.constants import DATA_DIR
from core.logger import log_debug

TOKEN_FILE = DATA_DIR / "ai_tokens.json"


class TokenTracker:
    """Track AI token usage per user and per chat with daily limits."""

    def __init__(self):
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        """Load token data from disk."""
        try:
            if TOKEN_FILE.exists():
                self._data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        except Exception:
            self._data = {}

        today = datetime.now().strftime("%Y-%m-%d")
        if self._data.get("date") != today:
            self._data = {"date": today, "users": {}, "chats": {}}
            self._save()

    def _save(self) -> None:
        """Save token data to disk."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    @property
    def _user_limit(self) -> int:
        """Daily per-user token limit."""
        from core.runtime_config import runtime_config

        return runtime_config.get_nested("agentic_ai", "daily_token_limit_user", default=50_000)

    @property
    def _chat_limit(self) -> int:
        """Daily per-chat token limit."""
        from core.runtime_config import runtime_config

        return runtime_config.get_nested("agentic_ai", "daily_token_limit_chat", default=200_000)

    def _ensure_today(self) -> None:
        """Reset counters if it's a new day."""
        today = datetime.now().strftime("%Y-%m-%d")
        if self._data.get("date") != today:
            self._data = {"date": today, "users": {}, "chats": {}}

    def can_use(self, user_id: str, chat_id: str, estimated_tokens: int = 1000) -> bool:
        """Check if a user/chat can use more tokens."""
        self._ensure_today()

        user_used = self._data.get("users", {}).get(user_id, 0)
        chat_used = self._data.get("chats", {}).get(chat_id, 0)

        if user_used + estimated_tokens > self._user_limit:
            log_debug(f"Token limit: user {user_id} at {user_used}/{self._user_limit}")
            return False

        if chat_used + estimated_tokens > self._chat_limit:
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

        self._save()
        log_debug(
            f"Token usage: user={user_id} +{tokens_used} "
            f"(total: {self._data['users'][user_id]}), "
            f"chat={chat_id} (total: {self._data['chats'][chat_id]})"
        )

    def get_usage(self, user_id: str) -> dict:
        """Get usage info for a user."""
        self._ensure_today()
        used = self._data.get("users", {}).get(user_id, 0)
        return {
            "used": used,
            "limit": self._user_limit,
            "remaining": max(0, self._user_limit - used),
        }


token_tracker = TokenTracker()
