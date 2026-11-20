"""Contract tests for the Clock port."""

from datetime import UTC, datetime, timedelta

from jarvis.fakes.clock import FakeClock
from jarvis.ports.clock import Clock


def test_fake_clock_implements_clock_port() -> None:
    """The fake must satisfy the Clock protocol."""
    clock: Clock = FakeClock()
    assert isinstance(clock, Clock)


def test_fake_clock_now_returns_aware_datetime() -> None:
    clock = FakeClock()
    now = clock.now()
    assert now.tzinfo is not None


def test_fake_clock_advance_moves_time() -> None:
    clock = FakeClock()
    start = clock.now()
    clock.advance(timedelta(hours=1))
    assert clock.now() == start + timedelta(hours=1)


def test_fake_clock_sleep_unlet_advances() -> None:
    clock = FakeClock()
    start = clock.now()
    future = start + timedelta(minutes=30)
    clock.sleep_until(future)
    assert clock.now() == future


def test_fake_clock_default_start_is_2026_11_20() -> None:
    clock = FakeClock()
    assert clock.now() == datetime(2026, 11, 20, 8, 0, 0, tzinfo=UTC)
