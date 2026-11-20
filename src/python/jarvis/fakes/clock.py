"""Fake clock for tests."""

from datetime import UTC, datetime, timedelta

from jarvis.ports.clock import Clock


class FakeClock(Clock):
    def __init__(self, start: datetime | None = None) -> None:
        self._now: datetime = start or datetime(2026, 11, 20, 8, 0, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta

    def sleep_until(self, target: datetime) -> None:
        self._now = max(self._now, target)
