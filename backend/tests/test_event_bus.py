"""Tests for the in-process event bus."""

from __future__ import annotations

import asyncio

from app.services.event_bus import EventBus


async def test_subscriber_receives_matching_topic() -> None:
    bus = EventBus()
    sub = bus.subscribe("power.*")

    bus.publish("power.grid", {"capacity": 100})
    bus.publish("factory.status", {"idle": 2})  # should not match

    event = await asyncio.wait_for(sub.get(), timeout=1)
    assert event.topic == "power.grid"
    assert event.payload == {"capacity": 100}
    assert sub.queue.empty()


async def test_wildcard_receives_everything() -> None:
    bus = EventBus()
    sub = bus.subscribe()  # defaults to "*"

    bus.publish("a", 1)
    bus.publish("b.c", 2)

    assert (await sub.get()).payload == 1
    assert (await sub.get()).payload == 2


async def test_unsubscribe_stops_delivery() -> None:
    bus = EventBus()
    sub = bus.subscribe("*")
    bus.unsubscribe(sub)

    bus.publish("a", 1)
    assert sub.queue.empty()
    assert bus.subscriber_count == 0


async def test_slow_consumer_drops_oldest() -> None:
    bus = EventBus()
    sub = bus.subscribe("*", queue_size=2)

    for i in range(5):
        bus.publish("t", i)

    assert sub.dropped == 3
    assert (await sub.get()).payload == 3
    assert (await sub.get()).payload == 4
