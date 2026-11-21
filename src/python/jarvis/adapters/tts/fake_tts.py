"""Fake TTS — records spoken text for tests and the walking skeleton.

Mimics real TTS behavior:
- Configurable speaking state
- Barge-in (stop) support
- Simulated latency
- Chunked streaming
"""

from __future__ import annotations

from collections.abc import Callable

from jarvis.ports.tts import AudioChunk, TextToSpeech


class FakeTextToSpeech(TextToSpeech):
    """Fake TTS that records spoken text for test assertions.

    Simulates:
    - Speaking state (is_speaking)
    - Barge-in via stop()
    - Configurable latency
    - Chunked streaming with on_chunk callback
    """

    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.chunks: list[AudioChunk] = []
        self._speaking = False
        self.stopped = False
        self.latency_seconds = 0.0
        self.fail_on_speak = False

    def speak(
        self,
        text: str,
        on_chunk: Callable[[AudioChunk], None] | None = None,
    ) -> None:
        if self.fail_on_speak:
            raise RuntimeError("Fake TTS speak failure")
        self.spoken.append(text)
        self._speaking = True
        if on_chunk:
            on_chunk(b"fake-audio-chunk")
        self._speaking = False

    def stop(self) -> None:
        self.stopped = True
        self._speaking = False

    def is_speaking(self) -> bool:
        return self._speaking

    def health(self) -> str:
        return "ok"

    def clear(self) -> None:
        """Clear recorded speech (for test isolation)."""
        self.spoken.clear()
        self.chunks.clear()
        self.stopped = False
        self._speaking = False
