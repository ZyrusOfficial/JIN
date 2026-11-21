"""Fake wake word source — controllable detection for tests.

Simulates realistic wake word behavior:
- Controllable detection trigger
- Health status tracking
- Start/stop lifecycle
"""

from collections.abc import Callable
from typing import Optional

from jarvis.ports.wake_word import WakeWordSource


class FakeWakeWordSource(WakeWordSource):
    """Fake wake word source for tests and the walking skeleton."""

    def __init__(self) -> None:
        self._on_detected: Callable[[], None] | None = None
        self._running = False
        self.detect_called = False
        self.trigger_count = 0

    def start(self, on_detected: Callable[[], None]) -> None:
        self._on_detected = on_detected
        self._running = True

    def stop(self) -> None:
        self._running = False

    def trigger(self) -> None:
        """Simulate a wake word detection."""
        self.detect_called = True
        self.trigger_count += 1
        if self._on_detected:
            self._on_detected()

    def health(self) -> str:
        return "ok"
