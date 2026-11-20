"""Fake calendar provider — controllable events for tests."""

from datetime import datetime

from jarvis.ports.calendar_provider import CalendarEvent, CalendarProvider


class FakeCalendarProvider(CalendarProvider):
    def __init__(self) -> None:
        self.events: dict[str, CalendarEvent] = {}
        self.created: list[tuple[CalendarEvent, bool]] = []
        self.moved: list[tuple[str, datetime, datetime, bool]] = []
        self.deleted: list[tuple[str, bool]] = []

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        return [e for e in self.events.values() if e.start >= start and e.end <= end]

    def create_event(self, event: CalendarEvent, confirm: bool) -> str:
        self.created.append((event, confirm))
        self.events[event.id] = event
        return event.id

    def move_event(
        self,
        event_id: str,
        new_start: datetime,
        new_end: datetime,
        confirm: bool,
    ) -> None:
        self.moved.append((event_id, new_start, new_end, confirm))
        if event_id in self.events:
            self.events[event_id].start = new_start
            self.events[event_id].end = new_end

    def delete_event(self, event_id: str, confirm: bool) -> None:
        self.deleted.append((event_id, confirm))
        self.events.pop(event_id, None)

    def health(self) -> str:
        return "ok"
