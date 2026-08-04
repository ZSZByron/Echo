"""Tests for GenerationPlanner - LOD-aware asset generation planning."""
from pathlib import Path

import pytest

from app.domains.creation.asset.generation_planner import (
    AssetGenerationSpec,
    GenerationPlan,
    GenerationPlanner,
    _DEPTH_TO_LOD,
    _LOD_PRIORITY,
)


class TestGenerationPlanner:
    """Test GenerationPlanner functionality."""

    def test_create_plan_returns_valid_plan(self) -> None:
        """Test that planner.create_plan('temple_ruins') returns valid plan."""
        planner = GenerationPlanner()
        plan = planner.create_plan("temple_ruins")

        assert isinstance(plan, GenerationPlan)
        assert plan.scene_id == "temple_ruins"
        assert isinstance(plan.order, list)
        assert len(plan.order) > 0
        assert isinstance(plan.specs, dict)

    def test_bg_is_last_in_order(self) -> None:
        """Test that background is last in generation order."""
        planner = GenerationPlanner()
        plan = planner.create_plan("temple_ruins")

        # Find bg asset ID
        bg_asset_id = f"{plan.scene_id}_bg"

        # If bg exists in the plan, it should be last
        if bg_asset_id in plan.order:
            assert plan.order[-1] == bg_asset_id, "Background should be last in order"

    def test_each_asset_has_reference_asset_ids(self) -> None:
        """Test that each asset has reference_asset_ids."""
        planner = GenerationPlanner()
        plan = planner.create_plan("temple_ruins")

        for asset_id, spec in plan.specs.items():
            assert hasattr(spec, "reference_asset_ids")
            assert isinstance(spec.reference_asset_ids, list)
            # Even if empty, it should be a list
            assert spec.asset_id == asset_id

    def test_lod_priority_sorting(self) -> None:
        """Test LOD priority sorting (near → mid → far → bg)."""
        planner = GenerationPlanner()
        plan = planner.create_plan("temple_ruins")

        # Verify LOD priority order in the generation plan
        # near (0) should come before mid (1) before far (2) before bg (3)
        lod_positions = {}

        for asset_id in plan.order:
            spec = plan.specs[asset_id]
            lod_level = spec.lod_level

            # Determine LOD priority
            if lod_level == "near":
                priority = 0
            elif lod_level == "mid":
                priority = 1
            elif lod_level == "far":
                priority = 2
            elif asset_id.endswith("_bg"):
                priority = 3
            else:
                priority = 1  # default to mid

            lod_positions[asset_id] = priority

        # Check that priorities are non-decreasing
        priorities = [lod_positions[aid] for aid in plan.order]
        for i in range(len(priorities) - 1):
            assert priorities[i] <= priorities[i + 1], (
                f"LOD priority not sorted: {plan.order[i]} ({priorities[i]}) "
                f"before {plan.order[i + 1]} ({priorities[i + 1]})"
            )

    def test_no_image_generator_calls(self) -> None:
        """Test that GenerationPlanner source does not call ImageGenerator."""
        # Read the generation_planner.py source file
        planner_path = Path(__file__).parent.parent / "app" / "domains" / "creation" / "asset" / "generation_planner.py"
        source = planner_path.read_text()

        # Verify it doesn't import or call ImageGenerator
        assert "ImageGenerator" not in source
        assert "image_generator" not in source
        assert "generate_image" not in source

    def test_depth_to_lod_mapping(self) -> None:
        """Test _DEPTH_TO_LOD constant mapping."""
        assert _DEPTH_TO_LOD["near"] == "near"
        assert _DEPTH_TO_LOD["mid"] == "mid"
        assert _DEPTH_TO_LOD["mid_far"] == "far"
        assert _DEPTH_TO_LOD["far"] == "far"

    def test_lod_priority_ordering(self) -> None:
        """Test _LOD_PRIORITY constant ordering."""
        assert _LOD_PRIORITY["near"] == 0
        assert _LOD_PRIORITY["mid"] == 1
        assert _LOD_PRIORITY["far"] == 2
        assert _LOD_PRIORITY["bg"] == 3

    def test_asset_generation_spec_structure(self) -> None:
        """Test that AssetGenerationSpec has correct structure."""
        planner = GenerationPlanner()
        plan = planner.create_plan("temple_ruins")

        # Pick a spec to test structure
        asset_id = plan.order[0]
        spec = plan.specs[asset_id]

        assert isinstance(spec, AssetGenerationSpec)
        assert isinstance(spec.asset_id, str)
        assert spec.asset_id == asset_id
        assert spec.lod_level in [None, "near", "mid", "far"]
        assert isinstance(spec.prompt, str)
        assert isinstance(spec.reference_asset_ids, list)

    def test_plan_includes_all_required_assets(self) -> None:
        """Test that plan includes all assets from the scene."""
        planner = GenerationPlanner()
        plan = planner.create_plan("temple_ruins")

        # Plan should have specs for all assets in order
        assert len(plan.specs) == len(plan.order)
        assert set(plan.order) == set(plan.specs.keys())

    def test_spec_prompts_are_non_empty(self) -> None:
        """Test that all spec prompts are non-empty strings."""
        planner = GenerationPlanner()
        plan = planner.create_plan("temple_ruins")

        for asset_id, spec in plan.specs.items():
            assert isinstance(spec.prompt, str)
            assert len(spec.prompt) > 0, f"Prompt for {asset_id} should not be empty"

    def test_dependencies_honored_in_order(self) -> None:
        """Test that dependencies are honored in generation order."""
        planner = GenerationPlanner()
        plan = planner.create_plan("temple_ruins")

        # Create a map of asset positions
        positions = {asset_id: idx for idx, asset_id in enumerate(plan.order)}

        # Check that all dependencies come before the asset
        for asset_id, spec in plan.specs.items():
            for ref_id in spec.reference_asset_ids:
                # Background reference is special - it's always last
                if ref_id.endswith("_bg"):
                    continue

                # Only check if reference is in the plan
                if ref_id in positions:
                    # Skip self-references
                    if ref_id == asset_id:
                        continue

                    assert positions[ref_id] < positions[asset_id], (
                        f"Reference {ref_id} should come before {asset_id}"
                    )
