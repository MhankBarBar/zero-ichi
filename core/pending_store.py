"""
Pending store for download, search, and playlist selections.

Stores pending download/search/playlist info keyed by the bot's reply message ID.
Auto-expires entries after a configurable TTL.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.downloader import MediaInfo, PlaylistEntry


@dataclass
class SearchResult:
    """A single search result entry."""

    title: str
    url: str
    duration: str
    uploader: str


@dataclass
class PendingSearch:
    """A pending search awaiting user's result selection."""

    query: str
    results: list[SearchResult]
    sender_jid: str
    chat_jid: str
    created_at: float = field(default_factory=time.time)


@dataclass
class PendingDownload:
    """A pending download awaiting user's format selection."""

    url: str
    info: MediaInfo
    sender_jid: str
    chat_jid: str
    created_at: float = field(default_factory=time.time)


@dataclass
class PendingPlaylist:
    """A pending playlist awaiting user's track selection."""

    title: str
    entries: list[PlaylistEntry]
    sender_jid: str
    chat_jid: str
    created_at: float = field(default_factory=time.time)


PendingItem = PendingDownload | PendingSearch | PendingPlaylist


class PendingStore:
    """In-memory store for pending selections with TTL."""

    TTL = 300

    def __init__(self) -> None:
        self._store: dict[str, PendingItem] = {}

    def add(self, message_id: str, pending: PendingItem) -> None:
        """Store a pending item keyed by message ID."""
        self._cleanup()
        self._store[message_id] = pending

    def get(self, message_id: str) -> PendingItem | None:
        """Retrieve and validate a pending item by message ID."""
        self._cleanup()
        return self._store.get(message_id)

    def remove(self, message_id: str) -> None:
        """Remove a pending item."""
        self._store.pop(message_id, None)

    def _cleanup(self) -> None:
        """Remove expired entries."""
        now = time.time()
        expired = [k for k, v in self._store.items() if now - v.created_at > self.TTL]
        for k in expired:
            del self._store[k]


pending_downloads = PendingStore()
