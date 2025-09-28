from __future__ import annotations

import aiosqlite
import json
from typing import Any, Optional


class ProfileStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        self._db = await aiosqlite.connect(self._db_path)
        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                gender TEXT,
                bio TEXT,
                attributes TEXT,          -- JSON
                profile_number INTEGER,   -- номер анкеты в канале (опционально)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    async def upsert_profile(
        self,
        *,
        user_id: str,
        username: Optional[str] = None,
        gender: Optional[str] = None,
        bio: Optional[str] = None,
        attributes: Optional[dict[str, Any]] = None,
        profile_number: Optional[int] = None,
    ) -> None:
        assert self._db is not None
        attrs = json.dumps(attributes or {}, ensure_ascii=False)
        await self._db.execute(
            """
            INSERT INTO profiles (user_id, username, gender, bio, attributes, profile_number)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                gender=excluded.gender,
                bio=excluded.bio,
                attributes=excluded.attributes,
                profile_number=excluded.profile_number,
                updated_at=CURRENT_TIMESTAMP
            """,
            (user_id, username, gender, bio, attrs, profile_number),
        )
        await self._db.commit()

    async def get_profile(self, user_id: str) -> Optional[dict[str, Any]]:
        assert self._db is not None
        cur = await self._db.execute(
            "SELECT user_id, username, gender, bio, attributes, profile_number FROM profiles WHERE user_id = ?",
            (user_id,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        return {
            "user_id": row[0],
            "username": row[1],
            "gender": row[2],
            "bio": row[3],
            "attributes": json.loads(row[4] or "{}"),
            "profile_number": row[5],
        }

    async def find_by_number(self, profile_number: int) -> Optional[dict[str, Any]]:
        assert self._db is not None
        cur = await self._db.execute(
            "SELECT user_id, username, gender, bio, attributes, profile_number FROM profiles WHERE profile_number = ?",
            (profile_number,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        return {
            "user_id": row[0],
            "username": row[1],
            "gender": row[2],
            "bio": row[3],
            "attributes": json.loads(row[4] or "{}"),
            "profile_number": row[5],
        }

    async def list_profiles(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        assert self._db is not None
        cur = await self._db.execute(
            "SELECT user_id, username, gender, bio, attributes, profile_number FROM profiles ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cur.fetchall()
        items = []
        for r in rows:
            items.append(
                {
                    "user_id": r[0],
                    "username": r[1],
                    "gender": r[2],
                    "bio": r[3],
                    "attributes": json.loads(r[4] or "{}"),
                    "profile_number": r[5],
                }
            )
        return items
