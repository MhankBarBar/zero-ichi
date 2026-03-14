"""
AI Token tracker.

Tracks token usage per user and per chat with configurable daily limits.
"""

import json
import os
import tempfile
import time
from atexit import register as on_exit
from datetime import datetime

from core.constants import DATA_DIR
from core.logger import log_debug
from core.runtime_config import runtime_config

TOKEN_FILE = DATA_DIR / "ai_tokens.json"
SAVE_INTERVAL_SECONDS = 2.0


def _atomic_write_json(file_path, data: dict) -> None:
    """Atomically write JSON payload to disk."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=file_path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, file_path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


class TokenTracker:
    """Track AI token usage per user and per chat with daily limits."""

    def __init__(self):
        self._data: dict = {}
        self._dirty = False
        self._last_save_ts = 0.0
        self._load()
        on_exit(self.flush)

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
            self._schedule_save(force=True)

    def _save(self) -> None:
        """Save token data to disk."""
        _atomic_write_json(TOKEN_FILE, self._data)
        self._dirty = False
        self._last_save_ts = time.time()

    def _schedule_save(self, force: bool = False) -> None:
        """Persist token usage on interval to reduce disk writes."""
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
        return {
            "used": used,
            "limit": self._user_limit,
            "remaining": max(0, self._user_limit - used),
        }


token_tracker = TokenTracker()
