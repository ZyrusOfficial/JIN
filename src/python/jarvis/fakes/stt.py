"""Fake speech-to-text — configurable transcriptions for tests."""

from collections.abc import Callable

from jarvis.ports.stt import SpeechToText, STTResult


class FakeSpeechToText(SpeechToText):
    def __init__(self) -> None:
        self.responses: list[STTResult] = []
        self.calls: list[bytes] = []
        self.index = 0
        self.transcribe_result = STTResult(text="", is_final=True)

    def transcribe_stream(self, on_result: Callable[[STTResult], None]) -> None:
        """Push all queued responses to the callback."""
        while self.index < len(self.responses):
            on_result(self.responses[self.index])
            self.index += 1

    def transcribe(self, audio_bytes: bytes) -> STTResult:
        self.calls.append(audio_bytes)
        return self.transcribe_result

    def health(self) -> str:
        return "ok"
