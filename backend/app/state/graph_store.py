"""SQLite-backed knowledge graph persistence using aiosqlite."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

from app.models.knowledge_graph import (
    EdgeType,
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
    NodeStatus,
)
from app.state.migrations import (
    CREATE_GRAPH_EDGES_TABLE_SQL,
    CREATE_GRAPH_NODES_TABLE_SQL,
)

from app.config.paths import ASSETS_DIR as _ASSETS_DIR

_DEFAULT_DB_PATH = _ASSETS_DIR / "graph.db"


class GraphStore:
    """Async CRUD store for knowledge graphs in SQLite.

    Uses aiosqlite directly (no ORM) for lightweight persistence.
    Database path defaults to ``data/assets/graph.db``.
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            db_path = _DEFAULT_DB_PATH
        self._db_path = str(db_path)
        self._connection: aiosqlite.Connection | None = None

    async def _get_connection(self) -> aiosqlite.Connection:
        """Lazily open (or return cached) aiosqlite connection."""
        if self._connection is None:
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            self._connection = await aiosqlite.connect(self._db_path)
        return self._connection

    async def init_db(self) -> None:
        """Create graph tables if they do not exist."""
        conn = await self._get_connection()
        await conn.execute(CREATE_GRAPH_NODES_TABLE_SQL)
        await conn.execute(CREATE_GRAPH_EDGES_TABLE_SQL)
        await conn.commit()

    # ------------------------------------------------------------------
    # Whole-graph operations
    # ------------------------------------------------------------------

    async def save_graph(self, graph: KnowledgeGraph) -> None:
        """Persist an entire ``KnowledgeGraph`` (upsert).

        Deletes existing nodes/edges for the same *scene_id* and re-inserts
        everything from *graph*.
        """
        conn = await self._get_connection()
        now = datetime.now(timezone.utc).isoformat()

        # Delete stale data
        await conn.execute(
            "DELETE FROM graph_edges WHERE scene_id = ?", (graph.scene_id,)
        )
        await conn.execute(
            "DELETE FROM graph_nodes WHERE scene_id = ?", (graph.scene_id,)
        )

        # Insert nodes
        for node in graph.nodes.values():
            is_bg = 1 if node.id == graph.background_node_id else 0
            await conn.execute(
                """INSERT INTO graph_nodes
                   (id, scene_id, serial_number, level, description,
                    status, background_flag, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    node.id,
                    graph.scene_id,
                    node.serial_number,
                    node.level,
                    node.description,
                    node.status.value,
                    is_bg,
                    now,
                ),
            )

        # Insert edges
        for edge in graph.edges:
            await conn.execute(
                """INSERT INTO graph_edges
                   (scene_id, from_node_id, to_node_id, edge_type,
                    visual_description, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    graph.scene_id,
                    edge.from_node_id,
                    edge.to_node_id,
                    edge.edge_type.value,
                    edge.visual_description,
                    now,
                ),
            )

        await conn.commit()

    async def load_graph(self, scene_id: str) -> KnowledgeGraph:
        """Load a ``KnowledgeGraph`` from SQLite.

        Returns an empty graph (no nodes/edges) if the scene has never been
        saved.
        """
        conn = await self._get_connection()
        graph = KnowledgeGraph(scene_id=scene_id)

        # Nodes
        cursor = await conn.execute(
            "SELECT id, serial_number, level, description, status, background_flag "
            "FROM graph_nodes WHERE scene_id = ?",
            (scene_id,),
        )
        rows = await cursor.fetchall()
        await cursor.close()

        for row in rows:
            node_id, serial, level, desc, status_val, bg_flag = row
            node = GraphNode(
                id=node_id,
                serial_number=serial,
                level=level,
                description=desc,
                status=NodeStatus(status_val),
            )
            graph.nodes[node_id] = node
            if bg_flag:
                graph.background_node_id = node_id

        # Edges
        cursor = await conn.execute(
            "SELECT from_node_id, to_node_id, edge_type, visual_description "
            "FROM graph_edges WHERE scene_id = ?",
            (scene_id,),
        )
        rows = await cursor.fetchall()
        await cursor.close()

        for row in rows:
            from_id, to_id, etype, vdesc = row
            edge = GraphEdge(
                from_node_id=from_id,
                to_node_id=to_id,
                edge_type=EdgeType(etype),
                visual_description=vdesc,
            )
            graph.edges.append(edge)

        return graph

    async def delete_graph(self, scene_id: str) -> None:
        """Remove all nodes and edges for *scene_id*."""
        conn = await self._get_connection()
        await conn.execute(
            "DELETE FROM graph_edges WHERE scene_id = ?", (scene_id,)
        )
        await conn.execute(
            "DELETE FROM graph_nodes WHERE scene_id = ?", (scene_id,)
        )
        await conn.commit()

    # ------------------------------------------------------------------
    # Incremental operations
    # ------------------------------------------------------------------

    async def add_node(self, scene_id: str, node: GraphNode) -> None:
        """Insert a single node (does NOT upsert — errors on duplicate id)."""
        conn = await self._get_connection()
        now = datetime.now(timezone.utc).isoformat()
        await conn.execute(
            """INSERT INTO graph_nodes
               (id, scene_id, serial_number, level, description,
                status, background_flag, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                node.id,
                scene_id,
                node.serial_number,
                node.level,
                node.description,
                node.status.value,
                0,
                now,
            ),
        )
        await conn.commit()

    async def add_edge(self, scene_id: str, edge: GraphEdge) -> None:
        """Insert a single edge."""
        conn = await self._get_connection()
        now = datetime.now(timezone.utc).isoformat()
        await conn.execute(
            """INSERT INTO graph_edges
               (scene_id, from_node_id, to_node_id, edge_type,
                visual_description, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                scene_id,
                edge.from_node_id,
                edge.to_node_id,
                edge.edge_type.value,
                edge.visual_description,
                now,
            ),
        )
        await conn.commit()

    async def update_node_description(
        self, scene_id: str, node_id: str, description: str
    ) -> None:
        """Update the description of an existing node."""
        conn = await self._get_connection()
        await conn.execute(
            "UPDATE graph_nodes SET description = ? WHERE scene_id = ? AND id = ?",
            (description, scene_id, node_id),
        )
        await conn.commit()

    async def update_edge_description(
        self, scene_id: str, edge_id: str, visual_desc: str
    ) -> None:
        """Update the visual_description of an edge identified by *edge_id*.

        *edge_id* is the SQLite row id (integer as string).  If you only have
        ``from_node_id`` / ``to_node_id``, query the row first.
        """
        conn = await self._get_connection()
        await conn.execute(
            "UPDATE graph_edges SET visual_description = ? "
            "WHERE scene_id = ? AND id = ?",
            (visual_desc, scene_id, int(edge_id)),
        )
        await conn.commit()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying SQLite connection."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
