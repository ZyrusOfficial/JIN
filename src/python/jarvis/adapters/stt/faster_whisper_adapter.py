"""Faster-whisper STT adapter — real implementation for production.

Supports Taglish via dominant-language code-switching. Falls back to cloud
STT (Google Cloud Chirp) when local model is unavailable.
"""

from __future__ import annotations

from collections.abc import Callable

from jarvis.ports.stt import SpeechToText, STTResult


class FasterWhisperAdapter(SpeechToText):
    """Faster-whisper (CTranslate2) STT implementation.

    Uses the faster-whisper Python package with Whisper large-v3 weights.
    Taglish is handled by setting the dominant language (e.g. "tl" for
    Tagalog/Filipino) and letting the model handle code-switching
    automatically.
    """

    def __init__(
        self,
        model_size: str = "base",
        language: str | None = None,
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self._model_size = model_size
        self._language = language  # e.g. "tl" for Tagalog, None for auto-detect
        self._device = device
        self._compute_type = compute_type
        self._model: object | None = None
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        """Check if faster-whisper is installed and a model can be loaded."""
        try:
            import faster_whisper

            return True
        except ImportError:
            return False

    def _load_model(self) -> None:
        """Lazy-load the whisper model."""
        if self._model is not None:
            return
        if not self._available:
            raise RuntimeError("faster-whisper not installed. Run: pip install faster-whisper")
        from faster_whisper import WhisperModel

        self._model = WhisperModel(
            self._model_size,
            device=self._device,
            compute_type=self._compute_type,
        )

    def transcribe_stream(self, on_result: Callable[[STTResult], None]) -> None:
        """Stream audio chunks; on_result called with STTResult.

        In production, this wraps a VAD-driven audio streamer that feeds
        chunks to faster-whisper and yields partial/final results.
        """
        raise NotImplementedError(
            "Streaming transcription requires an audio input pipeline. "
            "Use the fake adapter for tests or integrate with a real mic."
        )

    def transcribe(self, audio_bytes: bytes) -> STTResult:
        """Transcribe a single audio blob."""
        self._load_model()

        import numpy as np

        # Convert bytes to numpy array (16-bit PCM, mono)
        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        audio /= 32768.0  # normalize to [-1, 1]

        segments, info = self._model.transcribe(  # type: ignore[union-attr]
            audio,
            language=self._language,
            vad_filter=True,
        )

        text = " ".join(seg.text for seg in segments)
        return STTResult(
            text=text,
            is_final=True,
            language=info.language,
            confidence=info.language_probability,
        )

    def health(self) -> str:
        """Return health status."""
        if not self._available:
            return "unavailable: faster-whisper not installed"
        try:
            self._load_model()
            return "ok"
        except Exception as exc:
            return f"degraded: {exc}"


class CloudSTTAdapter(SpeechToText):
    """Cloud STT adapter (Google Cloud Chirp or OpenAI Whisper API).

    Used as fallback when local STT is unavailable or for higher accuracy
    on Taglish/Filipino.
    """

    def __init__(
        self,
        provider: str = "google",
        language: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._provider = provider
        self._language = language
        self._api_key = api_key
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        if self._provider == "google":
            try:
                import google.cloud.speech

                return True
            except ImportError:
                return False
        if self._provider == "openai":
            try:
                import openai

                return True
            except ImportError:
                return False
        return False

    def transcribe_stream(self, on_result: Callable[[STTResult], None]) -> None:
        raise NotImplementedError("Cloud streaming STT not yet implemented")

    def transcribe(self, audio_bytes: bytes) -> STTResult:
        """Transcribe using cloud API."""
        if not self._available:
            raise RuntimeError(f"{self._provider} STT not available")
        if self._provider == "google":
            return self._transcribe_google(audio_bytes)
        if self._provider == "openai":
            return self._transcribe_openai(audio_bytes)
        raise ValueError(f"Unknown provider: {self._provider}")

    def _transcribe_google(self, audio_bytes: bytes) -> STTResult:
        from google.cloud.speech import RecognitionAudio, RecognitionConfig, SpeechClient

        client = SpeechClient()
        audio = RecognitionAudio(content=audio_bytes)
        config = RecognitionConfig(
            encoding="LINEAR16",
            sample_rate_hertz=16000,
            language_code=self._language or "tl-PH",
            enable_automatic_punctuation=True,
            use_enhanced=True,
        )
        response = client.recognize(config=config, audio=audio)
        text = " ".join(result.alternatives[0].transcript for result in response.results)
        return STTResult(text=text, is_final=True, language=self._language)

    def _transcribe_openai(self, audio_bytes: bytes) -> STTResult:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)
        # OpenAI expects a file-like object
        import io

        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.wav"
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=self._language,
        )
        return STTResult(
            text=transcript.text,
            is_final=True,
            language=self._language,
        )

    def health(self) -> str:
        if not self._available:
            return f"unavailable: {self._provider} STT not installed"
        return "ok"
