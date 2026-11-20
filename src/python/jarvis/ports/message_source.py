"""Message source port — Messenger/SMS inbound and outbound (draft + confirm + send).

Non-negotiable (section 3.3, invariant 1): every outgoing message requires
approval unless a narrow standing rule exists.
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Protocol, runtime_checkable


class MessageDirection(Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageStatus(Enum):
    RECEIVED = "received"
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    SENT = "sent"
    FAILED = "failed"


@dataclass
class MessageEvent:
    id: str
    source: str  # messenger | sms
    thread_id: str
    from_contact: str
    text: str
    direction: MessageDirection
    status: MessageStatus
    timestamp: datetime
    sensitive: bool = False
    partial: bool = False  # True when notification was truncated
    has_image: bool = False
    image_url: str | None = None
    dedupe_key: str | None = None
    raw: dict[str, object] = field(default_factory=dict)


@dataclass
class Draft:
    thread_id: str
    text: str
    to_contact: str
    requires_approval: bool = True


@dataclass
class SendResult:
    accepted: bool
    message_id: str | None
    error: str | None = None


@runtime_checkable
class MessageSource(Protocol):
    @abstractmethod
    def events(self) -> list[MessageEvent]:
        """Return pending inbound message events."""

    @abstractmethod
    def fetch_thread(self, thread_id: str, since: datetime | None = None) -> list[MessageEvent]:
        """Fetch message history for a thread."""

    @abstractmethod
    def draft_reply(self, thread_id: str, text: str) -> Draft:
        """Draft a reply (never sends)."""

    @abstractmethod
    def send(self, draft: Draft, approval: bool) -> SendResult:
        """Send a draft, requires gate approval."""

    @abstractmethod
    def health(self) -> str:
        """Return health status."""
