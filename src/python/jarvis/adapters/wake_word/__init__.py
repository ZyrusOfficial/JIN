"""Wake word adapters."""

from jarvis.adapters.wake_word.fake_wake_word import FakeWakeWordSource
from jarvis.adapters.wake_word.openwakeword_adapter import OpenWakeWordAdapter

__all__ = ["FakeWakeWordSource", "OpenWakeWordAdapter"]
