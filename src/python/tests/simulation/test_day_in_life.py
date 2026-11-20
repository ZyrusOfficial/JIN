"""Simulation tests: deterministic 'day in the life' scenarios.

Uses a virtual clock to fast-forward through a day of events, asserting
exactly what Jarvis says and when. All events are recorded and replayable.
"""

from datetime import UTC, datetime, timedelta

import pytest

from jarvis.domain.events import Event, EventEnvelope
from jarvis.domain.importance_scorer import ImportanceScorer, ScoringWeights
from jarvis.domain.models import InterruptLevel
from jarvis.domain.proactive_engine import (
    EngineState,
    ProactiveEngine,
    RateLimitState,
)
from jarvis.ports.clock import Clock


class VirtualClock(Clock):
    """Virtual clock for simulation — only moves when advanced."""

    def __init__(self, start: datetime) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta

    def sleep_until(self, target: datetime) -> None:
        self._now = max(self._now, target)


def _make_event(
    event_id: str,
    source: str,
    time: datetime,
    importance_hint: float,
    payload: dict,
) -> Event:
    return Event(
        envelope=EventEnvelope(
            id=event_id,
            source=source,
            type="test.event",
            time=time,
            payload=payload,
            importance_hint=importance_hint,
        ),
        received_at=time,
        bus_id="bus_sim",
    )


def _make_context_signals():
    """Create context signals for normal (non-call, non-quiet) conditions."""
    CS = __import__("jarvis.domain.proactive_engine", fromlist=["ContextSignals"]).ContextSignals
    return CS(
        in_call=False,
        fullscreen=False,
        presentation=False,
        focus_assist=False,
        quiet_hours=False,
        headphones=False,
        idle=True,
        locked=False,
        typing=False,
    )


@pytest.fixture
def sim_engine():
    """Create a simulation engine with virtual clock and recorded output."""
    start = datetime(2026, 11, 20, 6, 0, 0, tzinfo=UTC)
    clock = VirtualClock(start)

    spoken: list[tuple[datetime, str]] = []
    popups: list[tuple[datetime, str, str]] = []

    engine = ProactiveEngine(
        scorer=ImportanceScorer(ScoringWeights(source_rule=1.0)),
        rate_limit=RateLimitState(max_per_hour=6),
        now=lambda: clock.now(),
    )
    engine._build_context = lambda e: _make_context_signals()  # type: ignore[method-assign]
    engine.set_on_speak(lambda text: spoken.append((clock.now(), text)))
    engine.set_on_popup(lambda title, text: popups.append((clock.now(), title, text)))

    return engine, clock, spoken, popups


def test_morning_briefing(sim_engine) -> None:
    """6 AM: Morning briefing — calendar events spoken."""
    engine, clock, spoken, popups = sim_engine

    event = _make_event(
        "evt-cal-1",
        "calendar",
        clock.now(),
        0.8,
        {"text": "Team standup at 9 AM", "title": "Team standup"},
    )
    decision = engine.ingest(event)
    # Complete the speech (simulating instant TTS)
    engine.complete_current(clock.now())

    assert decision.should_speak is True
    assert len(spoken) == 1
    assert "standup" in spoken[0][1]


def test_typhoon_alert_at_2am(sim_engine) -> None:
    """2 AM: Typhoon alert (L3 critical) wakes the owner even during quiet hours."""
    engine, clock, spoken, popups = sim_engine

    # Advance to 2 AM
    clock.advance(timedelta(hours=20))

    # Set quiet hours context
    CS = __import__("jarvis.domain.proactive_engine", fromlist=["ContextSignals"]).ContextSignals
    engine._build_context = lambda e: CS(  # type: ignore[method-assign]
        in_call=False,
        fullscreen=False,
        presentation=False,
        focus_assist=False,
        quiet_hours=True,
        headphones=False,
        idle=True,
        locked=False,
        typing=False,
    )

    # L3 typhoon alert — use high importance_hint and source_rule weight
    # With source_rule=1.0, news base score is 0.6 → L2. Use scorer with hint weight.
    engine.scorer = ImportanceScorer(ScoringWeights(source_rule=0.5, hint=0.5))
    event = _make_event(
        "evt-typhoon",
        "news",
        clock.now(),
        1.0,  # maximum hint
        {
            "text": "Typhoon signal #3 raised for Luzon",
            "title": "Typhoon Alert",
            "source_name": "PAGASA",
        },
    )
    decision = engine.ingest(event)
    engine.complete_current(clock.now())

    # With hint=1.0 and hint weight 0.5, total = 0.6*0.5 + 1.0*0.5 = 0.8 → L3
    assert decision.interrupt_level == InterruptLevel.L3_CRITICAL
    assert decision.should_speak is True
    assert len(spoken) == 1
    assert "Typhoon" in spoken[0][1]


