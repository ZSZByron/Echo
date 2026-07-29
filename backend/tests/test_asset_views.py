"""Tests for Asset model with views structure."""
from datetime import datetime, timezone

import pytest

from app.models.asset import Asset, AssetStatus, AssetType, Candidate, SceneStyleProfile


class TestAssetViews:
    """Test Asset views structure and methods."""

    def test_asset_creation_with_views(self) -> None:
        """Test Asset(views={'near': {...}}) creation."""
        views = {
            "near": {
                "prompt": "close-up view of altar",
                "file_path": "altar_near.png",
                "status": "completed"
            },
            "mid": {
                "prompt": "medium shot of altar",
                "file_path": "altar_mid.png",
                "status": "completed"
            },
            "far": {
                "prompt": "distant view of altar",
                "file_path": "altar_far.png",
                "status": "pending"
            }
        }

        asset = Asset(
            id="test_asset",
            type=AssetType.OBJECT,
            name="Test Altar",
            parent_scene="test_scene",
            views=views
        )

        assert asset.views == views
        assert asset.views is not None
        assert "near" in asset.views
        assert "mid" in asset.views
        assert "far" in asset.views

    def test_get_view_returns_correct_data(self) -> None:
        """Test get_view('near') returns correct data."""
        views = {
            "near": {"prompt": "near view", "file_path": "near.png"},
            "mid": {"prompt": "mid view", "file_path": "mid.png"},
            "far": {"prompt": "far view", "file_path": "far.png"}
        }

        asset = Asset(
            id="test_asset",
            type=AssetType.OBJECT,
            name="Test Object",
            parent_scene="test_scene",
            views=views
        )

        near_view = asset.get_view("near")
        assert near_view == {"prompt": "near view", "file_path": "near.png"}

        mid_view = asset.get_view("mid")
        assert mid_view == {"prompt": "mid view", "file_path": "mid.png"}

        far_view = asset.get_view("far")
        assert far_view == {"prompt": "far view", "file_path": "far.png"}

    def test_get_view_returns_none_for_nonexistent_level(self) -> None:
        """Test get_view returns None for nonexistent LOD level."""
        views = {"near": {"prompt": "near view"}}

        asset = Asset(
            id="test_asset",
            type=AssetType.OBJECT,
            name="Test Object",
            parent_scene="test_scene",
            views=views
        )

        # Non-existent LOD level should return None
        assert asset.get_view("nonexistent") is None

    def test_get_view_returns_none_when_views_is_none(self) -> None:
        """Test get_view returns None when views is None."""
        asset = Asset(
            id="test_asset",
            type=AssetType.OBJECT,
            name="Test Object",
            parent_scene="test_scene",
            views=None
        )

        assert asset.get_view("near") is None
        assert asset.get_view("mid") is None
        assert asset.get_view("far") is None

    def test_set_view_updates_correctly(self) -> None:
        """Test set_view('mid', prompt='x') updates correctly."""
        asset = Asset(
            id="test_asset",
            type=AssetType.OBJECT,
            name="Test Object",
            parent_scene="test_scene",
            views={"near": {"prompt": "near view"}}
        )

        # Set new view data for mid
        asset.set_view("mid", prompt="mid view", file_path="mid.png", status="completed")

        # Verify mid view was set correctly
        mid_view = asset.get_view("mid")
        assert mid_view is not None
        assert mid_view["prompt"] == "mid view"
        assert mid_view["file_path"] == "mid.png"
        assert mid_view["status"] == "completed"

        # Verify near view is still intact
        near_view = asset.get_view("near")
        assert near_view == {"prompt": "near view"}

    def test_set_view_creates_new_level_if_not_exists(self) -> None:
        """Test set_view creates new LOD level if it doesn't exist."""
        asset = Asset(
            id="test_asset",
            type=AssetType.OBJECT,
            name="Test Object",
            parent_scene="test_scene",
            views=None
        )

        # Set view when views is None
        asset.set_view("near", prompt="near view", file_path="near.png")

        assert asset.views is not None
        assert "near" in asset.views
        assert asset.views["near"]["prompt"] == "near view"
        assert asset.views["near"]["file_path"] == "near.png"

    def test_new_fields_default_to_none(self) -> None:
        """Test new fields (lod_level, puzzle_role, parent_object, depth) default to None."""
        asset = Asset(
            id="test_asset",
            type=AssetType.OBJECT,
            name="Test Object",
            parent_scene="test_scene"
        )

        assert asset.lod_level is None
        assert asset.puzzle_role is None
        assert asset.parent_object is None
        assert asset.depth is None

    def test_existing_fields_preserved(self) -> None:
        """Test existing fields are preserved when creating Asset."""
        created_at = datetime.now(timezone.utc)
        candidates = [
            Candidate(index=0, seed=12345, file_path="candidate_0.png", score=0.9),
            Candidate(index=1, seed=67890, file_path="candidate_1.png", score=0.8)
        ]
        style_profile = SceneStyleProfile(
            palette=["#ff0000", "#00ff00"],
            lighting={"type": "ambient", "intensity": 0.8}
        )

        asset = Asset(
            id="test_asset",
            type=AssetType.OBJECT,
            name="Test Object",
            parent_scene="test_scene",
            status=AssetStatus.COMPLETED,
            generation_status="completed",
            seed=42,
            created_at=created_at,
            approved_at=created_at,
            reviewer_note="Looks good",
            error_message=None,
            candidates=candidates,
            selected_candidate_index=0,
            reference_asset_ids=["asset_1", "asset_2"],
            style_profile=style_profile
        )

        assert asset.id == "test_asset"
        assert asset.type == AssetType.OBJECT
        assert asset.name == "Test Object"
        assert asset.parent_scene == "test_scene"
        assert asset.status == AssetStatus.COMPLETED
        assert asset.generation_status == "completed"
        assert asset.seed == 42
        assert asset.created_at == created_at
        assert asset.approved_at == created_at
        assert asset.reviewer_note == "Looks good"
        assert asset.error_message is None
        assert len(asset.candidates) == 2
        assert asset.candidates[0].index == 0
        assert asset.candidates[0].seed == 12345
        assert asset.selected_candidate_index == 0
        assert asset.reference_asset_ids == ["asset_1", "asset_2"]
        assert asset.style_profile is not None
        assert asset.style_profile.palette == ["#ff0000", "#00ff00"]

    def test_set_view_with_existing_data(self) -> None:
        """Test set_view updates existing data while preserving other fields."""
        asset = Asset(
            id="test_asset",
            type=AssetType.OBJECT,
            name="Test Object",
            parent_scene="test_scene",
            views={
                "near": {"prompt": "old near", "file_path": "old_near.png"}
            }
        )

        # Update near view with new prompt but keep file_path
        asset.set_view("near", prompt="new near")

        near_view = asset.get_view("near")
        assert near_view["prompt"] == "new near"
        assert near_view["file_path"] == "old_near.png"  # preserved

    def test_multiple_lod_levels_independent(self) -> None:
        """Test that multiple LOD levels are independent of each other."""
        asset = Asset(
            id="test_asset",
            type=AssetType.OBJECT,
            name="Test Object",
            parent_scene="test_scene"
        )

        # Set multiple LOD levels
        asset.set_view("near", prompt="near view", status="completed")
        asset.set_view("mid", prompt="mid view", status="pending")
        asset.set_view("far", prompt="far view", status="generating")

        # Verify they are independent
        assert asset.get_view("near")["status"] == "completed"
        assert asset.get_view("mid")["status"] == "pending"
        assert asset.get_view("far")["status"] == "generating"

        # Update mid should not affect near or far
        asset.set_view("mid", status="completed")
        assert asset.get_view("near")["status"] == "completed"
        assert asset.get_view("mid")["status"] == "completed"
        assert asset.get_view("far")["status"] == "generating"

    def test_asset_with_complete_views_structure(self) -> None:
        """Test Asset with complete views structure including all fields."""
        asset = Asset(
            id="temple_ruins_altar",
            type=AssetType.OBJECT,
            name="Holographic Altar",
            parent_scene="temple_ruins",
            views={
                "near": {
                    "prompt": "close-up cyberpunk altar",
                    "file_path": "altar_near.png",
                    "status": "completed",
                    "seed": 12345
                },
                "mid": {
                    "prompt": "medium shot altar",
                    "file_path": "altar_mid.png",
                    "status": "completed",
                    "seed": 67890
                },
                "far": {
                    "prompt": "distant altar",
                    "file_path": "altar_far.png",
                    "status": "pending",
                    "seed": 11111
                }
            },
            lod_level="mid",
            puzzle_role="reward",
            parent_object=None,
            depth="mid"
        )

        assert asset.views is not None
        assert len(asset.views) == 3
        assert asset.lod_level == "mid"
        assert asset.puzzle_role == "reward"
        assert asset.depth == "mid"

        near = asset.get_view("near")
        assert near is not None
        assert near["prompt"] == "close-up cyberpunk altar"
        assert near["status"] == "completed"

        far = asset.get_view("far")
        assert far is not None
        assert far["status"] == "pending"
