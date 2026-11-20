"""Audit log port — tamper-evident local log with a 'why' for every action.

Non-negotiable (section 3.3, invariant 9): everything Jarvis does is logged
to a local, tamper-evident audit log with a 'why'.
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass
class AuditEntry:
    id: str
    timestamp: datetime
    action: str
    actor: str  # "system", "llm", "owner", "capability"
    reason: str  # the "why"
    result: str  # "allowed", "denied", "asked", "completed", "failed"
    tier: str | None = None
    sensitive: bool = False


@runtime_checkable
class AuditLog(Protocol):
    @abstractmethod
    def append(self, entry: AuditEntry) -> None:
        """Append an audit entry (append-only, tamper-evident)."""

    @abstractmethod
    def query(
        self,
        action: str | None = None,
        actor: str | None = None,
        since: datetime | None = None,
    ) -> list[AuditEntry]:
        """Query audit entries."""
