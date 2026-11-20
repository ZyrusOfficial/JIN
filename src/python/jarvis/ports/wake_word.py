"""Wake word source port — detects 'Hey Jarvis'."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable
from typing import Protocol, runtime_checkable


@runtime_checkable
class WakeWordSource(Protocol):
    @abstractmethod
    def start(self, on_detected: Callable[[], None]) -> None:
        """Start listening for wake word. on_detected is called when heard."""

    @abstractmethod
    def stop(self) -> None:
        """Stop listening."""

    @abstractmethod
    def health(self) -> str:
        """Return health status: 'ok', 'degraded', 'unavailable'."""
