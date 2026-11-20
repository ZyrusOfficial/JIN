"""Contract tests for the PolicyGate port — safety-critical."""

from jarvis.fakes.policy_gate import FakePolicyGate
from jarvis.ports.policy_gate import GateDecision, PolicyGate, TrustTier


def test_fake_gate_implements_port() -> None:
    gate: PolicyGate = FakePolicyGate()
    assert isinstance(gate, PolicyGate)


def test_t0_auto_allowed() -> None:
    gate = FakePolicyGate()
    result = gate.evaluate("format_text", TrustTier.T0, {})
    assert result.decision == GateDecision.ALLOW


def test_t1_requires_ask() -> None:
    gate = FakePolicyGate()
    result = gate.evaluate("read_network", TrustTier.T1, {})
    assert result.decision == GateDecision.ASK


def test_t2_requires_ask() -> None:
    gate = FakePolicyGate()
    result = gate.evaluate("send_message", TrustTier.T2, {})
    assert result.decision == GateDecision.ASK


def test_t3_denied_by_default() -> None:
    gate = FakePolicyGate()
    result = gate.evaluate("change_system_setting", TrustTier.T3, {})
    assert result.decision == GateDecision.DENY


def test_gate_records_evaluation() -> None:
    gate = FakePolicyGate()
    gate.evaluate("test_action", TrustTier.T2, {"key": "value"})
    assert len(gate.evaluations) == 1
    assert gate.evaluations[0]["action"] == "test_action"
    assert gate.evaluations[0]["tier"] == "T2"


def test_approve_and_is_approved() -> None:
    gate = FakePolicyGate()
    gate.approve("action-1", "owner", "send_message", expires_at=None)
    assert gate.is_approved("action-1") is True
    assert gate.is_approved("nonexistent") is False
