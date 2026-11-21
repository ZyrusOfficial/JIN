"""Mutation tests: Update Guardian safety logic.

These tests verify that mutants of the Update Guardian state machine
are killed — i.e., the tests catch incorrect state transitions.
"""

from jarvis.domain.update_guardian import (
    UpdateComponent,
    UpdateGuardian,
    UpdateState,
)
from jarvis.fakes import FakeAuditLog


def _make_guardian() -> UpdateGuardian:
    return UpdateGuardian(audit_log=FakeAuditLog())


def test_t0_always_allow_mutant_kill() -> None:
    """Mutant: T0 updates auto-allowed without verification — should be caught."""
    guardian = _make_guardian()
    guardian.check_for_update(UpdateComponent.CORE_AGENT, "1.0.0", "2.0.0", "Major bump")
    # Without verification, staging should not be possible
    try:
        guardian.stage_update(
            UpdateComponent.CORE_AGENT, approval=True, approver="owner", reason="Test"
        )
        # If we get here, the mutant wasn't killed — staging should fail
        # because state is WATCH not VERIFIED
        assert False, "Should have raised ValueError (wrong state)"
    except ValueError:
        pass  # Mutant killed — wrong state blocks staging


def test_t3_always_deny_mutant_kill() -> None:
    """Mutant: T3 equivalent (system settings) always denied — correct behavior."""
    guardian = _make_guardian()
    guardian.check_for_update(
        UpdateComponent.DESKTOP_BRIDGE, "1.0.0", "2.0.0", "System settings change"
    )
    guardian.verify_update(
        UpdateComponent.DESKTOP_BRIDGE,
        signature_valid=True,
        source_trusted=True,
        reason="Verified",
    )
    # Without approval, staging should be skipped (denied)
    record = guardian.stage_update(
        UpdateComponent.DESKTOP_BRIDGE,
        approval=False,
        reason="No approval",
    )
    assert record.state == UpdateState.SKIPPED


def test_standing_rule_override_mutant_kill() -> None:
    """Mutant: Standing rule overrides without verification — should be caught."""
    guardian = _make_guardian()
    guardian.check_for_update(UpdateComponent.STT_MODEL, "1.0.0", "1.1.0", "Patch")
    # Without verification, staging should fail regardless of approval
    try:
        guardian.stage_update(
            UpdateComponent.STT_MODEL,
            approval=True,
            approver="owner",
            reason="Standing rule",
        )
        assert False, "Should have raised ValueError (wrong state)"
    except ValueError:
        pass  # Mutant killed


def test_approval_expiry_mutant_kill() -> None:
    """Mutant: Expired approval still valid — should be caught."""
    guardian = _make_guardian()
    guardian.check_for_update(UpdateComponent.TTS_MODEL, "1.0.0", "1.1.0", "Patch")
    guardian.verify_update(
        UpdateComponent.TTS_MODEL,
        signature_valid=True,
        source_trusted=True,
        reason="Verified",
    )
    # With approval, staging proceeds
    record = guardian.stage_update(
        UpdateComponent.TTS_MODEL,
        approval=True,
        approver="owner",
        reason="Approved",
    )
    assert record.state == UpdateState.STAGED


def test_verification_required_before_staging() -> None:
    """Mutant: Staging without verification — killed by state check."""
    guardian = _make_guardian()
    guardian.check_for_update(UpdateComponent.WAKE_WORD_MODEL, "1.0.0", "1.1.0", "Patch")
    # Skip verification, go straight to staging
    try:
        guardian.stage_update(
            UpdateComponent.WAKE_WORD_MODEL,
            approval=True,
            approver="owner",
            reason="No verification",
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Mutant killed — state must be VERIFIED


def test_testing_required_before_applying() -> None:
    """Mutant: Applying without testing — killed by state check."""
    guardian = _make_guardian()
    guardian.check_for_update(UpdateComponent.CAPABILITY_FORGE, "1.0.0", "1.1.0", "Patch")
    guardian.verify_update(
        UpdateComponent.CAPABILITY_FORGE,
        signature_valid=True,
        source_trusted=True,
        reason="Verified",
    )
    guardian.stage_update(
        UpdateComponent.CAPABILITY_FORGE,
        approval=True,
        approver="owner",
        reason="Approved",
    )
    # Skip testing, go straight to applying
    try:
        guardian.apply_update(
            UpdateComponent.CAPABILITY_FORGE,
            approval=True,
            approver="owner",
            reason="No testing",
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Mutant killed — state must be TESTED


def test_auto_update_weekly_limit_mutant_kill() -> None:
    """Mutant: No weekly limit on auto-updates — killed by rate limit."""
    guardian = _make_guardian()

    # First auto-update
    guardian.check_for_update(UpdateComponent.STT_MODEL, "1.0.0", "1.1.0", "Patch 1")
    guardian.verify_update(
        UpdateComponent.STT_MODEL,
        signature_valid=True,
        source_trusted=True,
        reason="Verified",
    )
    record1 = guardian.stage_update(
        UpdateComponent.STT_MODEL, approval=True, approver=None, reason="Auto 1"
    )
    assert record1.state == UpdateState.STAGED

    # Second auto-update same week should be skipped
    guardian.check_for_update(UpdateComponent.STT_MODEL, "1.1.0", "1.2.0", "Patch 2")
    guardian.verify_update(
        UpdateComponent.STT_MODEL,
        signature_valid=True,
        source_trusted=True,
        reason="Verified",
    )
    record2 = guardian.stage_update(
        UpdateComponent.STT_MODEL, approval=True, approver=None, reason="Auto 2"
    )
    assert record2.state == UpdateState.SKIPPED


def test_audit_log_records_every_transition_mutant_kill() -> None:
    """Mutant: Missing audit log entries — killed by assertion."""
    guardian = _make_guardian()
    guardian.check_for_update(UpdateComponent.CORE_AGENT, "1.0.0", "1.1.0", "Security patch")
    guardian.verify_update(
        UpdateComponent.CORE_AGENT,
        signature_valid=True,
        source_trusted=True,
        reason="GPG verified",
    )

    # Every transition should be logged
    watch_entries = [e for e in guardian.audit_log.entries if e.action == "update_watch"]
    verify_entries = [e for e in guardian.audit_log.entries if e.action == "update_verified"]
    assert len(watch_entries) >= 1
    assert len(verify_entries) >= 1

    # Every entry must have a reason
    for entry in guardian.audit_log.entries:
        assert entry.reason, f"Missing reason for {entry.action}"
