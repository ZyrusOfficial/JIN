"""Logic-flow tests: Capability Forge with hard guardrails."""

from jarvis.domain.capability_forge import (
    CapabilityForge,
    CapabilityTier,
    ForgeState,
)
from jarvis.fakes import FakeAuditLog


def _make_forge() -> tuple[CapabilityForge, FakeAuditLog]:
    audit_log = FakeAuditLog()
    forge = CapabilityForge(audit_log=audit_log)
    return forge, audit_log


def test_discover_gap_creates_record() -> None:
    """Discovering a gap creates a DISCOVERED record."""
    forge, audit_log = _make_forge()

    record = forge.discover_gap(
        capability_id="cap-weather",
        name="Weather Capability",
        description="Fetch weather alerts",
        reason="Owner requested weather alerts",
    )
    assert record.state == ForgeState.DISCOVERED
    assert record.manifest.tier == CapabilityTier.T0
    assert record.manifest.author == "forge"

    # Audit log should record the discovery
    assert any(e.action == "forge_gap_discovered" for e in audit_log.entries)


def test_source_existing_from_mcp() -> None:
    """Sourcing an existing capability from MCP registry."""
    forge, _ = _make_forge()

    forge.discover_gap(
        capability_id="cap-weather",
        name="Weather Capability",
        description="Fetch weather alerts",
        reason="Owner requested",
    )
    record = forge.source_existing(
        capability_id="cap-weather",
        mcp_server_url="http://localhost:8090",
        capability_name="weather",
        reason="Found in MCP registry",
    )
    assert record.state == ForgeState.SOURCED


def test_author_new_with_guardrails() -> None:
    """Authoring a new capability respects tier guardrails."""
    forge, _ = _make_forge()

    forge.discover_gap(
        capability_id="cap-calendar",
        name="Calendar Capability",
        description="Calendar read/write",
        reason="Owner needs calendar access",
    )
    forge.source_existing(
        capability_id="cap-calendar",
        mcp_server_url="http://localhost:8090",
        capability_name="calendar",
        reason="Sourced",
    )

    record = forge.author_new(
        capability_id="cap-calendar",
        source_code="def run(): pass",
        tier=CapabilityTier.T2,
        network_allowlist=["https://calendar.google.com"],
        secrets_required=["calendar_oauth_token"],
        permissions=["calendar:read", "calendar:write"],
        reason="Owner-authored calendar capability",
    )
    assert record.state == ForgeState.AUTHORED
    assert record.manifest.tier == CapabilityTier.T2
    assert "calendar:read" in record.manifest.permissions


def test_cannot_reauthor_after_authored() -> None:
    """Cannot call author_new on an already-authored capability."""
    forge, _ = _make_forge()

    forge.discover_gap(
        capability_id="cap-test",
        name="Test Capability",
        description="Test",
        reason="Test",
    )
    forge.author_new(
        capability_id="cap-test",
        source_code="def run(): pass",
        tier=CapabilityTier.T0,
        network_allowlist=[],
        secrets_required=[],
        permissions=[],
        reason="Initial author",
    )

    # Re-authoring should fail because state is AUTHORED
    try:
        forge.author_new(
            capability_id="cap-test",
            source_code="def run(): pass",
            tier=CapabilityTier.T2,
            network_allowlist=[],
            secrets_required=[],
            permissions=[],
            reason="Re-author attempt",
        )
        assert False, "Should have raised ValueError"
    except ValueError as exc:
        assert "state is authored" in str(exc)


def test_cannot_be_t3_without_justification() -> None:
    """T3 tier requires explicit owner justification."""
    forge, _ = _make_forge()

    forge.discover_gap(
        capability_id="cap-t3",
        name="T3 Capability",
        description="T3",
        reason="No justification",
    )

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
    except ValueError as exc:
        assert "owner justification" in str(exc)


