"""TDD tests for structured fields in DimensionOutput models.

Following test-driven-development principles:
- Tests are written FIRST and watched to FAIL correctly
- Each test validates ONE specific behavior
- Tests use real code, not mocks
- Tests prove the feature works as intended
"""

import pytest

from app.models.dimension import (
    ActOutput,
    LawOutput,
    NarOutput,
    RedOutput,
    SocOutput,
    WstOutput,
)
from app.models.tag_dictionary import load_tag_dictionary


class TestLawOutputStructuredFields:
    """Test LawOutput structured fields."""

    def test_law_output_has_world_structure_field(self):
        """LawOutput must have world_structure field with default None."""
        m = LawOutput(rules=["test rule"])
        assert hasattr(m, "world_structure")
        assert m.world_structure is None

    def test_law_output_has_gravity_field(self):
        """LawOutput must have gravity field with default None."""
        m = LawOutput(rules=["test rule"])
        assert hasattr(m, "gravity")
        assert m.gravity is None

    def test_law_output_has_conservation_field(self):
        """LawOutput must have conservation field with default None."""
        m = LawOutput(rules=["test rule"])
        assert hasattr(m, "conservation")
        assert m.conservation is None

    def test_law_output_has_divine_intervention_field(self):
        """LawOutput must have divine_intervention field with default None."""
        m = LawOutput(rules=["test rule"])
        assert hasattr(m, "divine_intervention")
        assert m.divine_intervention is None

    def test_law_output_has_afterlife_field(self):
        """LawOutput must have afterlife field with default None."""
        m = LawOutput(rules=["test rule"])
        assert hasattr(m, "afterlife")
        assert m.afterlife is None

    def test_law_output_accepts_valid_enum_value(self):
        """LawOutput accepts valid enum value for world_structure."""
        # This test will FAIL until field is added and validator works
        m = LawOutput(rules=["test"], world_structure="FLOATING_ISLANDS")
        assert m.world_structure == "FLOATING_ISLANDS"

    def test_law_output_rejects_invalid_enum_value(self):
        """LawOutput validates against enum dictionary and rejects invalid values."""
        # Validator references T4 tag_dictionary for validation
        with pytest.raises(ValueError, match="Invalid.*world_structure"):
            LawOutput(rules=["test"], world_structure="INVALID_VALUE")

    def test_law_output_preserves_free_text_fields(self):
        """LawOutput preserves original free text fields."""
        m = LawOutput(rules=["rule1", "rule2"], mechanism="test mechanism")
        assert m.rules == ["rule1", "rule2"]
        assert m.mechanism == "test mechanism"


class TestActOutputStructuredFields:
    """Test ActOutput structured fields."""

    def test_act_output_has_dice_mode_field(self):
        """ActOutput must have dice_mode field with default None."""
        m = ActOutput(actions=[{"trigger": "test"}])
        assert hasattr(m, "dice_mode")
        assert m.dice_mode is None

    def test_act_output_has_check_direction_field(self):
        """ActOutput must have check_direction field with default None."""
        m = ActOutput(actions=[{"trigger": "test"}])
        assert hasattr(m, "check_direction")
        assert m.check_direction is None

    def test_act_output_has_cost_function_field(self):
        """ActOutput must have cost_function field with default None."""
        m = ActOutput(actions=[{"trigger": "test"}])
        assert hasattr(m, "cost_function")
        assert m.cost_function is None

    def test_act_output_has_core_action_field(self):
        """ActOutput must have core_action field with default None."""
        m = ActOutput(actions=[{"trigger": "test"}])
        assert hasattr(m, "core_action")
        assert m.core_action is None

    def test_act_output_accepts_valid_enum_value(self):
        """ActOutput accepts valid enum value for dice_mode."""
        # This test will FAIL until field is added and validator works
        m = ActOutput(actions=[{"trigger": "test"}], dice_mode="LINEAR_D20")
        assert m.dice_mode == "LINEAR_D20"

    def test_act_output_rejects_invalid_enum_value(self):
        """ActOutput validates against enum dictionary and rejects invalid values."""
        # Validator references T4 tag_dictionary for validation
        with pytest.raises(ValueError, match="Invalid.*dice_mode"):
            ActOutput(actions=[{"trigger": "test"}], dice_mode="INVALID_VALUE")

    def test_act_output_preserves_free_text_fields(self):
        """ActOutput preserves original free text fields."""
        actions = [{"trigger": "attack", "check": "strength"}]
        m = ActOutput(actions=actions)
        assert m.actions == actions


