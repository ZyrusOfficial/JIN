"""Clock port — injectable virtual clock for deterministic timing tests."""

from __future__ import annotations

from abc import abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """Injectable clock. All scheduling, cooldowns, and quiet hours go through this."""

    @abstractmethod
    def now(self) -> datetime:
        """Return the current time as an aware UTC datetime."""

    @abstractmethod
    def advance(self, delta: timedelta) -> None:
        """Advance the clock by delta (used in tests)."""

    @abstractmethod
    def sleep_until(self, target: datetime) -> None:
        """Sleep until target (real implementations block; tests advance the clock)."""


class _CannotAdvanceClockError(RuntimeError):
    """Raised when attempting to advance the system clock."""

    def __init__(self) -> None:
        super().__init__("SystemClock cannot be advanced")


class SystemClock:
    """Real clock backed by the system wall clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)

    def advance(self, delta: timedelta) -> None:
        raise _CannotAdvanceClockError()

    def sleep_until(self, target: datetime) -> None:
        import time

        now = self.now()
        if target > now:
            time.sleep((target - now).total_seconds())


class VirtualClock:
    """Virtual clock for tests. Starts at a fixed epoch and only moves when advanced."""

    def __init__(self, start: datetime | None = None) -> None:
        self._now: datetime = start or datetime(2026, 11, 20, 0, 0, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta

    def sleep_until(self, target: datetime) -> None:
        self._now = max(self._now, target)
