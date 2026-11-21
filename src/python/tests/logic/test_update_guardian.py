"""Logic-flow tests: Update Guardian state machine."""

from jarvis.domain.update_guardian import (
    UpdateComponent,
    UpdateGuardian,
    UpdateState,
)
from jarvis.fakes import FakeAuditLog


def _make_guardian() -> tuple[UpdateGuardian, FakeAuditLog]:
    audit_log = FakeAuditLog()
    guardian = UpdateGuardian(audit_log=audit_log)
    return guardian, audit_log


def test_watch_transitions_to_verified() -> None:
    """Watch → verified when signature and source are valid."""
    guardian, audit_log = _make_guardian()

    record = guardian.check_for_update(
        UpdateComponent.CORE_AGENT,
        "1.0.0",
        "1.1.0",
        "Security patch available",
    )
    assert record.state == UpdateState.WATCH

    record = guardian.verify_update(
        UpdateComponent.CORE_AGENT,
        signature_valid=True,
        source_trusted=True,
        reason="Verified via GPG signature",
    )
    assert record.state == UpdateState.VERIFIED

    # Audit log should have entries
    entries = audit_log.entries
    assert any(e.action == "update_watch" for e in entries)
    assert any(e.action == "update_verified" for e in entries)


def test_verification_failed_goes_to_skipped() -> None:
    """Verification failure → skipped."""
    guardian, _ = _make_guardian()

    guardian.check_for_update(
        UpdateComponent.STT_MODEL,
        "2.0.0",
        "2.1.0",
        "New model available",
    )
    record = guardian.verify_update(
        UpdateComponent.STT_MODEL,
        signature_valid=False,
        source_trusted=True,
        reason="Invalid signature",
    )
    assert record.state == UpdateState.SKIPPED


def test_staging_requires_approval_for_major() -> None:
    """Major version change requires T2 approval."""
    guardian, audit_log = _make_guardian()

    guardian.check_for_update(
        UpdateComponent.CORE_AGENT,
        "1.0.0",
        "2.0.0",
        "Major version bump",
    )
    guardian.verify_update(
        UpdateComponent.CORE_AGENT,
        signature_valid=True,
        source_trusted=True,
        reason="Verified",
    )

    # Without approval → skipped
    record = guardian.stage_update(
        UpdateComponent.CORE_AGENT,
        approval=False,
        reason="No approval",
    )
    assert record.state == UpdateState.SKIPPED

    # Audit log should show denial
    denied_entries = [e for e in audit_log.entries if e.result == "denied"]
    assert len(denied_entries) >= 1


def test_staging_with_approval_proceeds() -> None:
    """With T2 approval, staging proceeds."""
    guardian, _ = _make_guardian()

    guardian.check_for_update(
        UpdateComponent.CORE_AGENT,
        "1.0.0",
        "2.0.0",
        "Major version bump",
    )
    guardian.verify_update(
        UpdateComponent.CORE_AGENT,
        signature_valid=True,
        source_trusted=True,
        reason="Verified",
    )

    record = guardian.stage_update(
        UpdateComponent.CORE_AGENT,
        approval=True,
        approver="owner",
        reason="Owner approved T2 update",
    )
    assert record.state == UpdateState.STAGED
    assert record.approved_by == "owner"


def test_test_passed_moves_to_tested() -> None:
    """Successful sandbox test → tested."""
    guardian, _ = _make_guardian()

    guardian.check_for_update(
        UpdateComponent.TTS_MODEL,
        "1.0.0",
        "1.1.0",
        "Minor version",
    )
    guardian.verify_update(
        UpdateComponent.TTS_MODEL,
        signature_valid=True,
        source_trusted=True,
        reason="Verified",
    )
    guardian.stage_update(
        UpdateComponent.TTS_MODEL,
        approval=True,
        approver="owner",
        reason="Approved",
    )

    record = guardian.test_update(
        UpdateComponent.TTS_MODEL,
        test_passed=True,
        reason="Sandbox tests passed",
    )
    assert record.state == UpdateState.TESTED


