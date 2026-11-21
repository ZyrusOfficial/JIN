"""Event coalescing — merge related events into single proactive items."""

from jarvis.domain.coalescing.engine import CoalescedEvent, CoalescingEngine

__all__ = ["CoalescedEvent", "CoalescingEngine"]