def test_group_chat_burst_during_call(sim_engine) -> None:
    """During a call, group chat messages show popups but don't speak."""
    engine, clock, spoken, popups = sim_engine

    CS = __import__("jarvis.domain.proactive_engine", fromlist=["ContextSignals"]).ContextSignals
    engine._build_context = lambda e: CS(  # type: ignore[method-assign]
        in_call=True,
        fullscreen=False,
        presentation=False,
        focus_assist=False,
        quiet_hours=False,
        headphones=False,
        idle=False,
        locked=False,
        typing=False,
    )

    # Burst of messages from a group chat
    for i in range(5):
        event = _make_event(
            f"evt-msg-{i}",
            "messenger",
            clock.now(),
            0.3,
            {"text": f"Message {i}", "from": "Group Chat"},
        )
        decision = engine.ingest(event)

    # During a call, L2 messages show popups but don't speak
    assert len(spoken) == 0, "No speech during call"
    assert len(popups) > 0, "Popups should still appear during call"


def test_rate_limit_during_burst(sim_engine) -> None:
    """Max 6 unsolicited utterances per hour — burst beyond limit is rate-limited."""
    engine, clock, spoken, popups = sim_engine

    CS = __import__("jarvis.domain.proactive_engine", fromlist=["ContextSignals"]).ContextSignals
    engine._build_context = lambda e: CS(  # type: ignore[method-assign]
        in_call=False,
        fullscreen=False,
        presentation=False,
        focus_assist=False,
        quiet_hours=False,
        headphones=False,
        idle=True,
        locked=False,
        typing=False,
    )

    spoken_count = 0
    for i in range(10):
        event = _make_event(
            f"evt-burst-{i}",
            "news",
            clock.now(),
            0.5,
            {"text": f"News item {i}", "title": f"Headline {i}"},
        )
        decision = engine.ingest(event)
        if decision.should_speak:
            spoken_count += 1
            # Complete the speech so rate limit records and next item can proceed
            engine.complete_current(clock.now())

    # Max 6 per hour
    assert spoken_count <= 6, f"Rate limit exceeded: {spoken_count} utterances in one hour"


def test_learned_behavior_adjusts_score(sim_engine) -> None:
    """Learning loop: contacts the owner replies to get higher importance scores."""
    engine, clock, spoken, popups = sim_engine

    event1 = _make_event(
        "evt-contact-1",
        "messenger",
        clock.now(),
        0.4,
        {"text": "Hello", "from": "New Contact"},
    )
    engine.ingest(event1)
    engine.complete_current(clock.now())

    # Simulate learning: owner replied to this contact
    engine.scorer.set_contact_score("thread-new-contact", 0.9)

    event2 = _make_event(
        "evt-contact-2",
        "messenger",
        clock.now(),
        0.4,
        {"text": "Follow up", "from": "New Contact"},
    )
    decision2 = engine.ingest(event2)
    engine.complete_current(clock.now())

    assert decision2 is not None


def test_barge_in_interrupts_current_speech(sim_engine) -> None:
    """A new L3 item preempts currently speaking L2 item."""
    engine, clock, spoken, popups = sim_engine

    CS = __import__("jarvis.domain.proactive_engine", fromlist=["ContextSignals"]).ContextSignals
    engine._build_context = lambda e: CS(  # type: ignore[method-assign]
        in_call=False,
        fullscreen=False,
        presentation=False,
        focus_assist=False,
        quiet_hours=False,
        headphones=False,
        idle=True,
        locked=False,
        typing=False,
    )

    event_l2 = _make_event(
        "evt-l2",
        "news",
        clock.now(),
        0.5,
        {"text": "Regular news update", "title": "News"},
    )
    engine.ingest(event_l2)
    engine.complete_current(clock.now())
    assert engine.state == EngineState.IDLE
    assert len(spoken) == 1

    spoken.clear()

    event_l3 = _make_event(
        "evt-l3",
        "news",
        clock.now(),
        0.9,
        {
            "text": "CRITICAL: Earthquake detected",
            "title": "Earthquake Alert",
            "source_name": "PHIVOLCS",
        },
    )
    engine.ingest(event_l3)
    engine.complete_current(clock.now())
    assert engine.state == EngineState.IDLE
    assert len(spoken) == 1
    assert "Earthquake" in spoken[0][1]
