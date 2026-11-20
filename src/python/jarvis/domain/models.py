"""Core domain models — enums and value objects used across the domain layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class InterruptLevel(Enum):
    """Proactive interrupt levels — from the brief section 6.2."""

    L1_LOW = "L1"  # queue for idle or briefing
    L2_NORMAL = "L2"  # next natural pause
    L3_CRITICAL = "L3"  # speak now, even over music


class Sensitivity(Enum):
    """Content sensitivity — controls whether content may be spoken on speakers."""

    PUBLIC = "public"  # safe to speak anywhere
    PRIVATE = "private"  # not on speakers unless allowed
    CONFIDENTIAL = "confidential"  # never on speakers, headphones only


class ImportanceHint(Enum):
    """Source-supplied importance hints (0..1)."""

    MINIMAL = 0.0
    LOW = 0.25
    MEDIUM = 0.5
    HIGH = 0.75
    CRITICAL = 1.0


@dataclass(frozen=True)
class DeliveryDecision:
    """Result of the proactive engine's delivery decision."""

    interrupt_level: InterruptLevel
    should_speak: bool
    should_show_popup: bool
    reason: str
    rate_limited: bool = False
    suppressed_by_context: bool = False
    cooldown_until: datetime | None = None
