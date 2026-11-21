"""Approval models — standing rules and approval records for the policy gate.

These are pure domain models with zero platform dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class ApprovalScope(Enum):
    """Scope of an approval — what it covers."""

    CONTACT = "contact"  # e.g. "contact:Ana" — messages to a specific person
    CALENDAR = "calendar"  # e.g. "calendar:work" — events on a specific calendar
    FILE = "file"  # e.g. "file:/docs" — files in a specific path
    SYSTEM = "system"  # e.g. "system:volume" — system settings
    GLOBAL = "global"  # all actions of a type


@dataclass(frozen=True)
class StandingRule:
    """A narrow standing rule that auto-approves matching actions.

    Standing rules are created by the owner and can be revoked or edited.
    They cannot grant T3 permissions or override the kill switch.
    """

    rule_id: str
    action_prefix: str  # e.g. "send_message" matches all send_message_* actions
    tier: str  # "T0" | "T1" | "T2" | "T3" — rule tier must be >= action tier
    scope: str  # e.g. "contact:Ana" or "calendar:work"
    expires_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_by: str = "owner"
    active: bool = True

    def matches(self, action: str, tier: str, now: datetime | None = None) -> bool:
        """Return True if this standing rule applies to the given action/tier."""
        if not self.active:
            return False
        if self.expires_at is not None:
            check_time = now or datetime.now(UTC)
            if check_time > self.expires_at:
                return False
        # Rule tier must be >= action tier (higher tier rule can approve lower tier action)
        tier_order = {"T0": 0, "T1": 1, "T2": 2, "T3": 3}
        # Normalize tier to string (accepts both str and TrustTier enum)
        rule_tier = self.tier.value if hasattr(self.tier, "value") else str(self.tier)
        action_tier = tier.value if hasattr(tier, "value") else str(tier)
        if tier_order.get(rule_tier, 0) < tier_order.get(action_tier, 0):
            return False
        if not action.startswith(self.action_prefix):
            return False
        return True


@dataclass(frozen=True)
class ApprovalRecord:
    """A recorded approval for a specific action."""

    action_id: str
    approver: str  # "owner" or a standing rule id
    scope: str
    tier: str
    expires_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    revoked: bool = False

    def is_valid(self, now: datetime | None = None) -> bool:
        """Return True if this approval is still valid (not expired, not revoked)."""
        if self.revoked:
            return False
        if self.expires_at is not None:
            check_time = now or datetime.now(UTC)
            if check_time > self.expires_at:
                return False
        return True
