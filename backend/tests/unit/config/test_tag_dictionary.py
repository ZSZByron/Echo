# Tests for tag_dictionary.yaml configuration
import pytest
from pathlib import Path
import yaml

# Resolve from tests/unit/config -> backend/app/config
TAG_DICT_PATH = Path(__file__).parent.parent.parent.parent / "app" / "config" / "tag_dictionary.yaml"


class TestTagDictionary:
    """Test tag dictionary structure and completeness."""

    def test_yaml_exists_and_parsable(self):
        """YAML file exists and is valid YAML."""
        assert TAG_DICT_PATH.exists(), f"Tag dictionary not found at {TAG_DICT_PATH}"
        with open(TAG_DICT_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), "Root must be a mapping"

    def test_all_dimensions_present(self):
        """All 6 constraint dimensions present + LOC/STY."""
        with open(TAG_DICT_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        required_dims = ["LAW", "ACT", "NAR", "WST", "SOC", "LOC", "STY"]
        for dim in required_dims:
            assert dim in data, f"Missing dimension: {dim}"
            assert isinstance(data[dim], dict), f"{dim} must be a mapping"

    def test_all_required_tags_present(self):
        """Each dimension has its required tags with values."""
        with open(TAG_DICT_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # LAW: world_structure / gravity / conservation / divine_intervention / afterlife
        assert "world_structure" in data["LAW"]
        assert "gravity" in data["LAW"]
        assert "conservation" in data["LAW"]
        assert "divine_intervention" in data["LAW"]
        assert "afterlife" in data["LAW"]

        # ACT: dice_mode / check_direction / cost_function / core_action
        assert "dice_mode" in data["ACT"]
        assert "check_direction" in data["ACT"]
        assert "cost_function" in data["ACT"]
        assert "core_action" in data["ACT"]

        # NAR: era_stage / time_mode / trajectory / success_granularity
        assert "era_stage" in data["NAR"]
        assert "time_mode" in data["NAR"]
        assert "trajectory" in data["NAR"]
        assert "success_granularity" in data["NAR"]

        # WST: cost_type / feedback_loop / climate_zone / power_saturation
        assert "cost_type" in data["WST"]
        assert "feedback_loop" in data["WST"]
        assert "climate_zone" in data["WST"]
        assert "power_saturation" in data["WST"]

        # SOC: political_type / access_topology / threshold / economy_type
        assert "political_type" in data["SOC"]
        assert "access_topology" in data["SOC"]
        assert "threshold" in data["SOC"]
        assert "economy_type" in data["SOC"]

        # LOC (A2新增): loc_topology / loc_connectivity
        assert "loc_topology" in data["LOC"]
        assert "loc_connectivity" in data["LOC"]

        # STY (A2新增): style_keywords / architecture_style
        assert "style_keywords" in data["STY"]
        assert "architecture_style" in data["STY"]

    def test_each_tag_has_layered_structure(self):
        """Each tag has attested/proposed layered structure."""
        with open(TAG_DICT_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        for dim_name, dim_data in data.items():
            for tag_name, tag_data in dim_data.items():
                assert "attested" in tag_data, f"{dim_name}.{tag_name} missing attested key"
                assert "proposed" in tag_data, f"{dim_name}.{tag_name} missing proposed key"
                assert isinstance(tag_data["attested"], list), f"{dim_name}.{tag_name} attested must be list"
                assert isinstance(tag_data["proposed"], list), f"{dim_name}.{tag_name} proposed must be list"
                # Combined should be non-empty
                combined = tag_data["attested"] + tag_data["proposed"]
                assert len(combined) > 0, f"{dim_name}.{tag_name} combined values cannot be empty"

    def test_enum_values_match_hierarchy_diagram(self):
        """Sample enum values match hierarchy diagram (A模块层级图-含断点.md L105-130)."""
        with open(TAG_DICT_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Spot-check LAW attested values (from example: FLOATING_ISLANDS, SPHERE, TREE)
        law_world_attested = data["LAW"]["world_structure"]["attested"]
        assert "FLOATING_ISLANDS" in law_world_attested, "Must contain FLOATING_ISLANDS from hierarchy"
        assert "SPHERE" in law_world_attested, "Must contain SPHERE from hierarchy"
        assert "TREE" in law_world_attested, "Must contain TREE from hierarchy"

        # Spot-check LAW gravity attested (from example: HIGH)
        law_gravity_attested = data["LAW"]["gravity"]["attested"]
        assert "HIGH" in law_gravity_attested, "Must contain HIGH from hierarchy"

        # Spot-check LAW conservation attested (from example: TRUE)
        law_conservation_attested = data["LAW"]["conservation"]["attested"]
        assert "TRUE" in law_conservation_attested, "Must contain TRUE from hierarchy"

        # Verify ACT has dice_mode (plan requirement)
        act_dice_attested = data["ACT"]["dice_mode"]["attested"]
        act_dice_proposed = data["ACT"]["dice_mode"]["proposed"]
        act_dice_all = act_dice_attested + act_dice_proposed
        assert len(act_dice_all) > 0, "dice_mode must have enum values"

        # Verify NAR has era_stage (plan requirement)
        nar_era_attested = data["NAR"]["era_stage"]["attested"]
        nar_era_proposed = data["NAR"]["era_stage"]["proposed"]
        nar_era_all = nar_era_attested + nar_era_proposed
        assert len(nar_era_all) > 0, "era_stage must have enum values"

        # Verify WST has cost_type (plan requirement)
        wst_cost_attested = data["WST"]["cost_type"]["attested"]
        wst_cost_proposed = data["WST"]["cost_type"]["proposed"]
        wst_cost_all = wst_cost_attested + wst_cost_proposed
        assert len(wst_cost_all) > 0, "cost_type must have enum values"

        # Verify SOC has political_type (plan requirement)
        soc_political_attested = data["SOC"]["political_type"]["attested"]
        soc_political_proposed = data["SOC"]["political_type"]["proposed"]
        soc_political_all = soc_political_attested + soc_political_proposed
        assert len(soc_political_all) > 0, "political_type must have enum values"
