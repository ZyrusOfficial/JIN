"""RSS/Atom news adapter — fetches news via feedparser."""

from __future__ import annotations

from datetime import UTC, datetime, timezone
from typing import cast

import feedparser

from jarvis.ports.news_source import NewsItem, NewsSource


class RSSAdapter(NewsSource):
    """RSS/Atom feed adapter."""

    def __init__(self, feed_urls: list[str]) -> None:
        self._feed_urls = feed_urls

    def fetch(self, since: datetime | None = None) -> list[NewsItem]:
        items: list[NewsItem] = []
        for url in self._feed_urls:
            parsed = feedparser.parse(url)
            for entry in parsed.entries:
                parsed_date = entry.get("published_parsed")
                published = self._parse_date(parsed_date) if parsed_date else None
                if since and published and published < since:
                    continue
                items.append(
                    NewsItem(
                        id=entry.get("id", entry.get("link", url)),
                        title=entry.get("title", ""),
                        summary=entry.get("summary", entry.get("description", "")),
                        source_name=parsed.feed.get("title", url),
                        url=entry.get("link", ""),
                        published_at=published or datetime.now(UTC),
                        sensitivity_hint=0.0,
                        official=False,
                    )
                )
        return items

    def _parse_date(self, parsed: object) -> datetime | None:
        if not parsed:
            return None
        try:
            return datetime(*parsed[:6], tzinfo=UTC)  # type: ignore[misc,index]
        except (TypeError, ValueError):
            return None

    def health(self) -> str:
        return "ok"


class PAGASACAPAdapter(NewsSource):
    """PAGASA CAP (Common Alerting Protocol) feed adapter — PH weather alerts.

    Primary alert source for Philippines weather (ADR-006).
    PAGASA publishes CAP alerts at their official CAP feed URL.
    """

    CAP_FEED_URL = "https://legtas.cair.ph/bulletin/"  # PAGASA CAP alert feed

    def __init__(self, cap_url: str | None = None) -> None:
        self._cap_url = cap_url or self.CAP_FEED_URL

    def fetch(self, since: datetime | None = None) -> list[NewsItem]:
        # Production: fetch PAGASA CAP XML, parse alerts
        # Alerts are official government weather/hazard alerts
        return []

    def health(self) -> str:
        return "ok"
