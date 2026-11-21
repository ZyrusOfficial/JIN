"""Contract tests: popup port and fake implementation."""

from jarvis.adapters.popup.fake_popup import FakePopupPort
from jarvis.ports.popup import PopupCard


def test_popup_show_records_card() -> None:
    """show() appends the card to the shown list."""
    popup = FakePopupPort()
    card = PopupCard(
        id="card-1",
        title="Test Alert",
        body="This is a test",
        source="calendar",
        interrupt_level="L2",
    )
    popup.show(card)
    assert len(popup.shown) == 1
    assert popup.shown[0].id == "card-1"


def test_popup_dismiss_records_id() -> None:
    """dismiss() records the card id."""
    popup = FakePopupPort()
    popup.dismiss("card-1")
    assert "card-1" in popup.dismissed


def test_popup_snooze_records_card_and_minutes() -> None:
    """snooze() records card id and minutes."""
    popup = FakePopupPort()
    popup.snooze("card-1", 30)
    assert ("card-1", 30) in popup.snoozed


def test_popup_respond_creates_response() -> None:
    """respond() creates a PopupResponse."""
    popup = FakePopupPort()
    response = popup.respond("card-1", "dismiss")
    assert response.card_id == "card-1"
    assert response.action == "dismiss"


def test_popup_health_returns_ok() -> None:
    """health() returns 'ok'."""
    popup = FakePopupPort()
    assert popup.health() == "ok"


def test_popup_card_defaults() -> None:
    """PopupCard has sensible defaults."""
    card = PopupCard(
        id="card-1",
        title="Test",
        body="Body",
        source="news",
        interrupt_level="L1",
    )
    assert card.actions == ["read", "snooze", "dismiss"]
    assert card.sensitive is False
    assert card.id == "card-1"


def test_popup_port_is_protocol() -> None:
    """PopupPort is a runtime_checkable Protocol."""
    # Verify it's a Protocol by checking it can be used with isinstance
    from typing import Protocol

    from jarvis.ports.popup import PopupPort

    assert issubclass(PopupPort, Protocol)


def test_fake_popup_implements_port() -> None:
    """FakePopupPort implements PopupPort."""

    from jarvis.adapters.popup.fake_popup import FakePopupPort
    from jarvis.ports.popup import PopupPort

    popup = FakePopupPort()
    assert isinstance(popup, PopupPort)
