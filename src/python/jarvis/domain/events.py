"""Event envelope and event types — the universal input format for JARVIS.

All sources (user, messenger, calendar, news, system) produce events that
conform to this versioned envelope. The envelope is the contract between
adapters and the domain layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class EventEnvelope:
    """Versioned event envelope — all sources use this format."""

    id: str
    source: str  # messenger|sms|calendar|news|system|user
    type: str  # message.received, calendar.event.created, news.item.published, etc.
    time: datetime
    payload: dict[str, Any] = field(default_factory=dict)
    importance_hint: float = 0.0  # 0..1, source-supplied hint
    sensitive: bool = False
    dedupe_key: str | None = None
    thread_id: str | None = None
    envelope_version: str = "1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "type": self.type,
            "time": self.time.isoformat(),
            "payload": self.payload,
            "importance_hint": self.importance_hint,
            "sensitive": self.sensitive,
            "dedupe_key": self.dedupe_key,
            "thread_id": self.thread_id,
            "envelope_version": self.envelope_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EventEnvelope:
        return cls(
            id=data["id"],
            source=data["source"],
            type=data["type"],
            time=datetime.fromisoformat(data["time"]),
            payload=data.get("payload", {}),
            importance_hint=data.get("importance_hint", 0.0),
            sensitive=data.get("sensitive", False),
            dedupe_key=data.get("dedupe_key"),
            thread_id=data.get("thread_id"),
            envelope_version=data.get("envelope_version", "1"),
        )


@dataclass(frozen=True)
class Event:
    """A domain event — envelope plus any domain-specific metadata added by the bus."""

    envelope: EventEnvelope
    received_at: datetime
    bus_id: str

    @property
    def id(self) -> str:
        return self.envelope.id

    @property
    def source(self) -> str:
        return self.envelope.source

    @property
    def type(self) -> str:
        return self.envelope.type

    @property
    def time(self) -> datetime:
        return self.envelope.time

    @property
    def payload(self) -> dict[str, Any]:
        return self.envelope.payload

    @property
    def importance_hint(self) -> float:
        return self.envelope.importance_hint

    @property
    def sensitive(self) -> bool:
        return self.envelope.sensitive

    @property
    def dedupe_key(self) -> str | None:
        return self.envelope.dedupe_key

    @property
    def thread_id(self) -> str | None:
        return self.envelope.thread_id