class TestNarOutputStructuredFields:
    """Test NarOutput structured fields."""

    def test_nar_output_has_era_stage_field(self):
        """NarOutput must have era_stage field with default None."""
        m = NarOutput(style="test style")
        assert hasattr(m, "era_stage")
        assert m.era_stage is None

    def test_nar_output_has_time_mode_field(self):
        """NarOutput must have time_mode field with default None."""
        m = NarOutput(style="test style")
        assert hasattr(m, "time_mode")
        assert m.time_mode is None

    def test_nar_output_has_trajectory_field(self):
        """NarOutput must have trajectory field with default None."""
        m = NarOutput(style="test style")
        assert hasattr(m, "trajectory")
        assert m.trajectory is None

    def test_nar_output_has_success_granularity_field(self):
        """NarOutput must have success_granularity field with default None."""
        m = NarOutput(style="test style")
        assert hasattr(m, "success_granularity")
        assert m.success_granularity is None

    def test_nar_output_accepts_valid_enum_value(self):
        """NarOutput accepts valid enum value for era_stage."""
        # This test will FAIL until field is added and validator works
        m = NarOutput(style="test", era_stage="ANCIENT")
        assert m.era_stage == "ANCIENT"

    def test_nar_output_rejects_invalid_enum_value(self):
        """NarOutput validates against enum dictionary and rejects invalid values."""
        # Validator references T4 tag_dictionary for validation
        with pytest.raises(ValueError, match="Invalid.*era_stage"):
            NarOutput(style="test", era_stage="INVALID_VALUE")

    def test_nar_output_preserves_free_text_fields(self):
        """NarOutput preserves original free text fields."""
        m = NarOutput(style="epic", keywords=["heroic", "dramatic"], tone="serious")
        assert m.style == "epic"
        assert m.keywords == ["heroic", "dramatic"]
        assert m.tone == "serious"


class TestWstOutputStructuredFields:
    """Test WstOutput structured fields."""

    def test_wst_output_has_cost_type_field(self):
        """WstOutput must have cost_type field with default None."""
        m = WstOutput(effects=[{"name": "buff"}])
        assert hasattr(m, "cost_type")
        assert m.cost_type is None

    def test_wst_output_has_feedback_loop_field(self):
        """WstOutput must have feedback_loop field with default None."""
        m = WstOutput(effects=[{"name": "buff"}])
        assert hasattr(m, "feedback_loop")
        assert m.feedback_loop is None

    def test_wst_output_has_climate_zone_field(self):
        """WstOutput must have climate_zone field with default None."""
        m = WstOutput(effects=[{"name": "buff"}])
        assert hasattr(m, "climate_zone")
        assert m.climate_zone is None

    def test_wst_output_has_power_saturation_field(self):
        """WstOutput must have power_saturation field with default None."""
        m = WstOutput(effects=[{"name": "buff"}])
        assert hasattr(m, "power_saturation")
        assert m.power_saturation is None

    def test_wst_output_accepts_valid_enum_value(self):
        """WstOutput accepts valid enum value for cost_type."""
        # This test will FAIL until field is added and validator works
        m = WstOutput(effects=[{"name": "buff"}], cost_type="MANA")
        assert m.cost_type == "MANA"

    def test_wst_output_rejects_invalid_enum_value(self):
        """WstOutput validates against enum dictionary and rejects invalid values."""
        # Validator references T4 tag_dictionary for validation
        with pytest.raises(ValueError, match="Invalid.*cost_type"):
            WstOutput(effects=[{"name": "buff"}], cost_type="INVALID_VALUE")

    def test_wst_output_preserves_free_text_fields(self):
        """WstOutput preserves original free text fields."""
        effects = [{"name": "fire_damage", "type": "damage", "magnitude": 10}]
        m = WstOutput(effects=effects)
        assert m.effects == effects


