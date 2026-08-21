"""Tests for preset_loader — TDD RED phase."""

from app.domains.creation.seed.preset_loader import PresetSeed, load_presets


class TestLoadPresets:
    """TDD: 8 presets load from seed-presets-catalog.md authority."""

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
            for key in p.dimension_defaults:
                assert isinstance(key, str)
                assert isinstance(p.dimension_defaults[key], str)

    def test_dimension_defaults_contains_expected_sections(self):
        expected = {
            "世界观", "地理", "力量体系", "历史纪元", "社会生态",
            "经济", "红线规则", "叙事基调", "美术风格", "核心冲突",
        }
        presets = load_presets()
        for p in presets:
            assert set(p.dimension_defaults.keys()) == expected

    def test_preset_1_lovecraftian_fields(self):
        presets = load_presets()
        p1 = next(p for p in presets if p.id == 1)
        assert p1.name == "深渊低语"
        assert p1.genre == "克苏鲁恐怖"

    def test_preset_2_cyberpunk_fields(self):
        presets = load_presets()
        p2 = next(p for p in presets if p.id == 2)
        assert p2.name == "霓虹窃案"
        assert p2.genre == "赛博朋克"

    def test_preset_ids_are_sequential(self):
        presets = load_presets()
        ids = [p.id for p in presets]
        assert ids == [1, 2, 3, 4, 5, 6, 7, 8]

    def test_preset_model_is_immutable_dataclass(self):
        from dataclasses import fields
        assert len(fields(PresetSeed)) >= 4