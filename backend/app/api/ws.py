"""WebSocket endpoint bridging the internal event bus to clients.

Protocol (JSON messages):

Client → server::

    {"action": "subscribe", "topics": ["power.*", "factory.status"]}
    {"action": "unsubscribe"}
    {"action": "ping"}

Server → client::

    {"topic": "power.grid", "timestamp": "…", "payload": {…}}   # bus events
    {"topic": "_system", "timestamp": "…", "payload": {…}}      # acks / pong

Clients start with no subscriptions; they must subscribe explicitly. A new
``subscribe`` replaces the previous topic set.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.event_bus import EventBus, Subscription

logger = logging.getLogger(__name__)

router = APIRouter()


def _envelope(topic: str, payload: Any) -> str:
    return json.dumps(
        {
            "topic": topic,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        },
        default=str,
    )


async def _forward_events(websocket: WebSocket, subscription: Subscription) -> None:
    """Pump bus events for *subscription* to the client until cancelled."""
    while True:
        event = await subscription.get()
        await websocket.send_text(_envelope(event.topic, event.payload))


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Accept a client and serve the subscribe/ping protocol described above."""
    bus: EventBus = websocket.app.state.event_bus
    await websocket.accept()

    subscription: Subscription | None = None
    forwarder: asyncio.Task[None] | None = None

    async def replace_subscription(topics: list[str]) -> None:
        nonlocal subscription, forwarder
        if forwarder is not None:
            forwarder.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await forwarder
            forwarder = None
        if subscription is not None:
            bus.unsubscribe(subscription)
            subscription = None
        if topics:
            subscription = bus.subscribe(*topics)
            forwarder = asyncio.create_task(_forward_events(websocket, subscription))

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
                action = message.get("action")
            except (json.JSONDecodeError, AttributeError):
                await websocket.send_text(
                    _envelope("_system", {"error": "invalid_message", "received": raw[:200]})
                )
                continue

            if action == "subscribe":
                topics = [t for t in message.get("topics", []) if isinstance(t, str)]
                await replace_subscription(topics)
                await websocket.send_text(_envelope("_system", {"subscribed": topics}))
            elif action == "unsubscribe":
                await replace_subscription([])
                await websocket.send_text(_envelope("_system", {"subscribed": []}))
            elif action == "ping":
                await websocket.send_text(_envelope("_system", {"pong": True}))
            else:
                await websocket.send_text(
                    _envelope("_system", {"error": "unknown_action", "action": action})
                )
    except WebSocketDisconnect:
        pass
    finally:
        if forwarder is not None:
            forwarder.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await forwarder
        if subscription is not None:
            bus.unsubscribe(subscription)
