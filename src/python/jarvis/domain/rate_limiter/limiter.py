"""Utterance rate limiter — max 6 unsolicited utterances per hour.

Non-negotiable (section 6.2): max N unsolicited utterances per hour.
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime, timedelta


class UtteranceRateLimiter:
    """Tracks unsolicited utterance rate and enforces a per-hour limit."""

    def __init__(self, max_per_hour: int = 6, window_seconds: float = 3600.0) -> None:
        self._max_per_hour = max_per_hour
        self._window = timedelta(seconds=window_seconds)
        self._utterances: deque[datetime] = deque()

    def is_rate_limited(self, now: datetime | None = None) -> bool:
        """Return True if the rate limit has been reached (no more utterances allowed)."""
        now = now or datetime.now(UTC)
        cutoff = now - self._window
        while self._utterances and self._utterances[0] < cutoff:
            self._utterances.popleft()
        return len(self._utterances) >= self._max_per_hour

    def record(self, now: datetime | None = None) -> None:
        """Record an utterance against the rate limit."""
        now = now or datetime.now(UTC)
        self._utterances.append(now)

    def remaining(self, now: datetime | None = None) -> int:
        """Return remaining utterances allowed in the current window."""
        now = now or datetime.now(UTC)
        cutoff = now - self._window
        while self._utterances and self._utterances[0] < cutoff:
            self._utterances.popleft()
        return max(0, self._max_per_hour - len(self._utterances))

    def reset(self) -> None:
        """Clear all recorded utterances (for testing or reset)."""
        self._utterances.clear()

    def set_max_per_hour(self, max_per_hour: int) -> None:
        """Change the maximum utterances per hour."""
        self._max_per_hour = max_per_hour
