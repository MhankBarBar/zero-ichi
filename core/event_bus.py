"""
Event bus for real-time dashboard updates.

Simple pub/sub pattern using asyncio queues for WebSocket broadcasting.
"""

import asyncio
from datetime import datetime
from typing import Any


class EventBus:
    """In-memory event bus for broadcasting events to WebSocket clients."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        """Subscribe to events. Returns a queue that receives events."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unsubscribe from events."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def emit(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """Emit an event to all subscribers."""
        event = {
            "type": event_type,
            "data": data or {},
            "timestamp": datetime.now().isoformat(),
        }

        dead_queues = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead_queues.append(queue)

        for q in dead_queues:
            self._subscribers.remove(q)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


event_bus = EventBus()
