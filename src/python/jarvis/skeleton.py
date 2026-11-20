"""Walking skeleton: fake mic input, fake LLM, TTS stub, one popup — end to end.

This is the thinnest end-to-end slice. It wires together:
- Fake microphone input (user says "Hey Jarvis" then a message)
- Fake wake word detection
- Fake STT
- Fake LLM (brain) — echoes back a canned response
- Fake TTS stub — speaks the response
- One popup — shows the response

Run with: PYTHONPATH=src/python python -m jarvis.skeleton
"""

from __future__ import annotations

from jarvis.fakes import (
    FakeAuditLog,
    FakeCalendarProvider,
    FakeClock,
    FakeDesktopControl,
    FakeEchoCanceller,
    FakeMemoryStore,
    FakeMessageSource,
    FakeNewsSource,
    FakeNotificationSource,
    FakePolicyGate,
    FakeSecretsBroker,
    FakeSpeechToText,
    FakeTextToSpeech,
    FakeVoiceActivityDetector,
    FakeWakeWordSource,
)
from jarvis.ports.audit_log import AuditEntry
from jarvis.ports.clock import Clock
from jarvis.ports.policy_gate import GateDecision, PolicyGate, TrustTier


class FakeLLM:
    """Fake LLM that returns canned responses for the walking skeleton."""

    def __init__(self) -> None:
        self.responses = {
            "hello": "Hello! I'm JARVIS, your assistant. How can I help?",
            "hey jarvis": "I'm here. What do you need?",
            "default": "I heard you. That's all the walking skeleton knows so far.",
        }

    def respond(self, text: str) -> str:
        key = text.strip().lower()
        return self.responses.get(key, self.responses["default"])


class Popup:
    """One popup card — shows text on screen."""

    def __init__(self) -> None:
        self.shown: list[str] = []

    def show(self, title: str, body: str) -> None:
        self.shown.append(f"{title}: {body}")
        print(f"[POPUP] {title}: {body}")


class WalkingSkeleton:
    """End-to-end walking skeleton with fakes everywhere."""

    def __init__(self) -> None:
        self.clock: Clock = FakeClock()
        self.policy_gate: PolicyGate = FakePolicyGate()
        self.audit_log = FakeAuditLog()
        self.memory = FakeMemoryStore()
        self.secrets = FakeSecretsBroker()
        self.wake_word = FakeWakeWordSource()
        self.wake_word.start(self.handle_wake_word)
        self.vad = FakeVoiceActivityDetector()
        self.echo = FakeEchoCanceller()
        self.stt = FakeSpeechToText()
        self.tts = FakeTextToSpeech()
        self.messages = FakeMessageSource()
        self.calendar = FakeCalendarProvider()
        self.news = FakeNewsSource()
        self.notifications = FakeNotificationSource()
        self.desktop = FakeDesktopControl()
        self.llm = FakeLLM()
        self.popup = Popup()
        self._running = False

    def handle_wake_word(self) -> None:
        """Called when the fake wake word fires."""
        print("[WAKE] 'Hey Jarvis' detected")
        self._listen_and_respond()

    def _listen_and_respond(self) -> None:
        """Simulate: mic -> STT -> LLM -> TTS + popup."""
        # Simulate user saying "Hey Jarvis, hello"
        audio = b"fake-audio"
        result = self.stt.transcribe(audio)
        result.text = "hello"  # simulate STT output

        # Check policy gate for any action (T0 = auto-allowed)
        gate_result = self.policy_gate.evaluate("speak_response", TrustTier.T0, {})
        if gate_result.decision == GateDecision.DENY:
            print("[DENY] Policy gate blocked response")
            return

        # Get LLM response
        response = self.llm.respond(result.text)

        # Speak via TTS
        self.tts.speak(response)

        # Show popup
        self.popup.show("JARVIS", response)

        # Audit log
        self.audit_log.append(
            AuditEntry(
                id="audit-1",
                timestamp=self.clock.now(),
                action="speak_response",
                actor="system",
                reason="walking skeleton response",
                result="completed",
            )
        )

        print(f"[TTS] {response}")
        print("[SKELETON] End-to-end cycle complete")

    def run(self) -> None:
        """Run the walking skeleton synchronously."""
        self._running = True
        print("=== JARVIS Walking Skeleton ===")
        print("Fakes active: wake word, STT, TTS, LLM, popup, policy gate, audit log")
        print("Triggering wake word...")

        self.wake_word.trigger()

        print("\n=== Skeleton finished ===")
        print(f"Popup shown: {len(self.popup.shown)} time(s)")
        print(f"TTS spoken: {len(self.tts.spoken)} time(s)")
        print(f"Audit entries: {len(self.audit_log.entries)}")

    def stop(self) -> None:
        self._running = False


def main() -> None:
    skeleton = WalkingSkeleton()
    try:
        skeleton.run()
    finally:
        skeleton.stop()


if __name__ == "__main__":
    main()
