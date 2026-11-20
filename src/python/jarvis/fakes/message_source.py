"""Fake message source — controllable inbound/outbound messages for tests."""

from datetime import datetime

from jarvis.ports.message_source import (
    Draft,
    MessageEvent,
    MessageSource,
    SendResult,
)


class FakeMessageSource(MessageSource):
    def __init__(self) -> None:
        self.inbound: list[MessageEvent] = []
        self.sent: list[tuple[Draft, bool]] = []  # (draft, was_approved)
        self.threads: dict[str, list[MessageEvent]] = {}
        self.send_should_fail = False

    def events(self) -> list[MessageEvent]:
        return list(self.inbound)

    def fetch_thread(self, thread_id: str, since: datetime | None = None) -> list[MessageEvent]:
        return self.threads.get(thread_id, [])

    def draft_reply(self, thread_id: str, text: str) -> Draft:
        return Draft(thread_id=thread_id, text=text, to_contact="fake-contact")

    def send(self, draft: Draft, approval: bool) -> SendResult:
        self.sent.append((draft, approval))
        if self.send_should_fail:
            return SendResult(accepted=False, message_id=None, error="fake send failure")
        return SendResult(accepted=True, message_id="fake-msg-1")

    def add_inbound(self, event: MessageEvent) -> None:
        self.inbound.append(event)
        self.threads.setdefault(event.thread_id, []).append(event)

    def health(self) -> str:
        return "ok"
