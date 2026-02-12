"""
Pending store for download selections.

Stores pending download info keyed by the bot's reply message ID.
Auto-expires entries after a configurable TTL.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.downloader import MediaInfo


@dataclass
class PendingDownload:
    """A pending download awaiting user's format selection."""

    url: str
    info: MediaInfo
    sender_jid: str
    chat_jid: str
    created_at: float = field(default_factory=time.time)


class PendingStore:
    """In-memory store for pending download selections."""

    TTL = 300

    def __init__(self) -> None:
        self._store: dict[str, PendingDownload] = {}

    def add(self, message_id: str, pending: PendingDownload) -> None:
        """Store a pending download keyed by message ID."""
        self._cleanup()
        self._store[message_id] = pending

    def get(self, message_id: str) -> PendingDownload | None:
        """Retrieve and validate a pending download by message ID."""
        self._cleanup()
        return self._store.get(message_id)

    def remove(self, message_id: str) -> None:
        """Remove a pending download."""
        self._store.pop(message_id, None)

    def _cleanup(self) -> None:
        """Remove expired entries."""
        now = time.time()
        expired = [k for k, v in self._store.items() if now - v.created_at > self.TTL]
        for k in expired:
            del self._store[k]


pending_downloads = PendingStore()
