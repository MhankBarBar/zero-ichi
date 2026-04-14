"""
Pending store for download, search, and playlist selections.

Stores pending download/search/playlist info keyed by the bot's reply message ID.
Auto-expires entries after a configurable TTL.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING

from core.db import (
    create_pending_item,
    delete_expired_pending_items,
    delete_pending_item,
    get_pending_item,
    kv_get_scope_keys,
)

if TYPE_CHECKING:
    from core.applemusic import AppleMusicTrack
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


@dataclass
class PendingAppleMusic:
    """A pending Apple Music album awaiting user's track selection."""

    tracks: list[AppleMusicTrack]
    album_name: str
    sender_jid: str
    chat_jid: str
    created_at: float = field(default_factory=time.time)


PendingItem = PendingDownload | PendingSearch | PendingPlaylist | PendingAppleMusic


def _serialize_pending_item(pending: PendingItem) -> tuple[str, dict]:
    """Convert a pending dataclass item into a JSON-safe payload."""
    return type(pending).__name__, asdict(pending)


def _deserialize_pending_item(kind: str, payload: dict) -> PendingItem | None:
    """Reconstruct a pending dataclass item from persisted payload."""
    if kind == "PendingSearch":
        results = [SearchResult(**item) for item in payload.get("results", [])]
        return PendingSearch(
            query=str(payload.get("query", "")),
            results=results,
            sender_jid=str(payload.get("sender_jid", "")),
            chat_jid=str(payload.get("chat_jid", "")),
            created_at=float(payload.get("created_at", time.time())),
        )

    if kind == "PendingDownload":
        from core.downloader import FormatOption, MediaInfo

        info_payload = payload.get("info", {})
        formats = [FormatOption(**item) for item in info_payload.get("formats", [])]
        info = MediaInfo(
            title=str(info_payload.get("title", "")),
            duration=int(info_payload.get("duration", 0) or 0),
            uploader=str(info_payload.get("uploader", "")),
            platform=str(info_payload.get("platform", "")),
            url=str(info_payload.get("url", "")),
            thumbnail=str(info_payload.get("thumbnail", "")),
            filesize_approx=int(info_payload.get("filesize_approx", 0) or 0),
            is_playlist=bool(info_payload.get("is_playlist", False)),
            formats=formats,
        )
        return PendingDownload(
            url=str(payload.get("url", "")),
            info=info,
            sender_jid=str(payload.get("sender_jid", "")),
            chat_jid=str(payload.get("chat_jid", "")),
            created_at=float(payload.get("created_at", time.time())),
        )

    if kind == "PendingPlaylist":
        from core.downloader import PlaylistEntry

        entries = [PlaylistEntry(**item) for item in payload.get("entries", [])]
        return PendingPlaylist(
            title=str(payload.get("title", "")),
            entries=entries,
            sender_jid=str(payload.get("sender_jid", "")),
            chat_jid=str(payload.get("chat_jid", "")),
            created_at=float(payload.get("created_at", time.time())),
        )

    if kind == "PendingAppleMusic":
        from core.applemusic import AppleMusicTrack

        tracks = [AppleMusicTrack(**item) for item in payload.get("tracks", [])]
        return PendingAppleMusic(
            tracks=tracks,
            album_name=str(payload.get("album_name", "")),
            sender_jid=str(payload.get("sender_jid", "")),
            chat_jid=str(payload.get("chat_jid", "")),
            created_at=float(payload.get("created_at", time.time())),
        )

    return None


class PendingStore:
    """Persistent store for pending selections with TTL."""

    TTL = 300

    def __init__(self) -> None:
        self._default_ttl = self.TTL

    def add(self, message_id: str, pending: PendingItem) -> None:
        """Store a pending item keyed by message ID."""
        self._cleanup()
        kind, payload = _serialize_pending_item(pending)
        create_pending_item(
            message_id,
            kind=kind,
            payload=payload,
            expires_at=float(pending.created_at) + float(self.TTL),
            chat_jid=str(getattr(pending, "chat_jid", "")),
            sender_jid=str(getattr(pending, "sender_jid", "")),
        )

    def get(self, message_id: str) -> PendingItem | None:
        """Retrieve and validate a pending item by message ID."""
        self._cleanup()
        row = get_pending_item(message_id)
        if not isinstance(row, dict):
            return None
        try:
            expires_at = float(row.get("expires_at", 0.0))
        except (TypeError, ValueError):
            expires_at = 0.0
        if expires_at <= time.time():
            delete_pending_item(message_id)
            return None
        payload = row.get("payload", {})
        if not isinstance(payload, dict):
            return None
        return _deserialize_pending_item(str(row.get("kind", "")), payload)

    def remove(self, message_id: str) -> None:
        """Remove a pending item."""
        delete_pending_item(message_id)

    def clear_all_for_tests(self) -> None:
        """Clear pending items and restore default TTL for isolated tests."""
        for key in kv_get_scope_keys("pending_items"):
            delete_pending_item(key)
        self.TTL = self._default_ttl

    def cleanup_expired(self, now_ts: float | None = None) -> int:
        """Delete expired pending entries and return removed count."""
        effective_now = time.time() if now_ts is None else float(now_ts)
        return delete_expired_pending_items(effective_now)

    def _cleanup(self) -> None:
        """Remove expired entries."""
        self.cleanup_expired()


pending_downloads = PendingStore()
