from __future__ import annotations

import aiosqlite
from typing import Sequence
import pathlib


class DialogueStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        path = pathlib.Path(self._db_path)
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)

        self._db = await aiosqlite.connect(str(path))
        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    async def add_message(self, user_id: str, role: str, content: str) -> None:
        assert self._db is not None
        await self._db.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content),
        )
        await self._db.commit()

    async def get_recent_messages(self, user_id: str, limit: int = 12) -> list[dict[str, str]]:
        assert self._db is not None
        cur = await self._db.execute(
            "SELECT role, content FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        rows: Sequence[tuple[str, str]] = await cur.fetchall()
        return list(reversed([{"role": r[0], "content": r[1]} for r in rows]))
