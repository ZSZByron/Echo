"""SQLite state repository using aiosqlite + SQLAlchemy async."""
from __future__ import annotations

from typing import Any
import json
from pathlib import Path

import aiosqlite

from app.models.player import PlayerState, PlayerStatus
from app.state.migrations import CREATE_TABLE_SQL


class StateRepository:
    """Manages player state in SQLite."""

    def __init__(self, db_path: str = "ugc.db") -> None:
        """Initialize repository with database path.

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
        """Create table if not exists."""
        conn = await self._get_connection()
        await conn.execute(CREATE_TABLE_SQL)
        await conn.commit()

    async def get_state(self, player_id: str = "player_001") -> PlayerState | None:
        """Get player state from DB. Returns None if not found.

        Args:
            player_id: Unique player identifier

        Returns:
            PlayerState if found, None otherwise
        """
        conn = await self._get_connection()
        cursor = await conn.execute(
            "SELECT data FROM player_state WHERE id = ?",
            (player_id,)
        )
        row = await cursor.fetchone()
        await cursor.close()

        if row is None:
            return None

        data = json.loads(row[0])
        return PlayerState(**data)

    async def update_state(self, player_id: str, state: PlayerState) -> None:
        """Update or insert player state.

        Args:
            player_id: Unique player identifier
            state: Player state to save
        """
        conn = await self._get_connection()
        data_json = state.model_dump_json()
        await conn.execute(
            "INSERT OR REPLACE INTO player_state (id, data, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (player_id, data_json)
        )
        await conn.commit()

    async def reset_state(self, player_id: str = "player_001") -> PlayerState:
        """Reset player to default state from default_player.json.

        Args:
            player_id: Unique player identifier

        Returns:
            Reset PlayerState with default values
        """
        # Load default player data
        default_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "data"
            / "default_player.json"
        )

        with default_path.open(encoding="utf-8") as f:
            default_data = json.load(f)

        # Create PlayerState from default data
        default_state = PlayerState(**default_data)

        # Save to database
        await self.update_state(player_id, default_state)

        return default_state

    async def close(self) -> None:
        """Close database connection."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
