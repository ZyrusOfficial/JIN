"""Fake news source — controllable news items for tests."""

from datetime import datetime

from jarvis.ports.news_source import NewsItem, NewsSource


class FakeNewsSource(NewsSource):
    def __init__(self) -> None:
        self.items: list[NewsItem] = []

    def fetch(self, since: datetime | None = None) -> list[NewsItem]:
        if since is None:
            return list(self.items)
        return [i for i in self.items if i.published_at >= since]

    def add_item(self, item: NewsItem) -> None:
        self.items.append(item)

    def health(self) -> str:
        return "ok"
