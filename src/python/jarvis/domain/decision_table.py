"""Proactive engine decision table — stored as data so tests can enumerate every row.

Each row defines: importance range, interrupt level, context conditions,
rate-limit state → expected delivery decision.

This is the single source of truth for the proactive engine's behavior.
Tests load this table and assert every row produces the expected outcome.
"""

from __future__ import annotations

from dataclasses import dataclass

from jarvis.domain.models import InterruptLevel


@dataclass(frozen=True)
class DecisionTableRow:
    """A single row in the proactive engine decision table."""

    id: str
    description: str
    importance_min: float
    importance_max: float
    interrupt_level: InterruptLevel
    in_call: bool
    fullscreen: bool
    presentation: bool
    focus_assist: bool
    quiet_hours: bool
    headphones: bool
    idle: bool
    locked: bool
    typing: bool
    rate_limited: bool
    expected_should_speak: bool
    expected_should_show_popup: bool
    expected_rate_limited: bool
    expected_suppressed: bool
    expected_reason_contains: str


# The complete decision table — every combination that matters.
# Tests should enumerate every row and assert the engine's output matches.
DECISION_TABLE: list[DecisionTableRow] = [
    # === L3 CRITICAL ===
    DecisionTableRow(
        id="L3-01",
        description="L3 critical, no context blocks, not rate limited",
        importance_min=0.7,
        importance_max=1.0,
        interrupt_level=InterruptLevel.L3_CRITICAL,
        in_call=False,
        fullscreen=False,
        presentation=False,
        focus_assist=False,
        quiet_hours=False,
        headphones=False,
        idle=False,
        locked=False,
        typing=False,
        rate_limited=False,
        expected_should_speak=True,
        expected_should_show_popup=True,
        expected_rate_limited=False,
        expected_suppressed=False,
        expected_reason_contains="L3 critical",
    ),
    DecisionTableRow(
        id="L3-02",
        description="L3 critical, device locked — popup only",
        importance_min=0.7,
        importance_max=1.0,
        interrupt_level=InterruptLevel.L3_CRITICAL,
        in_call=False,
        fullscreen=False,
        presentation=False,
        focus_assist=False,
        quiet_hours=False,
        headphones=False,
        idle=False,
        locked=True,
        typing=False,
        rate_limited=False,
        expected_should_speak=False,
        expected_should_show_popup=True,
        expected_rate_limited=False,
        expected_suppressed=True,
        expected_reason_contains="locked",
    ),
    DecisionTableRow(
        id="L3-03",
        description="L3 critical, in call — still speaks (critical overrides)",
        importance_min=0.7,
        importance_max=1.0,
        interrupt_level=InterruptLevel.L3_CRITICAL,
        in_call=True,
        fullscreen=False,
        presentation=False,
        focus_assist=False,
        quiet_hours=False,
        headphones=False,
        idle=False,
        locked=False,
        typing=False,
        rate_limited=False,
        expected_should_speak=True,
        expected_should_show_popup=True,
        expected_rate_limited=False,
        expected_suppressed=False,
        expected_reason_contains="L3 critical",
    ),
    # === L2 NORMAL ===
    DecisionTableRow(
        id="L2-01",
        description="L2 normal, idle, not typing, not rate limited",
        importance_min=0.4,
        importance_max=0.69,
        interrupt_level=InterruptLevel.L2_NORMAL,
        in_call=False,
        fullscreen=False,
        presentation=False,
        focus_assist=False,
        quiet_hours=False,
        headphones=False,
        idle=True,
        locked=False,
        typing=False,
        rate_limited=False,
        expected_should_speak=True,
        expected_should_show_popup=True,
        expected_rate_limited=False,
        expected_suppressed=False,
        expected_reason_contains="L2 normal",
    ),
    DecisionTableRow(
        id="L2-02",
        description="L2 normal, in call — suppressed",
        importance_min=0.4,
        importance_max=0.69,
        interrupt_level=InterruptLevel.L2_NORMAL,
        in_call=True,
        fullscreen=False,
        presentation=False,
        focus_assist=False,
        quiet_hours=False,
        headphones=False,
        idle=False,
        locked=False,
        typing=False,
        rate_limited=False,
        expected_should_speak=False,
        expected_should_show_popup=True,
        expected_rate_limited=False,
        expected_suppressed=True,
        expected_reason_contains="context blocks",
    ),
    DecisionTableRow(
        id="L2-03",
        description="L2 normal, fullscreen — suppressed",
        importance_min=0.4,
        importance_max=0.69,
        interrupt_level=InterruptLevel.L2_NORMAL,
        in_call=False,
        fullscreen=True,
        presentation=False,
        focus_assist=False,
        quiet_hours=False,
        headphones=False,
        idle=False,
        locked=False,
        typing=False,
        rate_limited=False,
        expected_should_speak=False,
        expected_should_show_popup=True,
        expected_rate_limited=False,
        expected_suppressed=True,
        expected_reason_contains="context blocks",
    ),
    DecisionTableRow(
        id="L2-04",
        description="L2 normal, quiet hours — suppressed",
        importance_min=0.4,
        importance_max=0.69,
        interrupt_level=InterruptLevel.L2_NORMAL,
        in_call=False,
        fullscreen=False,
        presentation=False,
        focus_assist=False,
        quiet_hours=True,
        headphones=False,
        idle=False,
        locked=False,
        typing=False,
        rate_limited=False,
        expected_should_speak=False,
        expected_should_show_popup=False,
        expected_rate_limited=False,
        expected_suppressed=True,
        expected_reason_contains="context blocks",
    ),
    DecisionTableRow(
        id="L2-05",
        description="L2 normal, typing — suppressed (not natural pause)",
        importance_min=0.4,
        importance_max=0.69,
        interrupt_level=InterruptLevel.L2_NORMAL,
        in_call=False,
        fullscreen=False,
        presentation=False,
        focus_assist=False,
        quiet_hours=False,
        headphones=False,
        idle=False,
        locked=False,
        typing=True,
        rate_limited=False,
        expected_should_speak=False,
        expected_should_show_popup=False,
        expected_rate_limited=False,
        expected_suppressed=True,
        expected_reason_contains="context blocks",
    ),
    DecisionTableRow(
        id="L2-06",
        description="L2 normal, rate limited — suppressed",
        importance_min=0.4,
        importance_max=0.69,
        interrupt_level=InterruptLevel.L2_NORMAL,
        in_call=False,
        fullscreen=False,
        presentation=False,
        focus_assist=False,
        quiet_hours=False,
        headphones=False,
        idle=True,
        locked=False,
        typing=False,
        rate_limited=True,
        expected_should_speak=False,
        expected_should_show_popup=False,
        expected_rate_limited=True,
        expected_suppressed=False,
        expected_reason_contains="rate limited",
    ),
    # === L1 LOW ===
    DecisionTableRow(
        id="L1-01",
        description="L1 low, idle, not rate limited",
        importance_min=0.0,
        importance_max=0.39,
        interrupt_level=InterruptLevel.L1_LOW,
        in_call=False,
        fullscreen=False,
        presentation=False,
        focus_assist=False,
        quiet_hours=False,
        headphones=False,
        idle=True,
        locked=False,
        typing=False,
        rate_limited=False,
        expected_should_speak=True,
        expected_should_show_popup=False,
        expected_rate_limited=False,
        expected_suppressed=False,
        expected_reason_contains="L1 low",
    ),
    DecisionTableRow(
        id="L1-02",
        description="L1 low, not idle — suppressed",
        importance_min=0.0,
        importance_max=0.39,
        interrupt_level=InterruptLevel.L1_LOW,
        in_call=False,
        fullscreen=False,
        presentation=False,
        focus_assist=False,
        quiet_hours=False,
        headphones=False,
        idle=False,
        locked=False,
        typing=False,
        rate_limited=False,
        expected_should_speak=False,
        expected_should_show_popup=False,
        expected_rate_limited=False,
        expected_suppressed=True,
        expected_reason_contains="not idle",
    ),
    DecisionTableRow(
        id="L1-03",
        description="L1 low, quiet hours — suppressed",
        importance_min=0.0,
        importance_max=0.39,
        interrupt_level=InterruptLevel.L1_LOW,
        in_call=False,
        fullscreen=False,
        presentation=False,
        focus_assist=False,
        quiet_hours=True,
        headphones=False,
        idle=True,
        locked=False,
        typing=False,
        rate_limited=False,
        expected_should_speak=False,
        expected_should_show_popup=False,
        expected_rate_limited=False,
        expected_suppressed=True,
        expected_reason_contains="not idle/quiet",
    ),
    DecisionTableRow(
        id="L1-04",
        description="L1 low, rate limited — suppressed",
        importance_min=0.0,
        importance_max=0.39,
        interrupt_level=InterruptLevel.L1_LOW,
        in_call=False,
        fullscreen=False,
        presentation=False,
        focus_assist=False,
        quiet_hours=False,
        headphones=False,
        idle=True,
        locked=False,
        typing=False,
        rate_limited=True,
        expected_should_speak=False,
        expected_should_show_popup=False,
        expected_rate_limited=True,
        expected_suppressed=False,
        expected_reason_contains="rate limited",
    ),
    # === Edge cases ===
    DecisionTableRow(
        id="EDGE-01",
        description="L1 low, locked — suppressed",
        importance_min=0.0,
        importance_max=0.39,
        interrupt_level=InterruptLevel.L1_LOW,
        in_call=False,
        fullscreen=False,
        presentation=False,
        focus_assist=False,
        quiet_hours=False,
        headphones=False,
        idle=True,
        locked=True,
        typing=False,
        rate_limited=False,
        expected_should_speak=False,
        expected_should_show_popup=False,
        expected_rate_limited=False,
        expected_suppressed=True,
        expected_reason_contains="not idle/quiet",
    ),
    DecisionTableRow(
        id="EDGE-02",
        description="L2 normal, presentation — suppressed",
        importance_min=0.4,
        importance_max=0.69,
        interrupt_level=InterruptLevel.L2_NORMAL,
        in_call=False,
        fullscreen=False,
        presentation=True,
        focus_assist=False,
        quiet_hours=False,
        headphones=False,
        idle=False,
        locked=False,
        typing=False,
        rate_limited=False,
        expected_should_speak=False,
        expected_should_show_popup=True,
        expected_rate_limited=False,
        expected_suppressed=True,
        expected_reason_contains="context blocks",
    ),
    DecisionTableRow(
        id="EDGE-03",
        description="L2 normal, focus assist — suppressed",
        importance_min=0.4,
        importance_max=0.69,
        interrupt_level=InterruptLevel.L2_NORMAL,
        in_call=False,
        fullscreen=False,
        presentation=False,
        focus_assist=True,
        quiet_hours=False,
        headphones=False,
        idle=False,
        locked=False,
        typing=False,
        rate_limited=False,
        expected_should_speak=False,
        expected_should_show_popup=True,
        expected_rate_limited=False,
        expected_suppressed=True,
        expected_reason_contains="context blocks",
    ),
]


def rows_for_level(level: InterruptLevel) -> list[DecisionTableRow]:
    """Return all decision table rows for a given interrupt level."""
    return [row for row in DECISION_TABLE if row.interrupt_level == level]


def rows_with_condition(**kwargs: object) -> list[DecisionTableRow]:
    """Return rows matching given context conditions (e.g. in_call=True)."""
    results = []
    for row in DECISION_TABLE:
        match = True
        for key, value in kwargs.items():
            if getattr(row, key) != value:
                match = False
                break
        if match:
            results.append(row)
    return results
