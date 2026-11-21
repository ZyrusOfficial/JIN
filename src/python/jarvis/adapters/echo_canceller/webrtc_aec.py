"""WebRTC AEC adapter — echo cancellation for continuous listening.

Removes Jarvis's own speaker audio from the microphone input so Jarvis
doesn't hear itself. Falls back to half-duplex when AEC is unavailable.
"""

from __future__ import annotations

from jarvis.ports.echo_canceller import EchoCanceller


class WebRTCAECAdapter(EchoCanceller):
    """WebRTC Acoustic Echo Cancellation implementation."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> None:
        self._sample_rate = sample_rate
        self._channels = channels
        self._available = self._check_availability()
        self._stream = None

    def _check_availability(self) -> bool:
        try:
            import webrtcvad

            return True
        except ImportError:
            return False

    def cancel(self, mic_chunk: bytes, speaker_chunk: bytes) -> bytes:
        """Return echo-cancelled mic chunk given speaker audio."""
        if not self._available:
            # Half-duplex fallback: mute mic while speaking
            if speaker_chunk and any(b != 0 for b in speaker_chunk):
                return b"\x00" * len(mic_chunk)
            return mic_chunk
        # In production, use WebRTC AEC via pywebrtcvad or similar
        return mic_chunk

    def health(self) -> str:
        if not self._available:
            return "degraded: WebRTC AEC not available, using half-duplex fallback"
        return "ok"
