"""Voice loop — the core voice-first interaction loop for JARVIS.

Wires together wake word → VAD → echo cancellation → STT → LLM → TTS,
plus the proactive engine → speech queue for unsolicited alerts.

Non-negotiables honored:
- Global kill switch (hotkey + tray) stops speech, listening, proactive behavior
- Policy gate confirms T2/T3 actions deterministically (never LLM prompt)
- Audit log records every action with a 'why'
- Barge-in support via kill switch / VAD detection during TTS
- Quiet hours and rate limiting suppress proactive interruptions
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from jarvis.adapters.echo_canceller.fake_echo_canceller import FakeEchoCanceller
from jarvis.adapters.stt.fake_stt import FakeSpeechToText
from jarvis.adapters.tts.fake_tts import FakeTextToSpeech
from jarvis.adapters.vad.fake_vad import FakeVoiceActivityDetector
from jarvis.adapters.wake_word.fake_wake_word import FakeWakeWordSource
from jarvis.domain.events import Event, EventEnvelope
from jarvis.domain.importance_scorer import ImportanceScorer
from jarvis.domain.models import DeliveryDecision, InterruptLevel
from jarvis.domain.policy_gate import PolicyGate
from jarvis.domain.proactive_engine import ProactiveEngine
from jarvis.domain.speech_queue import SpeechQueue, Utterance
from jarvis.ports.audit_log import AuditEntry, AuditLog
from jarvis.ports.clock import Clock
from jarvis.ports.echo_canceller import EchoCanceller
from jarvis.ports.message_source import MessageEvent
from jarvis.ports.news_source import NewsItem
from jarvis.ports.policy_gate import GateDecision, TrustTier
from jarvis.ports.stt import SpeechToText, STTResult
from jarvis.ports.tts import TextToSpeech
from jarvis.ports.vad import VoiceActivityDetector
from jarvis.ports.wake_word import WakeWordSource


@dataclass
class VoiceLoopConfig:
    """Configuration for the voice loop."""

    wake_word_phrase: str = "Hey Jarvis"
    listen_timeout_seconds: float = 10.0
    max_utterances_per_hour: int = 6
    quiet_hours_enabled: bool = False
    barge_in_enabled: bool = True
    kill_switch_hotkey: str = "ctrl+alt+j"


@dataclass
class VoiceLoopState:
    """Current voice loop state."""

    listening: bool = False
    speaking: bool = False
    kill_switch_active: bool = False
    wake_word_count: int = 0
    utterance_count: int = 0
    last_wake_word: datetime | None = None


class VoiceLoop:
    """Core voice loop — listens, understands, responds.

    States:
      IDLE → LISTENING (on wake word) → PROCESSING (STT+LLM) → SPEAKING (TTS)
      → IDLE

    Proactive events can interrupt at any point (subject to context/rate limits).
    The kill switch can stop everything at any time.
    """

    def __init__(
        self,
        wake_word: WakeWordSource,
        vad: VoiceActivityDetector,
        echo_canceller: EchoCanceller,
        stt: SpeechToText,
        tts: TextToSpeech,
        policy_gate: PolicyGate,
        audit_log: AuditLog,
        clock: Clock,
        proactive_engine: ProactiveEngine,
        speech_queue: SpeechQueue,
        config: VoiceLoopConfig | None = None,
    ) -> None:

        self.config = config or VoiceLoopConfig()
        self.state = VoiceLoopState()

        # Adapters
        self.wake_word = wake_word
        self.vad = vad
        self.echo = echo_canceller
        self.stt = stt
        self.tts = tts

        # Domain
        self.policy_gate = policy_gate
        self.audit_log = audit_log
        self.clock = clock
        self.proactive_engine = proactive_engine
        self.speech_queue = speech_queue

        # Callbacks (set by UI shell / main)
        self._on_speak: Callable[[str], None] | None = None
        self._on_popup: Callable[[str, str], None] | None = None
        self._on_listening: Callable[[bool], None] | None = None
        self._on_transcription: Callable[[str], None] | None = None
        self._on_response: Callable[[str], None] | None = None

        # Kill switch state
        self._kill_switch_lock = threading.Lock()

        # Pending audio buffer for injection
        self._pending_audio = b""

        # Wire up proactive engine callbacks
        self.proactive_engine.set_on_speak(self._handle_proactive_speak)
        self.proactive_engine.set_on_popup(self._handle_proactive_popup)
        self.proactive_engine.set_on_delivered(self._handle_proactive_delivered)

        # Wire up speech queue callbacks
        self.speech_queue.set_on_chunk(self._handle_speech_chunk)
        self.speech_queue.set_on_utterance_complete(self._handle_utterance_complete)

        # Register wake word handler
        self.wake_word.start(self._on_wake_word_detected)

    # -- Public API ---------------------------------------------------------

    def set_on_speak(self, callback: Callable[[str], None]) -> None:
        self._on_speak = callback

    def set_on_popup(self, callback: Callable[[str, str], None]) -> None:
        self._on_popup = callback

    def set_on_listening(self, callback: Callable[[bool], None]) -> None:
        self._on_listening = callback

    def set_on_transcription(self, callback: Callable[[str], None]) -> None:
        self._on_transcription = callback

    def set_on_response(self, callback: Callable[[str], None]) -> None:
        self._on_response = callback

    def activate_kill_switch(self) -> None:
        """Global kill switch — stops speech, listening, proactive behavior.

        Non-negotiable: hotkey + tray kills everything immediately.
        """
        with self._kill_switch_lock:
            self.state.kill_switch_active = True
        self.state.listening = False
        self.state.speaking = False
        self.tts.stop()
        self.speech_queue.stop()
        self.proactive_engine.preempt()
        self._audit(
            "kill_switch_activated",
            actor="owner",
            reason=(
                "Global kill switch activated — stopped all speech, listening, proactive behavior"
            ),
            result="completed",
        )

    def deactivate_kill_switch(self) -> None:
        with self._kill_switch_lock:
            self.state.kill_switch_active = False
        self._audit(
            "kill_switch_deactivated",
            actor="owner",
            reason="Global kill switch deactivated",
            result="completed",
        )

    def is_kill_switch_active(self) -> bool:
        with self._kill_switch_lock:
            return self.state.kill_switch_active

    # -- Wake word handling -------------------------------------------------

    def _on_wake_word_detected(self) -> None:
        """Called when wake word fires."""
        if self.is_kill_switch_active():
            return
        if self.state.listening or self.state.speaking:
            return  # Already listening or speaking — ignore duplicate wake

        self.state.wake_word_count += 1
        self.state.last_wake_word = self.clock.now()
        self.state.listening = True

        self._audit(
            "wake_word_detected",
            actor="system",
            reason=f"Wake word '{self.config.wake_word_phrase}' detected",
            result="completed",
        )

        if self._on_listening:
            self._on_listening(True)

        # Start listening loop in background thread
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _listen_loop(self) -> None:
        """Listen for user speech after wake word detection."""
        try:
            # Collect audio chunks until VAD detects end of speech
            audio_chunks: list[bytes] = []
            _silence_chunks = 0
            _max_silence = 5  # chunks of silence before ending
            _start_time = self.clock.now()

            while self.state.listening and not self.is_kill_switch_active():
                # Check for injected audio (tests/spikes)
                injected = getattr(self, "_pending_audio", b"")
                if injected:
                    audio_chunks.append(injected)
                    self._pending_audio = b""
                    break

                # In production, read from mic here. For now, break after
                # first iteration to avoid busy loop with fakes.
                break

            # Transcribe collected audio
            if audio_chunks and not self.is_kill_switch_active():
                audio = b"".join(audio_chunks)
                self._process_utterance(audio)
        finally:
            self.state.listening = False
            if self._on_listening:
                self._on_listening(False)

    def inject_audio(self, audio_chunk: bytes) -> None:
        """Inject audio into the voice loop (for tests and spike kits)."""
        if not self.state.listening:
            return
        cleaned = self.echo.cancel(audio_chunk, b"")
        self._pending_audio = getattr(self, "_pending_audio", b"") + cleaned

    # -- Utterance processing ----------------------------------------------

    def _process_utterance(self, audio: bytes) -> None:
        """Transcribe audio, get LLM response, speak it."""
        if self.is_kill_switch_active():
            return

        self.state.utterance_count += 1

        # STT
        result: STTResult = self.stt.transcribe(audio)
        text = result.text.strip()

        if self._on_transcription:
            self._on_transcription(text)

        self._audit(
            "stt_transcribe",
            actor="system",
            reason=f"Transcribed user speech: {text[:100]}",
            result="completed",
        )

        if not text:
            self._audit(
                "stt_empty",
                actor="system",
                reason="STT returned empty transcription",
                result="completed",
            )
            return

        # Check policy gate for responding to user (T0 = auto-allowed)
        gate_result = self.policy_gate.evaluate("respond_to_user", TrustTier.T0, {"text": text})
        if gate_result.decision == GateDecision.DENY:
            self._audit(
                "response_denied",
                actor="system",
                reason=f"Policy gate denied response: {gate_result.reason}",
                result="denied",
            )
            return

        # Get LLM response
        self.state.speaking = True
        try:
            response = self._get_llm_response(text)
        finally:
            self.state.speaking = False

        if self._on_response:
            self._on_response(response)

        # Speak via TTS (with speech queue for priority management)
        self._speak(response, InterruptLevel.L2_NORMAL)

        self._audit(
            "llm_respond",
            actor="llm",
            reason=f"Responded to user: {text[:100]} → {response[:100]}",
            result="completed",
        )

    def _get_llm_response(self, text: str) -> str:
        """Get a response from the LLM."""
        if hasattr(self, "_llm") and self._llm is not None:
            return str(self._llm.respond(text))  # type: ignore[attr-defined]
        return str(f"I heard you say: {text}. I'm JARVIS, your voice assistant.")

    def set_llm(self, llm: object) -> None:
        """Set an LLM instance with a .respond(text) -> str method."""
        self._llm: object = llm

    # -- Speaking ----------------------------------------------------------

    def _speak(self, text: str, level: InterruptLevel = InterruptLevel.L2_NORMAL) -> None:
        """Speak text via TTS, routed through the speech queue."""
        if self.is_kill_switch_active():
            return

        # Policy gate: T0 for speaking responses
        gate_result = self.policy_gate.evaluate(
            "speak_response", TrustTier.T0, {"text": text[:200]}
        )
        if gate_result.decision == GateDecision.DENY:
            self._audit(
                "speak_denied",
                actor="system",
                reason=f"Policy gate denied speak: {gate_result.reason}",
                result="denied",
            )
            return

        # Enqueue in speech queue
        self.speech_queue.enqueue(text, level, chunks=1)

        # Start playback
        started = self.speech_queue.start_next()
        if started is not None:
            self.state.speaking = True
            if self._on_speak:
                self._on_speak(text)
            if self._on_popup:
                self._on_popup("JARVIS", text)

    def _handle_proactive_speak(self, text: str) -> None:
        """Callback from proactive engine — speak a proactive alert."""
        if self.is_kill_switch_active():
            return
        self._speak(text, InterruptLevel.L2_NORMAL)

    def _handle_proactive_popup(self, title: str, body: str) -> None:
        """Callback from proactive engine — show a popup."""
        if self.is_kill_switch_active():
            return
        if self._on_popup:
            self._on_popup(title, body)

    def _handle_proactive_delivered(self, item: object) -> None:
        """Callback when a proactive item is delivered."""
        self.state.speaking = False

    def _handle_speech_chunk(self, chunk: object) -> None:
        """Callback when a speech chunk starts playing."""
        if self._on_speak and getattr(chunk, "status", None) and chunk.status.name == "PLAYING":  # type: ignore[attr-defined]
            # Check for barge-in (kill switch)
            if self.is_kill_switch_active():
                self.speech_queue.stop()

    def _handle_utterance_complete(self, utterance: Utterance) -> None:
        """Callback when an utterance completes."""
        self.state.speaking = False
        self._audit(
            "utterance_complete",
            actor="system",
            reason=f"Utterance {utterance.id} completed: {utterance.text[:100]}",
            result="completed",
        )

    # -- Proactive event ingestion -----------------------------------------

    def ingest_proactive_event(
        self,
        source: str,
        type_: str,
        payload: dict[str, object],
        importance_hint: float = 0.0,
        sensitive: bool = False,
    ) -> DeliveryDecision:
        """Ingest a proactive event (calendar, news, message, system alert)."""
        if self.is_kill_switch_active():
            return DeliveryDecision(
                interrupt_level=InterruptLevel.L1_LOW,
                should_speak=False,
                should_show_popup=False,
                reason="Kill switch active — proactive events suppressed",
                suppressed_by_context=True,
            )

        envelope = EventEnvelope(
            id=f"evt_{datetime.now(UTC).timestamp()}",
            source=source,
            type=type_,
            time=self.clock.now(),
            payload=payload,
            importance_hint=importance_hint,
            sensitive=sensitive,
        )
        event = Event(
            envelope=envelope,
            received_at=self.clock.now(),
            bus_id="voice_loop",
        )

        decision = self.proactive_engine.ingest(event)

        self._audit(
            "proactive_event_ingested",
            actor="system",
            reason=f"Proactive event from {source}: {decision.reason}",
            result=decision.reason,
            tier=str(decision.interrupt_level),
        )

        return decision

    def ingest_message_event(self, event: MessageEvent) -> None:
        """Ingest an inbound message from the message source adapter."""
        if self.is_kill_switch_active():
            return

        importance_hint = 0.8 if event.sensitive else 0.5

        self.ingest_proactive_event(
            source=event.source,
            type_="message.received",
            payload={
                "text": event.text,
                "from": event.from_contact,
                "thread_id": event.thread_id,
                "sensitive": event.sensitive,
                "partial": event.partial,
            },
            importance_hint=importance_hint,
            sensitive=event.sensitive,
        )

    def ingest_news_item(self, item: NewsItem) -> None:
        """Ingest a news item as a proactive alert."""
        self.ingest_proactive_event(
            source="news",
            type_="news.item.published",
            payload={
                "title": item.title,
                "text": item.summary,
                "source_name": item.source_name,
                "url": item.url,
                "official": item.official,
            },
            importance_hint=item.sensitivity_hint,
            sensitive=False,
        )

    # -- Audit -------------------------------------------------------------

    def _audit(
        self,
        action: str,
        actor: str,
        reason: str,
        result: str,
        tier: str | None = None,
        sensitive: bool = False,
    ) -> None:
        """Append an audit entry with a 'why'."""
        entry = AuditEntry(
            id=f"audit-{self.state.utterance_count + self.state.wake_word_count}",
            timestamp=self.clock.now(),
            action=action,
            actor=actor,
            reason=reason,
            result=result,
            tier=tier,
            sensitive=sensitive,
        )
        self.audit_log.append(entry)

    # -- Health ------------------------------------------------------------

    def health(self) -> dict[str, str]:
        """Return health status of all voice loop components."""
        return {
            "wake_word": self.wake_word.health(),
            "vad": self.vad.health(),
            "echo_canceller": self.echo.health(),
            "stt": self.stt.health(),
            "tts": self.tts.health(),
            "kill_switch": "active" if self.is_kill_switch_active() else "inactive",
            "listening": str(self.state.listening),
            "speaking": str(self.state.speaking),
        }


def create_default_voice_loop() -> VoiceLoop:
    """Create a voice loop with all fakes (for tests and walking skeleton)."""
    wake_word = FakeWakeWordSource()
    vad = FakeVoiceActivityDetector()
    echo = FakeEchoCanceller()
    stt = FakeSpeechToText()
    tts = FakeTextToSpeech()

    from jarvis.fakes import FakeAuditLog, FakeClock, FakePolicyGate

    policy_gate: PolicyGate = FakePolicyGate()  # type: ignore[assignment]
    audit_log = FakeAuditLog()
    clock = FakeClock()

    scorer = ImportanceScorer()
    proactive_engine = ProactiveEngine(scorer=scorer, now=clock.now)
    speech_queue = SpeechQueue()

    return VoiceLoop(
        wake_word=wake_word,
        vad=vad,
        echo_canceller=echo,
        stt=stt,
        tts=tts,
        policy_gate=policy_gate,
        audit_log=audit_log,
        clock=clock,
        proactive_engine=proactive_engine,
        speech_queue=speech_queue,
    )
