"""Fake news source — controllable news items for tests."""

from __future__ import annotations

from datetime import UTC, datetime

from jarvis.ports.news_source import NewsItem, NewsSource


class FakeNewsSource(NewsSource):
    """Fake news source for tests and the walking skeleton."""

    def __init__(self) -> None:
        self.items: list[NewsItem] = []
        self.fetch_fail = False

    def fetch(self, since: datetime | None = None) -> list[NewsItem]:
        if self.fetch_fail:
            raise RuntimeError("News fetch failure")
        if since is None:
            return list(self.items)
        return [item for item in self.items if item.published_at >= since]

    def add_item(
        self,
        title: str,
        summary: str,
        source_name: str,
        url: str,
        published_at: datetime | None = None,
        sensitivity_hint: float = 0.0,
        official: bool = False,
    ) -> NewsItem:
        item = NewsItem(
            id=f"news-{len(self.items)}",
            title=title,
            summary=summary,
            source_name=source_name,
            url=url,
            published_at=published_at or datetime.now(UTC),
            sensitivity_hint=sensitivity_hint,
            official=official,
        )
        self.items.append(item)
        return item

    def health(self) -> str:
        return "ok"
