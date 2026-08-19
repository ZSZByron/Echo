"""Structured file snapshot store with one-way export from graphs.

Implements the "graph = source of truth" principle:
- Files are immutable snapshots exported from graphs
- Modifying a file does NOT update the graph
- Re-finalizing creates a new snapshot with a new graph_code
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import aiosqlite
from pydantic import BaseModel, Field

from app.models.knowledge_graph import KnowledgeGraph


class StructuredFile(BaseModel):
    """Immutable snapshot of structured data exported from a graph.

    Attributes:
        file_id: UUID primary key
        user_id: Owner user identifier
        graph_code: Version code matching the source graph (e.g., IP0001-W1-v1)
        kind: Type discriminator - "file" or "graph"
        status: "draft" or "finalized"
        payload: JSON content of the structured file
        created_at: ISO timestamp
    """

    file_id: str = Field(default_factory=lambda: f"file_{uuid4().hex}")
    user_id: str
    graph_code: str
    kind: str = Field(default="file")  # "file" or "graph"
    status: str = Field(default="draft")  # "draft" or "finalized"
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class StructuredFileStore:
    """SQLite-backed store for structured file snapshots.

    Core principle: Graph = source of truth, Files = one-way export.
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
        """Create structured_files table if not exists."""
        conn = await self._get_connection()
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS structured_files (
                file_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                graph_code TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'file',
                status TEXT NOT NULL DEFAULT 'draft',
                payload TEXT NOT NULL DEFAULT '{}',
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await conn.commit()

    async def save(self, file: StructuredFile) -> None:
        """Save or update a structured file snapshot.

        Args:
            file: StructuredFile to persist
        """
        conn = await self._get_connection()
        payload_json = json.dumps(file.payload)
        await conn.execute(
            """INSERT OR REPLACE INTO structured_files
               (file_id, user_id, graph_code, kind, status, payload, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (
                file.file_id,
                file.user_id,
                file.graph_code,
                file.kind,
                file.status,
                payload_json,
                file.created_at,
            ),
        )
        await conn.commit()

    async def get(self, file_id: str) -> StructuredFile | None:
        """Get a structured file by ID.

        Args:
            file_id: File identifier

        Returns:
            StructuredFile if found, None otherwise
        """
        conn = await self._get_connection()
        cursor = await conn.execute(
            """SELECT file_id, user_id, graph_code, kind, status, payload, created_at
               FROM structured_files WHERE file_id = ?""",
            (file_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()

        if row is None:
            return None

        file_id, user_id, graph_code, kind, status, payload_json, created_at = row
        payload = json.loads(payload_json)

        return StructuredFile(
            file_id=file_id,
            user_id=user_id,
            graph_code=graph_code,
            kind=kind,
            status=status,
            payload=payload,
            created_at=created_at,
        )

    async def list_by_user(self, user_id: str) -> list[StructuredFile]:
        """List all files for a user.

        Args:
            user_id: User identifier

        Returns:
            List of StructuredFile objects
        """
        conn = await self._get_connection()
        cursor = await conn.execute(
            """SELECT file_id, user_id, graph_code, kind, status, payload, created_at
               FROM structured_files WHERE user_id = ?
               ORDER BY created_at DESC""",
            (user_id,),
        )
        rows = await cursor.fetchall()
        await cursor.close()

        files = []
        for row in rows:
            file_id, user_id, graph_code, kind, status, payload_json, created_at = row
            payload = json.loads(payload_json)
            files.append(
                StructuredFile(
                    file_id=file_id,
                    user_id=user_id,
                    graph_code=graph_code,
                    kind=kind,
                    status=status,
                    payload=payload,
                    created_at=created_at,
                )
            )

        return files

    async def delete(self, file_id: str) -> None:
        """Delete a structured file.

        Args:
            file_id: File identifier
        """
        conn = await self._get_connection()
        await conn.execute(
            "DELETE FROM structured_files WHERE file_id = ?",
            (file_id,),
        )
        await conn.commit()

    async def export_file_from_graph(
        self,
        graph: KnowledgeGraph,
        user_id: str = "system",
    ) -> StructuredFile:
        """Export a graph to a structured file snapshot.

        This is a ONE-WAY export:
        - Graph → File snapshot
        - File modifications do NOT update the graph
        - Only re-finalizing creates a new snapshot

        Args:
            graph: Source KnowledgeGraph
            user_id: Owner user identifier (default: "system")

        Returns:
            StructuredFile snapshot with kind="graph"
        """
        # Serialize graph to JSON-serializable dict
        graph_data = {
            "scene_id": graph.scene_id,
            "background_node_id": graph.background_node_id,
            "nodes": {
                node_id: {
                    "id": node.id,
                    "serial_number": node.serial_number,
                    "level": node.level,
                    "description": node.description,
                    "status": node.status.value,
                }
                for node_id, node in graph.nodes.items()
            },
            "edges": [
                {
                    "from_node_id": edge.from_node_id,
                    "to_node_id": edge.to_node_id,
                    "edge_type": edge.edge_type.value,
                    "visual_description": edge.visual_description,
                }
                for edge in graph.edges
            ],
        }

        # Create file snapshot
        file_snapshot = StructuredFile(
            file_id=f"graph_snapshot_{uuid4().hex}",
            user_id=user_id,
            graph_code=f"graph_{graph.scene_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            kind="graph",
            status="finalized",
            payload=graph_data,
        )

        return file_snapshot

    async def close(self) -> None:
        """Close database connection."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
