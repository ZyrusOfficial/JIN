"""Logic-flow tests: proactive engine decision table.

Every row in the decision table is tested to ensure the engine's delivery
decision matches the expected outcome for each combination of importance,
interrupt level, context, and rate-limit state.
"""

from datetime import UTC, datetime, timedelta

import pytest

from jarvis.domain.decision_table import DECISION_TABLE, DecisionTableRow
from jarvis.domain.events import Event, EventEnvelope
from jarvis.domain.importance_scorer import ImportanceScorer, ScoringWeights
from jarvis.domain.models import InterruptLevel
from jarvis.domain.proactive_engine import (
    ContextSignals,
    EngineState,
    ProactiveEngine,
    RateLimitState,
)
from jarvis.ports.clock import Clock


class FixedClock(Clock):
    """Clock that returns a fixed time (for deterministic tests)."""

    def __init__(self, time: datetime) -> None:
        self._time = time

    def now(self) -> datetime:
        return self._time

    def advance(self, delta: timedelta) -> None:
        self._time += delta

    def sleep_until(self, target: datetime) -> None:
        self._time = target


def _make_event(
    event_id: str,
    source: str,
    importance_hint: float,
    payload: dict | None = None,
    sensitive: bool = False,
) -> Event:
    return Event(
        envelope=EventEnvelope(
            id=event_id,
            source=source,
            type="test.event",
            time=datetime(2026, 11, 20, 9, 0, 0, tzinfo=UTC),
            payload=payload or {},
            importance_hint=importance_hint,
            sensitive=sensitive,
        ),
        received_at=datetime(2026, 11, 20, 9, 0, 0, tzinfo=UTC),
        bus_id="bus_1",
    )


def _make_context(
    in_call: bool = False,
    fullscreen: bool = False,
    presentation: bool = False,
    focus_assist: bool = False,
    quiet_hours: bool = False,
    headphones: bool = False,
    idle: bool = False,
    locked: bool = False,
    typing: bool = False,
) -> ContextSignals:
    return ContextSignals(
        in_call=in_call,
        fullscreen=fullscreen,
        presentation=presentation,
        focus_assist=focus_assist,
        quiet_hours=quiet_hours,
        headphones=headphones,
        idle=idle,
        locked=locked,
        typing=typing,
    )


def _build_engine(
    row: DecisionTableRow,
    now: datetime,
    scorer: ImportanceScorer | None = None,
) -> ProactiveEngine:
    """Build a proactive engine configured to match a decision table row."""
    engine = ProactiveEngine(
        scorer=scorer or ImportanceScorer(ScoringWeights(source_rule=1.0)),
        rate_limit=RateLimitState(max_per_hour=6),
        now=lambda: now,
    )
    # Monkey-patch _build_context to return the row's context
    row_context = _make_context(
        in_call=row.in_call,
        fullscreen=row.fullscreen,
        presentation=row.presentation,
        focus_assist=row.focus_assist,
        quiet_hours=row.quiet_hours,
        headphones=row.headphones,
        idle=row.idle,
        locked=row.locked,
        typing=row.typing,
    )
    engine._build_context = lambda event: row_context  # type: ignore[method-assign]

    # Monkey-patch rate limit
    if row.rate_limited:
        engine.rate_limit.utterances.append(now)  # fill the hour
        for _ in range(5):
            engine.rate_limit.utterances.append(now)

    return engine


@pytest.mark.parametrize("row", DECISION_TABLE, ids=lambda r: r.id)
def test_decision_table_row(row: DecisionTableRow) -> None:
    """Each decision table row must produce the expected delivery decision."""
    now = datetime(2026, 11, 20, 9, 0, 0, tzinfo=UTC)

    # Create an event with importance in the row's range
    importance = (row.importance_min + row.importance_max) / 2
    event = _make_event(
        event_id=row.id,
        source="test",
        importance_hint=importance,
        payload={},
    )

    engine = _build_engine(row, now)

    # Directly call _decide with the row's context and rate-limit state
    context = engine._build_context(event)  # type: ignore[attr-defined]
    rate_limited = engine.rate_limit.is_rate_limited(now)

    decision = engine._decide(
        level=row.interrupt_level,
        context=context,
        rate_limited=rate_limited,
        breakdown=None,  # type: ignore[arg-type]
    )

    assert decision.should_speak == row.expected_should_speak, (
        f"Row {row.id}: should_speak={decision.should_speak}, expected {row.expected_should_speak}"
    )
    assert decision.should_show_popup == row.expected_should_show_popup, (
        f"Row {row.id}: should_show_popup={decision.should_show_popup}, expected {row.expected_should_show_popup}"
    )
    assert decision.rate_limited == row.expected_rate_limited, (
        f"Row {row.id}: rate_limited={decision.rate_limited}, expected {row.expected_rate_limited}"
    )
    assert decision.suppressed_by_context == row.expected_suppressed, (
        f"Row {row.id}: suppressed={decision.suppressed_by_context}, expected {row.expected_suppressed}"
    )
    assert row.expected_reason_contains in decision.reason, (
        f"Row {row.id}: reason '{decision.reason}' does not contain '{row.expected_reason_contains}'"
    )


