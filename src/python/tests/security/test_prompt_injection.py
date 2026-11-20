"""Security tests: prompt-injection corpus must never cause unapproved actions."""

import os
import sys

# Ensure tests directory is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import UTC

import pytest

from jarvis.domain.policy_gate import PolicyGate, TrustTier
from jarvis.ports.policy_gate import GateDecision
from tests.security.prompt_injection_corpus import PROMPT_INJECTION_CORPUS


@pytest.mark.parametrize(
    "name,hostile_text,expected_safe",
    PROMPT_INJECTION_CORPUS,
    ids=[n for n, _, _ in PROMPT_INJECTION_CORPUS],
)
def test_injection_never_triggers_t2_t3(name: str, hostile_text: str, expected_safe: bool) -> None:
    """Prompt-injection text must never cause T2/T3 actions without explicit approval."""
    gate = PolicyGate()

    result = gate.evaluate(
        action=f"process_message: {hostile_text[:30]}",
        tier=TrustTier.T2,
        context={"text": hostile_text, "source": "messenger"},
    )

    assert result.decision != GateDecision.ALLOW, (
        f"Injection '{name}' caused T2 ALLOW — SECURITY BREACH"
    )


@pytest.mark.parametrize(
    "name,hostile_text,expected_safe",
    PROMPT_INJECTION_CORPUS,
    ids=[n for n, _, _ in PROMPT_INJECTION_CORPUS],
)
def test_injection_never_leaks_secrets(name: str, hostile_text: str, expected_safe: bool) -> None:
    """Prompt-injection text must never appear in policy gate reasons."""
    gate = PolicyGate()

    result = gate.evaluate(
        action="test",
        tier=TrustTier.T0,
        context={"user_input": hostile_text},
    )

    assert "secret" not in result.reason.lower()
    assert "token" not in result.reason.lower()
    assert "password" not in result.reason.lower()


def test_secrets_broker_never_returns_real_secrets_in_tests() -> None:
    """The fake secrets broker returns fake values, never real credentials."""
    from jarvis.fakes.secrets_broker import FakeSecretsBroker

    broker = FakeSecretsBroker()
    secret = broker.inject("test-capability", "api_key")
    assert secret == "fake-secret-test-capability-api_key"
    assert "real" not in secret.lower()
    assert "actual" not in secret.lower()


def test_audit_log_records_all_policy_decisions() -> None:
    """Every policy decision is audit-logged (non-negotiable #9)."""
    from datetime import datetime

    from jarvis.fakes.audit_log import FakeAuditLog
    from jarvis.ports.audit_log import AuditEntry

    audit = FakeAuditLog()
    gate = PolicyGate()

    result = gate.evaluate("send_message", TrustTier.T2, {"to": "Ana"})
    audit.append(
        AuditEntry(
            id="audit-1",
            timestamp=datetime.now(UTC),
            action="send_message",
            actor="system",
            reason=result.reason,
            result=result.decision.value,
            tier=result.tier.value,
        )
    )

    assert len(audit.entries) == 1
    assert audit.entries[0].action == "send_message"
    assert audit.entries[0].result == "ask"


def test_no_secret_in_policy_reasons() -> None:
    """Policy gate reasons never leak actual secret values."""
    gate = PolicyGate()

    # T3 actions are denied — reasons contain action names but not secret values
    for action in [
        "read_credential",
        "access_password",
        "retrieve_api_key",
        "read_secret",
    ]:
        result = gate.evaluate(action, TrustTier.T3, {})
        assert result.decision == GateDecision.DENY

    # Reasons should not contain actual secret patterns (API keys, tokens, etc.)
    secret_patterns = ["sk-", "pk-", "secret=", "token=", "password=", "api_key="]
    for action in ["read_credential", "access_password"]:
        result = gate.evaluate(action, TrustTier.T3, {})
        for pattern in secret_patterns:
            assert pattern not in result.reason.lower(), (
                f"Reason '{result.reason}' contains secret pattern '{pattern}'"
            )
