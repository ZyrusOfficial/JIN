"""Memory store port — SQLite + embeddings, encrypted at rest.

Memory tiers: working, episodic, semantic, profile. Sensitive categories
(health, finances, credentials) are not stored unless explicitly requested.
Raw message retention default 14 days.
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass
class MemoryItem:
    id: str
    tier: str  # working | episodic | semantic | profile
    content: str
    embedding: list[float] | None
    created_at: datetime
    sensitive: bool = False
    expires_at: datetime | None = None


@runtime_checkable
class MemoryStore(Protocol):
    @abstractmethod
    def write(self, item: MemoryItem) -> str:
        """Write a memory item, return its id."""

    @abstractmethod
    def read(self, item_id: str) -> MemoryItem | None:
        """Read a memory item by id."""

    @abstractmethod
    def search(
        self, query_embedding: list[float], tier: str | None, limit: int
    ) -> list[MemoryItem]:
        """Vector search for similar memories."""

    @abstractmethod
    def delete(self, item_id: str) -> bool:
        """Delete a memory item ('forget this' removes fact + derived data)."""

    @abstractmethod
    def expire_raw_messages(self, older_than: datetime) -> int:
        """Expire raw messages older than the retention window. Return count deleted."""
