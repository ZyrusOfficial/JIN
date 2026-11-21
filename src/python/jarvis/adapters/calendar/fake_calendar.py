"""Fake calendar provider — controllable events for tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jarvis.ports.calendar_provider import CalendarEvent, CalendarProvider


class FakeCalendarProvider(CalendarProvider):
    """Fake calendar provider for tests and the walking skeleton."""

    def __init__(self) -> None:
        self.events: list[CalendarEvent] = []
        self.fetch_fail = False

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        if self.fetch_fail:
            raise RuntimeError("Calendar fetch failure")
        return [e for e in self.events if start <= e.start < end]

    def upcoming(self, horizon_minutes: int = 60) -> list[CalendarEvent]:
        """Convenience: events starting within the next horizon_minutes."""
        now = datetime.now(UTC)
        cutoff = now + timedelta(minutes=horizon_minutes)
        return self.list_events(now, cutoff)

    def today_events(self) -> list[CalendarEvent]:
        now = datetime.now(UTC)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return self.list_events(start, end)

    def create_event(self, event: CalendarEvent, confirm: bool) -> str:
        if not confirm:
            raise PermissionError("T2 confirmation required to create calendar events")
        self.events.append(event)
        return event.id

    def move_event(
        self,
        event_id: str,
        new_start: datetime,
        new_end: datetime,
        confirm: bool,
    ) -> None:
        if not confirm:
            raise PermissionError("T2 confirmation required to move calendar events")
        for e in self.events:
            if e.id == event_id:
                e.start = new_start
                e.end = new_end
                return
        raise KeyError(f"Event {event_id} not found")

    def delete_event(self, event_id: str, confirm: bool) -> None:
        if not confirm:
            raise PermissionError("T2 confirmation required to delete calendar events")
        self.events[:] = [e for e in self.events if e.id != event_id]

    def add_event(
        self,
        title: str,
        start: datetime,
        end: datetime,
        location: str = "",
        attendees: list[str] | None = None,
    ) -> CalendarEvent:
        event = CalendarEvent(
            id=f"cal-{len(self.events)}",
            title=title,
            start=start,
            end=end,
            location=location,
            attendees=attendees or [],
        )
        self.events.append(event)
        return event

    def health(self) -> str:
        return "ok"
