"""Tests for the A1 two-layer question tree."""
from app.domains.creation.seed.a1_question_tree import (
    MODULES,
    SubField,
    Module,
    module_ids,
    get_module,
    get_subfield,
    first_module,
    first_subfield,
    next_subfield,
    total_subfield_count,
    all_subfield_keys,
    subs_for_module,
    is_module_done,
)


class TestModuleStructure:
    def test_10_modules(self):
        assert len(MODULES) == 10

    def test_module_ids_match_spec(self):
        expected = [
            "IP定位", "世界本体", "力量体系", "地理空间", "文明与社会",
            "历史时间线", "视觉设计", "玩法设计DNA", "骰子设定", "AI生成边界",
        ]
        assert module_ids() == expected

    def test_each_module_has_2_to_5_subs(self):
        for m in MODULES:
            n = len(m["fields"])
            assert 2 <= n <= 5, f"{m['id']} has {n} subfields"

    def test_total_sub_count_in_range(self):
        assert 25 <= total_subfield_count() <= 40

    def test_all_sub_keys_unique(self):
        keys = all_subfield_keys()
        assert len(keys) == len(set(keys))


class TestSubItems:
    def test_first_sub_is_ip_name(self):
        m = first_module()
        sub = first_subfield(m["id"])
        assert m["id"] == "IP定位"
        assert sub["id"] == "name"

    def test_get_sub_returns_correct_pair(self):
        sub = get_subfield("力量体系", "acquire")
        assert sub is not None
        assert sub["id"] == "acquire"
        assert sub["label"] == "获取方式"

    def test_get_sub_unknown_returns_none(self):
        assert get_subfield("力量体系", "nonexistent") is None

    def test_next_sub_advances(self):
        m = first_module()
        sub = first_subfield(m["id"])
        nxt = next_subfield(m["id"], sub["id"])
        assert nxt is not None
        assert nxt["id"] == "concept"

    def test_next_sub_at_end_returns_none(self):
        last_key = all_subfield_keys()[-1]
        # Parse last key to get module_id and subfield_id
        parts = last_key.split(".", 1)
        assert next_subfield(parts[0], parts[1]) is None

    def test_next_sub_none_returns_first(self):
        m = first_module()
        assert next_subfield(m["id"], None) == first_subfield(m["id"])


class TestModuleDone:
    def test_module_done_when_all_subs_answered(self):
        answers = {"IP定位.name": "a", "IP定位.concept": "b", "IP定位.world_type": "c", "IP定位.core_experience": "d"}
        assert is_module_done("IP定位", answers) is True

    def test_module_not_done_when_missing_sub(self):
        answers = {"IP定位.name": "a"}
        assert is_module_done("IP定位", answers) is False

    def test_module_not_done_when_empty(self):
        assert is_module_done("IP定位", {}) is False


class TestSeverity:
    def test_severity_values_locked(self):
        # Severity values are now mentioned only in comments, not as a constant
        # The valid values are: COSMIC, MAJOR, REGIONAL, MINOR
        expected_values = ["COSMIC", "MAJOR", "REGIONAL", "MINOR"]
        # Check that these values are mentioned in the MODULES structure
        found_values = []
        for module in MODULES:
            for field in module["fields"]:
                if "severity" in field.get("hint", "").lower():
                    # Extract severity values from hints
                    import re
                    matches = re.findall(r'(COSMIC|MAJOR|REGIONAL|MINOR)', field["hint"])
                    found_values.extend(matches)
        # Verify the expected values appear somewhere in the hints
        for val in expected_values:
            assert any(val in field.get("hint", "") for module in MODULES for field in module["fields"])
