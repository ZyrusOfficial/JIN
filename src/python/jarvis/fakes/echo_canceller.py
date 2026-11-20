"""Fake echo canceller — passes mic audio through for tests."""

from jarvis.ports.echo_canceller import EchoCanceller


class FakeEchoCanceller(EchoCanceller):
    def cancel(self, mic_chunk: bytes, speaker_chunk: bytes) -> bytes:
        return mic_chunk

    def health(self) -> str:
        return "ok"
