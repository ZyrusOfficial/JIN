"""Cooldown manager — tracks cooldown periods for actions and events.

Prevents rapid-fire repetition of the same action (e.g. speaking the same
alert multiple times in quick succession).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass
class CooldownEntry:
    """A single cooldown entry."""

    key: str
    expires_at: datetime
    count: int = 1  # how many times this cooldown has been triggered


class CooldownManager:
    """Manages cooldown periods for actions.

    Each action key has a cooldown duration. While a cooldown is active,
    the action is suppressed. After the cooldown expires, the action can
    proceed again.
    """

    def __init__(self, default_duration_seconds: float = 300.0) -> None:
        self._default_duration = default_duration_seconds
        self._cooldowns: dict[str, CooldownEntry] = {}
        self._custom_durations: dict[str, float] = {}

    def set_duration(self, key: str, duration_seconds: float) -> None:
        """Set a custom cooldown duration for a specific key."""
        self._custom_durations[key] = duration_seconds

    def _duration_for(self, key: str) -> float:
        return self._custom_durations.get(key, self._default_duration)

    def is_cooled_down(self, key: str, now: datetime | None = None) -> bool:
        """Return True if the key is not in cooldown (can proceed)."""
        now = now or datetime.now(UTC)
        entry = self._cooldowns.get(key)
        if entry is None:
            return True
        return now > entry.expires_at

    def start_cooldown(
        self,
        key: str,
        now: datetime | None = None,
        duration_seconds: float | None = None,
    ) -> datetime:
        """Start (or extend) a cooldown for the key. Returns the expiry time."""
        now = now or datetime.now(UTC)
        duration = duration_seconds or self._duration_for(key)
        expires_at = now + timedelta(seconds=duration)

        existing = self._cooldowns.get(key)
        if existing is None:
            self._cooldowns[key] = CooldownEntry(key=key, expires_at=expires_at, count=1)
        else:
            # Extend the cooldown and increment count
            new_expires = max(existing.expires_at, expires_at)
            self._cooldowns[key] = CooldownEntry(
                key=key,
                expires_at=new_expires,
                count=existing.count + 1,
            )
        return expires_at

    def remaining_seconds(self, key: str, now: datetime | None = None) -> float:
        """Return seconds remaining in the cooldown, or 0 if not in cooldown."""
        now = now or datetime.now(UTC)
        entry = self._cooldowns.get(key)
        if entry is None:
            return 0.0
        remaining = (entry.expires_at - now).total_seconds()
        return max(0.0, remaining)

    def clear(self, key: str) -> bool:
        """Clear the cooldown for a key. Returns True if it existed."""
        return self._cooldowns.pop(key, None) is not None

    def clear_all(self) -> None:
        """Clear all cooldowns."""
        self._cooldowns.clear()

    def keys(self) -> list[str]:
        """Return all keys currently in cooldown."""
        now = datetime.now(UTC)
        return [k for k, v in self._cooldowns.items() if now < v.expires_at]
