"""Textual-based popup port — TUI popup cards with kill switch.

Provides a terminal UI for displaying proactive alert cards, kill switch
activation, and proactive engine status. This is the Phase 2 UI shell
that runs on the desktop (Windows) alongside the core agent.
"""

from __future__ import annotations

from datetime import datetime

from jarvis.ports.popup import PopupCard, PopupPort, PopupResponse


class TextualPopupPort(PopupPort):
    """Textual TUI popup port.

    Displays popup cards in a terminal UI with:
    - Always-on-top card display
    - Read / Reply / Snooze / Dismiss actions
    - Kill switch (global hotkey simulation)
    - Proactive engine status panel
    - Mic indicator (privacy by default)
    """

    def __init__(self) -> None:
        self.shown: list[PopupCard] = []
        self.responses: list[PopupResponse] = []
        self.dismissed: list[str] = []
        self.snoozed: list[tuple[str, int]] = []
        self._kill_switch_active = False
        self._mic_active = False
        self._app: object | None = None  # set by the UI shell when running

    # -- PopupPort API ------------------------------------------------------

    def show(self, card: PopupCard) -> None:
        self.shown.append(card)
        if self._app:
            self._app.show_card(card)  # type: ignore[attr-defined]

    def dismiss(self, card_id: str) -> None:
        self.dismissed.append(card_id)
        if self._app:
            self._app.dismiss_card(card_id)  # type: ignore[attr-defined]

    def snooze(self, card_id: str, minutes: int) -> None:
        self.snoozed.append((card_id, minutes))
        if self._app:
            self._app.snooze_card(card_id, minutes)  # type: ignore[attr-defined]

    def health(self) -> str:
        return "ok"

    # -- UI shell control (set by Textual app) -----------------------------

    def set_app(self, app: object) -> None:
        self._app = app

    def activate_kill_switch(self) -> None:
        self._kill_switch_active = True

    def deactivate_kill_switch(self) -> None:
        self._kill_switch_active = False

    def is_kill_switch_active(self) -> bool:
        return self._kill_switch_active

    def set_mic_active(self, active: bool) -> None:
        self._mic_active = active

    def is_mic_active(self) -> bool:
        return self._mic_active
