"""File-based tamper-evident audit log.

Appends JSON lines with SHA-256 hash chaining — each entry includes the
hash of the previous entry, making tampering detectable. Every action
is logged with a 'why' (reason).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from jarvis.ports.audit_log import AuditEntry, AuditLog


class FileAuditLog(AuditLog):
    """Tamper-evident file-based audit log with hash chaining."""

    def __init__(self, log_path: str = "logs/audit.log") -> None:
        self._log_path = Path(log_path)
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = self._compute_chain_head()

    def _compute_chain_head(self) -> str:
        """Compute the hash of the last entry (or genesis if empty)."""
        if not self._log_path.exists():
            return hashlib.sha256(b"genesis").hexdigest()

        last_line = None
        with self._log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    last_line = line

        if last_line is None:
            return hashlib.sha256(b"genesis").hexdigest()

        try:
            entry = json.loads(last_line)
            return entry.get("hash", hashlib.sha256(last_line.encode()).hexdigest())  # type: ignore[no-any-return]
        except (json.JSONDecodeError, KeyError):
            return hashlib.sha256(last_line.encode()).hexdigest()

    def _make_entry(self, entry: AuditEntry) -> dict[str, object]:
        """Create a chained audit entry."""
        payload = {
            "id": entry.id,
            "timestamp": entry.timestamp.isoformat(),
            "action": entry.action,
            "actor": entry.actor,
            "reason": entry.reason,
            "result": entry.result,
            "tier": entry.tier,
            "sensitive": entry.sensitive,
            "prev_hash": self._last_hash,
        }
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        entry_hash = hashlib.sha256(payload_bytes).hexdigest()
        payload["hash"] = entry_hash
        self._last_hash = entry_hash
        return payload  # type: ignore[return-value]

    def append(self, entry: AuditEntry) -> None:
        """Append an audit entry (append-only, tamper-evident)."""
        chained = self._make_entry(entry)
        with self._log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(chained, sort_keys=True) + "\n")

    def query(
        self,
        action: str | None = None,
        actor: str | None = None,
        since: datetime | None = None,
    ) -> list[AuditEntry]:
        """Query audit entries from the log file."""
        results: list[AuditEntry] = []
        if not self._log_path.exists():
            return results

        with self._log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if action and data.get("action") != action:
                    continue
                if actor and data.get("actor") != actor:
                    continue
                if since:
                    ts = datetime.fromisoformat(data.get("timestamp", ""))
                    if ts < since:
                        continue

                results.append(
                    AuditEntry(
                        id=data["id"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        action=data["action"],
                        actor=data["actor"],
                        reason=data["reason"],
                        result=data["result"],
                        tier=data.get("tier"),
                        sensitive=data.get("sensitive", False),
                    )
                )

        return results

    def verify_chain(self) -> bool:
        """Verify the hash chain integrity. Returns True if untampered."""
        if not self._log_path.exists():
            return True

        prev_hash = hashlib.sha256(b"genesis").hexdigest()
        with self._log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    return False

                if data.get("prev_hash") != prev_hash:
                    return False

                # Recompute hash
                payload = {k: v for k, v in data.items() if k != "hash"}
                payload_bytes = json.dumps(payload, sort_keys=True).encode()
                expected_hash = hashlib.sha256(payload_bytes).hexdigest()
                if data.get("hash") != expected_hash:
                    return False

                prev_hash = data.get("hash", "")

        return True

    def health(self) -> str:
        return "ok"