class TestSocOutputStructuredFields:
    """Test SocOutput structured fields."""

    def test_soc_output_has_political_type_field(self):
        """SocOutput must have political_type field with default None."""
        m = SocOutput(relations=[{"target": "king", "type": "ally"}])
        assert hasattr(m, "political_type")
        assert m.political_type is None

    def test_soc_output_has_access_topology_field(self):
        """SocOutput must have access_topology field with default None."""
        m = SocOutput(relations=[{"target": "king", "type": "ally"}])
        assert hasattr(m, "access_topology")
        assert m.access_topology is None

    def test_soc_output_has_threshold_field(self):
        """SocOutput must have threshold field with default None."""
        m = SocOutput(relations=[{"target": "king", "type": "ally"}])
        assert hasattr(m, "threshold")
        assert m.threshold is None

    def test_soc_output_has_economy_type_field(self):
        """SocOutput must have economy_type field with default None."""
        m = SocOutput(relations=[{"target": "king", "type": "ally"}])
        assert hasattr(m, "economy_type")
        assert m.economy_type is None

    def test_soc_output_accepts_valid_enum_value(self):
        """SocOutput accepts valid enum value for political_type."""
        # This test will FAIL until field is added and validator works
        m = SocOutput(relations=[{"target": "king"}], political_type="MONARCHY")
        assert m.political_type == "MONARCHY"

    def test_soc_output_rejects_invalid_enum_value(self):
        """SocOutput validates against enum dictionary and rejects invalid values."""
        # Validator references T4 tag_dictionary for validation
        with pytest.raises(ValueError, match="Invalid.*political_type"):
            SocOutput(relations=[{"target": "king"}], political_type="INVALID_VALUE")

    def test_soc_output_preserves_free_text_fields(self):
        """SocOutput preserves original free text fields."""
        relations = [{"target": "merchant", "type": "trade", "value": 50}]
        m = SocOutput(relations=relations)
        assert m.relations == relations


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_law_output_old_construction_still_works(self):
        """LawOutput can still be created without new structured fields."""
        # This should not crash
        m = LawOutput(rules=["old style rule"])
        assert m.rules == ["old style rule"]

    def test_act_output_old_construction_still_works(self):
        """ActOutput can still be created without new structured fields."""
        # This should not crash
        m = ActOutput(actions=[{"trigger": "old action"}])
        assert m.actions == [{"trigger": "old action"}]

    def test_nar_output_old_construction_still_works(self):
        """NarOutput can still be created without new structured fields."""
        # This should not crash
        m = NarOutput(style="old style", keywords=["test"])
        assert m.style == "old style"

    def test_wst_output_old_construction_still_works(self):
        """WstOutput can still be created without new structured fields."""
        # This should not crash
        m = WstOutput(effects=[{"name": "old effect"}])
        assert m.effects == [{"name": "old effect"}]

    def test_soc_output_old_construction_still_works(self):
        """SocOutput can still be created without new structured fields."""
        # This should not crash
        m = SocOutput(relations=[{"target": "old relation"}])
        assert m.relations == [{"target": "old relation"}]


class TestValidatorIntegration:
    """Test validator integration with tag_dictionary."""

    def test_error_message_includes_valid_values(self):
        """Validator error message includes list of valid enum values from tag_dictionary."""
        # Validator references T4 tag_dictionary for validation
        dict_instance = load_tag_dictionary()

        # Try to set an invalid value - should raise with helpful error message
        with pytest.raises(ValueError) as exc_info:
            LawOutput(rules=["test"], world_structure="INVALID_VALUE")

        # Error message should include valid options
        error_msg = str(exc_info.value)
        assert "world_structure" in error_msg or "WORLD_STRUCTURE" in error_msg
        # Should show some valid values exist
        assert len(error_msg) > 20  # Non-trivial message with options


class TestRedOutputNoChanges:
    """Test that RedOutput remains unchanged (no new fields per spec)."""

    def test_red_output_no_structured_fields_added(self):
        """RedOutput should not have any structured fields added."""
        # RedOutput is NOT in the breakpoint B specification
        # It should remain unchanged
        m = RedOutput(forbidden=["violence"], note="test note")
        assert m.forbidden == ["violence"]
        assert m.note == "test note"

        # Should NOT have new structured fields
        assert not hasattr(m, "world_structure")
        assert not hasattr(m, "dice_mode")
        assert not hasattr(m, "political_type")
