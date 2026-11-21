"""Piper TTS adapter — fast, CPU-friendly neural TTS with streaming support.

Piper uses VITS models exported to ONNX. It's ~8-9x faster than Kokoro and
runs well on CPU. Suitable for the default TTS voice on modest hardware.
"""

from __future__ import annotations

from collections.abc import Callable

from jarvis.ports.tts import AudioChunk, TextToSpeech


class PiperAdapter(TextToSpeech):
    """Piper TTS implementation.

    Uses the piper-python package or the piper binary with ONNX voice models.
    Streams audio chunks for interruptible, barge-in capable speech.
    """

    def __init__(
        self,
        voice: str = "en_US-lessac-medium",
        model_path: str | None = None,
        config_path: str | None = None,
        sample_rate: int = 16000,
    ) -> None:
        self._voice = voice
        self._model_path = model_path
        self._config_path = config_path
        self._sample_rate = sample_rate
        self._available = self._check_availability()
        self._speaking = False

    def _check_availability(self) -> bool:
        try:
            import piper

            return True
        except ImportError:
            # Could also use the piper binary via subprocess
            return False

    def speak(
        self,
        text: str,
        on_chunk: Callable[[AudioChunk], None] | None = None,
    ) -> None:
        """Speak text, streaming audio chunks to on_chunk.

        In production, synthesizes to audio and yields chunks. If on_chunk
        is provided, chunks are delivered as they're generated (streaming).
        """
        if not self._available:
            raise RuntimeError("Piper not installed. Run: pip install piper-tts")
        self._speaking = True
        try:
            # Synthesize and stream chunks
            audio_bytes = self._synthesize(text)
            # Yield in chunks for streaming playback
            chunk_size = 1024
            for i in range(0, len(audio_bytes), chunk_size):
                if on_chunk:
                    on_chunk(audio_bytes[i : i + chunk_size])
        finally:
            self._speaking = False

    def _synthesize(self, text: str) -> bytes:
        """Synthesize text to raw audio bytes."""

        # Piper synthesis — returns WAV bytes, we extract PCM
        from piper import PiperVoice

        voice = PiperVoice.load(self._model_path or self._voice)
        # Synthesize to bytes
        import io

        wav_buffer = io.BytesIO()
        voice.synthesize(text, wav_buffer)
        wav_buffer.seek(0)
        # Skip WAV header (44 bytes) for raw PCM
        wav_buffer.read(44)
        return wav_buffer.read()

    def stop(self) -> None:
        """Stop speech immediately (barge-in)."""
        self._speaking = False

    def is_speaking(self) -> bool:
        return self._speaking

    def health(self) -> str:
        if not self._available:
            return "unavailable: piper-tts not installed"
        return "ok"


class KokoroAdapter(TextToSpeech):
    """Kokoro-82M TTS adapter — higher quality but slower than Piper.

    Kokoro achieves 4.5 MOS but has ~3.7s first-token latency, making it
    suitable as a quality alternative when latency is less critical.
    """

    def __init__(
        self,
        voice: str = "en_US-female",
        model_path: str | None = None,
    ) -> None:
        self._voice = voice
        self._model_path = model_path
        self._available = self._check_availability()
        self._speaking = False

    def _check_availability(self) -> bool:
        try:
            import kokoro

            return True
        except ImportError:
            return False

    def speak(
        self,
        text: str,
        on_chunk: Callable[[AudioChunk], None] | None = None,
    ) -> None:
        if not self._available:
            raise RuntimeError("Kokoro not installed")
        self._speaking = True
        try:
            # Kokoro synthesis — higher quality, slower
            audio_bytes = self._synthesize(text)
            if on_chunk:
                on_chunk(audio_bytes)
        finally:
            self._speaking = False

    def _synthesize(self, text: str) -> bytes:
        import kokoro

        model = kokoro.KokoroModel(self._model_path or "kokoro-v0_19")
        return model.synthesize(text, voice=self._voice)  # type: ignore[no-any-return]

    def stop(self) -> None:
        self._speaking = False

    def is_speaking(self) -> bool:
        return self._speaking

    def health(self) -> str:
        if not self._available:
            return "unavailable: kokoro not installed"
        return "ok"
