"""Fake VAD — controllable voice activity detection for tests."""

from jarvis.ports.vad import VoiceActivityDetector


class FakeVoiceActivityDetector(VoiceActivityDetector):
    """Fake VAD with controllable speech detection."""

    def __init__(self) -> None:
        self.speech_chunks: set[bytes] = set()
        self.return_speech = False

    def is_speech(self, audio_chunk: bytes) -> bool:
        if audio_chunk in self.speech_chunks:
            return True
        return self.return_speech

    def health(self) -> str:
        return "ok"
