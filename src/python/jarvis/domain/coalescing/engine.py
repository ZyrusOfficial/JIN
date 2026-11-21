"""Event coalescing engine — merges related events into single proactive items.

Prevents notification storms by grouping related messages from the same
thread or source into a single proactive item with a count.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class CoalescedEvent:
    """A group of coalesced events."""

    thread_id: str
    source: str
    contact: str
    count: int
    latest_text: str
    latest_timestamp: datetime
    event_ids: list[str] = field(default_factory=list)
    first_timestamp: datetime | None = None


class CoalescingEngine:
    """Coalesces related events to prevent notification storms.

    Events from the same thread within a time window are merged into a
    single proactive item with a count (e.g. "5 new messages in group chat").
    """

    def __init__(
        self,
        window_seconds: float = 300.0,
        max_coalesced: int = 50,
    ) -> None:
        self._window = timedelta(seconds=window_seconds)
        self._max_coalesced = max_coalesced
        self._groups: dict[str, CoalescedEvent] = {}

    def add_event(
        self,
        event_id: str,
        thread_id: str,
        source: str,
        contact: str,
        text: str,
        timestamp: datetime,
    ) -> CoalescedEvent | None:
        """Add an event to a coalescing group.

        Returns the coalesced group if it exists (may be new or updated),
        or None if the event should be handled individually (no coalescing).
        """
        now = timestamp
        key = f"{source}:{thread_id}"

        # Clean up expired groups
        expired = [k for k, g in self._groups.items() if now - g.latest_timestamp > self._window]
        for k in expired:
            del self._groups[k]

        existing = self._groups.get(key)
        if existing is None:
            # Start a new group
            group = CoalescedEvent(
                thread_id=thread_id,
                source=source,
                contact=contact,
                count=1,
                latest_text=text,
                latest_timestamp=now,
                event_ids=[event_id],
                first_timestamp=now,
            )
            self._groups[key] = group
            return group

        # Update existing group
        existing.count = min(existing.count + 1, self._max_coalesced)
        existing.latest_text = text
        existing.latest_timestamp = now
        existing.event_ids.append(event_id)
        return existing

    def get_group(self, thread_id: str, source: str) -> CoalescedEvent | None:
        """Get the coalesced group for a thread/source."""
        key = f"{source}:{thread_id}"
        return self._groups.get(key)

    def remove_group(self, thread_id: str, source: str) -> bool:
        """Remove a coalesced group (after it's been delivered)."""
        key = f"{source}:{thread_id}"
        return self._groups.pop(key, None) is not None

    def all_groups(self) -> list[CoalescedEvent]:
        """Return all current coalesced groups."""
        return list(self._groups.values())

    def clear(self) -> None:
        """Clear all groups."""
        self._groups.clear()
