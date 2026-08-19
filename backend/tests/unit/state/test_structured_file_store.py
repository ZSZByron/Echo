"""Tests for StructuredFileStore, UserStore, and graph_store migrations.

Following TDD: All tests FAIL first, then implementation makes them PASS.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

from app.state.structured_file_store import StructuredFileStore, StructuredFile
from app.state.user_store import UserStore
from app.state.graph_store import GraphStore
from app.models.knowledge_graph import KnowledgeGraph, GraphNode, NodeStatus


@pytest.fixture
async def temp_db(tmp_path: Path) -> str:
    """Create temporary database path."""
    return str(tmp_path / "test.db")


# ============================================================================
# StructuredFileStore Tests (RED phase - these should FAIL initially)
# ============================================================================


@pytest.mark.asyncio
async def test_structured_file_store_crud(temp_db: str) -> None:
    """Test basic CRUD operations for StructuredFileStore."""
    store = StructuredFileStore(db_path=temp_db)
    await store.init_db()

    # CREATE
    file_id = "file_001"
    user_id = "u_test123"
    graph_code = "IP0001-W1-v1"
    file_data = StructuredFile(
        file_id=file_id,
        user_id=user_id,
        graph_code=graph_code,
        kind="file",
        status="draft",
        payload={"data": "test content"},
        created_at=datetime.now(timezone.utc).isoformat()
    )

    await store.save(file_data)

    # READ
    retrieved = await store.get(file_id)
    assert retrieved is not None
    assert retrieved.file_id == file_id
    assert retrieved.user_id == user_id
    assert retrieved.graph_code == graph_code
    assert retrieved.kind == "file"
    assert retrieved.status == "draft"

    # UPDATE
    updated = StructuredFile(
        file_id=file_id,
        user_id=user_id,
        graph_code=graph_code,
        kind="file",
        status="finalized",
        payload={"data": "updated content"},
        created_at=retrieved.created_at
    )
    await store.save(updated)

    retrieved_after_update = await store.get(file_id)
    assert retrieved_after_update is not None
    assert retrieved_after_update.status == "finalized"
    assert retrieved_after_update.payload["data"] == "updated content"

    # LIST by user
    user_files = await store.list_by_user(user_id)
    assert len(user_files) == 1
    assert user_files[0].file_id == file_id

    # DELETE
    await store.delete(file_id)
    deleted = await store.get(file_id)
    assert deleted is None


@pytest.mark.asyncio
async def test_structured_file_store_export_from_graph(temp_db: str) -> None:
    """Test one-way export: graph -> file snapshot."""
    store = StructuredFileStore(db_path=temp_db)
    await store.init_db()

    # Create a mock graph
    graph = KnowledgeGraph(scene_id="test_scene")
    graph.nodes = {
        "node1": GraphNode(
            id="node1",
            serial_number="001",
            level=1,
            description="Test node",
            status=NodeStatus.PENDING
        )
    }

    # Export graph to file
    file_snapshot = await store.export_file_from_graph(graph)
    assert file_snapshot is not None
    assert file_snapshot.kind == "graph"
    assert file_snapshot.status == "finalized"
    assert file_snapshot.payload is not None
    assert "nodes" in file_snapshot.payload

    # Save the snapshot
    await store.save(file_snapshot)

    # Retrieve and verify
    retrieved = await store.get(file_snapshot.file_id)
    assert retrieved is not None
    assert retrieved.kind == "graph"


@pytest.mark.asyncio
async def test_one_way_export_file_modification_does_not_update_graph(temp_db: str) -> None:
    """Test critical constraint: modifying file does NOT update graph.

    This is the core "graph = source of truth" test.
    Only re-finalizing should create a new snapshot.
    """
    store = StructuredFileStore(db_path=temp_db)
    await store.init_db()

    # Create initial graph snapshot
    graph = KnowledgeGraph(scene_id="test_scene")
    graph.nodes = {
        "node1": GraphNode(
            id="node1",
            serial_number="001",
            level=1,
            description="Original description",
            status=NodeStatus.PENDING
        )
    }

    file_snapshot = await store.export_file_from_graph(graph)
    original_graph_code = file_snapshot.graph_code
    await store.save(file_snapshot)

    # Modify the file (simulate user editing structured file)
    modified_file = StructuredFile(
        file_id=file_snapshot.file_id,
        user_id=file_snapshot.user_id,
        graph_code=original_graph_code,
        kind="file",
        status="draft",
        payload={"modified": "content"},
        created_at=file_snapshot.created_at
    )
    await store.save(modified_file)

    # Retrieve the file and verify graph_code unchanged
    retrieved = await store.get(file_snapshot.file_id)
    assert retrieved is not None
    assert retrieved.graph_code == original_graph_code

    # Verify no new graph snapshot was created
    user_files = await store.list_by_user(file_snapshot.user_id)
    # Should only have 1 file (the modified one), not 2
    assert len(user_files) == 1


# ============================================================================
# UserStore Tests (RED phase)
# ============================================================================


@pytest.mark.asyncio
async def test_user_store_save(temp_db: str) -> None:
    """Test UserStore.save() method signature compatibility."""
    store = UserStore(db_path=temp_db)
    await store.init_db()

    user_id = "u_testuser"
    tier = "FREE"

    # Save should work with signature: save(user_id: str, tier: str)
    await store.save(user_id, tier)

    # Retrieve and verify
    retrieved = await store.get(user_id)
    assert retrieved is not None
    assert retrieved["user_id"] == user_id
    assert retrieved["tier"] == tier


@pytest.mark.asyncio
async def test_user_store_duplicate_save_overwrites(temp_db: str) -> None:
    """Test that saving same user_id twice overwrites (idempotent)."""
    store = UserStore(db_path=temp_db)
    await store.init_db()

    user_id = "u_testuser"

    # Save first time
    await store.save(user_id, "FREE")

    # Save same user_id with different tier
    await store.save(user_id, "VIP")

    # Verify only one record exists with latest tier
    retrieved = await store.get(user_id)
    assert retrieved is not None
    assert retrieved["tier"] == "VIP"


# ============================================================================
# GraphStore Migration Tests (RED phase)
# ============================================================================


@pytest.mark.asyncio
async def test_graph_store_migration_adds_new_columns(temp_db: str) -> None:
    """Test that migration adds status, parent_graph_code, change_set columns."""
    store = GraphStore(db_path=temp_db)

    # Initialize with migration
    await store.init_db()

    # Verify new columns exist by checking PRAGMA table_info
    conn = await store._get_connection()
    cursor = await conn.execute("PRAGMA table_info(graph_nodes)")
    columns = await cursor.fetchall()
    await cursor.close()

    column_names = {col[1] for col in columns}  # col[1] is the name

    # Check new columns exist
    assert "status" in column_names
    assert "parent_graph_code" in column_names
    assert "change_set" in column_names


@pytest.mark.asyncio
async def test_graph_store_migration_is_idempotent(temp_db: str) -> None:
    """Test that running migration twice doesn't fail (idempotent)."""
    store = GraphStore(db_path=temp_db)

    # Run migration first time
    await store.init_db()

    # Run migration second time - should not fail
    await store.init_db()

    # Verify columns still exist
    conn = await store._get_connection()
    cursor = await conn.execute("PRAGMA table_info(graph_nodes)")
    columns = await cursor.fetchall()
    await cursor.close()

    column_names = {col[1] for col in columns}
    assert "status" in column_names
    assert "parent_graph_code" in column_names
    assert "change_set" in column_names


