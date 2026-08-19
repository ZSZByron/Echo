"""Tests for tag_dictionary module.

Tests the tag and enum dictionary that provides:
1. YAML loading with validation
2. 6 constraint dimensions (LAW/ACT/NAR/WST/SOC/RED)
3. A2 additions: LOC (location) and STY (style)
4. Query interface: get_enum_values(dim, tag) -> list[str]
5. Closed enum validation (no runtime additions)

Following TDD: This test is written FIRST, before implementation.
"""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError


class TestTagDictionaryTDD:
    """TDD tests for tag dictionary loading and validation."""

    def test_yaml_file_exists_and_loadable(self):
        """Test that the YAML file exists and can be loaded."""
        yaml_path = Path(__file__).parent.parent.parent.parent / "app" / "config" / "tag_dictionary.yaml"
        assert yaml_path.exists(), f"YAML file not found: {yaml_path}"

        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data is not None, "YAML file is empty"
        assert isinstance(data, dict), "YAML root must be a mapping"

    def test_all_6_constraint_dimensions_present(self):
        """Test that all 6 constraint dimensions exist in the dictionary."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()

        required_dims = ["LAW", "ACT", "NAR", "WST", "SOC", "RED"]
        for dim in required_dims:
            assert dim in dictionary.dimensions, f"Missing required dimension: {dim}"

    def test_a2_additions_loc_and_sty_present(self):
        """Test that A2 additions (LOC and STY) are present."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()

        assert "LOC" in dictionary.dimensions, "Missing A2 addition: LOC"
        assert "STY" in dictionary.dimensions, "Missing A2 addition: STY"

    def test_law_dimension_has_required_tags(self):
        """Test that LAW dimension has all required tags from 断点B."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()

        law_tags = dictionary.dimensions["LAW"]
        required_tags = ["world_structure", "gravity", "conservation", "divine_intervention", "afterlife"]

        for tag in required_tags:
            assert tag in law_tags, f"LAW dimension missing required tag: {tag}"

    def test_act_dimension_has_required_tags(self):
        """Test that ACT dimension has all required tags from 断点B."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()

        act_tags = dictionary.dimensions["ACT"]
        required_tags = ["dice_mode", "check_direction", "cost_function", "core_action"]

        for tag in required_tags:
            assert tag in act_tags, f"ACT dimension missing required tag: {tag}"

    def test_nar_dimension_has_required_tags(self):
        """Test that NAR dimension has all required tags from 断点B."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()

        nar_tags = dictionary.dimensions["NAR"]
        required_tags = ["era_stage", "time_mode", "trajectory", "success_granularity"]

        for tag in required_tags:
            assert tag in nar_tags, f"NAR dimension missing required tag: {tag}"

    def test_wst_dimension_has_required_tags(self):
        """Test that WST dimension has all required tags from 断点B."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()

        wst_tags = dictionary.dimensions["WST"]
        required_tags = ["cost_type", "feedback_loop", "climate_zone", "power_saturation"]

        for tag in required_tags:
            assert tag in wst_tags, f"WST dimension missing required tag: {tag}"

    def test_soc_dimension_has_required_tags(self):
        """Test that SOC dimension has all required tags from 断点B."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()

        soc_tags = dictionary.dimensions["SOC"]
        required_tags = ["political_type", "access_topology", "threshold", "economy_type"]

        for tag in required_tags:
            assert tag in soc_tags, f"SOC dimension missing required tag: {tag}"

    def test_loc_dimension_has_required_tags(self):
        """Test that LOC dimension has required tags from A2."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()

        loc_tags = dictionary.dimensions["LOC"]
        required_tags = ["loc_topology", "loc_connectivity"]

        for tag in required_tags:
            assert tag in loc_tags, f"LOC dimension missing required tag: {tag}"

    def test_sty_dimension_has_required_tags(self):
        """Test that STY dimension has required tags from A2."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()

        sty_tags = dictionary.dimensions["STY"]
        required_tags = ["style_keywords", "architecture_style"]

        for tag in required_tags:
            assert tag in sty_tags, f"STY dimension missing required tag: {tag}"

    def test_enum_values_closed_and_nonempty(self):
        """Test that all tags have non-empty closed enum value lists."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()

        for dim_name, tags in dictionary.dimensions.items():
            for tag_name in tags:
                enum_values = dictionary.get_enum_values(dim_name, tag_name)
                assert isinstance(enum_values, list), f"{dim_name}.{tag_name} enum values must be a list"
                assert len(enum_values) > 0, f"{dim_name}.{tag_name} has empty enum values list"

    def test_get_enum_values_returns_correct_values(self):
        """Test get_enum_values returns the expected enum list."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()

        # Test example from source: world_structure should have FLOATING_ISLANDS
        law_world_structure = dictionary.get_enum_values("LAW", "world_structure")
        assert "FLOATING_ISLANDS" in law_world_structure, "Missing expected enum: FLOATING_ISLANDS"

        # Verify it's a list (closed set)
        assert isinstance(law_world_structure, list), "get_enum_values must return a list"

    def test_invalid_dimension_raises_error(self):
        """Test that querying an invalid dimension raises an error."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()

        with pytest.raises(ValueError, match="Invalid dimension"):
            dictionary.get_enum_values("INVALID_DIM", "some_tag")

    def test_invalid_tag_raises_error(self):
        """Test that querying an invalid tag raises an error."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()

        with pytest.raises(ValueError, match="Invalid tag"):
            dictionary.get_enum_values("LAW", "invalid_tag_name")

    def test_enum_values_are_closed_set(self):
        """Test that enum values are a closed set (all strings, no dynamic values)."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()

        for dim_name, tags in dictionary.dimensions.items():
            for tag_name in tags:
                enum_values = dictionary.get_enum_values(dim_name, tag_name)
                # All values must be strings
                for value in enum_values:
                    assert isinstance(value, str), f"{dim_name}.{tag_name} has non-string enum value: {value}"

    def test_validate_enum_value_accepts_valid(self):
        """Test that validate_enum_value accepts valid enum values."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()

        # Test with known valid value from source
        result = dictionary.validate_enum_value("LAW", "world_structure", "FLOATING_ISLANDS")
        assert result is True, "validate_enum_value() should return True for valid enum value"

    def test_validate_enum_value_rejects_invalid(self):
        """Test that validate_enum_value rejects invalid enum values (closed set enforcement)."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()

        # Test with clearly invalid value
        result = dictionary.validate_enum_value("LAW", "world_structure", "NOT_A_REAL_VALUE")
        assert result is False, "validate_enum_value() should return False for invalid enum value"

    def test_dice_mode_has_probability_distribution_enums(self):
        """Test that dice_mode contains probability distribution enums from source L96-100."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()

        dice_mode_values = dictionary.get_enum_values("ACT", "dice_mode")

        # From source: 线性d20 (意志→线性) / 钟形3d6 (物质→钟形)
        # Using enum-like identifiers
        assert any("d20" in str(v).lower() for v in dice_mode_values), "dice_mode missing d20 linear distribution"
        assert any("3d6" in str(v).lower() for v in dice_mode_values), "dice_mode missing 3d6 bell curve distribution"

    def test_yaml_structure_matches_expected_format(self):
        """Test that YAML structure matches the expected dimension->tag->values format."""
        yaml_path = Path(__file__).parent.parent.parent.parent / "app" / "config" / "tag_dictionary.yaml"

        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Top level should be dimensions
        for dim_name in ["LAW", "ACT", "NAR", "WST", "SOC", "RED", "LOC", "STY"]:
            assert dim_name in data, f"YAML missing dimension: {dim_name}"
            assert isinstance(data[dim_name], dict), f"Dimension {dim_name} must be a mapping"

            # Each dimension should contain tags
            for tag_name, enum_values in data[dim_name].items():
                assert isinstance(enum_values, list), f"{dim_name}.{tag_name} values must be a list"
                assert len(enum_values) > 0, f"{dim_name}.{tag_name} has empty enum list"
