"""News source adapters — RSS/Atom/CAP feeds."""

from jarvis.adapters.news.fake_news import FakeNewsSource
from jarvis.adapters.news.pagasa_cap import PAGASACAPAdapter
from jarvis.adapters.news.rss_adapter import RSSAdapter

__all__ = ["FakeNewsSource", "PAGASACAPAdapter", "RSSAdapter"]
