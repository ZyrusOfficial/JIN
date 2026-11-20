"""Fake memory store — in-memory SQLite-like store for tests."""

from datetime import datetime

from jarvis.ports.memory_store import MemoryItem, MemoryStore


class FakeMemoryStore(MemoryStore):
    def __init__(self) -> None:
        self.items: dict[str, MemoryItem] = {}

    def write(self, item: MemoryItem) -> str:
        self.items[item.id] = item
        return item.id

    def read(self, item_id: str) -> MemoryItem | None:
        return self.items.get(item_id)

    def search(
        self,
        query_embedding: list[float] | None,
        tier: str | None,
        limit: int,
    ) -> list[MemoryItem]:
        results = [i for i in self.items.values() if tier is None or i.tier == tier]
        return results[:limit]

    def delete(self, item_id: str) -> bool:
        if item_id in self.items:
            del self.items[item_id]
            return True
        return False

    def expire_raw_messages(self, older_than: datetime) -> int:
        count = 0
        for item_id, item in list(self.items.items()):
            if item.tier == "episodic" and item.created_at < older_than:
                del self.items[item_id]
                count += 1
        return count
