"""Fake audit log — records entries for test assertions."""

from datetime import datetime

from jarvis.ports.audit_log import AuditEntry, AuditLog


class FakeAuditLog(AuditLog):
    def __init__(self) -> None:
        self.entries: list[AuditEntry] = []

    def append(self, entry: AuditEntry) -> None:
        self.entries.append(entry)

    def query(
        self,
        action: str | None = None,
        actor: str | None = None,
        since: datetime | None = None,
    ) -> list[AuditEntry]:
        results = self.entries
        if action:
            results = [e for e in results if e.action == action]
        if actor:
            results = [e for e in results if e.actor == actor]
        if since:
            results = [e for e in results if e.timestamp >= since]
        return results
