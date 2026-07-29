"""Unit tests for SQLite state management."""
from __future__ import annotations

import pytest
from pathlib import Path
from typing import AsyncGenerator

from app.models.player import PlayerState, PlayerStatus
from app.state.database import StateRepository


@pytest.fixture
async def temp_db(tmp_path: Path) -> AsyncGenerator[StateRepository, None]:
    """Create temporary database for testing.

    Args:
        tmp_path: Pytest temporary path fixture

    Yields:
        Initialized StateRepository with temp database
    """
    db_path = str(tmp_path / "test.db")
    repo = StateRepository(db_path=db_path)
    await repo.init_db()
    yield repo
    await repo.close()


@pytest.mark.asyncio
async def test_init_db_creates_table(temp_db: StateRepository) -> None:
    """Verify table exists after init."""
    # Check that table exists by querying schema
    conn = await temp_db._get_connection()
    cursor = await conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='player_state'"
    )
    result = await cursor.fetchone()
    await cursor.close()

    assert result is not None, "Table 'player_state' should exist"


@pytest.mark.asyncio
async def test_get_state_empty(temp_db: StateRepository) -> None:
    """Returns None for non-existent player."""
    state = await temp_db.get_state("nonexistent_player")
    assert state is None


@pytest.mark.asyncio
async def test_update_then_get(temp_db: StateRepository) -> None:
    """Update state, then get returns correct data."""
    player_id = "test_player_001"
    original_state = PlayerState(
        id=player_id,
        energy=50,
        health=75,
        strength=60,
        intelligence=70,
        echo_mode_enabled=False,
        mental_stability=80,
        location="test_location",
        inventory=["item_1", "item_2"],
        status=PlayerStatus.NORMAL
    )

    # Update state
    await temp_db.update_state(player_id, original_state)

    # Get state back
    retrieved_state = await temp_db.get_state(player_id)

    assert retrieved_state is not None
    assert retrieved_state.id == player_id
    assert retrieved_state.energy == 50
    assert retrieved_state.health == 75
    assert retrieved_state.strength == 60
    assert retrieved_state.intelligence == 70
    assert retrieved_state.echo_mode_enabled is False
    assert retrieved_state.mental_stability == 80
    assert retrieved_state.location == "test_location"
    assert retrieved_state.inventory == ["item_1", "item_2"]
    assert retrieved_state.status == PlayerStatus.NORMAL


@pytest.mark.asyncio
async def test_reset_state(temp_db: StateRepository) -> None:
    """Reset returns default player values."""
    # Reset state
    reset_state = await temp_db.reset_state("test_player_002")

    # Verify default values
    assert reset_state.id == "player_001"
    assert reset_state.energy == 80
    assert reset_state.health == 90
    assert reset_state.strength == 60
    assert reset_state.intelligence == 70
    assert reset_state.echo_mode_enabled is False
    assert reset_state.mental_stability == 85
    assert reset_state.location == "temple_ruins"
    assert reset_state.inventory == []
    assert reset_state.status == PlayerStatus.NORMAL
    assert reset_state.max_energy == 100
    assert reset_state.max_health == 100


@pytest.mark.asyncio
async def test_update_partial_fields(temp_db: StateRepository) -> None:
    """Update specific fields while preserving others."""
    player_id = "test_player_003"

    # Create initial state
    initial_state = PlayerState(
        id=player_id,
        energy=100,
        health=100,
        strength=50,
        intelligence=50,
        echo_mode_enabled=False,
        mental_stability=100,
        location="start",
        inventory=["old_item"],
        status=PlayerStatus.NORMAL
    )
    await temp_db.update_state(player_id, initial_state)

    # Update with new state (only some fields changed)
    updated_state = PlayerState(
        id=player_id,
        energy=30,  # Reduced
        health=90,  # Slightly reduced
        strength=50,  # Same
        intelligence=50,  # Same
        echo_mode_enabled=True,  # Changed
        mental_stability=100,  # Same
        location="dungeon",  # Changed
        inventory=["old_item", "new_item"],  # Added item
        status=PlayerStatus.EXHAUSTED  # Changed
    )
    await temp_db.update_state(player_id, updated_state)

    # Verify all fields are correct
    retrieved_state = await temp_db.get_state(player_id)
    assert retrieved_state is not None
    assert retrieved_state.energy == 30
    assert retrieved_state.health == 90
    assert retrieved_state.strength == 50
    assert retrieved_state.intelligence == 50
    assert retrieved_state.echo_mode_enabled is True
    assert retrieved_state.mental_stability == 100
    assert retrieved_state.location == "dungeon"
    assert retrieved_state.inventory == ["old_item", "new_item"]
    assert retrieved_state.status == PlayerStatus.EXHAUSTED


@pytest.mark.asyncio
async def test_state_roundtrip(temp_db: StateRepository) -> None:
    """Complex state survives save/load cycle."""
    player_id = "test_player_004"

    # Create complex state with all fields
    complex_state = PlayerState(
        id=player_id,
        energy=42,
        health=67,
        strength=88,
        intelligence=95,
        echo_mode_enabled=True,
        mental_stability=23,
        location="echo_chamber",
        inventory=["artifact_1", "key_red", "medkit", "echo_crystal"],
        status=PlayerStatus.ECHO_OVERLOAD,
        max_energy=150,
        max_health=120
    )

    # Save and load
    await temp_db.update_state(player_id, complex_state)
    retrieved_state = await temp_db.get_state(player_id)

    # Verify all fields match
    assert retrieved_state is not None
    assert retrieved_state.id == complex_state.id
    assert retrieved_state.energy == complex_state.energy
    assert retrieved_state.health == complex_state.health
    assert retrieved_state.strength == complex_state.strength
    assert retrieved_state.intelligence == complex_state.intelligence
    assert retrieved_state.echo_mode_enabled == complex_state.echo_mode_enabled
    assert retrieved_state.mental_stability == complex_state.mental_stability
    assert retrieved_state.location == complex_state.location
    assert retrieved_state.inventory == complex_state.inventory
    assert retrieved_state.status == complex_state.status
    assert retrieved_state.max_energy == complex_state.max_energy
    assert retrieved_state.max_health == complex_state.max_health
