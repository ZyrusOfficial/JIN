"""Rate limiter for unsolicited utterances (max 6 per hour)."""

from jarvis.domain.rate_limiter.limiter import UtteranceRateLimiter

__all__ = ["UtteranceRateLimiter"]
