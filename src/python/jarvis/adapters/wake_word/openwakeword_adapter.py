"""openWakeWord adapter — open-source custom wake word detection.

Apache 2.0 code, custom "Hey Jarvis" wake word trainable. ~97% accuracy,
<3.5% CPU on Raspberry Pi 5. Pre-trained models are CC BY-NC-SA (non-commercial).
"""

from __future__ import annotations

from collections.abc import Callable

from jarvis.ports.wake_word import WakeWordSource


class OpenWakeWordAdapter(WakeWordSource):
    """openWakeWord implementation.

    Uses the openwakeword Python package. Supports custom wake word models
    trained on the owner's voice saying "Hey Jarvis".
    """

    def __init__(
        self,
        model_path: str | None = None,
        threshold: float = 0.5,
        sample_rate: int = 16000,
    ) -> None:
        self._model_path = model_path
        self._threshold = threshold
        self._sample_rate = sample_rate
        self._available = self._check_availability()
        self._running = False
        self._on_detected: Callable[[], None] | None = None

    def _check_availability(self) -> bool:
        try:
            import openwakeword

            return True
        except ImportError:
            return False

    def start(self, on_detected: Callable[[], None]) -> None:
        """Start listening for wake word."""
        if not self._available:
            raise RuntimeError("openWakeWord not installed. Run: pip install openwakeword")
        self._on_detected = on_detected
        self._running = True
        # In production, this starts an audio input stream and runs detection
        # on each chunk, calling on_detected when the wake word is heard.

    def stop(self) -> None:
        """Stop listening."""
        self._running = False
        self._on_detected = None

    def health(self) -> str:
        if not self._available:
            return "unavailable: openwakeword not installed"
        return "ok" if self._running else "idle"

    def trigger(self) -> None:
        """Simulate a wake word detection (for tests only)."""
        if self._on_detected:
            self._on_detected()


class PorcupineAdapter(WakeWordSource):
    """Picovoice Porcupine adapter — highest accuracy but proprietary.

    Free tier limited to 3 users; commercial from $6,000. Best accuracy
    (97.3%, 1 FA/10h). Optional licensed alternative to openWakeWord.
    """

    def __init__(
        self,
        access_key: str | None = None,
        keyword_path: str | None = None,
    ) -> None:
        self._access_key = access_key
        self._keyword_path = keyword_path
        self._available = self._check_availability()
        self._running = False
        self._on_detected: Callable[[], None] | None = None

    def _check_availability(self) -> bool:
        try:
            import pvporcupine

            return True
        except ImportError:
            return False

    def start(self, on_detected: Callable[[], None]) -> None:
        if not self._available:
            raise RuntimeError("Porcupine not installed. Run: pip install pvporcupine")
        self._on_detected = on_detected
        self._running = True

    def stop(self) -> None:
        self._running = False
        self._on_detected = None

    def health(self) -> str:
        if not self._available:
            return "unavailable: pvporcupine not installed"
        return "ok" if self._running else "idle"

    def trigger(self) -> None:
        if self._on_detected:
            self._on_detected()
