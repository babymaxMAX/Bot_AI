from __future__ import annotations

import aiosqlite
from typing import Any, Optional


class MatchStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        self._db = await aiosqlite.connect(self._db_path)
        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                male_id TEXT NOT NULL,
                female_id TEXT NOT NULL,
                female_username TEXT,
                male_username TEXT,
                mutual INTEGER DEFAULT 0,
                paid INTEGER DEFAULT 0,
                invoice_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP
            )
            """
        )
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    async def create_match(
        self,
        *,
        male_id: str,
        female_id: str,
        mutual: bool,
        male_username: str | None = None,
        female_username: str | None = None,
    ) -> int:
        assert self._db is not None
        cur = await self._db.execute(
            """
            INSERT INTO matches (male_id, female_id, mutual, male_username, female_username)
            VALUES (?, ?, ?, ?, ?)
            """,
            (male_id, female_id, 1 if mutual else 0, male_username, female_username),
        )
        await self._db.commit()
        return int(cur.lastrowid)

    async def set_invoice_url(self, match_id: int, invoice_url: str) -> None:
        assert self._db is not None
        await self._db.execute(
            "UPDATE matches SET invoice_url = ? WHERE id = ?",
            (invoice_url, match_id),
        )
        await self._db.commit()

    async def mark_paid(self, match_id: int) -> None:
        assert self._db is not None
        await self._db.execute(
            "UPDATE matches SET paid = 1, paid_at = CURRENT_TIMESTAMP WHERE id = ?",
            (match_id,),
        )
        await self._db.commit()

    async def get_latest_match_for_user(self, user_id: str) -> Optional[dict[str, Any]]:
        assert self._db is not None
        cur = await self._db.execute(
            """
            SELECT id, male_id, female_id, female_username, male_username, mutual, paid, invoice_url
            FROM matches
            WHERE male_id = ? OR female_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (user_id, user_id),
        )
        row = await cur.fetchone()
        if not row:
            return None
        keys = [
            "id",
            "male_id",
            "female_id",
            "female_username",
            "male_username",
            "mutual",
            "paid",
            "invoice_url",
        ]
        return {k: row[i] for i, k in enumerate(keys)}

    async def list_matches_for_user(self, user_id: str, *, only_mutual: bool | None = None) -> list[dict[str, Any]]:
        assert self._db is not None
        if only_mutual is None:
            query = (
                "SELECT id, male_id, female_id, female_username, male_username, mutual, paid, invoice_url "
                "FROM matches WHERE male_id = ? OR female_id = ? ORDER BY id DESC"
            )
            params = (user_id, user_id)
        else:
            query = (
                "SELECT id, male_id, female_id, female_username, male_username, mutual, paid, invoice_url "
                "FROM matches WHERE (male_id = ? OR female_id = ?) AND mutual = ? ORDER BY id DESC"
            )
            params = (user_id, user_id, 1 if only_mutual else 0)
        cur = await self._db.execute(query, params)
        rows = await cur.fetchall()
        keys = [
            "id",
            "male_id",
            "female_id",
            "female_username",
            "male_username",
            "mutual",
            "paid",
            "invoice_url",
        ]
        return [{k: r[i] for i, k in enumerate(keys)} for r in rows]
