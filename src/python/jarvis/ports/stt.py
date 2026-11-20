"""Speech-to-text port — audio -> text."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class STTResult:
    text: str
    is_final: bool
    language: str | None = None
    confidence: float | None = None


@runtime_checkable
class SpeechToText(Protocol):
    @abstractmethod
    def transcribe_stream(self, on_result: Callable[[STTResult], None]) -> None:
        """Stream audio chunks; on_result called with STTResult."""

    @abstractmethod
    def transcribe(self, audio_bytes: bytes) -> STTResult:
        """Transcribe a single audio blob."""

    @abstractmethod
    def health(self) -> str:
        """Return health status."""
