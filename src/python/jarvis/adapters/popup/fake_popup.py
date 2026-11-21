"""Fake popup port — records shown cards for tests."""

from __future__ import annotations

from datetime import datetime

from jarvis.ports.popup import PopupCard, PopupPort, PopupResponse


class FakePopupPort(PopupPort):
    """Fake popup port for tests and the walking skeleton."""

    def __init__(self) -> None:
        self.shown: list[PopupCard] = []
        self.responses: list[PopupResponse] = []
        self.dismissed: list[str] = []
        self.snoozed: list[tuple[str, int]] = []

    def show(self, card: PopupCard) -> None:
        self.shown.append(card)

    def dismiss(self, card_id: str) -> None:
        self.dismissed.append(card_id)

    def snooze(self, card_id: str, minutes: int) -> None:
        self.snoozed.append((card_id, minutes))

    def respond(self, card_id: str, action: str) -> PopupResponse:
        """Record an owner response (test helper)."""
        response = PopupResponse(card_id=card_id, action=action)
        self.responses.append(response)
        return response

    def health(self) -> str:
        return "ok"
