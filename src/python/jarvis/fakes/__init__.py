"""Fake implementations of every port, for tests and the walking skeleton.

Re-exports from adapters to avoid duplication. The adapter fakes are the
canonical implementations; fakes/ re-exports them for test convenience.
"""

from jarvis.adapters.echo_canceller.fake_echo_canceller import FakeEchoCanceller
from jarvis.adapters.messages.fake_message_source import FakeMessageSource
from jarvis.adapters.popup.fake_popup import FakePopupPort
from jarvis.adapters.stt.fake_stt import FakeSpeechToText
from jarvis.adapters.tts.fake_tts import FakeTextToSpeech
from jarvis.adapters.vad.fake_vad import FakeVoiceActivityDetector
from jarvis.adapters.wake_word.fake_wake_word import FakeWakeWordSource
from jarvis.fakes.audit_log import FakeAuditLog
from jarvis.fakes.calendar_provider import FakeCalendarProvider
from jarvis.fakes.clock import FakeClock
from jarvis.fakes.desktop_control import FakeDesktopControl
from jarvis.fakes.memory_store import FakeMemoryStore
from jarvis.fakes.news_source import FakeNewsSource
from jarvis.fakes.notification_source import FakeNotificationSource
from jarvis.fakes.policy_gate import FakePolicyGate
from jarvis.fakes.secrets_broker import FakeSecretsBroker

__all__ = [
    "FakeAuditLog",
    "FakeCalendarProvider",
    "FakeClock",
    "FakeDesktopControl",
    "FakeEchoCanceller",
    "FakeMemoryStore",
    "FakeMessageSource",
    "FakeNewsSource",
    "FakeNotificationSource",
    "FakePolicyGate",
    "FakePopupPort",
    "FakeSecretsBroker",
    "FakeSpeechToText",
    "FakeTextToSpeech",
    "FakeVoiceActivityDetector",
    "FakeWakeWordSource",
]
