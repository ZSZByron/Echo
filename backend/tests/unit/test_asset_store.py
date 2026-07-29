"""Unit tests for AssetStore and Asset model."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.models.asset import Asset, AssetStatus, AssetType
from app.state.asset_store import AssetStore, InvalidTransitionError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path: Path) -> AssetStore:
    """AssetStore pointed at a temp manifest file."""
    return AssetStore(path=tmp_path / "manifest.json")


@pytest.fixture
def initialized_store(store: AssetStore) -> AssetStore:
    """AssetStore with manifest initialized from scene YAMLs."""
    store.init_manifest()
    return store


# ---------------------------------------------------------------------------
# Asset model
# ---------------------------------------------------------------------------


class TestAssetModel:
    def test_default_status_is_pending(self) -> None:
        asset = Asset(
            id="test_bg",
            type=AssetType.BACKGROUND,
            name="Test",
            parent_scene="test",
        )
        assert asset.status == AssetStatus.PENDING
        assert asset.generation_status == "pending"

    def test_created_at_is_utc(self) -> None:
        asset = Asset(
            id="x",
            type=AssetType.OBJECT,
            name="X",
            parent_scene="s",
        )
        assert asset.created_at.tzinfo is not None

    def test_optional_fields_default_none(self) -> None:
        asset = Asset(
            id="x",
            type=AssetType.OBJECT,
            name="X",
            parent_scene="s",
        )
        assert asset.file_path is None
        assert asset.seed is None
        assert asset.approved_at is None
        assert asset.reviewer_note is None
        assert asset.error_message is None


# ---------------------------------------------------------------------------
# init_manifest
# ---------------------------------------------------------------------------


class TestInitManifest:
    def test_creates_correct_asset_count(
        self, initialized_store: AssetStore
    ) -> None:
        """temple_ruins has 1 bg + 4 objects = 5 assets."""
        assets = initialized_store.list_assets()
        assert len(assets) >= 5

    def test_expected_asset_ids(
        self, initialized_store: AssetStore
    ) -> None:
        ids = {a.id for a in initialized_store.list_assets()}
        expected = {
            "temple_ruins_bg",
            "temple_ruins_ancient_locked_door",
            "temple_ruins_priest_corpse_01",
            "temple_ruins_holographic_altar",
            "temple_ruins_neon_circuit_pillar",
        }
        assert expected.issubset(ids)

    def test_background_asset_type(
        self, initialized_store: AssetStore
    ) -> None:
        bg = initialized_store.get_asset("temple_ruins_bg")
        assert bg is not None
        assert bg.type == AssetType.BACKGROUND
        assert bg.parent_scene == "temple_ruins"
        assert bg.name == "Temple of the Forgotten King"

    def test_object_asset_type(
        self, initialized_store: AssetStore
    ) -> None:
        obj = initialized_store.get_asset("temple_ruins_ancient_locked_door")
        assert obj is not None
        assert obj.type == AssetType.OBJECT
        assert obj.parent_scene == "temple_ruins"

    def test_idempotent(self, store: AssetStore) -> None:
        """Running init_manifest twice should not duplicate assets."""
        store.init_manifest()
        first_count = len(store.list_assets())
        store.init_manifest()
        second_count = len(store.list_assets())
        assert first_count == second_count

    def test_manifest_json_structure(
        self, initialized_store: AssetStore
    ) -> None:
        path = initialized_store._path
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        assert "assets" in raw
        assert "version" in raw
        assert "updated_at" in raw
        assert raw["version"] == "1.0"


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------


class TestCRUD:
    def test_get_asset_returns_none_for_missing(
        self, initialized_store: AssetStore
    ) -> None:
        assert initialized_store.get_asset("nonexistent") is None

    def test_get_asset_returns_asset(
        self, initialized_store: AssetStore
    ) -> None:
        asset = initialized_store.get_asset("temple_ruins_bg")
        assert asset is not None
        assert asset.id == "temple_ruins_bg"

    def test_list_assets_returns_list(
        self, initialized_store: AssetStore
    ) -> None:
        assets = initialized_store.list_assets()
        assert isinstance(assets, list)
        assert len(assets) > 0

    def test_update_asset_field(
        self, initialized_store: AssetStore
    ) -> None:
        updated = initialized_store.update_asset(
            "temple_ruins_bg", prompt="a dark temple"
        )
        assert updated.prompt == "a dark temple"

    def test_update_asset_raises_for_missing(
        self, initialized_store: AssetStore
    ) -> None:
        with pytest.raises(KeyError):
            initialized_store.update_asset("nope", status=AssetStatus.GENERATING)


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


class TestStatusTransitions:
    @pytest.mark.parametrize(
        ("path"),
        [
            # happy path: full generation → approval
            [
                AssetStatus.GENERATING,
                AssetStatus.COMPLETED,
                AssetStatus.APPROVED,
            ],
            # happy path: generation fails, retry
            [
                AssetStatus.GENERATING,
                AssetStatus.FAILED,
                AssetStatus.PENDING,
                AssetStatus.GENERATING,
                AssetStatus.COMPLETED,
                AssetStatus.APPROVED,
            ],
            # happy path: rejected → back to pending
            [
                AssetStatus.GENERATING,
                AssetStatus.COMPLETED,
                AssetStatus.REJECTED,
                AssetStatus.PENDING,
            ],
            # happy path: approved → re-review
            [
                AssetStatus.GENERATING,
                AssetStatus.COMPLETED,
                AssetStatus.APPROVED,
                AssetStatus.PENDING,
            ],
        ],
    )
    def test_allowed_transitions(
        self, initialized_store: AssetStore, path: list[AssetStatus]
    ) -> None:
        asset_id = "temple_ruins_bg"
        for target in path:
            initialized_store.update_asset(asset_id, status=target)
            result = initialized_store.get_asset(asset_id)
            assert result is not None
            assert result.status == target

    @pytest.mark.parametrize(
        ("current", "target"),
        [
            (AssetStatus.PENDING, AssetStatus.COMPLETED),
            (AssetStatus.PENDING, AssetStatus.APPROVED),
            (AssetStatus.PENDING, AssetStatus.REJECTED),
            (AssetStatus.GENERATING, AssetStatus.APPROVED),
            (AssetStatus.GENERATING, AssetStatus.PENDING),
            (AssetStatus.COMPLETED, AssetStatus.GENERATING),
            (AssetStatus.COMPLETED, AssetStatus.PENDING),
            (AssetStatus.APPROVED, AssetStatus.GENERATING),
            (AssetStatus.REJECTED, AssetStatus.GENERATING),
        ],
    )
    def test_disallowed_transitions_raise(
        self,
        initialized_store: AssetStore,
        current: AssetStatus,
        target: AssetStatus,
    ) -> None:
        asset_id = "temple_ruins_bg"
        # Set to current status by walking from PENDING
        _set_status_directly(initialized_store, asset_id, current)
        with pytest.raises(InvalidTransitionError):
            initialized_store.update_asset(asset_id, status=target)

    def test_generation_status_synced_on_generating(
        self, initialized_store: AssetStore
    ) -> None:
        initialized_store.update_asset(
            "temple_ruins_bg", status=AssetStatus.GENERATING
        )
        asset = initialized_store.get_asset("temple_ruins_bg")
        assert asset is not None
        assert asset.generation_status == "generating"

    def test_generation_status_synced_on_completed(
        self, initialized_store: AssetStore
    ) -> None:
        store = initialized_store
        store.update_asset("temple_ruins_bg", status=AssetStatus.GENERATING)
        store.update_asset("temple_ruins_bg", status=AssetStatus.COMPLETED)
        asset = store.get_asset("temple_ruins_bg")
        assert asset is not None
        assert asset.generation_status == "completed"

    def test_approved_at_set_on_approval(
        self, initialized_store: AssetStore
    ) -> None:
        store = initialized_store
        store.update_asset("temple_ruins_bg", status=AssetStatus.GENERATING)
        store.update_asset("temple_ruins_bg", status=AssetStatus.COMPLETED)
        store.update_asset("temple_ruins_bg", status=AssetStatus.APPROVED)
        asset = store.get_asset("temple_ruins_bg")
        assert asset is not None
        assert asset.approved_at is not None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_status_directly(
    store: AssetStore, asset_id: str, target: AssetStatus
) -> None:
    """Force an asset to *target* status via valid transitions.

    Walks a path from PENDING to *target* using only allowed transitions.
    This avoids bypassing the transition logic in tests.
    """
    # Define a walkable path to each target from PENDING
    paths: dict[AssetStatus, list[AssetStatus]] = {
        AssetStatus.PENDING: [],
        AssetStatus.GENERATING: [AssetStatus.GENERATING],
        AssetStatus.COMPLETED: [
            AssetStatus.GENERATING,
            AssetStatus.COMPLETED,
        ],
        AssetStatus.FAILED: [
            AssetStatus.GENERATING,
            AssetStatus.FAILED,
        ],
        AssetStatus.APPROVED: [
            AssetStatus.GENERATING,
            AssetStatus.COMPLETED,
            AssetStatus.APPROVED,
        ],
        AssetStatus.REJECTED: [
            AssetStatus.GENERATING,
            AssetStatus.COMPLETED,
            AssetStatus.REJECTED,
        ],
    }
    # Reset to PENDING first (via approved→pending or rejected→pending if needed)
    current = store.get_asset(asset_id)
    assert current is not None
    # If currently in a terminal state, reset to pending
    if current.status in (
        AssetStatus.APPROVED,
        AssetStatus.REJECTED,
        AssetStatus.FAILED,
    ):
        store.update_asset(asset_id, status=AssetStatus.PENDING)
    elif current.status == AssetStatus.GENERATING:
        store.update_asset(asset_id, status=AssetStatus.FAILED)
        store.update_asset(asset_id, status=AssetStatus.PENDING)
    elif current.status == AssetStatus.COMPLETED:
        store.update_asset(asset_id, status=AssetStatus.REJECTED)
        store.update_asset(asset_id, status=AssetStatus.PENDING)

    for step in paths[target]:
        store.update_asset(asset_id, status=step)
