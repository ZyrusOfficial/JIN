"""Logic-flow tests: speech queue — priority ordering, preemption, barge-in, checkpoints."""

from jarvis.domain.speech_queue import (
    ChunkStatus,
    InterruptLevel,
    SpeechChunk,
    SpeechQueue,
    Utterance,
)


def test_enqueue_orders_by_priority() -> None:
    """Queue orders by interrupt level: L3 first, then L2, then L1."""
    queue = SpeechQueue()

    u1 = queue.enqueue("low priority", InterruptLevel.L1_LOW)
    u3 = queue.enqueue("critical", InterruptLevel.L3_CRITICAL)
    u2 = queue.enqueue("normal", InterruptLevel.L2_NORMAL)

    assert queue.start_next().id == u3.id  # L3 first
    queue.checkpoint(u3.chunks[0].id)
    assert queue.start_next().id == u2.id  # L2 second
    queue.checkpoint(u2.chunks[0].id)
    assert queue.start_next().id == u1.id  # L1 last


def test_same_level_fifo() -> None:
    """Within the same level, FIFO order is preserved."""
    queue = SpeechQueue()

    u1 = queue.enqueue("first normal", InterruptLevel.L2_NORMAL)
    u2 = queue.enqueue("second normal", InterruptLevel.L2_NORMAL)

    assert queue.start_next().id == u1.id
    queue.checkpoint(u1.chunks[0].id)
    assert queue.start_next().id == u2.id


def test_checkpoint_advances_chunks() -> None:
    """Checkpoint between chunks advances playback."""
    queue = SpeechQueue()
    chunks_seen: list[str] = []
    queue.set_on_chunk(lambda c: chunks_seen.append(c.text))

    utt = queue.enqueue("Hello world", InterruptLevel.L2_NORMAL, chunks=3)
    queue.start_next()

    assert len(chunks_seen) == 1  # First chunk starts automatically
    assert chunks_seen[0] == "Hello world [chunk 1]"

    # Checkpoint advances to next chunk
    result = queue.checkpoint(utt.chunks[0].id)
    assert result is True
    assert len(chunks_seen) == 2
    assert chunks_seen[1] == "Hello world [chunk 2]"

    # Checkpoint again
    result = queue.checkpoint(utt.chunks[1].id)
    assert result is True
    assert len(chunks_seen) == 3
    result = queue.checkpoint(utt.chunks[2].id)
    assert result is True
    assert utt.is_complete


def test_barge_in_stops_speech() -> None:
    """Stop (barge-in/kill switch) halts all speech immediately."""
    queue = SpeechQueue()

    utt = queue.enqueue("Long message", InterruptLevel.L2_NORMAL, chunks=5)
    queue.start_next()
    assert queue.is_speaking

    stopped = queue.stop()
    assert stopped is not None
    assert stopped.id == utt.id
    assert not queue.is_speaking
    assert all(c.status == ChunkStatus.STOPPED for c in utt.chunks)


def test_higher_priority_preempts() -> None:
    """An L3 item preempts a currently speaking L1 item."""
    queue = SpeechQueue()
    preempted_ids: list[str] = []
    queue.set_on_preempted(lambda utt: preempted_ids.append(utt.id))

    low = queue.enqueue("low priority", InterruptLevel.L1_LOW, chunks=5)
    queue.start_next()
    assert queue.is_speaking

    high = queue.enqueue("critical alert", InterruptLevel.L3_CRITICAL)
    preempted = queue.preempt(InterruptLevel.L3_CRITICAL)
    assert preempted is not None
    assert preempted.id == low.id
    assert len(preempted_ids) == 1

    # After preemption, the high priority item starts
    assert queue.current_utterance is not None
    assert queue.current_utterance.id == high.id


def test_same_or_lower_priority_does_not_preempt() -> None:
    """L2 does not preempt L2; L1 does not preempt L2."""
    queue = SpeechQueue()

    low = queue.enqueue("low", InterruptLevel.L2_NORMAL, chunks=3)
    queue.start_next()

    # L2 preempting L2 should fail
    result = queue.preempt(InterruptLevel.L2_NORMAL)
    assert result is None
    assert queue.current_utterance is not None
    assert queue.current_utterance.id == low.id


def test_utterance_chunk_properties() -> None:
    """Utterance properties reflect chunk states correctly."""
    utt = Utterance(
        id="utt-1",
        text="Test",
        interrupt_level=InterruptLevel.L2_NORMAL,
        chunks=[
            SpeechChunk(id="c1", text="A", interrupt_level=InterruptLevel.L2_NORMAL, sequence=0),
            SpeechChunk(id="c2", text="B", interrupt_level=InterruptLevel.L2_NORMAL, sequence=1),
        ],
    )
    assert not utt.is_complete
    assert utt.next_pending_chunk is not None
    assert utt.next_pending_chunk.id == "c1"

    utt.chunks[0].status = ChunkStatus.COMPLETED
    assert not utt.is_complete

    utt.chunks[1].status = ChunkStatus.COMPLETED
    assert utt.is_complete
    assert utt.next_pending_chunk is None


def test_clear_queue() -> None:
    """Clear removes all queued utterances and stops current."""
    queue = SpeechQueue()
    queue.enqueue("a", InterruptLevel.L1_LOW)
    queue.enqueue("b", InterruptLevel.L1_LOW)
    queue.enqueue("c", InterruptLevel.L1_LOW)
    assert queue.queue_size == 3

    queue.clear()
    assert queue.queue_size == 0
