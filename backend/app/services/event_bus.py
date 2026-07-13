"""In-process publish/subscribe event bus.

Decouples data producers (FRM poller, workers, services) from consumers (the
WebSocket layer, analytics). Producers ``publish`` to a topic; consumers hold a
:class:`Subscription` whose queue receives every event for the topics it
subscribed to.

Topics are hierarchical dotted strings (``power.grid``, ``factory.status``) and
subscriptions support trailing wildcards (``power.*`` or ``*`` for everything).

Slow consumers never block producers: queues are bounded and the oldest event is
dropped (and counted) on overflow — correct behavior for live telemetry, where
the newest state always supersedes the old.
"""

from __future__ import annotations

import asyncio
import fnmatch
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_QUEUE_SIZE = 256


@dataclass(frozen=True)
class Event:
    """A single event published on the bus."""

    topic: str
    payload: Any
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class Subscription:
    """A consumer's handle on the bus; iterate or ``get()`` to receive events."""

    def __init__(self, patterns: tuple[str, ...], queue_size: int) -> None:
        self.patterns = patterns
        self.queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=queue_size)
        self.dropped = 0

    def matches(self, topic: str) -> bool:
        """Return True if *topic* matches any subscribed pattern."""
        return any(fnmatch.fnmatchcase(topic, pattern) for pattern in self.patterns)

    def _offer(self, event: Event) -> None:
        """Enqueue *event*, dropping the oldest one if the queue is full."""
        while True:
            try:
                self.queue.put_nowait(event)
                return
            except asyncio.QueueFull:
                try:
                    self.queue.get_nowait()
                    self.dropped += 1
                except asyncio.QueueEmpty:  # pragma: no cover - race guard
                    pass

    async def get(self) -> Event:
        """Wait for and return the next event."""
        return await self.queue.get()


class EventBus:
    """Topic-based pub/sub hub shared across the application."""

    def __init__(self) -> None:
        self._subscriptions: set[Subscription] = set()

    def subscribe(
        self, *patterns: str, queue_size: int = DEFAULT_QUEUE_SIZE
    ) -> Subscription:
        """Register a subscription for one or more topic patterns."""
        subscription = Subscription(patterns or ("*",), queue_size)
        self._subscriptions.add(subscription)
        return subscription

    def unsubscribe(self, subscription: Subscription) -> None:
        """Remove *subscription*; safe to call twice."""
        self._subscriptions.discard(subscription)

    def publish(self, topic: str, payload: Any) -> Event:
        """Publish *payload* on *topic* to all matching subscribers."""
        event = Event(topic=topic, payload=payload)
        for subscription in self._subscriptions:
            if subscription.matches(topic):
                subscription._offer(event)
        return event

    @property
    def subscriber_count(self) -> int:
        """Number of active subscriptions (used by health/metrics)."""
        return len(self._subscriptions)
