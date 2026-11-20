"""Echo cancellation port — removes Jarvis's own audio from mic input."""

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class EchoCanceller(Protocol):
    @abstractmethod
    def cancel(self, mic_chunk: bytes, speaker_chunk: bytes) -> bytes:
        """Return echo-cancelled mic chunk given the speaker audio."""

    @abstractmethod
    def health(self) -> str:
        """Return health status."""
