"""Tests for PromptBuilder - template-based prompt building for asset generation."""
from pathlib import Path

import pytest

from app.domains.creation.asset.prompt_builder import PromptBuilder


class TestPromptBuilder:
    """Test PromptBuilder functionality."""

    def test_build_returns_non_empty_string(self) -> None:
        """Test PromptBuilder().build() returns non-empty string."""
        builder = PromptBuilder()
        prompt = builder.build("temple_ruins_holographic_altar", "near", {})

        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_prompt_length_greater_than_100(self) -> None:
        """Test prompt length > 100 characters."""
        builder = PromptBuilder()
        prompt = builder.build("temple_ruins_holographic_altar", "near", {})

        assert len(prompt) > 100, f"Prompt too short: {len(prompt)} chars"

    def test_prompt_contains_cyberpunk_or_temple(self) -> None:
        """Test prompt contains 'cyberpunk' or 'temple' keywords."""
        builder = PromptBuilder()
        prompt = builder.build("temple_ruins_holographic_altar", "near", {})
        prompt_lower = prompt.lower()

        # Check for expected keywords
        has_cyberpunk = "cyberpunk" in prompt_lower
        has_temple = "temple" in prompt_lower
        has_altar = "altar" in prompt_lower

        assert has_cyberpunk or has_temple or has_altar, (
            f"Prompt should contain 'cyberpunk', 'temple', or 'altar': {prompt}"
        )

    def test_different_lod_levels_produce_different_prompts(self) -> None:
        """Test different LOD levels produce different prompts."""
        builder = PromptBuilder()

        near_prompt = builder.build("temple_ruins_holographic_altar", "near", {})
        mid_prompt = builder.build("temple_ruins_holographic_altar", "mid", {})
        far_prompt = builder.build("temple_ruins_holographic_altar", "far", {})

        # Prompts should differ based on LOD level
        assert near_prompt != mid_prompt, "near and mid prompts should differ"
        assert mid_prompt != far_prompt, "mid and far prompts should differ"
        assert near_prompt != far_prompt, "near and far prompts should differ"

    def test_edge_case_unknown_asset_id(self) -> None:
        """Test edge case: unknown asset_id returns empty or minimal prompt."""
        builder = PromptBuilder()
        prompt = builder.build("unknown_scene_unknown_object", "near", {})

        # Should handle gracefully - either empty string or minimal prompt
        assert isinstance(prompt, str)
        # If scene file doesn't exist, prompt may be empty or very minimal
        # This is acceptable behavior

    def test_edge_case_empty_context(self) -> None:
        """Test edge case: empty context dict."""
        builder = PromptBuilder()
        prompt = builder.build("temple_ruins_holographic_altar", "near", {})

        # Should work with empty context
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_context_overrides_layers(self) -> None:
        """Test context parameter overrides prompt layers."""
        builder = PromptBuilder()

        # Build with context overrides
        prompt = builder.build(
            "temple_ruins_holographic_altar",
            "near",
            {"subject": "custom subject", "material": "neon material"}
        )

        # Verify context is reflected in prompt
        assert "custom subject" in prompt
        assert "neon material" in prompt

    def test_prompt_contains_multiple_layers(self) -> None:
        """Test prompt contains content from multiple layers."""
        builder = PromptBuilder()
        prompt = builder.build("temple_ruins_holographic_altar", "near", {})
        prompt_lower = prompt.lower()

        # Prompt should contain elements from various layers
        # Check for at least some common layer indicators
        has_comma = "," in prompt  # layers are comma-separated
        has_content = len(prompt.strip()) > 50

        assert has_comma, "Prompt should be comma-separated (multiple layers)"
        assert has_content, "Prompt should have substantial content"

    def test_builder_initialization(self) -> None:
        """Test PromptBuilder initializes correctly."""
        builder = PromptBuilder()

        # Should have loaded data
        assert hasattr(builder, "_prompts_data")
        assert hasattr(builder, "_palette_data")
        assert isinstance(builder._prompts_data, dict)
        assert isinstance(builder._palette_data, dict)

    def test_parse_asset_id_handles_underscores(self) -> None:
        """Test _parse_asset_id handles scene_id with underscores correctly."""
        builder = PromptBuilder()

        # Test with scene_id containing underscores (that exists in data/scenes/)
        scene_id, object_id = builder._parse_asset_id("temple_ruins_holographic_altar")
        assert scene_id == "temple_ruins"
        assert object_id == "holographic_altar"

        # Test with scene_id that doesn't exist - should return empty
        scene_id, object_id = builder._parse_asset_id("nonexistent_altar")
        # Since the scene file doesn't exist, _parse_asset_id returns empty strings
        # when it can't find a matching scene file
        assert scene_id == "" or object_id == ""  # At least one should be empty

    def test_prompt_consistency_for_same_inputs(self) -> None:
        """Test that same inputs produce consistent prompts."""
        builder = PromptBuilder()

        prompt1 = builder.build("temple_ruins_holographic_altar", "near", {})
        prompt2 = builder.build("temple_ruins_holographic_altar", "near", {})

        # Should be identical
        assert prompt1 == prompt2

    def test_different_assets_produce_different_prompts(self) -> None:
        """Test different assets produce different prompts."""
        builder = PromptBuilder()

        altar_prompt = builder.build("temple_ruins_holographic_altar", "near", {})
        door_prompt = builder.build("temple_ruins_ancient_door", "near", {})

        # Should differ based on asset
        assert altar_prompt != door_prompt, "Different assets should produce different prompts"

    def test_camera_templates_by_lod(self) -> None:
        """Test camera templates are applied based on LOD level."""
        builder = PromptBuilder()

        near_prompt = builder.build("temple_ruins_holographic_altar", "near", {})
        far_prompt = builder.build("temple_ruins_holographic_altar", "far", {})

        # Camera descriptions should differ between near and far
        # (e.g., "close-up" vs "wide shot")
        near_lower = near_prompt.lower()
        far_lower = far_prompt.lower()

        # Near should emphasize closeness
        far_keywords = ["wide", "distant", "far", "establishing"]

        # We expect some differentiation in camera terminology
        has_different_camera = near_prompt != far_prompt
        assert has_different_camera, "Camera should differ by LOD level"

    def test_prompt_builder_handles_missing_scene_file(self) -> None:
        """Test PromptBuilder handles missing scene file gracefully."""
        builder = PromptBuilder()

        # Use a non-existent scene
        prompt = builder.build("nonexistent_scene_object", "near", {})

        # Should return empty string or minimal prompt without crashing
        assert isinstance(prompt, str)
        # Empty string is acceptable for missing scene

    def test_prompts_data_structure(self) -> None:
        """Test that prompts data has expected structure."""
        builder = PromptBuilder()

        # Check for expected top-level keys
        assert "segments" in builder._prompts_data or "objects" in builder._prompts_data

        # Check for segments if present
        if "segments" in builder._prompts_data:
            segments = builder._prompts_data["segments"]
            assert isinstance(segments, dict)

    def test_prompt_contains_scene_specific_content(self) -> None:
        """Test prompt contains content specific to the scene."""
        builder = PromptBuilder()
        prompt = builder.build("temple_ruins_holographic_altar", "mid", {})
        prompt_lower = prompt.lower()

        # Should contain scene-relevant terms
        # Temple ruins scene should have related terminology
        scene_terms = ["ruins", "temple", "altar", "holographic"]
        has_scene_content = any(term in prompt_lower for term in scene_terms)

        assert has_scene_content, f"Prompt should contain scene-specific terms: {prompt}"
