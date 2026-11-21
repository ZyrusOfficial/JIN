"""Speech-to-text adapters."""

from jarvis.adapters.stt.fake_stt import FakeSpeechToText
from jarvis.adapters.stt.faster_whisper_adapter import FasterWhisperAdapter

__all__ = ["FakeSpeechToText", "FasterWhisperAdapter"]
