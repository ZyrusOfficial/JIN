"""Property tests: speech queue invariants — simplified versions."""

from datetime import UTC, datetime

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from jarvis.domain.speech_queue import ChunkStatus, InterruptLevel, SpeechQueue

level_strategy = st.sampled_from(list(InterruptLevel))
text_strategy = st.text(min_size=1, max_size=30)


def _drain_queue(queue: SpeechQueue) -> list[str]:
    """Drain the queue completely, returning spoken utterance IDs."""
    spoken_ids = []
    while queue.queue_size > 0 or queue.current_utterance is not None:
        if queue.current_utterance is not None:
            utt = queue.current_utterance
            # Complete all pending chunks
            while not utt.is_complete:
                nxt = utt.next_pending_chunk
                if nxt is None:
                    # No pending chunks but not complete — force complete
                    # the currently playing chunk
                    for c in utt.chunks:
                        if c.status == ChunkStatus.PLAYING:
                            c.status = ChunkStatus.COMPLETED
                            c.completed_at = datetime.now(UTC)
                    break
                queue.checkpoint(nxt.id)
            if utt.is_complete:
                spoken_ids.append(utt.id)
                queue._current = None  # type: ignore[attr-defined]
        else:
            started = queue.start_next()
            if started is not None:
                # Immediately complete single-chunk utterances
                while not started.is_complete:
                    nxt = started.next_pending_chunk
                    if nxt is None:
                        break
                    queue.checkpoint(nxt.id)
                if started.is_complete:
                    spoken_ids.append(started.id)
    return spoken_ids


@given(
    texts=st.lists(text_strategy, min_size=1, max_size=10),
    levels=st.lists(level_strategy, min_size=1, max_size=10),
)
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_all_enqueued_are_spoken(texts: list[str], levels: list[InterruptLevel]) -> None:
    """Property: Every enqueued utterance eventually gets spoken."""
    queue = SpeechQueue()

    for text, level in zip(texts, levels):
        queue.enqueue(text, level)

    spoken_ids = _drain_queue(queue)

    # We can't compare exact IDs because queue reorders by priority,
    # but we can verify count matches
    expected_count = min(len(texts), len(levels))
    assert len(spoken_ids) == expected_count, (
        f"Expected {expected_count} spoken, got {len(spoken_ids)}"
    )


@given(
    texts=st.lists(text_strategy, min_size=1, max_size=10),
)
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_no_duplicate_speech(texts: list[str]) -> None:
    """Property: No utterance is spoken twice."""
    queue = SpeechQueue()

    for text in texts:
        queue.enqueue(text, InterruptLevel.L2_NORMAL)

    spoken_ids = _drain_queue(queue)

    assert len(spoken_ids) == len(set(spoken_ids)), "Duplicate speech detected"


@given(
    levels=st.lists(level_strategy, min_size=1, max_size=10),
)
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_l3_always_spoken(levels: list[InterruptLevel]) -> None:
    """Property: L3 critical items are always spoken (no lost L3 events)."""
    queue = SpeechQueue()

    utterances = [queue.enqueue(f"msg_{i}", level) for i, level in enumerate(levels)]

    l3_ids = {u.id for u in utterances if u.interrupt_level == InterruptLevel.L3_CRITICAL}

    spoken_ids = _drain_queue(queue)

    assert l3_ids.issubset(set(spoken_ids)), "L3 critical utterances were lost"
