"""Windows notification listener adapter — reads Messenger/SMS notifications.

Backend A (primary): Android notification capture via Windows notification
listener (Phone Link mirroring or browser toasts). Read-oriented, low risk.
"""

from __future__ import annotations

from datetime import UTC, datetime

from jarvis.ports.message_source import (
    Draft,
    MessageDirection,
    MessageEvent,
    MessageSource,
    MessageStatus,
    SendResult,
)


class WindowsNotificationAdapter(MessageSource):
    """Windows notification listener for Messenger/SMS.

    Uses Windows UserNotificationListener API to read notifications from
    Messenger (via Phone Link or browser) and SMS. Does not require package
    identity for reading notifications.

    Non-negotiable: every outgoing message requires approval unless a narrow
    standing rule exists.
    """

    def __init__(self) -> None:
        self._access = False
        self._notifications: list[MessageEvent] = []
        self._counter = 0

    def set_access(self, granted: bool) -> None:
        """Set notification listener access (simulates Windows Settings grant)."""
        self._access = granted

    def has_access(self) -> bool:
        return self._access

    def events(self) -> list[MessageEvent]:
        """Return pending inbound message events from notifications."""
        if not self._access:
            return []
        events = list(self._notifications)
        self._notifications.clear()
        return events

    def fetch_thread(self, thread_id: str, since: datetime | None = None) -> list[MessageEvent]:
        """Fetch message history — notifications are lossy, so this is limited."""
        if not self._access:
            return []
        return [
            e
            for e in self._notifications
            if e.thread_id == thread_id and (since is None or e.timestamp >= since)
        ]

    def draft_reply(self, thread_id: str, text: str) -> Draft:
        """Draft a reply — never sends. Requires T2 confirmation to send."""
        return Draft(
            thread_id=thread_id,
            text=text,
            to_contact="notification-contact",
            requires_approval=True,
        )

    def send(self, draft: Draft, approval: bool) -> SendResult:
        """Send a draft via notification reply action.

        Requires gate approval (T2). Without approval, the draft is not sent.
        """
        if not approval:
            return SendResult(
                accepted=False,
                message_id=None,
                error="T2 approval required for sending messages",
            )
        # In production, this would use the Windows notification reply action
        # or the mautrix-meta bridge (backend B)
        return SendResult(
            accepted=True,
            message_id=f"notif-msg-{self._counter}",
        )

    def add_notification(
        self,
        app_id: str,
        title: str,
        text: str,
        thread_id: str,
        from_contact: str,
        timestamp: datetime | None = None,
        partial: bool = False,
        sensitive: bool = False,
    ) -> None:
        """Add a simulated notification (for tests and spike S1)."""
        self._counter += 1
        self._notifications.append(
            MessageEvent(
                id=f"notif-{self._counter}",
                source="messenger",
                thread_id=thread_id,
                from_contact=from_contact,
                text=text,
                direction=MessageDirection.INBOUND,
                status=MessageStatus.RECEIVED,
                timestamp=timestamp or datetime.now(UTC),
                sensitive=sensitive,
                partial=partial,
                raw={"app_id": app_id, "title": title},
            )
        )

    def health(self) -> str:
        if not self._access:
            return "degraded: notification listener access not granted"
        return "ok"


class MaustrixMetaAdapter(MessageSource):
    """mautrix-meta Messenger bridge adapter (backend B, opt-in).

    Self-hosted Matrix bridge that puppets Facebook Messenger. High
    completeness but medium-high detection risk. Must be trialed on a
    spare account first (spike S6).

    Non-negotiable: no automatic logins. Owner performs login once in
    trusted UI. Never run on owner's main account.
    """

    def __init__(self, bridge_url: str = "http://localhost:8090") -> None:
        self._bridge_url = bridge_url
        self._logged_in = False
        self._spare_account = False  # Must be True for safety
        self._notifications: list[MessageEvent] = []
        self._counter = 0

    def set_login(self, logged_in: bool, spare_account: bool = False) -> None:
        """Set login state. Requires spare_account=True for safety."""
        if logged_in and not spare_account:
            raise ValueError("mautrix-meta must use a spare account — never the main account")
        self._logged_in = logged_in
        self._spare_account = spare_account

    def is_logged_in(self) -> bool:
        return self._logged_in

    def events(self) -> list[MessageEvent]:
        if not self._logged_in:
            return []
        events = list(self._notifications)
        self._notifications.clear()
        return events

    def fetch_thread(self, thread_id: str, since: datetime | None = None) -> list[MessageEvent]:
        if not self._logged_in:
            return []
        return [
            e
            for e in self._notifications
            if e.thread_id == thread_id and (since is None or e.timestamp >= since)
        ]

    def draft_reply(self, thread_id: str, text: str) -> Draft:
        return Draft(
            thread_id=thread_id,
            text=text,
            to_contact="bridge-contact",
            requires_approval=True,
        )

    def send(self, draft: Draft, approval: bool) -> SendResult:
        if not self._logged_in:
            return SendResult(
                accepted=False,
                message_id=None,
                error="Not logged in — owner must perform login in trusted UI",
            )
        if not approval:
            return SendResult(
                accepted=False,
                message_id=None,
                error="T2 approval required for sending messages",
            )
        self._counter += 1
        return SendResult(
            accepted=True,
            message_id=f"bridge-msg-{self._counter}",
        )

    def add_message(
        self,
        thread_id: str,
        from_contact: str,
        text: str,
        timestamp: datetime | None = None,
        partial: bool = False,
    ) -> None:
        """Add a simulated message from the bridge (for tests)."""
        from datetime import UTC, datetime

        self._counter += 1
        self._notifications.append(
            MessageEvent(
                id=f"bridge-{self._counter}",
                source="messenger",
                thread_id=thread_id,
                from_contact=from_contact,
                text=text,
                direction=__import__(
                    "jarvis.ports.message_source", fromlist=["MessageDirection"]
                ).MessageDirection.INBOUND,
                status=__import__(
                    "jarvis.ports.message_source", fromlist=["MessageStatus"]
                ).MessageStatus.RECEIVED,
                timestamp=timestamp or datetime.now(UTC),
                partial=partial,
                raw={"bridge": "mautrix-meta"},
            )
        )

    def health(self) -> str:
        if not self._logged_in:
            return "degraded: not logged in"
        return "ok"
