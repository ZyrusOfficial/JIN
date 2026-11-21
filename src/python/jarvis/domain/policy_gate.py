"""Real policy gate implementation — deterministic allow/ask/deny with trust tiers.

Non-negotiable (section 3.3, invariant 1): sending, deleting, spending,
installing, or changing permissions requires approval unless a narrow standing
rule exists. The gate lives in deterministic code, never in an LLM prompt.

This is the production implementation (FakePolicyGate remains for tests).
"""

from __future__ import annotations

from datetime import UTC, datetime

from jarvis.domain.approval.models import ApprovalRecord as DomainApprovalRecord
from jarvis.domain.approval.models import StandingRule as DomainStandingRule
from jarvis.ports.policy_gate import GateDecision, GateResult, TrustTier

# Re-export for backward compatibility with tests
StandingRule = DomainStandingRule
ApprovalRecord = DomainApprovalRecord


class PolicyGate:
    """Deterministic policy gate. The LLM proposes; code disposes.

    Tier rules:
      T0: Auto-allow after sandbox tests pass.
      T1: Ask once at install (network read to declared hosts).
      T2: Ask at install + confirm each action unless a narrow standing rule exists.
      T3: Never automatic — explicit approval with second confirmation.
    """

    def __init__(self) -> None:
        self._standing_rules: dict[str, StandingRule] = {}
        self._approvals: dict[str, ApprovalRecord] = {}
        self._evaluation_history: list[dict[str, object]] = []
        self._next_decision: GateDecision | None = None  # override for tests

    # -- Standing rules -------------------------------------------------------

    def add_standing_rule(self, rule: StandingRule) -> None:
        """Register a standing rule that auto-approves matching actions."""
        self._standing_rules[rule.rule_id] = rule

    def remove_standing_rule(self, rule_id: str) -> bool:
        """Remove a standing rule. Returns True if it existed."""
        return self._standing_rules.pop(rule_id, None) is not None

    def list_standing_rules(self) -> list[StandingRule]:
        """Return all active (non-expired) standing rules."""
        now = datetime.now(UTC)
        return [r for r in self._standing_rules.values() if r.matches("dummy", "T0", now)]

    # -- Approvals ------------------------------------------------------------

    def approve(
        self,
        action_id: str,
        approver: str,
        scope: str,
        tier: TrustTier,
        expires_at: datetime | None = None,
    ) -> None:
        """Record an approval for a specific action."""
        self._approvals[action_id] = ApprovalRecord(
            action_id=action_id,
            approver=approver,
            scope=scope,
            tier=tier.value,
            expires_at=expires_at,
        )

    def revoke_approval(self, action_id: str) -> bool:
        """Revoke an approval. Returns True if it existed and was revoked.

        After revocation, the record is removed so subsequent calls return False
        and is_approved returns False.
        """
        record = self._approvals.pop(action_id, None)
        if record is None:
            return False
        return True

    def is_approved(self, action_id: str) -> bool:
        """Check whether an action has a current, non-expired approval."""
        record = self._approvals.get(action_id)
        if record is None:
            return False
        return record.is_valid()

    # -- Evaluation -----------------------------------------------------------

    def evaluate(
        self,
        action: str,
        tier: TrustTier,
        context: dict[str, object],
        standing_rules: list[str] | None = None,
    ) -> GateResult:
        """Evaluate an action and return allow/ask/deny with a reason.

        Decision logic (deterministic code, never LLM):
          - T0 -> ALLOW (pure computation, local reads)
          - T1 -> ASK (network read, approve once at install)
          - T2 -> ASK unless matching standing rule exists -> ALLOW
          - T3 -> DENY (never automatic, needs explicit + second confirmation)
        """
        now = datetime.now(UTC)
        rules = standing_rules or []

        # Check for matching standing rule (can override T2 ask)
        standing_rule_id: str | None = None
        for rule_id in rules:
            rule = self._standing_rules.get(rule_id)
            if rule is None:
                continue
            if not rule.matches(action, tier.value, now):
                continue
            standing_rule_id = rule_id
            break

        # Determine decision
        if self._next_decision is not None:
            decision = self._next_decision
            self._next_decision = None  # consume override
        elif tier == TrustTier.T0:
            decision = GateDecision.ALLOW
        elif tier == TrustTier.T1:
            decision = GateDecision.ASK
        elif tier == TrustTier.T2:
            if standing_rule_id is not None:
                decision = GateDecision.ALLOW
            else:
                decision = GateDecision.ASK
        else:  # T3
            decision = GateDecision.DENY

        requires_approval = decision == GateDecision.ASK

        reason = self._build_reason(action, tier, decision, standing_rule_id)

        result = GateResult(
            decision=decision,
            tier=tier,
            reason=reason,
            requires_approval=requires_approval,
            standing_rule_id=standing_rule_id,
        )

        self._evaluation_history.append(
            {
                "action": action,
                "tier": tier.value,
                "context": context,
                "standing_rules": rules,
                "decision": decision.value,
                "standing_rule_id": standing_rule_id,
                "timestamp": now.isoformat(),
            }
        )

        return result

    def set_next_decision(self, decision: GateDecision) -> None:
        """Override the next evaluation's decision (for testing)."""
        self._next_decision = decision

    def _build_reason(
        self,
        action: str,
        tier: TrustTier,
        decision: GateDecision,
        standing_rule_id: str | None,
    ) -> str:
        if standing_rule_id:
            return f"{decision.value}: {action} (tier {tier.value}, rule {standing_rule_id})"
        return f"{decision.value}: {action} (tier {tier.value})"

    # -- Inspection -----------------------------------------------------------

    def evaluation_history(self) -> list[dict[str, object]]:
        """Return all evaluations (for test assertions)."""
        return list(self._evaluation_history)

    def clear_history(self) -> None:
        """Clear evaluation history (for test isolation)."""
        self._evaluation_history.clear()
