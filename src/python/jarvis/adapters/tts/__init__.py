"""Text-to-speech adapters."""

from jarvis.adapters.tts.fake_tts import FakeTextToSpeech
from jarvis.adapters.tts.piper_adapter import KokoroAdapter, PiperAdapter

__all__ = ["FakeTextToSpeech", "KokoroAdapter", "PiperAdapter"]
