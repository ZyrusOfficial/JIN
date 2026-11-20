"""Logic-flow tests: policy gate — the safety-critical deterministic gate."""

from datetime import UTC, datetime

from jarvis.domain.policy_gate import PolicyGate, StandingRule, TrustTier
from jarvis.ports.policy_gate import GateDecision


def test_t0_auto_allow() -> None:
    """T0 actions (pure computation) are always auto-allowed."""
    gate = PolicyGate()
    result = gate.evaluate("format_text", TrustTier.T0, {})
    assert result.decision == GateDecision.ALLOW
    assert result.requires_approval is False


def test_t1_requires_ask() -> None:
    """T1 actions (network read) require ask."""
    gate = PolicyGate()
    result = gate.evaluate("fetch_weather", TrustTier.T1, {})
    assert result.decision == GateDecision.ASK
    assert result.requires_approval is True


def test_t2_requires_ask_without_standing_rule() -> None:
    """T2 actions (send message) require ask unless standing rule."""
    gate = PolicyGate()
    result = gate.evaluate("send_message", TrustTier.T2, {})
    assert result.decision == GateDecision.ASK


def test_t2_allowed_with_matching_standing_rule() -> None:
    """T2 actions are allowed if a matching standing rule exists."""
    gate = PolicyGate()
    rule = StandingRule(
        rule_id="msg-to-ana",
        action_prefix="send_message",
        tier=TrustTier.T2,
        scope="contact:Ana",
    )
    gate.add_standing_rule(rule)

    result = gate.evaluate(
        "send_message_to_Ana",
        TrustTier.T2,
        {},
        standing_rules=["msg-to-ana"],
    )
    assert result.decision == GateDecision.ALLOW
    assert result.standing_rule_id == "msg-to-ana"


def test_t2_not_allowed_with_wrong_scope_standing_rule() -> None:
    """Standing rule with wrong action prefix doesn't match."""
    gate = PolicyGate()
    rule = StandingRule(
        rule_id="msg-to-ana",
        action_prefix="send_email",  # different prefix
        tier=TrustTier.T2,
        scope="contact:Ana",
    )
    gate.add_standing_rule(rule)

    result = gate.evaluate(
        "send_message_to_Ana",
        TrustTier.T2,
        {},
        standing_rules=["msg-to-ana"],
    )
    assert result.decision == GateDecision.ASK


def test_t3_never_auto() -> None:
    """T3 actions (credentials, system settings) are never auto-allowed."""
    gate = PolicyGate()
    result = gate.evaluate("change_system_setting", TrustTier.T3, {})
    assert result.decision == GateDecision.DENY


def test_standing_rule_expires() -> None:
    """Expired standing rules don't apply."""
    gate = PolicyGate()
    rule = StandingRule(
        rule_id="temp-rule",
        action_prefix="send_message",
        tier=TrustTier.T2,
        scope="contact:Ana",
        expires_at=datetime(2020, 1, 1, tzinfo=UTC),  # long expired
    )
    gate.add_standing_rule(rule)

    result = gate.evaluate(
        "send_message_to_Ana",
        TrustTier.T2,
        {},
        standing_rules=["temp-rule"],
    )
    assert result.decision == GateDecision.ASK  # expired rule doesn't apply


def test_approval_record_and_check() -> None:
    """Approvals can be recorded and checked."""
    gate = PolicyGate()
    gate.approve(
        action_id="action-1",
        approver="owner",
        scope="send_message",
        tier=TrustTier.T2,
    )
    assert gate.is_approved("action-1") is True
    assert gate.is_approved("nonexistent") is False


def test_approval_expiry() -> None:
    """Approvals can expire."""
    gate = PolicyGate()
    gate.approve(
        action_id="action-1",
        approver="owner",
        scope="send_message",
        tier=TrustTier.T2,
        expires_at=datetime(2020, 1, 1, tzinfo=UTC),
    )
    assert gate.is_approved("action-1") is False


def test_revoke_approval() -> None:
    """Approvals can be revoked."""
    gate = PolicyGate()
    gate.approve("action-1", "owner", "send_message", TrustTier.T2)
    assert gate.is_approved("action-1") is True
    assert gate.revoke_approval("action-1") is True
    assert gate.is_approved("action-1") is False


def test_evaluation_history_recorded() -> None:
    """Every evaluation is recorded for audit."""
    gate = PolicyGate()
    gate.evaluate("test_action", TrustTier.T2, {"key": "value"})
    history = gate.evaluation_history()
    assert len(history) == 1
    assert history[0]["action"] == "test_action"
    assert history[0]["tier"] == "T2"
    assert history[0]["decision"] == "ask"


def test_gate_returns_allow_ask_deny_with_reason() -> None:
    """Gate always returns a decision with a reason string."""
    gate = PolicyGate()
    for tier in TrustTier:
        result = gate.evaluate("test", tier, {})
        assert result.decision in (GateDecision.ALLOW, GateDecision.ASK, GateDecision.DENY)
        assert isinstance(result.reason, str)
        assert len(result.reason) > 0
