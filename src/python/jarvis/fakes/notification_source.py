"""Fake notification source — controllable Windows notifications for tests."""

from datetime import UTC, datetime

from jarvis.ports.notification_source import (
    NotificationEvent,
    NotificationSource,
)


class FakeNotificationSource(NotificationSource):
    def __init__(self) -> None:
        self.notifications: list[NotificationEvent] = []
        self._access = True

    def events(self) -> list[NotificationEvent]:
        return list(self.notifications)

    def has_access(self) -> bool:
        return self._access

    def set_access(self, granted: bool) -> None:
        self._access = granted

    def add_notification(
        self,
        app_id: str,
        title: str,
        text: str,
        timestamp: datetime | None = None,
    ) -> None:
        self.notifications.append(
            NotificationEvent(
                id=f"notif-{len(self.notifications)}",
                app_id=app_id,
                title=title,
                text=text,
                timestamp=timestamp or datetime(2026, 11, 20, 9, 0, 0, tzinfo=UTC),
            )
        )

    def health(self) -> str:
        return "ok"
