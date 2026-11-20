"""Text-to-speech port — text -> streaming audio."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable
from typing import Protocol, runtime_checkable

AudioChunk = bytes


@runtime_checkable
class TextToSpeech(Protocol):
    @abstractmethod
    def speak(self, text: str, on_chunk: Callable[[AudioChunk], None] | None = None) -> None:
        """Speak text, streaming audio chunks to on_chunk if provided."""

    @abstractmethod
    def stop(self) -> None:
        """Stop speech immediately (barge-in)."""

    @abstractmethod
    def is_speaking(self) -> bool:
        """Return True if currently speaking."""

    @abstractmethod
    def health(self) -> str:
        """Return health status."""
