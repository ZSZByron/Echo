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

            # Each dimension should contain tags with attested/proposed structure
            for tag_name, tag_data in data[dim_name].items():
                # New layered structure
                assert isinstance(tag_data, dict), f"{dim_name}.{tag_name} must be a mapping"
                assert "attested" in tag_data, f"{dim_name}.{tag_name} missing 'attested' key"
                assert "proposed" in tag_data, f"{dim_name}.{tag_name} missing 'proposed' key"
                assert isinstance(tag_data["attested"], list), f"{dim_name}.{tag_name}.attested must be list"
                assert isinstance(tag_data["proposed"], list), f"{dim_name}.{tag_name}.proposed must be list"

                # Combined list should be non-empty
                combined = tag_data["attested"] + tag_data["proposed"]
                assert len(combined) > 0, f"{dim_name}.{tag_name} has empty combined enum list"

    def test_layered_api_methods_work(self):
        """Test that the new layered API methods work correctly."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()

        # Test get_enum_values (returns merged attested + proposed)
        law_world = dictionary.get_enum_values("LAW", "world_structure")
        assert "FLOATING_ISLANDS" in law_world, "Should contain attested value FLOATING_ISLANDS"
        assert "FLAT_PLANE" in law_world, "Should contain proposed value FLAT_PLANE"

        # Test get_attested_values (returns only attested)
        attested = dictionary.get_attested_values("LAW", "world_structure")
        assert "FLOATING_ISLANDS" in attested, "Attested should contain FLOATING_ISLANDS"
        assert "FLAT_PLANE" not in attested, "Attested should not contain proposed value FLAT_PLANE"

        # Test get_proposed_values (returns only proposed)
        proposed = dictionary.get_proposed_values("LAW", "world_structure")
        assert "FLOATING_ISLANDS" not in proposed, "Proposed should not contain attested value"
        assert "FLAT_PLANE" in proposed, "Proposed should contain FLAT_PLANE"

    def test_attested_values_match_hierarchy_l105_130(self):
        """Test that attested values match hierarchy diagram L105-130 exactly."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()

        # world_structure: FLOATING_ISLANDS / SPHERE / TREE(+"/...")
        law_world_attested = dictionary.get_attested_values("LAW", "world_structure")
        assert "FLOATING_ISLANDS" in law_world_attested, "Must contain FLOATING_ISLANDS from hierarchy"
        assert "SPHERE" in law_world_attested, "Must contain SPHERE from hierarchy"
        assert "TREE" in law_world_attested, "Must contain TREE from hierarchy"
        assert len(law_world_attested) == 3, "world_structure should have exactly 3 attested values"

        # gravity: HIGH
        law_gravity_attested = dictionary.get_attested_values("LAW", "gravity")
        assert "HIGH" in law_gravity_attested, "Must contain HIGH from hierarchy"
        assert len(law_gravity_attested) == 1, "gravity should have exactly 1 attested value"

        # conservation: TRUE
        law_conservation_attested = dictionary.get_attested_values("LAW", "conservation")
        assert "TRUE" in law_conservation_attested, "Must contain TRUE from hierarchy"
        assert len(law_conservation_attested) == 1, "conservation should have exactly 1 attested value"

    def test_gravity_does_not_contain_true_false(self):
        """Test that gravity no longer contains TRUE/FALSE (they belong to conservation)."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()
        law_gravity = dictionary.get_enum_values("LAW", "gravity")

        assert "TRUE" not in law_gravity, "gravity should not contain TRUE (belongs to conservation)"
        assert "FALSE" not in law_gravity, "gravity should not contain FALSE (belongs to conservation)"
        assert "HIGH" in law_gravity, "gravity should still contain HIGH"

    def test_conservation_contains_true(self):
        """Test that conservation contains TRUE (and optionally FALSE)."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()
        law_conservation = dictionary.get_enum_values("LAW", "conservation")

        assert "TRUE" in law_conservation, "conservation must contain TRUE from hierarchy"

    def test_proposed_values_extension_works(self):
        """Test that proposed values properly extend attested values."""
        from app.models.tag_dictionary import load_tag_dictionary

        dictionary = load_tag_dictionary()

        # gravity should have HIGH (attested) + NORMAL/LOW/ZERO/VARIABLE (proposed)
        gravity_all = dictionary.get_enum_values("LAW", "gravity")
        gravity_attested = dictionary.get_attested_values("LAW", "gravity")
        gravity_proposed = dictionary.get_proposed_values("LAW", "gravity")

        assert len(gravity_attested) == 1, "gravity should have 1 attested value"
        assert len(gravity_proposed) > 0, "gravity should have proposed extensions"
        assert len(gravity_all) == len(gravity_attested) + len(gravity_proposed), "Total should equal attested + proposed"
        assert set(gravity_all) == set(gravity_attested + gravity_proposed), "Combined values should match union"
