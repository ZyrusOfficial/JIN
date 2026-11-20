"""Port interfaces (hexagonal architecture adapters implement these)."""

from jarvis.ports.audit_log import AuditLog
from jarvis.ports.calendar_provider import CalendarProvider
from jarvis.ports.clock import Clock
from jarvis.ports.desktop_control import DesktopControl
from jarvis.ports.echo_canceller import EchoCanceller
from jarvis.ports.memory_store import MemoryStore
from jarvis.ports.message_source import MessageSource
from jarvis.ports.news_source import NewsSource
from jarvis.ports.notification_source import NotificationSource
from jarvis.ports.policy_gate import GateDecision, PolicyGate, TrustTier
from jarvis.ports.secrets_broker import SecretsBroker
from jarvis.ports.stt import SpeechToText
from jarvis.ports.tts import TextToSpeech
from jarvis.ports.vad import VoiceActivityDetector
from jarvis.ports.wake_word import WakeWordSource

__all__ = [
    "AuditLog",
    "CalendarProvider",
    "Clock",
    "DesktopControl",
    "EchoCanceller",
    "GateDecision",
    "MemoryStore",
    "MessageSource",
    "NewsSource",
    "NotificationSource",
    "PolicyGate",
    "SecretsBroker",
    "SpeechToText",
    "TextToSpeech",
    "TrustTier",
    "VoiceActivityDetector",
    "WakeWordSource",
]
