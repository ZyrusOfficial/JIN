"""Calendar provider port — Google Calendar / Microsoft Graph / offline ICS."""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass
class CalendarEvent:
    id: str
    title: str
    start: datetime
    end: datetime
    location: str | None = None
    attendees: list[str] = field(default_factory=list)
    timezone: str = "UTC"
    recurring: bool = False
    raw: dict[str, object] = field(default_factory=dict)


@runtime_checkable
class CalendarProvider(Protocol):
    @abstractmethod
    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        """List events in a time window."""

    @abstractmethod
    def create_event(self, event: CalendarEvent, confirm: bool) -> str:
        """Create an event, requires confirmation (T2). Returns event id."""

    @abstractmethod
    def move_event(
        self, event_id: str, new_start: datetime, new_end: datetime, confirm: bool
    ) -> None:
        """Move an event, requires confirmation (T2)."""

    @abstractmethod
    def delete_event(self, event_id: str, confirm: bool) -> None:
        """Delete an event, requires confirmation (T2)."""

    @abstractmethod
    def health(self) -> str:
        """Return health status."""
