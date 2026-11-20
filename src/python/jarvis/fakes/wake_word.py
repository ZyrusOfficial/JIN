"""Fake wake word source — controllable detection for tests."""

from collections.abc import Callable

from jarvis.ports.wake_word import WakeWordSource


class FakeWakeWordSource(WakeWordSource):
    def __init__(self) -> None:
        self._on_detected: Callable[[], None] | None = None
        self._running = False
        self.detect_called = False

    def start(self, on_detected: Callable[[], None]) -> None:
        self._on_detected = on_detected
        self._running = True

    def stop(self) -> None:
        self._running = False

    def trigger(self) -> None:
        """Simulate a wake word detection."""
        self.detect_called = True
        if self._on_detected:
            self._on_detected()

    def health(self) -> str:
        return "ok"
