"""Textual UI shell — Phase 2 popup + proactive engine interface.

A terminal UI that shows:
- Popup cards for proactive alerts (calendar, news, messages)
- Kill switch activation (Ctrl+Alt+K)
- Mic activity indicator (privacy by default)
- Proactive engine status
- Voice loop status

Run with: PYTHONPATH=src/python python -m jarvis.ui_shell
"""

from __future__ import annotations

from datetime import UTC, datetime

from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Button, Footer, Header, Label, Static

from jarvis.adapters.popup.textual_popup import TextualPopupPort
from jarvis.domain.proactive_engine import (
    ProactiveEngine,
)
from jarvis.domain.speech_queue import SpeechQueue
from jarvis.ports.popup import PopupCard


class KillSwitchButton(Button):
    """Kill switch button — red when active."""

    def __init__(self) -> None:
        super().__init__("KILL SWITCH (Ctrl+Alt+K)", id="kill-switch")
        self._active = False
        self._update_style()

    def _update_style(self) -> None:
        if self._active:
            self.add_class("kill-active")
            self.remove_class("kill-inactive")
            self.label = "KILL SWITCH ACTIVE — Tap to deactivate"
        else:
            self.add_class("kill-inactive")
            self.remove_class("kill-active")
            self.label = "KILL SWITCH (Ctrl+Alt+K)"

    @property
    def active(self) -> bool:
        return self._active

    def activate(self) -> None:
        self._active = True
        self._update_style()

    def deactivate(self) -> None:
        self._active = False
        self._update_style()


class MicIndicator(Static):
    """Mic activity indicator — green when mic is on."""

    def __init__(self) -> None:
        super().__init__("MIC: OFF", id="mic-indicator")
        self._active = False
        self._update_style()

    def _update_style(self) -> None:
        if self._active:
            self.add_class("mic-on")
            self.remove_class("mic-off")
            self.update("MIC: ON  (privacy indicator)")
        else:
            self.add_class("mic-off")
            self.remove_class("mic-on")
            self.update("MIC: OFF")

    @property
    def active(self) -> bool:
        return self._active

    def activate(self) -> None:
        self._active = True
        self._update_style()

    def deactivate(self) -> None:
        self._active = False
        self._update_style()


class PopupCardWidget(Static):
    """A single popup card widget."""

    def __init__(self, card: PopupCard) -> None:
        super().__init__(id=f"popup-{card.id}")
        self.card = card
        self._update_content()

    def _update_content(self) -> None:
        level_color = {
            "L1": "yellow",
            "L2": "orange",
            "L3": "red",
        }.get(self.card.interrupt_level, "white")
        self.update(
            f"[bold {level_color}][{self.card.interrupt_level}][/] "
            f"{self.card.title}\n{self.card.body}\n"
            f"Source: {self.card.source} | "
            f"Actions: {', '.join(self.card.actions)}"
        )


class UIShell(App[None]):
    """Textual UI shell for JARVIS proactive alerts.

    Shows popup cards, kill switch, mic indicator, and proactive engine
    status. Integrates with VoiceLoop and ProactiveEngine.
    """

    CSS = """
    #kill-switch {
        width: 100%;
        height: 3;
        margin: 1;
    }
    #kill-active {
        background: $error;
        color: $text;
    }
    #kill-inactive {
        background: $success;
        color: $text;
    }
    #mic-indicator {
        width: 100%;
        height: 1;
        margin: 1;
        color: $text;
    }
    #mic-on {
        color: green;
    }
    #mic-off {
        color: gray;
    }
    #popup-container {
        height: 1fr;
        overflow-y: auto;
        border: round $primary;
        margin: 1;
        padding: 1;
    }
    #status-panel {
        height: 12;
        border: round $primary;
        margin: 1;
        padding: 1;
    }
    """

    def __init__(
        self,
        popup_port: TextualPopupPort,
        proactive_engine: ProactiveEngine | None = None,
        speech_queue: SpeechQueue | None = None,
    ) -> None:
        super().__init__()
        self.popup_port = popup_port
        self.popup_port.set_app(self)
        self.proactive_engine = proactive_engine
        self.speech_queue = speech_queue
        self.kill_switch = KillSwitchButton()
        self.mic_indicator = MicIndicator()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            self.kill_switch,
            self.mic_indicator,
            id="top-bar",
        )
        yield Container(
            Label("Proactive Alerts", id="alerts-title"),
            VerticalScroll(id="popup-container"),
            id="popup-container-outer",
        )
        yield Container(
            Label("System Status", id="status-title"),
            Static("Idle", id="status-text"),
            id="status-panel",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = "JARVIS — Voice-First Assistant"
        self.sub_title = "Phase 2 — Popups + Proactive Engine"

    def show_card(self, card: PopupCard) -> None:
        """Display a new popup card."""
        container = self.query_one("#popup-container", VerticalScroll)
        widget = PopupCardWidget(card)
        container.mount(widget)
        # Scroll to bottom
        container.scroll_end(animate=False)

    def dismiss_card(self, card_id: str) -> None:
        """Remove a popup card from display."""
        try:
            self.query_one(f"#popup-{card_id}", PopupCardWidget).remove()
        except Exception:
            pass  # Card already removed

    def snooze_card(self, card_id: str, minutes: int) -> None:
        """Mark a card as snoozed."""
        # In production, this would grey out the card until snooze expires
        pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "kill-switch":
            if self.kill_switch.active:
                self.kill_switch.deactivate()
                self.popup_port.deactivate_kill_switch()
                self._log_status("Kill switch deactivated")
            else:
                self.kill_switch.activate()
                self.popup_port.activate_kill_switch()
                self._log_status("Kill switch ACTIVATED — all speech/listening stopped")

    def _log_status(self, message: str) -> None:
        status = self.query_one("#status-text", Static)
        timestamp = datetime.now(UTC).strftime("%H:%M:%S")
        status.update(f"[{timestamp}] {message}")


def run_ui_shell() -> None:
    """Run the Textual UI shell."""
    popup_port = TextualPopupPort()
    app = UIShell(popup_port)
    app.run()


if __name__ == "__main__":
    run_ui_shell()
