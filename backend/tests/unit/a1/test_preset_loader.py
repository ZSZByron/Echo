"""Tests for preset_loader."""
from app.domains.creation.seed.preset_loader import PresetSeed, load_presets

EXPECTED_IDS = {
    "IP定位", "世界本体", "力量体系", "地理空间", "文明与社会",
    "历史时间线", "视觉设计", "玩法设计DNA", "骰子设定", "AI生成边界",
}


class TestLoadPresets:
    def test_returns_8_presets(self):
        presets = load_presets()
        assert len(presets) == 8

    def test_each_preset_has_required_fields(self):
        presets = load_presets()
        for p in presets:
            assert p.id in {1, 2, 3, 4, 5, 6, 7, 8}
            assert isinstance(p.name, str) and len(p.name) > 0
            assert isinstance(p.genre, str) and len(p.genre) > 0
            assert isinstance(p.description, str) and len(p.description) > 0

    def test_dimension_defaults_has_10_sections(self):
        presets = load_presets()
        for p in presets:
            assert len(p.dimension_defaults) == 10

    def test_dimension_defaults_contains_new_module_ids(self):
        presets = load_presets()
        for p in presets:
            assert set(p.dimension_defaults.keys()) == EXPECTED_IDS

    def test_preset_1_fields(self):
        presets = load_presets()
        p1 = next(p for p in presets if p.id == 1)
        assert p1.name == "深渊低语"
        assert p1.genre == "克苏鲁恐怖"

    def test_preset_ids_sequential(self):
        presets = load_presets()
        ids = [p.id for p in presets]
        assert ids == [1, 2, 3, 4, 5, 6, 7, 8]

    def test_preset_model_is_immutable_dataclass(self):
        from dataclasses import fields
        assert len(fields(PresetSeed)) >= 4
