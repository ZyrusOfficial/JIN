"""News source port — RSS/Atom/CAP feeds for alerts and news."""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass
class NewsItem:
    id: str
    title: str
    summary: str
    source_name: str
    url: str
    published_at: datetime
    sensitivity_hint: float = 0.0  # 0..1, higher = more likely breaking
    official: bool = False  # True if from an official agency (PAGASA, PHIVOLCS, etc.)
    raw: dict[str, object] = field(default_factory=dict)


@runtime_checkable
class NewsSource(Protocol):
    @abstractmethod
    def fetch(self, since: datetime | None = None) -> list[NewsItem]:
        """Fetch news items since a timestamp."""

    @abstractmethod
    def health(self) -> str:
        """Return health status."""