def test_engine_state_transitions() -> None:
    """Engine transitions through states correctly on ingest and delivery."""
    now = datetime(2026, 11, 20, 9, 0, 0, tzinfo=UTC)
    engine = ProactiveEngine(now=lambda: now)

    assert engine.state == EngineState.IDLE

    # Ingest an L3 event
    event = _make_event("evt-1", "news", 0.9, {"text": "Breaking news", "source_name": "PAGASA"})
    engine._build_context = lambda e: ContextSignals(  # type: ignore[method-assign]
        in_call=False,
        fullscreen=False,
        presentation=False,
        focus_assist=False,
        quiet_hours=False,
        headphones=False,
        idle=False,
        locked=False,
        typing=False,
    )
    engine.scorer = ImportanceScorer(ScoringWeights(source_rule=1.0))

    decision = engine.ingest(event)
    assert decision.should_speak is True
    assert engine.state == EngineState.SPEAKING
    assert engine.current_item is not None


def test_preemption_higher_priority() -> None:
    """An L3 item preempts a currently speaking L1 item."""
    now = datetime(2026, 11, 20, 9, 0, 0, tzinfo=UTC)
    engine = ProactiveEngine(now=lambda: now)
    engine._build_context = lambda e: ContextSignals(  # type: ignore[method-assign]
        in_call=False,
        fullscreen=False,
        presentation=False,
        focus_assist=False,
        quiet_hours=False,
        headphones=False,
        idle=False,
        locked=False,
        typing=False,
    )
    engine.scorer = ImportanceScorer(ScoringWeights(source_rule=1.0))

    spoken: list[str] = []
    engine.set_on_speak(lambda text: spoken.append(text))

    # Ingest L1 item
    event_l1 = _make_event("evt-l1", "news", 0.2, {"text": "Low priority news"})
    engine.ingest(event_l1)
    assert engine.state == EngineState.SPEAKING

    # Preempt with L3
    preempted = engine.preempt(InterruptLevel.L3_CRITICAL)
    assert preempted is not None
    assert preempted.event.id == "evt-l1"
    assert engine.state == EngineState.PREEMPTED

    # Clear spoken from the L1 utterance
    spoken.clear()

    # Ingest L3 item (this calls _attempt_delivery internally)
    event_l3 = _make_event("evt-l3", "news", 0.9, {"text": "Critical alert"})
    engine.ingest(event_l3)
    assert engine.state == EngineState.SPEAKING
    assert "Critical alert" in spoken[0]


def test_rate_limit_max_six_per_hour() -> None:
    """Rate limit: max 6 unsolicited utterances per hour."""
    now = datetime(2026, 11, 20, 9, 0, 0, tzinfo=UTC)
    rate_limit = RateLimitState(max_per_hour=6)

    # Before each of the first 6 utterances, we should NOT be limited
    for i in range(6):
        assert not rate_limit.is_rate_limited(now), f"Should not be limited before {i + 1}"
        rate_limit.record(now)

    # After 6 utterances, the 7th should be rate limited
    assert rate_limit.is_rate_limited(now), "Should be rate limited after 6 utterances"


def test_rate_limit_window_expires() -> None:
    """Rate limit window is 1 hour — old utterances expire."""
    from datetime import timedelta

    now = datetime(2026, 11, 20, 9, 0, 0, tzinfo=UTC)
    rate_limit = RateLimitState(max_per_hour=2)

    # Record 2 utterances
    rate_limit.record(now)
    rate_limit.record(now)
    assert rate_limit.is_rate_limited(now)

    # Advance 1 hour + 1 second — they should expire
    later = now + timedelta(hours=1, seconds=1)
    assert not rate_limit.is_rate_limited(later)
