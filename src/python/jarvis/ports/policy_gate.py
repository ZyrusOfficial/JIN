"""Policy gate port — deterministic allow/ask/deny with trust tiers.

Non-negotiable (section 3.3, invariant 1): sending, deleting, spending,
installing, or changing permissions requires approval unless a narrow standing
rule exists. The gate lives in deterministic code, never in an LLM prompt.
"""

from __future__ import annotations

from abc import abstractmethod
from datetime import UTC, datetime
from enum import Enum
from typing import Protocol, runtime_checkable


class TrustTier(Enum):
    T0 = "T0"  # pure computation, local non-sensitive reads
    T1 = "T1"  # network read to declared hosts
    T2 = "T2"  # writes, sends messages, calendar/file edits
    T3 = "T3"  # credentials, payments, system settings, security tools, self-edits


class GateDecision(Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


class GateResult:
    def __init__(
        self,
        decision: GateDecision,
        tier: TrustTier,
        reason: str,
        requires_approval: bool,
        standing_rule_id: str | None = None,
    ) -> None:
        self.decision = decision
        self.tier = tier
        self.reason = reason
        self.requires_approval = requires_approval
        self.standing_rule_id = standing_rule_id
        self.timestamp = datetime.now(UTC)


@runtime_checkable
class PolicyGate(Protocol):
    """Deterministic policy gate. The LLM proposes; code disposes."""

    @abstractmethod
    def evaluate(
        self,
        action: str,
        tier: TrustTier,
        context: dict[str, object],
        standing_rules: list[str] | None = None,
    ) -> GateResult:
        """Evaluate an action and return allow/ask/deny with a reason."""

    @abstractmethod
    def approve(
        self,
        action_id: str,
        approver: str,
        scope: str,
        expires_at: datetime | None = None,
    ) -> None:
        """Record an approval for a specific action."""

    @abstractmethod
    def is_approved(self, action_id: str) -> bool:
        """Check whether an action has a current approval."""
