"""Property tests: policy gate — no sequence of calls reaches T2/T3 behavior without approval."""

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from jarvis.domain.policy_gate import PolicyGate, StandingRule, TrustTier
from jarvis.ports.policy_gate import GateDecision

# Strategies for generating random actions and tiers
action_strategy = st.text(
    min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N", "P", "S"))
)
tier_strategy = st.sampled_from(list(TrustTier))
context_strategy = st.dictionaries(
    st.text(min_size=1, max_size=10), st.text(min_size=0, max_size=20)
)


@given(
    action=action_strategy,
    tier=tier_strategy,
    context=context_strategy,
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_no_t2_t3_without_approval(action: str, tier: TrustTier, context: dict) -> None:
    """Property: T2/T3 actions never auto-allow without standing rule or approval."""
    gate = PolicyGate()
    result = gate.evaluate(action, tier, context)

    if tier == TrustTier.T0:
        assert result.decision == GateDecision.ALLOW
    elif tier == TrustTier.T1:
        assert result.decision == GateDecision.ASK
    elif tier == TrustTier.T2:
        # Without standing rules, T2 always requires ask
        assert result.decision == GateDecision.ASK
    elif tier == TrustTier.T3:
        assert result.decision == GateDecision.DENY


@given(
    action=action_strategy,
    context=context_strategy,
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_standing_rule_can_override_t2(action: str, context: dict) -> None:
    """Property: A matching standing rule with sufficient tier allows T2."""
    gate = PolicyGate()
    rule = StandingRule(
        rule_id="test-rule",
        action_prefix=action[:3] if len(action) >= 3 else action,
        tier=TrustTier.T2,
        scope="test",
    )
    gate.add_standing_rule(rule)

    result = gate.evaluate(
        f"{action}_suffix",
        TrustTier.T2,
        context,
        standing_rules=["test-rule"],
    )

    if action[:3] == rule.action_prefix or action.startswith(rule.action_prefix):
        assert result.decision == GateDecision.ALLOW
        assert result.standing_rule_id == "test-rule"


@given(
    action_id=st.text(min_size=1, max_size=30),
    approver=st.text(min_size=1, max_size=20),
    scope=st.text(min_size=1, max_size=20),
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_approval_roundtrip(action_id: str, approver: str, scope: str) -> None:
    """Property: Approve then is_approved returns True; revoke then False."""
    gate = PolicyGate()
    assert gate.is_approved(action_id) is False

    gate.approve(action_id, approver, scope, TrustTier.T2)
    assert gate.is_approved(action_id) is True

    assert gate.revoke_approval(action_id) is True
    assert gate.is_approved(action_id) is False

    # Revoking again returns False
    assert gate.revoke_approval(action_id) is False


@given(
    tier=tier_strategy,
    context=context_strategy,
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_every_evaluation_has_reason(tier: TrustTier, context: dict) -> None:
    """Property: Every gate result has a non-empty reason string."""
    gate = PolicyGate()
    result = gate.evaluate("test_action", tier, context)
    assert isinstance(result.reason, str)
    assert len(result.reason) > 0
    assert result.tier == tier


@given(
    tier=tier_strategy,
    context=context_strategy,
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_t3_never_allows(tier: TrustTier, context: dict) -> None:
    """Property: T3 decisions are never ALLOW (only ASK or DENY, but default is DENY)."""
    gate = PolicyGate()
    result = gate.evaluate("test_action", tier, context)

    if tier == TrustTier.T3:
        assert result.decision != GateDecision.ALLOW
        assert result.decision == GateDecision.DENY
