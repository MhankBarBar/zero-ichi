"""
AI Memory module - Persistent conversation memory for AI agent.

Stores conversation history per chat with rich message context.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from core.logger import log_debug, log_error

MEMORY_DIR = Path("data/ai_memory")
MAX_MESSAGES = 100


@dataclass
class MemoryEntry:
    """A single memory entry with rich context."""

    role: Literal["user", "assistant"]
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    sender_name: str | None = None
    message_type: str = "text"
    is_reply: bool = False
    reply_to: str | None = None


class AIMemory:
    """Persistent memory manager for a single chat."""

    def __init__(self, chat_id: str):
        self.chat_id = chat_id
        self._safe_id = chat_id.replace("@", "_").replace(":", "_")
        self._entries: list[MemoryEntry] = []
        self._load()

    @property
    def _file_path(self) -> Path:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        return MEMORY_DIR / f"{self._safe_id}.json"

    def _load(self) -> None:
        """Load memory from disk."""
        try:
            if self._file_path.exists():
                data = json.loads(self._file_path.read_text(encoding="utf-8"))
                self._entries = [MemoryEntry(**entry) for entry in data]
                log_debug(f"Loaded {len(self._entries)} memory entries for {self.chat_id}")
        except Exception as e:
            log_error(f"Failed to load memory for {self.chat_id}: {e}")
            self._entries = []

    def _save(self) -> None:
        """Save memory to disk."""
        try:
            data = [asdict(entry) for entry in self._entries]
            self._file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            log_error(f"Failed to save memory for {self.chat_id}: {e}")

    def add(
        self,
        role: Literal["user", "assistant"],
        content: str,
        sender_name: str | None = None,
        message_type: str = "text",
        is_reply: bool = False,
        reply_to: str | None = None,
    ) -> None:
        """Add a new entry to memory."""
        if not content or not content.strip():
            return

        entry = MemoryEntry(
            role=role,
            content=content.strip(),
            sender_name=sender_name,
            message_type=message_type,
            is_reply=is_reply,
            reply_to=reply_to,
        )
        self._entries.append(entry)

        if len(self._entries) > MAX_MESSAGES * 2:
            self._entries = self._entries[-MAX_MESSAGES * 2 :]

        self._save()

    def get_history(self, limit: int = MAX_MESSAGES) -> list[MemoryEntry]:
        """Get recent conversation history."""
        return self._entries[-limit:]

    def get_context_string(self, limit: int = MAX_MESSAGES) -> str:
        """Build a context string for the AI prompt."""
        history = self.get_history(limit)
        if not history:
            return ""

        lines = ["Recent conversation:"]
        for entry in history:
            prefix = f"[{entry.sender_name}]" if entry.sender_name else f"[{entry.role}]"
            type_info = f" ({entry.message_type})" if entry.message_type != "text" else ""
            reply_info = f" (replying to: {entry.reply_to[:50]}...)" if entry.reply_to else ""

            content_preview = entry.content[:150]
            if len(entry.content) > 150:
                content_preview += "..."

            lines.append(f"- {prefix}{type_info}{reply_info}: {content_preview}")

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all memory for this chat."""
        self._entries = []
        if self._file_path.exists():
            self._file_path.unlink()


_memory_cache: dict[str, AIMemory] = {}


def get_memory(chat_id: str) -> AIMemory:
    """Get or create memory for a chat."""
    if chat_id not in _memory_cache:
        _memory_cache[chat_id] = AIMemory(chat_id)
    return _memory_cache[chat_id]


def clear_memory(chat_id: str | None = None) -> None:
    """Clear memory for a chat or all chats."""
    global _memory_cache
    if chat_id:
        if chat_id in _memory_cache:
            _memory_cache[chat_id].clear()
            del _memory_cache[chat_id]
    else:
        for mem in _memory_cache.values():
            mem.clear()
        _memory_cache.clear()
