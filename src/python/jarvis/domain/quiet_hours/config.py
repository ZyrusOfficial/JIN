"""Quiet hours configuration — time windows when L1/L2 interrupts are suppressed."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, time

_SATURDAY = 5


@dataclass
class QuietHoursConfig:
    """Quiet hours — L1 and L2 interrupts are suppressed during these windows.

    L3 critical interrupts always break through quiet hours.
    """

    enabled: bool = False
    start_time: time = time(22, 0)  # 10 PM
    end_time: time = time(7, 0)  # 7 AM
    timezone: str = "Asia/Manila"
    days_of_week: set[int] = field(default_factory=lambda: set(range(7)))  # 0=Monday
    weekend_only: bool = False
    allow_l3: bool = True  # L3 always breaks through

    def is_quiet(self, now: datetime | None = None) -> bool:
        """Return True if the given time is within quiet hours."""
        if not self.enabled:
            return False

        now = now or datetime.now(UTC)
        # Convert to the configured timezone (simplified — assumes UTC offset)
        # In production, use zoneinfo for proper timezone handling
        local_time = now.time()
        weekday = now.weekday()

        # Check day of week
        if self.weekend_only and weekday < _SATURDAY:
            return False
        if weekday not in self.days_of_week:
            return False

        # Check time window
        if self.start_time <= self.end_time:
            # Same-day window (e.g. 22:00 to 07:00 next day)
            return self.start_time <= local_time or local_time <= self.end_time
        # Overnight window (e.g. 22:00 to 07:00)
        return self.start_time <= local_time or local_time <= self.end_time

    def allows_level(self, level: str, now: datetime | None = None) -> bool:
        """Return True if the given interrupt level is allowed during quiet hours."""
        if level == "L3" and self.allow_l3:
            return True
        if level in ("L1", "L2"):
            return not self.is_quiet(now)
        return True  # Unknown levels allowed
