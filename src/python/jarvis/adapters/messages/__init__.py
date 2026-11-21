"""Message source adapters (Messenger, SMS)."""

from jarvis.adapters.messages.fake_message_source import FakeMessageSource
from jarvis.adapters.messages.notification_adapter import WindowsNotificationAdapter

__all__ = ["FakeMessageSource", "WindowsNotificationAdapter"]
