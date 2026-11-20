"""Proactive engine — state machine that decides when and how to interrupt.

Pipeline: event → importance score → context check → delivery decision → speech queue.

States: Idle → Scoring → ContextCheck → Queued → Speaking → Preempted → Suppressed → Delivered

Interrupt levels:
  L3 critical: speak now, even over music
  L2 normal: next natural pause (~3s no typing, end of media track)
  L1 low: queue for idle or briefing
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum

from jarvis.domain.events import Event
from jarvis.domain.importance_scorer import ImportanceScorer, ScoreBreakdown
from jarvis.domain.models import DeliveryDecision, InterruptLevel

# Score thresholds for interrupt levels
_SCORE_L3_THRESHOLD = 0.7
_SCORE_L2_THRESHOLD = 0.4


class EngineState(Enum):
    """Proactive engine states."""

    IDLE = "idle"
    SCORING = "scoring"
    CONTEXT_CHECK = "context_check"
    QUEUED = "queued"
    SPEAKING = "speaking"
    PREEMPTED = "preempted"
    SUPPRESSED = "suppressed"
    DELIVERED = "delivered"


@dataclass
class ContextSignals:
    """Windows context signals that affect interrupt decisions."""

    in_call: bool = False
    fullscreen: bool = False
    presentation: bool = False
    focus_assist: bool = False
    quiet_hours: bool = False
    headphones: bool = False  # True if headphones, False if speakers
    idle: bool = False
    locked: bool = False
    typing: bool = False  # True if user is actively typing

    def allows_interrupt(self, level: InterruptLevel) -> bool:
        """Determine if this context allows an interrupt at the given level."""
        # L3 critical always interrupts (except locked)
        if level == InterruptLevel.L3_CRITICAL:
            return not self.locked

        # L2 and L1 are suppressed by call, fullscreen, presentation, focus assist
        if self.in_call or self.fullscreen or self.presentation or self.focus_assist or self.locked:
            return False

        # Quiet hours suppress L1 and L2
        if self.quiet_hours and level in (InterruptLevel.L1_LOW, InterruptLevel.L2_NORMAL):
            return False

        # L2 requires natural pause (not typing)
        if level == InterruptLevel.L2_NORMAL and self.typing:
            return False

        # L1 requires idle
        if level == InterruptLevel.L1_LOW and not self.idle:
            return False

        return True


@dataclass
class RateLimitState:
    """Tracks unsolicited utterance rate limits."""

    max_per_hour: int = 6
    utterances: deque[datetime] = field(default_factory=deque)

    def is_rate_limited(self, now: datetime) -> bool:
        """Check if we've exceeded the rate limit in the last hour."""
        cutoff = now - timedelta(hours=1)
        # Remove old entries
        while self.utterances and self.utterances[0] < cutoff:
            self.utterances.popleft()
        return len(self.utterances) >= self.max_per_hour

    def record(self, now: datetime) -> None:
        """Record an utterance."""
        self.utterances.append(now)

    def remaining(self, now: datetime) -> int:
        """Return remaining utterances allowed in the current hour."""
        cutoff = now - timedelta(hours=1)
        while self.utterances and self.utterances[0] < cutoff:
            self.utterances.popleft()
        return max(0, self.max_per_hour - len(self.utterances))


@dataclass
class ProactiveItem:
    """An item awaiting or in the process of proactive delivery."""

    event: Event
    score_breakdown: ScoreBreakdown
    interrupt_level: InterruptLevel
    created_at: datetime
    delivered_at: datetime | None = None
    suppressed_at: datetime | None = None
    preempted_at: datetime | None = None