def test_static_review_blocks_dangerous_calls() -> None:
    """Static review blocks capabilities with dangerous calls."""
    forge, audit_log = _make_forge()

    forge.discover_gap(
        capability_id="cap-dangerous",
        name="Dangerous Capability",
        description="Dangerous",
        reason="Test",
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
        reason="Dangerous call detected",
    )
    assert record.state == ForgeState.REVIEWED
    assert any("DANGEROUS CALLS" in n for n in record.review_notes)

    # Audit log should record denial
    denied = [e for e in audit_log.entries if e.result == "denied"]
    assert len(denied) >= 1


def test_static_review_blocks_obfuscation() -> None:
    """Static review blocks obfuscated code."""
    forge, _ = _make_forge()

    forge.discover_gap(
        capability_id="cap-obfuscated",
        name="Obfuscated Capability",
        description="Obfuscated",
        reason="Test",
    )
    forge.author_new(
        capability_id="cap-obfuscated",
        source_code="eval(base64.b64decode('...'))",
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
        reason="Obfuscation detected",
    )
    assert any("OBFUSCATION DETECTED" in n for n in record.review_notes)


def test_static_review_blocks_undeclared_access() -> None:
    """Static review blocks undeclared network access."""
    forge, _ = _make_forge()

    forge.discover_gap(
        capability_id="cap-undeclared",
        name="Undeclared Access",
        description="Undeclared",
        reason="Test",
    )
    forge.author_new(
        capability_id="cap-undeclared",
        source_code="def run(): pass",
        tier=CapabilityTier.T0,
        network_allowlist=["https://allowed.com"],
        secrets_required=[],
        permissions=[],
        reason="Test",
    )

    record = forge.static_review(
        capability_id="cap-undeclared",
        dangerous_calls_found=[],
        undeclared_access=["https://evil.com"],
        obfuscation_detected=False,
        reason="Undeclared access",
    )
    assert any("UNDECLARED ACCESS" in n for n in record.review_notes)


def test_permission_diff_shows_changes() -> None:
    """Permission diff correctly shows added/removed permissions."""
    forge, _ = _make_forge()

    forge.discover_gap(
        capability_id="cap-diff",
        name="Diff Capability",
        description="Diff test",
        reason="Test",
    )
    forge.author_new(
        capability_id="cap-diff",
        source_code="def run(): pass",
        tier=CapabilityTier.T0,
        network_allowlist=["https://a.com"],
        secrets_required=["secret-a"],
        permissions=["perm-a"],
        reason="Test",
    )

    diff = forge.permission_diff(
        capability_id="cap-diff",
        new_permissions=["perm-a", "perm-b"],
        new_network_allowlist=["https://a.com", "https://b.com"],
        new_secrets=["secret-a", "secret-b"],
        new_tier=CapabilityTier.T0,
    )
    assert "perm-b" in diff.added_permissions
    assert "https://b.com" in diff.changed_network_allowlist
    assert "secret-b" in diff.added_secrets
    assert diff.tier_change is None  # same tier


def test_permission_diff_rejects_tier_increase() -> None:
    """Permission diff rejects tier increases."""
    forge, _ = _make_forge()

    forge.discover_gap(
        capability_id="cap-tier",
        name="Tier Capability",
        description="Tier test",
        reason="Test",
    )
    forge.author_new(
        capability_id="cap-tier",
        source_code="def run(): pass",
        tier=CapabilityTier.T0,
        network_allowlist=[],
        secrets_required=[],
        permissions=[],
        reason="Test",
    )

    try:
        forge.permission_diff(
            capability_id="cap-tier",
            new_permissions=[],
            new_network_allowlist=[],
            new_secrets=[],
            new_tier=CapabilityTier.T2,
        )
        assert False, "Should have raised ValueError"
    except ValueError as exc:
        assert "cannot raise tier" in str(exc).lower()


