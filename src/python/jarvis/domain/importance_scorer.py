"""Importance scorer — combines source rules, content classification, recency,
and learned behavior into a 0..1 importance score.

Used by the proactive engine to determine interrupt level.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from jarvis.domain.events import Event


@dataclass
class ScoringWeights:
    """Configurable weights for the importance scoring formula."""

    source_rule: float = 0.30  # VIP contact, official alert feed, calendar proximity
    content_classification: float = 0.25  # urgent, question, social, spam
    recency: float = 0.20  # how recent the event is
    learned_behavior: float = 0.15  # what the owner acts on vs dismisses
    hint: float = 0.10  # source-supplied importance_hint

    def normalized(self) -> ScoringWeights:
        """Return weights normalized to sum to 1.0."""
        total = (
            self.source_rule
            + self.content_classification
            + self.recency
            + self.learned_behavior
            + self.hint
        )
        if total == 0:
            return ScoringWeights()
        return ScoringWeights(
            source_rule=self.source_rule / total,
            content_classification=self.content_classification / total,
            recency=self.recency / total,
            learned_behavior=self.learned_behavior / total,
            hint=self.hint / total,
        )


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of an importance score."""

    source_rule_score: float
    content_classification_score: float
    recency_score: float
    learned_behavior_score: float
    hint_score: float
    total: float


class ImportanceScorer:
    """Scores event importance from 0.0 to 1.0.

    The score combines multiple factors with configurable weights. All inputs
    are clamped to [0, 1] before weighting.
    """

    def __init__(self, weights: ScoringWeights | None = None) -> None:
        self.weights = (weights or ScoringWeights()).normalized()
        # Learned behavior: contact_id -> average positive response rate (0..1)
        self._contact_scores: dict[str, float] = {}
        # Source type -> base importance (official alerts score high)
        self._source_base_scores: dict[str, float] = {
            "news": 0.6,  # official feeds score higher
            "calendar": 0.7,  # calendar events are important
            "system": 0.5,
            "messenger": 0.4,
            "sms": 0.4,
            "user": 0.3,
        }

    def set_contact_score(self, contact_id: str, score: float) -> None:
        """Record learned behavior score for a contact (0..1)."""
        self._contact_scores[contact_id] = max(0.0, min(1.0, score))

    def set_source_base_score(self, source: str, score: float) -> None:
        """Set base importance for a source type (0..1)."""
        self._source_base_scores[source] = max(0.0, min(1.0, score))

    def score(self, event: Event, now: datetime | None = None) -> ScoreBreakdown:
        """Score an event's importance.

        Returns a ScoreBreakdown with the total clamped to [0, 1].
        """
        now = now or datetime.now(UTC)

        # Source rule score: VIP contact, official alert, calendar proximity
        source_score = self._source_base_scores.get(event.source, 0.3)
        if event.thread_id:
            contact_score = self._contact_scores.get(event.thread_id, 0.3)
            source_score = max(source_score, contact_score)
        source_score = max(0.0, min(1.0, source_score))

        # Content classification: derived from payload keywords (deterministic)
        content_score = self._classify_content(event.payload)

        # Recency score: decays exponentially with age
        age_seconds = (now - event.time).total_seconds()
        recency_score = self._recency_decay(age_seconds)

        # Learned behavior: from contact history
        learned_score = self._contact_scores.get(event.thread_id or "", 0.5)

        # Hint score: source-supplied hint
        hint_score = max(0.0, min(1.0, event.importance_hint))

        # Weighted total
        total = (
            source_score * self.weights.source_rule
            + content_score * self.weights.content_classification
            + recency_score * self.weights.recency
            + learned_score * self.weights.learned_behavior
            + hint_score * self.weights.hint
        )
        total = max(0.0, min(1.0, total))

        return ScoreBreakdown(
            source_rule_score=source_score,
            content_classification_score=content_score,
            recency_score=recency_score,
            learned_behavior_score=learned_score,
            hint_score=hint_score,
            total=total,
        )

    def _classify_content(self, payload: dict[str, object]) -> float:
        """Deterministic content classification from payload keywords.

        Returns 0..1 where higher = more important/urgent.
        """
        text = ""
        text_val = payload.get("text")
        title_val = payload.get("title")
        summary_val = payload.get("summary")
        if isinstance(text_val, str):
            text = text_val
        elif isinstance(title_val, str):
            text = title_val
        elif isinstance(summary_val, str):
            text = summary_val

        text_lower = text.lower()

        # Urgent keywords
        urgent = [
            "urgent",
            "emergency",
            "help",
            "alert",
            "warning",
            "critical",
            "now",
            "immediately",
        ]
        # Question keywords
        question = ["?", "can you", "could you", "please", "remind", "schedule"]
        # Spam/low-value keywords
        spam = ["sale", "discount", "promo", "unsubscribe", "newsletter", "offer"]

        urgent_count = sum(1 for kw in urgent if kw in text_lower)
        question_count = sum(1 for kw in question if kw in text_lower)
        spam_count = sum(1 for kw in spam if kw in text_lower)

        # Score: urgent raises, questions moderately raise, spam lowers
        score = 0.3  # baseline
        score += min(0.4, urgent_count * 0.15)
        score += min(0.2, question_count * 0.08)
        score -= min(0.3, spam_count * 0.10)

        return max(0.0, min(1.0, score))

    def _recency_decay(self, age_seconds: float) -> float:
        """Exponential decay: 1.0 now, ~0.5 after 1 hour, ~0.1 after 6 hours."""
        half_life_seconds = 3600.0  # 1 hour
        return float(max(0.0, min(1.0, 2.0 ** (-age_seconds / half_life_seconds))))
