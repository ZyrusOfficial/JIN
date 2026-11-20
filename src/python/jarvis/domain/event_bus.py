"""Event bus — the central pub/sub backbone for all JARVIS events.

Every input becomes a normalized event on this bus. Subscribers (proactive
engine, voice pipeline, UI shell) react to events without knowing their source.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from jarvis.domain.events import Event, EventEnvelope

EventHandler = Callable[[Event], None]


@dataclass
class EventBus:
    """In-process event bus with typed subscriptions.

    Subscribers register handlers for specific event types (or "*" for all).
    Publishing is synchronous and blocking — handlers must be fast or
    dispatch to their own queues.
    """

    _handlers: dict[str, list[EventHandler]] = field(default_factory=lambda: defaultdict(list))
    _published: list[Event] = field(default_factory=list)
    _counter: int = 0

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register a handler for events of type `event_type` (or "*" for all)."""
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Register a handler that receives every published event."""
        self.subscribe("*", handler)

    def publish(self, envelope: EventEnvelope) -> Event:
        """Publish an envelope as an event, notifying all subscribers."""
        self._counter += 1
        event = Event(
            envelope=envelope,
            received_at=datetime.now(UTC),
            bus_id=f"evt_bus_{self._counter}",
        )
        self._published.append(event)

        # Notify specific-type handlers
        for handler in self._handlers.get(envelope.type, []):
            handler(event)

        # Notify wildcard handlers
        for handler in self._handlers.get("*", []):
            handler(event)

        return event

    def published(self) -> list[Event]:
        """Return all events published so far (for test inspection)."""
        return list(self._published)

    def clear(self) -> None:
        """Clear published history (for test isolation)."""
        self._published.clear()
        self._counter = 0