def test_approve_and_install() -> None:
    """Approve and install flow works correctly."""
    forge, _ = _make_forge()

    forge.discover_gap(
        capability_id="cap-install",
        name="Install Capability",
        description="Install test",
        reason="Test",
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

    record = forge.approve_installation(
        capability_id="cap-install",
        approver="owner",
        reason="Owner approved",
    )
    assert record.state == ForgeState.APPROVED

    record = forge.install(
        capability_id="cap-install",
        install_path="/opt/jarvis/capabilities/cap-install",
        reason="Installed",
    )
    assert record.state == ForgeState.INSTALLED
    assert record.install_path == "/opt/jarvis/capabilities/cap-install"
    assert record.rollback_available


def test_activate_and_revoke() -> None:
    """Activate and revoke flow works correctly."""
    forge, _ = _make_forge()

    forge.discover_gap(
        capability_id="cap-activate",
        name="Activate Capability",
        description="Activate test",
        reason="Test",
    )
    forge.author_new(
        capability_id="cap-activate",
        source_code="def run(): pass",
        tier=CapabilityTier.T0,
        network_allowlist=[],
        secrets_required=[],
        permissions=[],
        reason="Test",
    )
    forge.static_review(
        capability_id="cap-activate",
        dangerous_calls_found=[],
        undeclared_access=[],
        obfuscation_detected=False,
        reason="Clean",
    )
    forge.approve_installation(
        capability_id="cap-activate",
        approver="owner",
        reason="Approved",
    )
    forge.install(
        capability_id="cap-activate",
        install_path="/opt/jarvis/capabilities/cap-activate",
        reason="Installed",
    )

    record = forge.activate(
        capability_id="cap-activate",
        reason="Activated",
    )
    assert record.state == ForgeState.ACTIVE
    assert forge.is_active("cap-activate")

    record = forge.revoke(
        capability_id="cap-activate",
        reason="Owner revoked",
    )
    assert record.state == ForgeState.REVOKED
    assert not forge.is_active("cap-activate")


def test_rollback_restores_previous_manifest() -> None:
    """Rollback restores the previous manifest."""
    forge, _ = _make_forge()

    forge.discover_gap(
        capability_id="cap-rollback",
        name="Rollback Capability",
        description="Rollback test",
        reason="Test",
    )
    forge.author_new(
        capability_id="cap-rollback",
        source_code="def run(): pass",
        tier=CapabilityTier.T0,
        network_allowlist=["https://a.com"],
        secrets_required=["secret-a"],
        permissions=["perm-a"],
        reason="Test",
    )
    forge.static_review(
        capability_id="cap-rollback",
        dangerous_calls_found=[],
        undeclared_access=[],
        obfuscation_detected=False,
        reason="Clean",
    )
    forge.approve_installation(
        capability_id="cap-rollback",
        approver="owner",
        reason="Approved",
    )
    forge.install(
        capability_id="cap-rollback",
        install_path="/opt/jarvis/capabilities/cap-rollback",
        reason="Installed",
    )
    forge.activate(
        capability_id="cap-rollback",
        reason="Activated",
    )

    # Rollback
    record = forge.rollback(
        capability_id="cap-rollback",
        reason="Failed in production",
    )
    assert record.state == ForgeState.ROLLED_BACK


def test_code_integrity_verification() -> None:
    """Code integrity verification works."""
    forge, _ = _make_forge()

    forge.discover_gap(
        capability_id="cap-integrity",
        name="Integrity Capability",
        description="Integrity test",
        reason="Test",
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

    assert forge.verify_code_integrity("cap-integrity")

    # Tamper with code
    forge._installed_code["cap-integrity"] = "def run(): return 0"  # tampered
    assert not forge.verify_code_integrity("cap-integrity")


def test_audit_log_records_forge_actions() -> None:
    """Every forge action is recorded in the audit log."""
    forge, audit_log = _make_forge()

    forge.discover_gap(
        capability_id="cap-audit",
        name="Audit Capability",
        description="Audit test",
        reason="Test",
    )

    actions = [e.action for e in audit_log.entries]
    assert "forge_gap_discovered" in actions

    # Every entry should have a reason
    for entry in audit_log.entries:
        assert entry.reason, f"Audit entry {entry.action} missing reason"


def test_forbidden_permissions_blocked() -> None:
    """Forbidden permissions (policy_gate, core_code, tier:raise) are blocked."""
    forge, _ = _make_forge()

    forge.discover_gap(
        capability_id="cap-forbidden",
        name="Forbidden Capability",
        description="Forbidden test",
        reason="Test",
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
    except ValueError as exc:
        assert "forbidden" in str(exc).lower()
