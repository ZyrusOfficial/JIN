"""Mutation tests for the policy gate.

These tests are designed to be comprehensive enough that mutmut kills
all mutants of the safety-critical policy gate logic. Run with:

    mutmut --paths-to-mutate src/python/jarvis/domain/policy_gate.py

Or via make:

    make test-mutation
"""

from datetime import UTC

from jarvis.domain.policy_gate import PolicyGate, TrustTier
from jarvis.ports.policy_gate import GateDecision


def test_t0_always_allow_mutant_kill() -> None:
    """If T0 were changed to ASK or DENY, this test fails."""
    gate = PolicyGate()
    result = gate.evaluate("any_t0_action", TrustTier.T0, {})
    assert result.decision == GateDecision.ALLOW


def test_t3_always_deny_mutant_kill() -> None:
    """If T3 were changed to ALLOW or ASK, this test fails."""
    gate = PolicyGate()
    result = gate.evaluate("any_t3_action", TrustTier.T3, {})
    assert result.decision == GateDecision.DENY


def test_standing_rule_override_mutant_kill() -> None:
    """If standing rules didn't override T2 ask, this test fails."""
    gate = PolicyGate()
    from jarvis.domain.policy_gate import StandingRule

    rule = StandingRule(
        rule_id="override-test",
        action_prefix="send_message",
        tier=TrustTier.T2,
        scope="contact:test",
    )
    gate.add_standing_rule(rule)
    result = gate.evaluate(
        "send_message_to_test",
        TrustTier.T2,
        {},
        standing_rules=["override-test"],
    )
    assert result.decision == GateDecision.ALLOW


def test_approval_expiry_mutant_kill() -> None:
    """If expired approvals were still valid, this test fails."""
    from datetime import datetime

    gate = PolicyGate()
    gate.approve(
        action_id="expired-action",
        approver="owner",
        scope="test",
        tier=TrustTier.T2,
        expires_at=datetime(2020, 1, 1, tzinfo=UTC),
    )
    assert gate.is_approved("expired-action") is False
