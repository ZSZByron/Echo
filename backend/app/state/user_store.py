"""User store for persisting user identity information.

Implements the UserStore.save(user_id: str, tier: str) signature
required by the identity registration system.
"""
from __future__ import annotations

import aiosqlite


class UserStore:
    """SQLite-backed store for user identity data.

    Signature-compatible with MockUserStore from T1:
    - save(user_id: str, tier: str) -> None
    """

    def __init__(self, db_path: str = "ugc.db") -> None:
        """Initialize store with database path.

        Args:
            db_path: Path to SQLite database file
        """
        self._db_path = db_path
        self._connection: aiosqlite.Connection | None = None

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get or create database connection.

        Returns:
            Active aiosqlite connection
        """
        if self._connection is None:
            self._connection = await aiosqlite.connect(self._db_path)
        return self._connection

    async def init_db(self) -> None:
        """Create users table if not exists."""
        conn = await self._get_connection()
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                tier TEXT NOT NULL DEFAULT 'FREE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await conn.commit()

    async def save(self, user_id: str, tier: str) -> None:
        """Save or update user tier information.

        This method signature is REQUIRED for compatibility with
        the register() function in app.domains.identity.key_manager.

        Args:
            user_id: Unique user identifier
            tier: User tier level (e.g., "FREE", "VIP", "SVIP")
        """
        conn = await self._get_connection()
        await conn.execute(
            """INSERT OR REPLACE INTO users (user_id, tier, created_at, updated_at)
               VALUES (?, ?, COALESCE((SELECT created_at FROM users WHERE user_id = ?), CURRENT_TIMESTAMP), CURRENT_TIMESTAMP)""",
            (user_id, tier, user_id),
        )
        await conn.commit()

    async def get(self, user_id: str) -> dict | None:
        """Get user information by ID.

        Args:
            user_id: User identifier

        Returns:
            Dict with user_id and tier if found, None otherwise
        """
        conn = await self._get_connection()
        cursor = await conn.execute(
            "SELECT user_id, tier FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()

        if row is None:
            return None

        user_id, tier = row
        return {"user_id": user_id, "tier": tier}

    async def close(self) -> None:
        """Close database connection."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
