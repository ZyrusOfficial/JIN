"""Update Guardian — state machine for safe software updates.

State machine: watch → verified → staged → tested → applied →
healthy | rolled_back | skipped

Non-negotiables honored:
- Never auto-login to third-party accounts
- No new permissions without approval (T2 confirmation for writes)
- Max one auto-update per component per week
- Capability cannot raise its own tier or edit policy gate
- Everything logged to audit log with 'why'
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

from jarvis.ports.audit_log import AuditEntry, AuditLog


class UpdateState(Enum):
    """Update Guardian state machine states."""

    WATCH = "watch"  # Monitoring for available updates
    VERIFIED = "verified"  # Update verified (signature, source)
    STAGED = "staged"  # Update staged for installation
    TESTED = "tested"  # Update tested in sandbox
    APPLIED = "applied"  # Update applied to production
    HEALTHY = "healthy"  # Update confirmed healthy after rollout
    ROLLED_BACK = "rolled_back"  # Update rolled back due to issues
    SKIPPED = "skipped"  # Update skipped (owner decision or policy)


class UpdateComponent(Enum):
    """Components that can be updated."""

    CORE_AGENT = "core_agent"
    STT_MODEL = "stt_model"
    TTS_MODEL = "tts_model"
    WAKE_WORD_MODEL = "wake_word_model"
    LLM_MODEL = "llm_model"
    CAPABILITY_FORGE = "capability_forge"
    DESKTOP_BRIDGE = "desktop_bridge"
    ANDROID_COMPANION = "android_companion"


@dataclass
class UpdateRecord:
    """Record of an update attempt."""

    component: UpdateComponent
    version_from: str
    version_to: str
    state: UpdateState
    created_at: datetime
    updated_at: datetime
    reason: str  # the "why" for audit
    approved_by: str | None = None  # owner who approved
    auto_approved: bool = False  # whether standing rule allowed it
    health_check_passed: bool = False
    rollback_reason: str | None = None
    attempts: int = 0
    max_attempts: int = 3


@dataclass
class UpdatePolicy:
    """Policy governing auto-updates."""

    max_auto_updates_per_component_per_week: int = 1
    require_approval_for_major: bool = True  # major version = T2
    require_approval_for_minor: bool = False  # minor version = T1
    require_approval_for_patch: bool = False  # patch = T0
    auto_rollback_on_failure: bool = True
    health_check_duration_minutes: int = 15
    sandbox_test_required: bool = True


class UpdateGuardian:
    """Update Guardian state machine.

    Manages software updates with a strict state machine. Each transition
    requires specific conditions and is logged to the audit trail.
    """

    def __init__(
        self,
        audit_log: AuditLog,
        policy: UpdatePolicy | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.audit_log = audit_log
        self.policy = policy or UpdatePolicy()
        self._now: Callable[[], datetime] = now or (lambda: datetime.now(UTC))
        self._records: dict[UpdateComponent, UpdateRecord] = {}
        self._auto_update_count: dict[
            tuple[UpdateComponent, str], int
        ] = {}  # (component, week_key) -> count

    # -- Public API ---------------------------------------------------------

    def check_for_update(
        self,
        component: UpdateComponent,
        current_version: str,
        available_version: str,
        reason: str,
    ) -> UpdateRecord:
        """Watch phase: detect an available update."""
        now = self._now()
        record = UpdateRecord(
            component=component,
            version_from=current_version,
            version_to=available_version,
            state=UpdateState.WATCH,
            created_at=now,
            updated_at=now,
            reason=reason,
        )
        self._records[component] = record

        self._audit(
            "update_watch",
            actor="system",
            reason=f"Update available for {component.value}: {current_version} → {available_version}. {reason}",
            result="completed",
            component=component.value,
        )
        return record

    def verify_update(
        self,
        component: UpdateComponent,
        signature_valid: bool,
        source_trusted: bool,
        reason: str,
    ) -> UpdateRecord:
        """Verified phase: validate update signature and source."""
        record = self._get_or_create(component)
        if record.state != UpdateState.WATCH:
            raise ValueError(
                f"Cannot verify {component.value}: current state is {record.state.value}"
            )

        if not signature_valid or not source_trusted:
            record.state = UpdateState.SKIPPED
            record.updated_at = self._now()
            self._records[component] = record

            self._audit(
                "update_verification_failed",
                actor="system",
                reason=f"Update verification failed for {component.value}: signature_valid={signature_valid}, source_trusted={source_trusted}. {reason}",
                result="denied",
                component=component.value,
            )
            return record

        record.state = UpdateState.VERIFIED
        record.updated_at = self._now()
        self._records[component] = record

        self._audit(
            "update_verified",
            actor="system",
            reason=f"Update verified for {component.value}: {record.version_from} → {record.version_to}. {reason}",
            result="completed",
            component=component.value,
        )
        return record

    def stage_update(
        self,
        component: UpdateComponent,
        approval: bool,
        approver: str | None = None,
        reason: str = "",
    ) -> UpdateRecord:
        """Staged phase: stage update for installation.

        Requires T2 approval for major version changes, or if policy
        requires approval for this update type.
        """
        record = self._get_or_create(component)
        if record.state != UpdateState.VERIFIED:
            raise ValueError(
                f"Cannot stage {component.value}: current state is {record.state.value}"
            )

        # Determine if approval is required
        requires_approval = self._requires_approval(record)
        if requires_approval and not approval:
            record.state = UpdateState.SKIPPED
            record.updated_at = self._now()
            self._records[component] = record

            self._audit(
                "update_staging_denied",
                actor="system",
                reason=f"Update staging denied for {component.value}: T2 approval required but not granted. {reason}",
                result="denied",
                component=component.value,
            )
            return record

        # Check weekly auto-update limit
        if approval and approver is None:  # auto-approved via standing rule
            week_key = self._week_key()
            count = self._auto_update_count.get((component, week_key), 0)
            if count >= self.policy.max_auto_updates_per_component_per_week:
                record.state = UpdateState.SKIPPED
                record.updated_at = self._now()
                self._records[component] = record

                self._audit(
                    "update_auto_limit_reached",
                    actor="system",
                    reason=f"Auto-update limit reached for {component.value}: max {self.policy.max_auto_updates_per_component_per_week}/week. {reason}",
                    result="denied",
                    component=component.value,
                )
                return record
            self._auto_update_count[(component, week_key)] = count + 1
            record.auto_approved = True

        record.state = UpdateState.STAGED
        record.updated_at = self._now()
        record.approved_by = approver
        self._records[component] = record

        self._audit(
            "update_staged",
            actor=approver or "system",
            reason=f"Update staged for {component.value}: {record.version_from} → {record.version_to}. Approved: {approval}. {reason}",
            result="completed",
            component=component.value,
        )
        return record

    def test_update(
        self,
        component: UpdateComponent,
        test_passed: bool,
        reason: str = "",
    ) -> UpdateRecord:
        """Tested phase: test update in sandbox."""
        record = self._get_or_create(component)
        if record.state != UpdateState.STAGED:
            raise ValueError(
                f"Cannot test {component.value}: current state is {record.state.value}"
            )

        record.attempts += 1

        if not test_passed:
            if record.attempts >= record.max_attempts:
                record.state = UpdateState.SKIPPED
                record.updated_at = self._now()
                self._records[component] = record

                self._audit(
                    "update_test_failed_max_attempts",
                    actor="system",
                    reason=f"Update test failed after {record.attempts} attempts for {component.value}. {reason}",
                    result="failed",
                    component=component.value,
                )
            else:
                # Stay in STAGED, can retry
                record.updated_at = self._now()
                self._records[component] = record

                self._audit(
                    "update_test_failed_retry",
                    actor="system",
                    reason=f"Update test failed for {component.value}: attempt {record.attempts}/{record.max_attempts}. {reason}",
                    result="failed",
                    component=component.value,
                )
            return record

        record.state = UpdateState.TESTED
        record.updated_at = self._now()
        self._records[component] = record

        self._audit(
            "update_tested",
            actor="system",
            reason=f"Update tested successfully for {component.value}: {record.version_from} → {record.version_to}. {reason}",
            result="completed",
            component=component.value,
        )
        return record

    def apply_update(
        self,
        component: UpdateComponent,
        approval: bool,
        approver: str | None = None,
        reason: str = "",
    ) -> UpdateRecord:
        """Applied phase: apply update to production.

        Requires T2 confirmation for applying updates.
        """
        record = self._get_or_create(component)
        if record.state != UpdateState.TESTED:
            raise ValueError(
                f"Cannot apply {component.value}: current state is {record.state.value}"
            )

        if not approval:
            record.state = UpdateState.SKIPPED
            record.updated_at = self._now()
            self._records[component] = record

            self._audit(
                "update_apply_denied",
                actor="system",
                reason=f"Update apply denied for {component.value}: T2 confirmation required. {reason}",
                result="denied",
                component=component.value,
            )
            return record

        record.state = UpdateState.APPLIED
        record.updated_at = self._now()
        record.approved_by = approver
        self._records[component] = record

        self._audit(
            "update_applied",
            actor=approver or "system",
            reason=f"Update applied for {component.value}: {record.version_from} → {record.version_to}. {reason}",
            result="completed",
            component=component.value,
        )
        return record

    def confirm_healthy(
        self,
        component: UpdateComponent,
        health_check_passed: bool,
        reason: str = "",
    ) -> UpdateRecord:
        """Healthy phase: confirm update is healthy after rollout."""
        record = self._get_or_create(component)
        if record.state != UpdateState.APPLIED:
            raise ValueError(
                f"Cannot confirm health for {component.value}: current state is {record.state.value}"
            )

        record.health_check_passed = health_check_passed
        record.updated_at = self._now()

        if health_check_passed:
            record.state = UpdateState.HEALTHY
            self._records[component] = record

            self._audit(
                "update_healthy",
                actor="system",
                reason=f"Update confirmed healthy for {component.value}: {record.version_from} → {record.version_to}. {reason}",
                result="completed",
                component=component.value,
            )
        else:
            # Roll back
            return self.rollback_update(component, reason="Health check failed after rollout")

        return record

    def rollback_update(
        self,
        component: UpdateComponent,
        reason: str = "",
    ) -> UpdateRecord:
        """Rolled back phase: revert a failed update."""
        record = self._get_or_create(component)
        if record.state not in (UpdateState.APPLIED, UpdateState.TESTED):
            raise ValueError(
                f"Cannot rollback {component.value}: current state is {record.state.value}"
            )

        record.state = UpdateState.ROLLED_BACK
        record.updated_at = self._now()
        record.rollback_reason = reason or "Rollback initiated"
        self._records[component] = record

        self._audit(
            "update_rolled_back",
            actor="system",
            reason=f"Update rolled back for {component.value}: {record.version_from} → {record.version_to}. Reason: {reason}",
            result="completed",
            component=component.value,
        )
        return record

    def skip_update(
        self,
        component: UpdateComponent,
        reason: str = "",
    ) -> UpdateRecord:
        """Skip an update (owner decision)."""
        record = self._get_or_create(component)
        record.state = UpdateState.SKIPPED
        record.updated_at = self._now()
        self._records[component] = record

        self._audit(
            "update_skipped",
            actor="owner",
            reason=f"Update skipped for {component.value}: {record.version_from} → {record.version_to}. {reason}",
            result="completed",
            component=component.value,
        )
        return record

    # -- Inspection ---------------------------------------------------------

    def get_record(self, component: UpdateComponent) -> UpdateRecord | None:
        """Get the current update record for a component."""
        return self._records.get(component)

    def get_all_records(self) -> list[UpdateRecord]:
        """Get all update records."""
        return list(self._records.values())

    def get_state(self, component: UpdateComponent) -> UpdateState | None:
        """Get the current state for a component."""
        record = self._records.get(component)
        return record.state if record else None

    def is_in_state(self, component: UpdateComponent, state: UpdateState) -> bool:
        """Check if a component is in a given state."""
        return self.get_state(component) == state

    # -- Helpers ------------------------------------------------------------

    def _get_or_create(self, component: UpdateComponent) -> UpdateRecord:
        record = self._records.get(component)
        if record is None:
            now = self._now()
            record = UpdateRecord(
                component=component,
                version_from="unknown",
                version_to="unknown",
                state=UpdateState.WATCH,
                created_at=now,
                updated_at=now,
                reason="Initial record",
            )
            self._records[component] = record
        return record

    def _requires_approval(self, record: UpdateRecord) -> bool:
        """Determine if an update requires T2 approval."""
        # Major version changes always require approval
        try:
            major_from = int(record.version_from.split(".")[0])
            major_to = int(record.version_to.split(".")[0])
            if major_to > major_from:
                return self.policy.require_approval_for_major
        except (ValueError, IndexError):
            pass

        # Check policy for minor/patch
        if self.policy.require_approval_for_minor:
            return True
        if self.policy.require_approval_for_patch:
            return True

        return False

    def _week_key(self) -> str:
        """Get the current ISO week key for rate limiting."""
        now = self._now()
        iso_year, iso_week, _ = now.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"

    def _audit(
        self,
        action: str,
        actor: str,
        reason: str,
        result: str,
        component: str | None = None,
    ) -> None:
        entry = AuditEntry(
            id=f"update-{action}-{datetime.now(UTC).timestamp()}",
            timestamp=self._now(),
            action=action,
            actor=actor,
            reason=reason,
            result=result,
            tier="T2" if action in ("update_staged", "update_applied") else "T0",
            sensitive=False,
        )
        self.audit_log.append(entry)


def create_update_guardian(audit_log: AuditLog) -> UpdateGuardian:
    """Create an UpdateGuardian with default policy."""
    return UpdateGuardian(audit_log=audit_log)
