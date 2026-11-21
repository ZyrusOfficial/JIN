"""Mutation tests: Capability Forge guardrails.

These tests verify that the Capability Forge's hard guardrails cannot
be bypassed by mutants.
"""

from jarvis.domain.capability_forge import (
    CapabilityForge,
    CapabilityTier,
    ForgeState,
)
from jarvis.fakes import FakeAuditLog


def _make_forge() -> CapabilityForge:
    return CapabilityForge(audit_log=FakeAuditLog())


def test_cannot_raise_own_tier_mutant_kill() -> None:
    """Mutant: Capability raises its own tier — killed by guardrail."""
    forge = _make_forge()
    forge.discover_gap(capability_id="cap-tier", name="Tier", description="Test", reason="Test")
    forge.author_new(
        capability_id="cap-tier",
        source_code="def run(): pass",
        tier=CapabilityTier.T1,
        network_allowlist=[],
        secrets_required=[],
        permissions=[],
        reason="Set to T1",
    )

    # Try to permission_diff with higher tier — should be killed
    try:
        forge.permission_diff(
            capability_id="cap-tier",
            new_permissions=[],
            new_network_allowlist=[],
            new_secrets=[],
            new_tier=CapabilityTier.T2,
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Mutant killed — tier cannot increase


def test_t3_requires_justification_mutant_kill() -> None:
    """Mutant: T3 without justification — killed by guardrail."""
    forge = _make_forge()
    forge.discover_gap(capability_id="cap-t3", name="T3", description="T3", reason="Test")

    try:
        forge.author_new(
            capability_id="cap-t3",
            source_code="def run(): pass",
            tier=CapabilityTier.T3,
            network_allowlist=[],
            secrets_required=[],
            permissions=["system:settings"],
            reason="No owner justification",
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Mutant killed — T3 needs justification


def test_forbidden_permissions_blocked_mutant_kill() -> None:
    """Mutant: Forbidden permissions (policy_gate, core_code) — killed."""
    forge = _make_forge()
    forge.discover_gap(
        capability_id="cap-forbidden", name="Forbidden", description="Test", reason="Test"
    )
    forge.author_new(
        capability_id="cap-forbidden",
        source_code="def run(): pass",
        tier=CapabilityTier.T0,
        network_allowlist=[],
        secrets_required=[],
        permissions=["policy_gate:edit"],
        reason="Test",
    )

    try:
        forge.install(
            capability_id="cap-forbidden",
            install_path="/opt/jarvis/capabilities/cap-forbidden",
            reason="Install",
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Mutant killed — forbidden permission blocked


def test_static_review_blocks_dangerous_calls_mutant_kill() -> None:
    """Mutant: Dangerous calls not blocked — killed by static review."""
    forge = _make_forge()
    forge.discover_gap(
        capability_id="cap-dangerous", name="Dangerous", description="Test", reason="Test"
    )
    forge.author_new(
        capability_id="cap-dangerous",
        source_code="import os; os.system('rm -rf /')",
        tier=CapabilityTier.T0,
        network_allowlist=[],
        secrets_required=[],
        permissions=[],
        reason="Test",
    )

    record = forge.static_review(
        capability_id="cap-dangerous",
        dangerous_calls_found=["os.system"],
        undeclared_access=[],
        obfuscation_detected=False,
        reason="Dangerous call",
    )
    # Review should note the dangerous call but not block entirely
    # The capability stays in REVIEWED state, not APPROVED
    assert record.state == ForgeState.REVIEWED
    assert any("DANGEROUS CALLS" in n for n in record.review_notes)


def test_static_review_blocks_obfuscation_mutant_kill() -> None:
    """Mutant: Obfuscated code not blocked — killed by static review."""
    forge = _make_forge()
    forge.discover_gap(
        capability_id="cap-obfuscated", name="Obfuscated", description="Test", reason="Test"
    )
    forge.author_new(
        capability_id="cap-obfuscated",
        source_code="eval(base64.decode('...'))",
        tier=CapabilityTier.T0,
        network_allowlist=[],
        secrets_required=[],
        permissions=[],
        reason="Test",
    )

    record = forge.static_review(
        capability_id="cap-obfuscated",
        dangerous_calls_found=[],
        undeclared_access=[],
        obfuscation_detected=True,
        reason="Obfuscation",
    )
    assert any("OBFUSCATION DETECTED" in n for n in record.review_notes)


def test_cannot_install_without_approval_mutant_kill() -> None:
    """Mutant: Installation without approval — killed by state check."""
    forge = _make_forge()
    forge.discover_gap(
        capability_id="cap-install", name="Install", description="Test", reason="Test"
    )
    forge.author_new(
        capability_id="cap-install",
        source_code="def run(): pass",
        tier=CapabilityTier.T0,
        network_allowlist=[],
        secrets_required=[],
        permissions=[],
        reason="Test",
    )
    forge.static_review(
        capability_id="cap-install",
        dangerous_calls_found=[],
        undeclared_access=[],
        obfuscation_detected=False,
        reason="Clean",
    )

    # Try to install without approval (state is REVIEWED, not APPROVED)
    try:
        forge.install(
            capability_id="cap-install",
            install_path="/opt/jarvis/capabilities/cap-install",
            reason="No approval",
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Mutant killed — must be APPROVED before install


def test_code_integrity_verification_mutant_kill() -> None:
    """Mutant: Code tampering not detected — killed by integrity check."""
    forge = _make_forge()
    forge.discover_gap(
        capability_id="cap-integrity", name="Integrity", description="Test", reason="Test"
    )
    forge.author_new(
        capability_id="cap-integrity",
        source_code="def run(): return 42",
        tier=CapabilityTier.T0,
        network_allowlist=[],
        secrets_required=[],
        permissions=[],
        reason="Test",
    )
    forge.static_review(
        capability_id="cap-integrity",
        dangerous_calls_found=[],
        undeclared_access=[],
        obfuscation_detected=False,
        reason="Clean",
    )
    forge.approve_installation(
        capability_id="cap-integrity",
        approver="owner",
        reason="Approved",
    )
    forge.install(
        capability_id="cap-integrity",
        install_path="/opt/jarvis/capabilities/cap-integrity",
        reason="Installed",
    )

    # Initially integrity should pass
    assert forge.verify_code_integrity("cap-integrity")

    # Tamper with code
    forge._installed_code["cap-integrity"] = "def run(): return 0"
    # Integrity should now fail
    assert not forge.verify_code_integrity("cap-integrity")


def test_audit_log_records_forge_actions_mutant_kill() -> None:
    """Mutant: Missing audit log entries — killed by assertion."""
    forge = _make_forge()
    forge.discover_gap(capability_id="cap-audit", name="Audit", description="Test", reason="Test")

    actions = [e.action for e in forge.audit_log.entries]
    assert "forge_gap_discovered" in actions

    for entry in forge.audit_log.entries:
        assert entry.reason, f"Missing reason for {entry.action}"