def test_test_failed_max_attempts_goes_to_skipped() -> None:
    """Max test attempts exceeded → skipped."""
    guardian, _ = _make_guardian()

    guardian.check_for_update(
        UpdateComponent.WAKE_WORD_MODEL,
        "1.0.0",
        "1.1.0",
        "Update available",
    )
    guardian.verify_update(
        UpdateComponent.WAKE_WORD_MODEL,
        signature_valid=True,
        source_trusted=True,
        reason="Verified",
    )
    guardian.stage_update(
        UpdateComponent.WAKE_WORD_MODEL,
        approval=True,
        approver="owner",
        reason="Approved",
    )

    # Fail tests 3 times (max_attempts=3)
    for i in range(3):
        record = guardian.test_update(
            UpdateComponent.WAKE_WORD_MODEL,
            test_passed=False,
            reason=f"Test failure {i + 1}",
        )

    assert record.state == UpdateState.SKIPPED


def test_apply_requires_approval() -> None:
    """Applying update requires T2 confirmation."""
    guardian, _ = _make_guardian()

    guardian.check_for_update(
        UpdateComponent.DESKTOP_BRIDGE,
        "1.0.0",
        "1.1.0",
        "Patch",
    )
    guardian.verify_update(
        UpdateComponent.DESKTOP_BRIDGE,
        signature_valid=True,
        source_trusted=True,
        reason="Verified",
    )
    guardian.stage_update(
        UpdateComponent.DESKTOP_BRIDGE,
        approval=True,
        approver="owner",
        reason="Approved",
    )
    guardian.test_update(
        UpdateComponent.DESKTOP_BRIDGE,
        test_passed=True,
        reason="Tested",
    )

    # Without confirmation → skipped
    record = guardian.apply_update(
        UpdateComponent.DESKTOP_BRIDGE,
        approval=False,
        reason="No confirmation",
    )
    assert record.state == UpdateState.SKIPPED


def test_apply_with_confirmation_goes_to_applied() -> None:
    """With T2 confirmation, update is applied."""
    guardian, _ = _make_guardian()

    guardian.check_for_update(
        UpdateComponent.ANDROID_COMPANION,
        "1.0.0",
        "1.1.0",
        "Patch",
    )
    guardian.verify_update(
        UpdateComponent.ANDROID_COMPANION,
        signature_valid=True,
        source_trusted=True,
        reason="Verified",
    )
    guardian.stage_update(
        UpdateComponent.ANDROID_COMPANION,
        approval=True,
        approver="owner",
        reason="Approved",
    )
    guardian.test_update(
        UpdateComponent.ANDROID_COMPANION,
        test_passed=True,
        reason="Tested",
    )

    record = guardian.apply_update(
        UpdateComponent.ANDROID_COMPANION,
        approval=True,
        approver="owner",
        reason="Owner confirmed",
    )
    assert record.state == UpdateState.APPLIED


def test_healthy_transition_after_health_check() -> None:
    """Health check passed → healthy."""
    guardian, _ = _make_guardian()

    guardian.check_for_update(
        UpdateComponent.CAPABILITY_FORGE,
        "1.0.0",
        "1.1.0",
        "Patch",
    )
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
    guardian.test_update(
        UpdateComponent.CAPABILITY_FORGE,
        test_passed=True,
        reason="Tested",
    )
    guardian.apply_update(
        UpdateComponent.CAPABILITY_FORGE,
        approval=True,
        approver="owner",
        reason="Confirmed",
    )

    record = guardian.confirm_healthy(
        UpdateComponent.CAPABILITY_FORGE,
        health_check_passed=True,
        reason="Health check passed",
    )
    assert record.state == UpdateState.HEALTHY


