"""Popup port — proactive alert cards and UI notifications.

Popup cards are shown to the owner for proactive alerts (calendar, news,
messages) and require owner action (read, reply, snooze, dismiss).
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass
class PopupCard:
    """A popup card shown to the owner."""

    id: str
    title: str
    body: str
    source: str  # calendar | news | messenger | sms | system
    interrupt_level: str  # L1 | L2 | L3
    actions: list[str] = field(default_factory=lambda: ["read", "snooze", "dismiss"])
    created_at: datetime = field(default_factory=datetime.now)
    sensitive: bool = False


@dataclass
class PopupResponse:
    """Owner's response to a popup card."""

    card_id: str
    action: str  # read | reply | snooze | dismiss
    timestamp: datetime = field(default_factory=datetime.now)


@runtime_checkable
class PopupPort(Protocol):
    """Port for showing popup cards to the owner."""

    @abstractmethod
    def show(self, card: PopupCard) -> None:
        """Show a popup card to the owner."""

    @abstractmethod
    def dismiss(self, card_id: str) -> None:
        """Dismiss a popup card."""

    @abstractmethod
    def snooze(self, card_id: str, minutes: int) -> None:
        """Snooze a popup card for N minutes."""

    @abstractmethod
    def health(self) -> str:
        """Return health status."""
