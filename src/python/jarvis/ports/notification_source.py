"""Notification source port — Windows notifications (toast, Phone Link, etc.)."""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass
class NotificationEvent:
    id: str
    app_id: str
    title: str
    text: str
    timestamp: datetime
    is_group: bool = False
    has_actions: bool = False
    raw: dict[str, object] = field(default_factory=dict)


@runtime_checkable
class NotificationSource(Protocol):
    @abstractmethod
    def events(self) -> list[NotificationEvent]:
        """Return pending notification events."""

    @abstractmethod
    def has_access(self) -> bool:
        """Return True if notification listener access is granted."""

    @abstractmethod
    def health(self) -> str:
        """Return health status."""
