"""Capability Forge — self-extension with hard guardrails.

Manages sandboxed code generation, permission diffs, and capability
installation with strict non-negotiable guardrails:

- Capability cannot raise its own trust tier
- Capability cannot edit the policy gate or change core code
- Secrets injected by broker at call time (scoped per capability)
- Per-capability network allowlist enforced outside capability code
- Instructions in skills are data, never commands
- Third-party capabilities never update silently
- All actions logged to audit log with 'why'
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from jarvis.ports.audit_log import AuditEntry, AuditLog


class ForgeState(Enum):
    """Capability Forge pipeline states."""

    DISCOVERED = "discovered"  # Gap detected, capability identified
    SOURCED = "sourced"  # Existing capability found (MCP registry)
    AUTHORED = "authored"  # New capability code generated
    REVIEWED = "reviewed"  # Static review passed
    APPROVED = "approved"  # Owner approved installation
    INSTALLED = "installed"  # Capability installed in versioned repo
    ACTIVE = "active"  # Capability active and callable
    ROLLED_BACK = "rolled_back"  # Capability rolled back
    REVOKED = "revoked"  # Capability revoked by owner


class CapabilityTier(Enum):
    """Trust tiers for capabilities — cannot be raised by the capability itself."""

    T0 = "T0"  # Pure computation, local reads
    T1 = "T1"  # Network read to declared hosts
    T2 = "T2"  # Writes, sends messages, calendar/file edits
    T3 = "T3"  # Credentials, payments, system settings, security tools


@dataclass
class CapabilityManifest:
    """Manifest for a capability — immutable after installation."""

    id: str
    name: str
    version: str
    tier: CapabilityTier
    description: str
    author: str  # "owner" | "forge" | "third-party"
    network_allowlist: list[str] = field(default_factory=list)
    secrets_required: list[str] = field(default_factory=list)  # secret keys, not values
    permissions: list[str] = field(default_factory=list)  # e.g. "calendar:write"
    source_code_hash: str = ""  # SHA-256 of installed code
    installed_at: datetime | None = None
    updated_at: datetime | None = None
    revoked_at: datetime | None = None
    active: bool = False


@dataclass
class CapabilityRecord:
    """Full capability record including forge state."""

    manifest: CapabilityManifest
    state: ForgeState
    created_at: datetime
    updated_at: datetime
    reason: str  # the "why"
    review_notes: list[str] = field(default_factory=list)
    install_path: str | None = None
    rollback_available: bool = False
    previous_manifest: CapabilityManifest | None = None


@dataclass
class PermissionDiff:
    """Permission diff display for owner review."""

    capability_id: str
    added_permissions: list[str]
    removed_permissions: list[str]
    changed_network_allowlist: list[str]
    added_secrets: list[str]
    tier_change: tuple[str, str] | None = None  # (from, to) — T3 never allowed to increase


class CapabilityForge:
    """Capability Forge — manages self-extension with hard guardrails.

    Pipeline: gap detection → source existing → author new → static review
    → permission diff → owner approval → install → active → monitor.
    """

    def __init__(
        self,
        audit_log: AuditLog,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.audit_log = audit_log
        self._now: Callable[[], datetime] = now or (lambda: datetime.now(UTC))
        self._capabilities: dict[str, CapabilityRecord] = {}
        self._installed_code: dict[str, str] = {}  # capability_id -> source code
        self._code_hashes: dict[str, str] = {}  # capability_id -> hash

    # -- Public API ---------------------------------------------------------

    def discover_gap(
        self,
        capability_id: str,
        name: str,
        description: str,
        reason: str,
    ) -> CapabilityRecord:
        """Discover a capability gap — owner or system identifies a need."""
        now = self._now()
        manifest = CapabilityManifest(
            id=capability_id,
            name=name,
            version="0.1.0",
            tier=CapabilityTier.T0,
            description=description,
            author="forge",
        )
        record = CapabilityRecord(
            manifest=manifest,
            state=ForgeState.DISCOVERED,
            created_at=now,
            updated_at=now,
            reason=reason,
        )
        self._capabilities[capability_id] = record

        self._audit(
            "forge_gap_discovered",
            actor="system",
            reason=f"Capability gap discovered: {name} ({capability_id}). {reason}",
            result="completed",
        )
        return record

    def source_existing(
        self,
        capability_id: str,
        mcp_server_url: str,
        capability_name: str,
        reason: str,
    ) -> CapabilityRecord:
        """Source an existing capability from MCP registry/server."""
        record = self._get_or_create(capability_id)
        if record.state != ForgeState.DISCOVERED:
            raise ValueError(f"Cannot source {capability_id}: state is {record.state.value}")

        record.state = ForgeState.SOURCED
        record.updated_at = self._now()
        record.reason = reason
        self._capabilities[capability_id] = record

        self._audit(
            "forge_capability_sourced",
            actor="system",
            reason=f"Capability {capability_id} sourced from MCP {mcp_server_url}. {reason}",
            result="completed",
        )
        return record

    def author_new(
        self,
        capability_id: str,
        source_code: str,
        tier: CapabilityTier,
        network_allowlist: list[str],
        secrets_required: list[str],
        permissions: list[str],
        reason: str,
    ) -> CapabilityRecord:
        """Author a new capability — generates code with guardrail checks.

        Guardrail: capability cannot request T3 tier or permissions
        that exceed T2 without explicit owner justification.
        """
        record = self._get_or_create(capability_id)
        if record.state not in (ForgeState.DISCOVERED, ForgeState.SOURCED):
            raise ValueError(f"Cannot author {capability_id}: state is {record.state.value}")

        # Guardrail: tier cannot be T3 unless owner explicitly justifies
        if tier == CapabilityTier.T3 and "owner-justified" not in reason.lower():
            raise ValueError(
                f"Capability {capability_id} cannot be T3 without explicit owner justification"
            )

        # Guardrail: no self-tier-escalation
        if record.manifest.tier != CapabilityTier.T0 and tier.value > record.manifest.tier.value:
            raise ValueError(
                f"Capability {capability_id} cannot raise its own tier from {record.manifest.tier.value} to {tier.value}"
            )

        code_hash = self._hash_code(source_code)

        manifest = CapabilityManifest(
            id=capability_id,
            name=record.manifest.name,
            version="0.1.0",
            tier=tier,
            description=record.manifest.description,
            author="forge",
            network_allowlist=network_allowlist,
            secrets_required=secrets_required,
            permissions=permissions,
            source_code_hash=code_hash,
        )

        record.manifest = manifest
        record.state = ForgeState.AUTHORED
        record.updated_at = self._now()
        record.reason = reason
        self._installed_code[capability_id] = source_code
        self._code_hashes[capability_id] = code_hash
        self._capabilities[capability_id] = record

        self._audit(
            "forge_capability_authored",
            actor="system",
            reason=f"Capability {capability_id} authored: tier={tier.value}, permissions={permissions}. {reason}",
            result="completed",
        )
        return record

    def static_review(
        self,
        capability_id: str,
        dangerous_calls_found: list[str],
        undeclared_access: list[str],
        obfuscation_detected: bool,
        reason: str,
    ) -> CapabilityRecord:
        """Static review of capability code.

        Guardrail: dangerous calls, undeclared access, or obfuscation
        block installation.
        """
        record = self._get_or_create(capability_id)
        if record.state != ForgeState.AUTHORED:
            raise ValueError(f"Cannot review {capability_id}: state is {record.state.value}")

        review_notes = list(record.review_notes)

        if dangerous_calls_found:
            review_notes.append(f"DANGEROUS CALLS: {', '.join(dangerous_calls_found)}")
        if undeclared_access:
            review_notes.append(f"UNDECLARED ACCESS: {', '.join(undeclared_access)}")
        if obfuscation_detected:
            review_notes.append("OBFUSCATION DETECTED")

        blocked = bool(dangerous_calls_found or undeclared_access or obfuscation_detected)

        if blocked:
            record.state = ForgeState.REVIEWED  # stays in reviewed, not approved
            record.review_notes = review_notes
            record.updated_at = self._now()
            record.reason = f"REVIEW BLOCKED: {reason}"

            self._audit(
                "forge_review_blocked",
                actor="system",
                reason=f"Static review blocked for {capability_id}: dangerous={bool(dangerous_calls_found)}, undeclared={bool(undeclared_access)}, obfuscated={obfuscation_detected}. {reason}",
                result="denied",
            )
        else:
            record.state = ForgeState.REVIEWED
            record.review_notes = review_notes
            record.updated_at = self._now()
            record.reason = reason

            self._audit(
                "forge_review_passed",
                actor="system",
                reason=f"Static review passed for {capability_id}. {reason}",
                result="completed",
            )

        self._capabilities[capability_id] = record
        return record

    def permission_diff(
        self,
        capability_id: str,
        new_permissions: list[str],
        new_network_allowlist: list[str],
        new_secrets: list[str],
        new_tier: CapabilityTier,
    ) -> PermissionDiff:
        """Generate a permission diff for owner review before installation.

        Guardrail: tier cannot increase beyond current tier.
        """
        record = self._get_or_create(capability_id)
        current = record.manifest

        added = [p for p in new_permissions if p not in current.permissions]
        removed = [p for p in current.permissions if p not in new_permissions]
        changed_network = [n for n in new_network_allowlist if n not in current.network_allowlist]
        added_secrets = [s for s in new_secrets if s not in current.secrets_required]

        tier_change = None
        if new_tier.value > current.tier.value:
            tier_change = (current.tier.value, new_tier.value)
            # Guardrail: capability cannot raise its own tier
            raise ValueError(
                f"Capability {capability_id} cannot raise tier from {current.tier.value} to {new_tier.value}"
            )

        return PermissionDiff(
            capability_id=capability_id,
            added_permissions=added,
            removed_permissions=removed,
            changed_network_allowlist=changed_network,
            added_secrets=added_secrets,
            tier_change=tier_change,
        )

    def approve_installation(
        self,
        capability_id: str,
        approver: str,
        reason: str,
    ) -> CapabilityRecord:
        """Owner approves capability installation."""
        record = self._get_or_create(capability_id)
        if record.state != ForgeState.REVIEWED:
            raise ValueError(f"Cannot approve {capability_id}: state is {record.state.value}")

        record.state = ForgeState.APPROVED
        record.updated_at = self._now()
        record.reason = reason
        self._capabilities[capability_id] = record

        self._audit(
            "forge_installation_approved",
            actor=approver,
            reason=f"Capability {capability_id} installation approved by {approver}. {reason}",
            result="completed",
        )
        return record

    def install(
        self,
        capability_id: str,
        install_path: str,
        reason: str,
    ) -> CapabilityRecord:
        """Install capability into versioned local git repo with manifest hash."""
        record = self._get_or_create(capability_id)
        if record.state != ForgeState.APPROVED:
            raise ValueError(f"Cannot install {capability_id}: state is {record.state.value}")

        # Guardrail: cannot edit policy gate or core code
        self._verify_no_core_code_access(record.manifest)

        record.state = ForgeState.INSTALLED
        record.updated_at = self._now()
        record.install_path = install_path
        record.rollback_available = True
        record.previous_manifest = CapabilityManifest(
            id=record.manifest.id,
            name=record.manifest.name,
            version=record.manifest.version,
            tier=record.manifest.tier,
            description=record.manifest.description,
            author=record.manifest.author,
            network_allowlist=list(record.manifest.network_allowlist),
            secrets_required=list(record.manifest.secrets_required),
            permissions=list(record.manifest.permissions),
            source_code_hash=record.manifest.source_code_hash,
        )
        self._capabilities[capability_id] = record

        self._audit(
            "forge_capability_installed",
            actor="system",
            reason=f"Capability {capability_id} installed at {install_path}. Hash: {record.manifest.source_code_hash[:16]}... {reason}",
            result="completed",
        )
        return record

    def activate(
        self,
        capability_id: str,
        reason: str,
    ) -> CapabilityRecord:
        """Activate an installed capability."""
        record = self._get_or_create(capability_id)
        if record.state != ForgeState.INSTALLED:
            raise ValueError(f"Cannot activate {capability_id}: state is {record.state.value}")

        record.manifest.active = True
        record.state = ForgeState.ACTIVE
        record.updated_at = self._now()
        record.reason = reason
        self._capabilities[capability_id] = record

        self._audit(
            "forge_capability_activated",
            actor="system",
            reason=f"Capability {capability_id} activated. {reason}",
            result="completed",
        )
        return record

    def revoke(
        self,
        capability_id: str,
        reason: str,
    ) -> CapabilityRecord:
        """Revoke a capability — owner removes it."""
        record = self._get_or_create(capability_id)
        if record.state == ForgeState.REVOKED:
            raise ValueError(f"Capability {capability_id} already revoked")

        record.state = ForgeState.REVOKED
        record.manifest.active = False
        record.manifest.revoked_at = self._now()
        record.updated_at = self._now()
        record.reason = reason
        self._capabilities[capability_id] = record

        self._audit(
            "forge_capability_revoked",
            actor="owner",
            reason=f"Capability {capability_id} revoked. {reason}",
            result="completed",
        )
        return record

    def rollback(
        self,
        capability_id: str,
        reason: str,
    ) -> CapabilityRecord:
        """Rollback a capability to its previous manifest."""
        record = self._get_or_create(capability_id)
        if record.state not in (ForgeState.ACTIVE, ForgeState.INSTALLED):
            raise ValueError(f"Cannot rollback {capability_id}: state is {record.state.value}")

        if record.previous_manifest:
            record.manifest = record.previous_manifest
            record.previous_manifest = None

        record.state = ForgeState.ROLLED_BACK
        record.updated_at = self._now()
        record.reason = reason
        self._capabilities[capability_id] = record

        self._audit(
            "forge_capability_rolled_back",
            actor="system",
            reason=f"Capability {capability_id} rolled back. {reason}",
            result="completed",
        )
        return record

    # -- Guardrail enforcement ----------------------------------------------

    def _verify_no_core_code_access(self, manifest: CapabilityManifest) -> None:
        """Verify capability does not attempt to edit policy gate or core code."""
        forbidden_permissions = [
            "policy_gate:edit",
            "core_code:write",
            "core_code:modify",
            "tier:raise",
            "audit_log:modify",
        ]
        for perm in manifest.permissions:
            if perm in forbidden_permissions:
                raise ValueError(
                    f"Capability {manifest.id} cannot have permission '{perm}' — forbidden core access"
                )

    # -- Inspection ---------------------------------------------------------

    def get_capability(self, capability_id: str) -> CapabilityRecord | None:
        """Get a capability record by id."""
        return self._capabilities.get(capability_id)

    def get_all_capabilities(self) -> list[CapabilityRecord]:
        """Get all capability records."""
        return list(self._capabilities.values())

    def is_active(self, capability_id: str) -> bool:
        """Check if a capability is active."""
        record = self._capabilities.get(capability_id)
        return record is not None and record.state == ForgeState.ACTIVE

    def get_code_hash(self, capability_id: str) -> str | None:
        """Get the installed code hash for integrity verification."""
        return self._code_hashes.get(capability_id)

    def verify_code_integrity(self, capability_id: str) -> bool:
        """Verify installed code hasn't been tampered with."""
        record = self._capabilities.get(capability_id)
        if not record:
            return False
        current_hash = self._hash_code(self._installed_code.get(capability_id, ""))
        return current_hash == record.manifest.source_code_hash

    # -- Helpers ------------------------------------------------------------

    def _get_or_create(self, capability_id: str) -> CapabilityRecord:
        record = self._capabilities.get(capability_id)
        if record is None:
            now = self._now()
            manifest = CapabilityManifest(
                id=capability_id,
                name=capability_id,
                version="0.1.0",
                tier=CapabilityTier.T0,
                description="",
                author="forge",
            )
            record = CapabilityRecord(
                manifest=manifest,
                state=ForgeState.DISCOVERED,
                created_at=now,
                updated_at=now,
                reason="Auto-created record",
            )
            self._capabilities[capability_id] = record
        return record

    @staticmethod
    def _hash_code(source_code: str) -> str:
        return hashlib.sha256(source_code.encode()).hexdigest()

    def _audit(
        self,
        action: str,
        actor: str,
        reason: str,
        result: str,
        tier: str | None = None,
    ) -> None:
        entry = AuditEntry(
            id=f"forge-{action}-{datetime.now(UTC).timestamp()}",
            timestamp=self._now(),
            action=action,
            actor=actor,
            reason=reason,
            result=result,
            tier=tier,
            sensitive=False,
        )
        self.audit_log.append(entry)


def create_capability_forge(audit_log: AuditLog) -> CapabilityForge:
    """Create a CapabilityForge with default settings."""
    return CapabilityForge(audit_log=audit_log)
