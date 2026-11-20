"""Contract tests for the MessageSource port."""

from datetime import UTC, datetime

from jarvis.fakes.message_source import FakeMessageSource
from jarvis.ports.message_source import (
    Draft,
    MessageDirection,
    MessageEvent,
    MessageSource,
    MessageStatus,
)


def test_fake_message_source_implements_port() -> None:
    source: MessageSource = FakeMessageSource()
    assert isinstance(source, MessageSource)


def test_events_returns_inbound_messages() -> None:
    source = FakeMessageSource()
    event = MessageEvent(
        id="evt-1",
        source="messenger",
        thread_id="thread-1",
        from_contact="Ana",
        text="Hello",
        direction=MessageDirection.INBOUND,
        status=MessageStatus.RECEIVED,
        timestamp=datetime(2026, 11, 20, 9, 0, 0, tzinfo=UTC),
    )
    source.add_inbound(event)
    assert len(source.events()) == 1
    assert source.events()[0].text == "Hello"


def test_draft_reply_never_sends() -> None:
    source = FakeMessageSource()
    draft = source.draft_reply("thread-1", "Hello back")
    assert isinstance(draft, Draft)
    assert draft.text == "Hello back"
    assert len(source.sent) == 0  # draft does not send


def test_send_requires_approval_and_records() -> None:
    source = FakeMessageSource()
    draft = Draft(thread_id="thread-1", text="Hi", to_contact="Ana")
    result = source.send(draft, approval=True)
    assert result.accepted is True
    assert len(source.sent) == 1
    assert source.sent[0][1] is True  # was approved


def test_send_without_approval_still_records() -> None:
    source = FakeMessageSource()
    draft = Draft(thread_id="thread-1", text="Hi", to_contact="Ana")
    source.send(draft, approval=False)
    assert source.sent[0][1] is False
