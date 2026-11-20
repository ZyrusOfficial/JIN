"""Speech queue — priority queue with preemption, barge-in, and chunk checkpoints.

Manages the order and timing of TTS output. A critical (L3) item can preempt
a low-priority one, speak, then offer to resume. Checkpoints between streamed
chunks check for barge-in, higher-priority interrupts, or stop commands.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from jarvis.domain.models import InterruptLevel


class ChunkStatus(Enum):
    """Status of a streamed audio chunk."""

    PENDING = "pending"
    PLAYING = "playing"
    COMPLETED = "completed"
    PREEMPTED = "preempted"
    STOPPED = "stopped"


@dataclass
class SpeechChunk:
    """A single chunk of speech to be spoken."""

    id: str
    text: str
    interrupt_level: InterruptLevel
    sequence: int
    status: ChunkStatus = ChunkStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class Utterance:
    """A complete utterance — one or more chunks."""

    id: str
    text: str
    interrupt_level: InterruptLevel
    chunks: list[SpeechChunk] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    preempted_at: datetime | None = None
    stopped_at: datetime | None = None

    @property
    def is_complete(self) -> bool:
        return all(c.status == ChunkStatus.COMPLETED for c in self.chunks)

    @property
    def is_preempted(self) -> bool:
        return self.preempted_at is not None

    @property
    def is_stopped(self) -> bool:
        return self.stopped_at is not None

    @property
    def next_pending_chunk(self) -> SpeechChunk | None:
        """Return the next pending chunk, or None if all complete/preempted."""
        for chunk in self.chunks:
            if chunk.status == ChunkStatus.PENDING:
                return chunk
        return None


class SpeechQueue:
    """Priority queue with preemption and checkpoint support.

    The queue orders utterances by interrupt level (L3 first, then L2, then L1).
    Within the same level, FIFO order is preserved.

    Checkpoints between chunks allow barge-in, higher-priority interrupts,
    or stop commands to halt speech instantly. Playback does NOT auto-advance
    between chunks — the caller must call checkpoint() to proceed.
    """

    def __init__(self) -> None:
        self._queue: list[Utterance] = []
        self._current: Utterance | None = None
        self._counter = 0

        # Callbacks
        self._on_chunk: Callable[[SpeechChunk], None] | None = None
        self._on_utterance_complete: Callable[[Utterance], None] | None = None
        self._on_preempted: Callable[[Utterance], None] | None = None

        # Barge-in / stop state
        self._stop_requested = False

    # -- Callbacks ----------------------------------------------------------

    def set_on_chunk(self, callback: Callable[[SpeechChunk], None]) -> None:
        self._on_chunk = callback

    def set_on_utterance_complete(self, callback: Callable[[Utterance], None]) -> None:
        self._on_utterance_complete = callback

    def set_on_preempted(self, callback: Callable[[Utterance], None]) -> None:
        self._on_preempted = callback

    # -- Enqueue ------------------------------------------------------------

    def enqueue(self, text: str, level: InterruptLevel, chunks: int = 1) -> Utterance:
        """Add an utterance to the queue. Returns the created utterance."""
        self._counter += 1
        utterance = Utterance(
            id=f"utt_{self._counter}",
            text=text,
            interrupt_level=level,
            chunks=[
                SpeechChunk(
                    id=f"utt_{self._counter}_chunk_{i}",
                    text=text if chunks == 1 else f"{text} [chunk {i + 1}]",
                    interrupt_level=level,
                    sequence=i,
                )
                for i in range(chunks)
            ],
        )
        self._queue.append(utterance)
        self._sort_queue()
        return utterance

    def _sort_queue(self) -> None:
        """Sort by interrupt level (L3 first), then insertion order."""
        level_order = {
            InterruptLevel.L3_CRITICAL: 0,
            InterruptLevel.L2_NORMAL: 1,
            InterruptLevel.L1_LOW: 2,
        }
        self._queue.sort(key=lambda u: (level_order[u.interrupt_level], u.created_at))

    # -- Playback -----------------------------------------------------------

    def start_next(self) -> Utterance | None:
        """Start speaking the next utterance in the queue.

        Returns the utterance that was started, or None if queue is empty.
        Only the FIRST chunk is set to PLAYING — the caller must use
        checkpoint() to advance between chunks.
        """
        if self._current is not None and not self._current.is_complete:
            return None  # Already speaking

        if self._current is not None:
            self._current = None  # Clear completed utterance

        if not self._queue:
            return None

        self._stop_requested = False
        self._current = self._queue.pop(0)

        # Play first chunk only
        chunk: SpeechChunk | None = self._current.next_pending_chunk
        if chunk is not None:
            chunk.status = ChunkStatus.PLAYING
            chunk.started_at = datetime.now(UTC)
            if self._on_chunk:
                self._on_chunk(chunk)

        return self._current

    def checkpoint(self, chunk_id: str) -> bool:
        """Mark a chunk as complete and advance to the next pending chunk.

        Returns False if stop was requested (barge-in/kill switch).
        Returns True if another chunk is now playing or utterance is complete.
        """
        if self._stop_requested:
            return False

        if self._current is None:
            return False

        # Mark the specified chunk as complete
        for c in self._current.chunks:
            if c.id == chunk_id:
                c.status = ChunkStatus.COMPLETED
                c.completed_at = datetime.now(UTC)
                break

        # Check if all chunks are complete
        if self._current.is_complete:
            self._current.completed_at = datetime.now(UTC)
            if self._on_utterance_complete:
                self._on_utterance_complete(self._current)
            self._current = None
            return True  # Utterance complete

        # Advance to next pending chunk
        chunk: SpeechChunk | None = self._current.next_pending_chunk
        if chunk is not None:
            chunk.status = ChunkStatus.PLAYING
            chunk.started_at = datetime.now(UTC)
            if self._on_chunk:
                self._on_chunk(chunk)

        return True

    def preempt(self, higher_level: InterruptLevel) -> Utterance | None:
        """Preempt the current utterance if a higher-priority one arrives.

        Returns the preempted utterance, or None if nothing was speaking
        or the new item isn't higher priority.
        """
        if self._current is None:
            return None

        level_order = {
            InterruptLevel.L3_CRITICAL: 0,
            InterruptLevel.L2_NORMAL: 1,
            InterruptLevel.L1_LOW: 2,
        }

        if level_order[higher_level] >= level_order[self._current.interrupt_level]:
            return None  # Not higher priority

        # Mark pending chunks as preempted
        for chunk in self._current.chunks:
            if chunk.status == ChunkStatus.PENDING:
                chunk.status = ChunkStatus.PREEMPTED

        self._current.preempted_at = datetime.now(UTC)
        preempted = self._current

        # Put remaining chunks back as a new utterance at the front
        remaining_chunks = [c for c in self._current.chunks if c.status == ChunkStatus.PENDING]
        if remaining_chunks:
            self._queue.insert(0, preempted)

        self._current = None
        if self._on_preempted:
            self._on_preempted(preempted)

        # Start the new higher-priority item (caller should have enqueued it)
        self.start_next()
        return preempted

    def stop(self) -> Utterance | None:
        """Stop all speech immediately (barge-in / kill switch)."""
        self._stop_requested = True
        if self._current is not None:
            for chunk in self._current.chunks:
                if chunk.status in (ChunkStatus.PENDING, ChunkStatus.PLAYING):
                    chunk.status = ChunkStatus.STOPPED
            self._current.stopped_at = datetime.now(UTC)
            stopped = self._current
            self._current = None
            return stopped
        return None

    # -- Inspection ---------------------------------------------------------

    @property
    def is_speaking(self) -> bool:
        return self._current is not None and not self._current.is_complete

    @property
    def current_utterance(self) -> Utterance | None:
        return self._current

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    @property
    def stop_requested(self) -> bool:
        return self._stop_requested

    def clear(self) -> None:
        """Clear the queue and stop current utterance."""
        self.stop()
        self._queue.clear()
