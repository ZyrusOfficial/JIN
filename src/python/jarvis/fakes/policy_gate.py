"""Fake policy gate for tests — deterministic allow/ask/deny with recording."""

from datetime import datetime

from jarvis.ports.policy_gate import (
    GateDecision,
    GateResult,
    PolicyGate,
    TrustTier,
)


class FakePolicyGate(PolicyGate):
    """Records all evaluations and approvals for test assertions."""

    def __init__(self) -> None:
        self.evaluations: list[dict[str, object]] = []
        self.approvals: dict[str, dict[str, object]] = {}
        self.next_decision: GateDecision | None = None  # override for tests

    def evaluate(
        self,
        action: str,
        tier: TrustTier,
        context: dict[str, object],
        standing_rules: list[str] | None = None,
    ) -> GateResult:
        decision = self.next_decision or self._default_decision(tier, standing_rules or [])
        result = GateResult(
            decision=decision,
            tier=tier,
            reason=f"fake gate: {decision.value} for {action} (tier {tier.value})",
            requires_approval=decision == GateDecision.ASK,
            standing_rule_id=None,
        )
        self.evaluations.append(
            {
                "action": action,
                "tier": tier.value,
                "context": context,
                "standing_rules": standing_rules or [],
                "decision": decision.value,
            }
        )
        return result

    def _default_decision(self, tier: TrustTier, standing_rules: list[str]) -> GateDecision:
        if tier == TrustTier.T0:
            return GateDecision.ALLOW
        if tier == TrustTier.T1:
            return GateDecision.ASK
        if tier == TrustTier.T2:
            return GateDecision.ASK
        return GateDecision.DENY

    def approve(
        self,
        action_id: str,
        approver: str,
        scope: str,
        expires_at: datetime | None = None,
    ) -> None:
        self.approvals[action_id] = {
            "approver": approver,
            "scope": scope,
            "expires_at": expires_at,
        }

    def is_approved(self, action_id: str) -> bool:
        return action_id in self.approvals