def test_rollback_on_failed_health_check() -> None:
    """Failed health check → rolled back."""
    guardian, _ = _make_guardian()

    guardian.check_for_update(
        UpdateComponent.CORE_AGENT,
        "1.0.0",
        "1.1.0",
        "Patch",
    )
    guardian.verify_update(
        UpdateComponent.CORE_AGENT,
        signature_valid=True,
        source_trusted=True,
        reason="Verified",
    )
    guardian.stage_update(
        UpdateComponent.CORE_AGENT,
        approval=True,
        approver="owner",
        reason="Approved",
    )
    guardian.test_update(
        UpdateComponent.CORE_AGENT,
        test_passed=True,
        reason="Tested",
    )
    guardian.apply_update(
        UpdateComponent.CORE_AGENT,
        approval=True,
        approver="owner",
        reason="Confirmed",
    )

    record = guardian.confirm_healthy(
        UpdateComponent.CORE_AGENT,
        health_check_passed=False,
        reason="Health check failed",
    )
    assert record.state == UpdateState.ROLLED_BACK


def test_auto_update_weekly_limit() -> None:
    """Max one auto-update per component per week."""
    guardian, _ = _make_guardian()

    # First auto-update (no approver = auto-approved via standing rule)
    guardian.check_for_update(
        UpdateComponent.STT_MODEL,
        "1.0.0",
        "1.1.0",
        "Patch 1",
    )
    guardian.verify_update(
        UpdateComponent.STT_MODEL,
        signature_valid=True,
        source_trusted=True,
        reason="Verified",
    )
    record1 = guardian.stage_update(
        UpdateComponent.STT_MODEL,
        approval=True,  # auto-approved
        approver=None,
        reason="Auto-update 1",
    )
    assert record1.state == UpdateState.STAGED

    # Second auto-update same component same week → should be skipped
    guardian.check_for_update(
        UpdateComponent.STT_MODEL,
        "1.1.0",
        "1.2.0",
        "Patch 2",
    )
    guardian.verify_update(
        UpdateComponent.STT_MODEL,
        signature_valid=True,
        source_trusted=True,
        reason="Verified",
    )
    record2 = guardian.stage_update(
        UpdateComponent.STT_MODEL,
        approval=True,
        approver=None,
        reason="Auto-update 2",
    )
    assert record2.state == UpdateState.SKIPPED


def test_get_record_and_state() -> None:
    """get_record and get_state work correctly."""
    guardian, _ = _make_guardian()

    assert guardian.get_record(UpdateComponent.CORE_AGENT) is None
    assert guardian.get_state(UpdateComponent.CORE_AGENT) is None

    guardian.check_for_update(
        UpdateComponent.CORE_AGENT,
        "1.0.0",
        "1.1.0",
        "Test",
    )
    record = guardian.get_record(UpdateComponent.CORE_AGENT)
    assert record is not None
    assert record.state == UpdateState.WATCH
    assert guardian.is_in_state(UpdateComponent.CORE_AGENT, UpdateState.WATCH)


def test_all_components_covered() -> None:
    """All UpdateComponent enum values are testable."""
    guardian, _ = _make_guardian()

    for component in UpdateComponent:
        guardian.check_for_update(
            component,
            "1.0.0",
            "1.1.0",
            f"Update for {component.value}",
        )
        record = guardian.get_record(component)
        assert record is not None
        assert record.component == component


def test_audit_log_records_every_transition() -> None:
    """Every state transition is recorded in the audit log with 'why'."""
    guardian, audit_log = _make_guardian()

    guardian.check_for_update(
        UpdateComponent.CORE_AGENT,
        "1.0.0",
        "1.1.0",
        "Security patch",
    )
    guardian.verify_update(
        UpdateComponent.CORE_AGENT,
        signature_valid=True,
        source_trusted=True,
        reason="GPG verified",
    )
    guardian.stage_update(
        UpdateComponent.CORE_AGENT,
        approval=True,
        approver="owner",
        reason="Owner approved",
    )

    actions = [e.action for e in audit_log.entries]
    assert "update_watch" in actions
    assert "update_verified" in actions
    assert "update_staged" in actions

    # Every entry should have a non-empty reason
    for entry in audit_log.entries:
        assert entry.reason, f"Audit entry {entry.action} missing reason"
        assert entry.result, f"Audit entry {entry.action} missing result"
