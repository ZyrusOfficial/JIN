"""Silero VAD adapter — voice activity detection.

Silero VAD is a lightweight, accurate VAD model that drives end-of-speech
detection and barge-in. Works well on CPU.
"""

from __future__ import annotations

from jarvis.ports.vad import VoiceActivityDetector


class SileroVADAdapter(VoiceActivityDetector):
    """Silero VAD implementation."""

    def __init__(
        self,
        sample_rate: int = 16000,
        threshold: float = 0.5,
        min_silence_ms: int = 500,
    ) -> None:
        self._sample_rate = sample_rate
        self._threshold = threshold
        self._min_silence_ms = min_silence_ms
        self._available = self._check_availability()
        self._model = None

    def _check_availability(self) -> bool:
        try:
            import torch

            return True
        except ImportError:
            return False

    def _load_model(self) -> None:
        if self._model is not None:
            return
        import torch

        self._model, _utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
        )

    def is_speech(self, audio_chunk: bytes) -> bool:
        """Return True if the chunk contains speech."""
        if not self._available:
            return False  # Conservative: assume silence if unavailable
        import numpy as np

        self._load_model()
        audio = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32)
        audio /= 32768.0

        import torch

        audio_tensor = torch.from_numpy(audio)
        assert self._model is not None
        confidence = self._model(audio_tensor, self._sample_rate).item()
        return confidence >= self._threshold

    def health(self) -> str:
        if not self._available:
            return "unavailable: torch not installed"
        return "ok"
