"""Fake implementations of every port, for tests and the walking skeleton."""

from jarvis.fakes.audit_log import FakeAuditLog
from jarvis.fakes.calendar_provider import FakeCalendarProvider
from jarvis.fakes.clock import FakeClock
from jarvis.fakes.desktop_control import FakeDesktopControl
from jarvis.fakes.echo_canceller import FakeEchoCanceller
from jarvis.fakes.memory_store import FakeMemoryStore
from jarvis.fakes.message_source import FakeMessageSource
from jarvis.fakes.news_source import FakeNewsSource
from jarvis.fakes.notification_source import FakeNotificationSource
from jarvis.fakes.policy_gate import FakePolicyGate
from jarvis.fakes.secrets_broker import FakeSecretsBroker
from jarvis.fakes.stt import FakeSpeechToText
from jarvis.fakes.tts import FakeTextToSpeech
from jarvis.fakes.vad import FakeVoiceActivityDetector
from jarvis.fakes.wake_word import FakeWakeWordSource

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
    "FakeSecretsBroker",
    "FakeSpeechToText",
    "FakeTextToSpeech",
    "FakeVoiceActivityDetector",
    "FakeWakeWordSource",
]
