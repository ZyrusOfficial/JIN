"""Fake text-to-speech — records spoken text for tests."""

from collections.abc import Callable

from jarvis.ports.tts import AudioChunk, TextToSpeech


class FakeTextToSpeech(TextToSpeech):
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.chunks: list[AudioChunk] = []
        self._speaking = False
        self.stopped = False

    def speak(
        self,
        text: str,
        on_chunk: Callable[[AudioChunk], None] | None = None,
    ) -> None:
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
