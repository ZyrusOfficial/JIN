"""Learning loop — tracks owner responses to proactive items and adjusts scores.

Records listened, replied, snoozed, dismissed actions per source/contact and
adjusts importance scores accordingly. Exposes adjustments in settings with undo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class OwnerAction(StrEnum):
    """Owner response types to proactive items."""

    LISTENED = "listened"  # owner listened to the full message
    REPLIED = "replied"  # owner replied to the message
    SNOOZED = "snoozed"  # owner snoozed the item
    DISMISSED = "dismissed"  # owner dismissed without acting
    IGNORED = "ignored"  # owner let it expire without response


@dataclass
class ResponseRecord:
    """A single owner response to a proactive item."""

    source: str
    contact_id: str | None
    action: OwnerAction
    timestamp: datetime
    interrupt_level: str  # "L1" | "L2" | "L3"
    was_helpful: bool | None = None  # explicit feedback if provided


class LearningLoop:
    """Adjusts per-contact and per-source importance scores based on owner behavior."""

    def __init__(self, learning_rate: float = 0.1) -> None:
        self._learning_rate = learning_rate
        self._contact_scores: dict[str, float] = {}  # contact_id -> 0..1 score
        self._source_scores: dict[str, float] = {}  # source -> 0..1 score
        self._history: list[ResponseRecord] = []

    def record_response(
        self,
        source: str,
        action: OwnerAction,
        contact_id: str | None = None,
        interrupt_level: str = "L2",
        was_helpful: bool | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """Record an owner response and update scores."""
        now = timestamp or datetime.now(UTC)
        record = ResponseRecord(
            source=source,
            contact_id=contact_id,
            action=action,
            timestamp=now,
            interrupt_level=interrupt_level,
            was_helpful=was_helpful,
        )
        self._history.append(record)
        self._adjust_scores(record)

    def _adjust_scores(self, record: ResponseRecord) -> None:
        """Adjust scores based on the owner's response."""
        # Positive actions increase scores, negative actions decrease
        if record.action == OwnerAction.REPLIED:
            delta = self._learning_rate
        elif record.action == OwnerAction.LISTENED:
            delta = self._learning_rate * 0.5
        elif record.action == OwnerAction.SNOOZED:
            delta = -self._learning_rate * 0.3
        elif record.action == OwnerAction.DISMISSED:
            delta = -self._learning_rate
        else:  # IGNORED
            delta = -self._learning_rate * 0.2

        # Update source score
        if record.source:
            current = self._source_scores.get(record.source, 0.5)
            self._source_scores[record.source] = max(0.0, min(1.0, current + delta))

        # Update contact score
        if record.contact_id:
            current = self._contact_scores.get(record.contact_id, 0.5)
            self._contact_scores[record.contact_id] = max(0.0, min(1.0, current + delta))

    def get_contact_score(self, contact_id: str) -> float:
        """Return the learned importance score for a contact (0..1)."""
        return self._contact_scores.get(contact_id, 0.5)

    def get_source_score(self, source: str) -> float:
        """Return the learned importance score for a source (0..1)."""
        return self._source_scores.get(source, 0.5)

    def get_history(self) -> list[ResponseRecord]:
        """Return all recorded responses."""
        return list(self._history)

    def undo(self, record_index: int) -> bool:
        """Undo a response at the given index, reverting score adjustments."""
        if record_index < 0 or record_index >= len(self._history):
            return False
        record = self._history.pop(record_index)
        # Revert the adjustment (approximate — we subtract the delta)
        if record.action == OwnerAction.REPLIED:
            delta = -self._learning_rate
        elif record.action == OwnerAction.LISTENED:
            delta = -self._learning_rate * 0.5
        elif record.action == OwnerAction.SNOOZED:
            delta = self._learning_rate * 0.3
        elif record.action == OwnerAction.DISMISSED:
            delta = self._learning_rate
        else:
            delta = self._learning_rate * 0.2

        if record.source:
            current = self._source_scores.get(record.source, 0.5)
            self._source_scores[record.source] = max(0.0, min(1.0, current + delta))
        if record.contact_id:
            current = self._contact_scores.get(record.contact_id, 0.5)
            self._contact_scores[record.contact_id] = max(0.0, min(1.0, current + delta))
        return True

    def set_learning_rate(self, rate: float) -> None:
        """Set the learning rate (0..1)."""
        self._learning_rate = max(0.0, min(1.0, rate))
