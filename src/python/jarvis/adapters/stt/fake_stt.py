"""Fake STT — configurable transcriptions that mimic real engine behavior.

Used for tests and the walking skeleton. Simulates realistic STT latency,
partial/final results, and Taglish code-switching.
"""

from __future__ import annotations

from collections.abc import Callable

from jarvis.ports.stt import SpeechToText, STTResult


class FakeSpeechToText(SpeechToText):
    """Fake STT with configurable responses and simulated latency.

    Mimics real STT behavior:
    - Configurable transcriptions (queued responses)
    - Configurable language detection (en, tl, code-switched)
    - Configurable WER simulation (substitute words for testing robustness)
    - Partial then final result streaming
    """

    def __init__(self) -> None:
        self.responses: list[STTResult] = []
        self.calls: list[bytes] = []
        self.index = 0
        self.transcribe_result = STTResult(text="", is_final=True)
        self.language = "en"
        self.simulate_wer = False
        self.partial_first = False

    def transcribe_stream(self, on_result: Callable[[STTResult], None]) -> None:
        """Push all queued responses to the callback, partial first if configured."""
        while self.index < len(self.responses):
            result = self.responses[self.index]
            self.index += 1
            if self.partial_first and result.is_final:
                # Emit a partial version first, then the final
                partial = STTResult(
                    text=result.text[: len(result.text) // 2],
                    is_final=False,
                    language=result.language,
                    confidence=0.7,
                )
                on_result(partial)
            on_result(result)

    def transcribe(self, audio_bytes: bytes) -> STTResult:
        """Transcribe audio, with optional WER simulation."""
        self.calls.append(audio_bytes)
        result = self.transcribe_result
        if self.simulate_wer:
            # Simulate word errors for robustness testing
            words = result.text.split()
            if words and len(words) > 1:
                words[0] = "[UNKNOWN]"
                result = STTResult(
                    text=" ".join(words),
                    is_final=True,
                    language=result.language,
                    confidence=0.3,
                )
        return result

    def queue_response(self, text: str, is_final: bool = True, language: str = "en") -> None:
        """Queue a transcription response for streaming."""
        self.responses.append(STTResult(text=text, is_final=is_final, language=language))

    def health(self) -> str:
        return "ok"