@pytest.mark.asyncio
async def test_graph_store_backward_compatible_with_old_schema(temp_db: str) -> None:
    """Test that migration works with existing old schema (no new columns)."""
    import aiosqlite

    # Create old schema manually (without new columns)
    conn = await aiosqlite.connect(temp_db)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS graph_nodes (
            id TEXT NOT NULL,
            scene_id TEXT NOT NULL,
            serial_number TEXT NOT NULL,
            level INTEGER NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            background_flag INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id, scene_id)
        );
    """)
    await conn.commit()
    await conn.close()

    # Now run migration - should add missing columns
    store = GraphStore(db_path=temp_db)
    await store.init_db()

    # Verify new columns were added
    conn = await store._get_connection()
    cursor = await conn.execute("PRAGMA table_info(graph_nodes)")
    columns = await cursor.fetchall()
    await cursor.close()

    column_names = {col[1] for col in columns}
    assert "status" in column_names  # Existing column
    assert "parent_graph_code" in column_names  # NEW column
    assert "change_set" in column_names  # NEW column


# ============================================================================
# Database WAL Mode Tests (RED phase)
# ============================================================================


@pytest.mark.asyncio
async def test_database_enables_wal_mode(temp_db: str) -> None:
    """Test that database initialization enables WAL mode."""
    from app.state.database import StateRepository

    repo = StateRepository(db_path=temp_db)
    await repo.init_db()

    # Check PRAGMA values
    conn = await repo._get_connection()

    # Check journal_mode
    cursor = await conn.execute("PRAGMA journal_mode")
    journal_mode = await cursor.fetchone()
    await cursor.close()
    assert journal_mode is not None
    assert journal_mode[0].upper() == "WAL"

    # Check synchronous
    cursor = await conn.execute("PRAGMA synchronous")
    synchronous = await cursor.fetchone()
    await cursor.close()
    assert synchronous is not None
    # NORMAL = 1
    assert synchronous[0] in (1, "1", "NORMAL")