class ProactiveEngine:
    """Proactive engine state machine.

    Transitions:
      Idle -> Scoring (on event)
      Scoring -> ContextCheck (score computed)
      ContextCheck -> Queued (allowed to interrupt)
      ContextCheck -> Suppressed (blocked by context/rate limit)
      Queued -> Speaking (turn comes up)
      Speaking -> Preempted (higher priority item arrives)
      Speaking -> Delivered (finished speaking)
      Preempted -> Speaking (resumed after preemption)
      Suppressed -> Idle (or retried later)
    """

    def __init__(
        self,
        scorer: ImportanceScorer | None = None,
        rate_limit: RateLimitState | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.scorer = scorer or ImportanceScorer()
        self.rate_limit = rate_limit or RateLimitState()
        self._now = now or (lambda: datetime.now(UTC))

        self._state = EngineState.IDLE
        self._queue: deque[ProactiveItem] = deque()
        self._current: ProactiveItem | None = None
        self._history: list[ProactiveItem] = []
        self._state_transitions: list[tuple[EngineState, EngineState, str]] = []

        # Callbacks (set by the voice pipeline / UI shell)
        self._on_speak: Callable[[str], None] | None = None
        self._on_popup: Callable[[str, str], None] | None = None
        self._on_delivered: Callable[[ProactiveItem], None] | None = None

    # -- State ---------------------------------------------------------------

    @property
    def state(self) -> EngineState:
        return self._state

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    @property
    def current_item(self) -> ProactiveItem | None:
        return self._current

    def state_transition_history(self) -> list[tuple[EngineState, EngineState, str]]:
        return list(self._state_transitions)

    def _transition(self, new_state: EngineState, reason: str) -> None:
        old_state = self._state
        self._state = new_state
        self._state_transitions.append((old_state, new_state, reason))

    # -- Callbacks -----------------------------------------------------------

    def set_on_speak(self, callback: Callable[[str], None]) -> None:
        self._on_speak = callback

    def set_on_popup(self, callback: Callable[[str, str], None]) -> None:
        self._on_popup = callback

    def set_on_delivered(self, callback: Callable[[ProactiveItem], None]) -> None:
        self._on_delivered = callback

    # -- Event ingestion -----------------------------------------------------

    def ingest(self, event: Event) -> DeliveryDecision:
        """Ingest an event and run the full pipeline. Returns the delivery decision."""
        now = self._now()

        # 1. Score
        self._transition(EngineState.SCORING, f"event {event.id}")
        breakdown = self.scorer.score(event, now)

        # 2. Determine interrupt level from score
        level = self._score_to_interrupt_level(breakdown.total)

        # 3. Context check
        self._transition(EngineState.CONTEXT_CHECK, f"score={breakdown.total:.2f}")
        context = self._build_context(event)

        # 4. Rate limit check
        rate_limited = self.rate_limit.is_rate_limited(now)

        # 5. Delivery decision
        decision = self._decide(level, context, rate_limited, breakdown)

        # 6. Execute decision
        if decision.suppressed_by_context:
            self._transition(EngineState.SUPPRESSED, "context or rate limit")
            item = ProactiveItem(
                event=event,
                score_breakdown=breakdown,
                interrupt_level=level,
                created_at=now,
                suppressed_at=now,
            )
            self._history.append(item)
            # Show popup even when suppressed (if decision says so)
            if decision.should_show_popup and self._on_popup:
                self._on_popup("JARVIS", self._render_speech(item))
            return decision

        if decision.rate_limited:
            self._transition(EngineState.SUPPRESSED, "rate limited")
            item = ProactiveItem(
                event=event,
                score_breakdown=breakdown,
                interrupt_level=level,
                created_at=now,
                suppressed_at=now,
            )
            self._history.append(item)
            # Rate-limited items don't show popups (they're deferred)
            return decision

        # Queue the item
        self._transition(EngineState.QUEUED, f"level={level.value}")
        item = ProactiveItem(
            event=event,
            score_breakdown=breakdown,
            interrupt_level=level,
            created_at=now,
        )
        self._queue.append(item)

        # Try to deliver immediately if nothing is speaking
        self._attempt_delivery(now)

        return decision

    def preempt(self, now: datetime | None = None) -> ProactiveItem | None:
        """Preempt the current speaking item (barge-in or higher priority)."""
        now = now or self._now()
        if self._current is not None and self._state == EngineState.SPEAKING:
            self._current.preempted_at = now
            self._transition(EngineState.PREEMPTED, "preempted")
            preempted = self._current
            self._current = None
            self._history.append(preempted)
            # Do NOT auto-attempt delivery — caller decides what to do next
            return preempted
        return None

    def complete_current(self, now: datetime | None = None) -> ProactiveItem | None:
        """Mark the current speaking item as delivered."""
        now = now or self._now()
        if self._current is not None:
            self._current.delivered_at = now
            self._transition(EngineState.DELIVERED, "completed")
            completed = self._current
            self._current = None
            self._history.append(completed)
            self._attempt_delivery(now)
            return completed
        return None

    def _attempt_delivery(self, now: datetime) -> None:
        """Try to deliver the next queued item."""
        if self._current is not None:
            return  # Already speaking

        if not self._queue:
            self._transition(EngineState.IDLE, "queue empty")
            return

        # Pop the highest priority item (queue is already ordered by level)
        item = self._queue.popleft()
        self._current = item

        # Check context again before speaking
        context = self._build_context(item.event)
        if not context.allows_interrupt(item.interrupt_level):
            # Still blocked — put back and suppress
            self._queue.appendleft(item)
            self._current = None
            self._transition(EngineState.SUPPRESSED, "context still blocking")
            item.suppressed_at = now
            self._history.append(item)
            return

        # Record rate limit usage
        self.rate_limit.record(now)

        # Speak
        self._transition(EngineState.SPEAKING, f"level={item.interrupt_level.value}")
        text = self._render_speech(item)
        if self._on_speak:
            self._on_speak(text)
        if self._on_popup:
            self._on_popup("JARVIS", text)

    def _score_to_interrupt_level(self, score: float) -> InterruptLevel:
        """Map importance score to interrupt level."""
        if score >= _SCORE_L3_THRESHOLD:
            return InterruptLevel.L3_CRITICAL
        if score >= _SCORE_L2_THRESHOLD:
            return InterruptLevel.L2_NORMAL
        return InterruptLevel.L1_LOW

    def _build_context(self, event: Event) -> ContextSignals:
        """Build context signals from event payload (deterministic for now)."""
        payload = event.payload
        return ContextSignals(
            in_call=payload.get("in_call", False),
            fullscreen=payload.get("fullscreen", False),
            presentation=payload.get("presentation", False),
            focus_assist=payload.get("focus_assist", False),
            quiet_hours=payload.get("quiet_hours", False),
            headphones=payload.get("headphones", False),
            idle=payload.get("idle", False),
            locked=payload.get("locked", False),
            typing=payload.get("typing", False),
        )

    def _decide(  # noqa: PLR0911
        self,
        level: InterruptLevel,
        context: ContextSignals,
        rate_limited: bool,
        breakdown: ScoreBreakdown,
    ) -> DeliveryDecision:
        """Make the delivery decision based on level, context, and rate limits."""
        # L3 critical: speak now unless locked
        if level == InterruptLevel.L3_CRITICAL:
            if context.locked:
                return DeliveryDecision(
                    interrupt_level=level,
                    should_speak=False,
                    should_show_popup=True,
                    reason="L3 critical but device locked — popup only",
                    suppressed_by_context=True,
                )
            return DeliveryDecision(
                interrupt_level=level,
                should_speak=True,
                should_show_popup=True,
                reason="L3 critical — speak now",
            )

        # L2 normal: next natural pause
        if level == InterruptLevel.L2_NORMAL:
            if rate_limited:
                return DeliveryDecision(
                    interrupt_level=level,
                    should_speak=False,
                    should_show_popup=False,
                    reason="L2 normal but rate limited",
                    rate_limited=True,
                )
            if not context.allows_interrupt(level):
                # Quiet hours and typing: fully suppressed (no popup)
                if context.quiet_hours or context.typing:
                    return DeliveryDecision(
                        interrupt_level=level,
                        should_speak=False,
                        should_show_popup=False,
                        reason="L2 normal but context blocks (quiet hours/typing)",
                        suppressed_by_context=True,
                    )
                return DeliveryDecision(
                    interrupt_level=level,
                    should_speak=False,
                    should_show_popup=True,
                    reason="L2 normal but context blocks (call/fullscreen/etc.)",
                    suppressed_by_context=True,
                )
            return DeliveryDecision(
                interrupt_level=level,
                should_speak=True,
                should_show_popup=True,
                reason="L2 normal — next natural pause",
            )

        # L1 low: queue for idle or briefing
        if level == InterruptLevel.L1_LOW:
            if rate_limited:
                return DeliveryDecision(
                    interrupt_level=level,
                    should_speak=False,
                    should_show_popup=False,
                    reason="L1 low but rate limited",
                    rate_limited=True,
                )
            if not context.allows_interrupt(level):
                return DeliveryDecision(
                    interrupt_level=level,
                    should_speak=False,
                    should_show_popup=False,
                    reason="L1 low but not idle/quiet",
                    suppressed_by_context=True,
                )
            return DeliveryDecision(
                interrupt_level=level,
                should_speak=True,
                should_show_popup=False,
                reason="L1 low — queued for idle",
            )

        return DeliveryDecision(
            interrupt_level=level,
            should_speak=False,
            should_show_popup=False,
            reason="Unknown interrupt level",
        )

    def _render_speech(self, item: ProactiveItem) -> str:
        """Render a proactive item into speakable text."""
        event = item.event
        source = event.source
        text = event.payload.get("text", event.payload.get("title", ""))
        if source == "news":
            return f"Breaking: {text}. Source: {event.payload.get('source_name', 'unknown')}."
        if source == "calendar":
            return f"Calendar alert: {text}."
        if source in ("messenger", "sms"):
            return f"New message from {event.payload.get('from', 'unknown')}: {text}."
        return text or "You have a new notification."
