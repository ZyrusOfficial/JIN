"""Voice activity detection port — speech/silence segmentation."""

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class VoiceActivityDetector(Protocol):
    @abstractmethod
    def is_speech(self, audio_chunk: bytes) -> bool:
        """Return True if the chunk contains speech."""

    @abstractmethod
    def health(self) -> str:
        """Return health status."""
