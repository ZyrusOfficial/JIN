"""Voice activity detection adapters."""

from jarvis.adapters.vad.fake_vad import FakeVoiceActivityDetector
from jarvis.adapters.vad.silero_adapter import SileroVADAdapter

__all__ = ["FakeVoiceActivityDetector", "SileroVADAdapter"]
