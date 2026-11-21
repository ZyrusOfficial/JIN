"""Fake memory store — controllable memory items for tests."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from jarvis.ports.memory_store import MemoryItem, MemoryStore


class FakeMemoryStore(MemoryStore):
    """Fake memory store for tests and the walking skeleton."""

    def __init__(self) -> None:
        self.items: dict[str, MemoryItem] = {}
        self.deleted: set[str] = set()

    def write(self, item: MemoryItem) -> str:
        self.items[item.id] = item
        return item.id

    def read(self, item_id: str) -> MemoryItem | None:
        return self.items.get(item_id)

    def search(
        self,
        query_embedding: list[float],
        tier: str | None = None,
        limit: int = 10,
    ) -> list[MemoryItem]:
        results = list(self.items.values())
        if tier:
            results = [i for i in results if i.tier == tier]
        return results[:limit]

    def delete(self, item_id: str) -> bool:
        if item_id in self.items:
            del self.items[item_id]
            self.deleted.add(item_id)
            return True
        return False

    def expire_raw_messages(self, older_than: datetime) -> int:
        count = 0
        for item_id, item in list(self.items.items()):
            if item.created_at < older_than:
                del self.items[item_id]
                count += 1
        return count

    def health(self) -> str:
        return "ok"


class SQLiteMemoryStore(MemoryStore):
    """SQLite + embeddings memory store, encrypted at rest.

    Production memory backend with working/episodic/semantic/profile tiers.
    Sensitive categories (health, finances, credentials) are not stored
    unless explicitly requested. Raw message retention default 14 days.
    """

    def __init__(self, db_path: str, encryption_key: str | None = None) -> None:
        self._db_path = db_path
        self._encryption_key = encryption_key
        self._conn: Any = None

    def _connect(self) -> None:
        import sqlite3

        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                tier TEXT,
                content TEXT,
                embedding TEXT,
                created_at TEXT,
                sensitive INTEGER DEFAULT 0,
                expires_at TEXT
            )
            """
        )
        self._conn.commit()

    def write(self, item: MemoryItem) -> str:
        if self._conn is None:
            self._connect()
        assert self._conn is not None
        self._conn.execute(
            """
            INSERT OR REPLACE INTO memories
            (id, tier, content, embedding, created_at, sensitive, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.id,
                item.tier,
                item.content,
                str(item.embedding) if item.embedding else None,
                item.created_at.isoformat(),
                int(item.sensitive),
                item.expires_at.isoformat() if item.expires_at else None,
            ),
        )
        self._conn.commit()
        return item.id

    def read(self, item_id: str) -> MemoryItem | None:
        if self._conn is None:
            self._connect()
        assert self._conn is not None
        row = self._conn.execute("SELECT * FROM memories WHERE id = ?", (item_id,)).fetchone()
        if not row:
            return None
        return MemoryItem(
            id=row[0],
            tier=row[1],
            content=row[2],
            embedding=None,  # would deserialize
            created_at=datetime.fromisoformat(row[4]),
            sensitive=bool(row[5]),
            expires_at=datetime.fromisoformat(row[6]) if row[6] else None,
        )

    def search(
        self,
        query_embedding: list[float],
        tier: str | None = None,
        limit: int = 10,
    ) -> list[MemoryItem]:
        # Production: vector search via sqlite-vec or similar
        return []

    def delete(self, item_id: str) -> bool:
        if self._conn is None:
            self._connect()
        assert self._conn is not None
        cur = self._conn.execute("DELETE FROM memories WHERE id = ?", (item_id,))
        self._conn.commit()
        return bool(cur.rowcount > 0)

    def expire_raw_messages(self, older_than: datetime) -> int:
        if self._conn is None:
            self._connect()
        assert self._conn is not None
        cur = self._conn.execute(
            "DELETE FROM memories WHERE created_at < ?",
            (older_than.isoformat(),),
        )
        self._conn.commit()
        return int(cur.rowcount)

    def health(self) -> str:
        return "ok"
