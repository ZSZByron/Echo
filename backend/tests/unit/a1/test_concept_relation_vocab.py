"""TDD测试 - ConceptRelationVocab 概念关系词典 (Task T-A)

测试策略：
1. 纯静态种子表完整性：10条 / 三级分布 3★-5◆-2◇ / name唯一
2. RelationRegistry 运行时词典：is_known / add（默认◆semantic）/ all_specs
3. 零 LLM 调用
"""
from __future__ import annotations

from app.domains.creation.a1.concept_relation_vocab import (
    RELATION_NAMES,
    RELATION_VOCAB,
    RelationRegistry,
    RelationSpec,
)


class TestSeedVocab:
    def test_seed_has_exactly_10_relations(self):
        assert len(RELATION_VOCAB) == 10

    def test_seed_level_distribution_3_5_2(self):
        counts = {"rule": 0, "semantic": 0, "structure": 0}
        for spec in RELATION_VOCAB:
            counts[spec.level] += 1
        assert counts == {"rule": 3, "semantic": 5, "structure": 2}

    def test_seed_names_unique(self):
        names = [spec.name for spec in RELATION_VOCAB]
        assert len(names) == len(set(names))

    def test_seed_names_verbatim(self):
        """种子关系名逐字匹配用户决策（★3 / ◆5 / ◇2）."""
        expected = {
            # ★rule
            "隶属", "对立", "等同",
            # ◆semantic
            "引发", "转化", "依赖", "象征", "制约",
            # ◇structure
            "共现", "分型",
        }
        assert set(spec.name for spec in RELATION_VOCAB) == expected

    def test_seed_names_in_relation_names(self):
        assert RELATION_NAMES == frozenset(spec.name for spec in RELATION_VOCAB)

    def test_relation_spec_fields(self):
        spec = RELATION_VOCAB[0]
        assert isinstance(spec, RelationSpec)
        assert spec.name
        assert spec.level in ("rule", "semantic", "structure")
        assert spec.gloss
        # example 是可选但种子表全给了
        assert spec.example


class TestRelationRegistry:
    def test_is_known_seed_names(self):
        reg = RelationRegistry()
        assert reg.is_known("引发") is True
        assert reg.is_known("不存在的词") is False

    def test_add_new_relation_defaults_semantic(self):
        reg = RelationRegistry()
        spec = reg.add("共鸣", gloss="A与B同频共振")
        assert spec.level == "semantic"  # 默认◆
        assert spec.name == "共鸣"
        assert reg.is_known("共鸣") is True

    def test_add_explicit_level(self):
        reg = RelationRegistry()
        spec = reg.add("互斥", level="rule", gloss="A与B不可共存")
        assert spec.level == "rule"

    def test_add_does_not_mutate_global_seed(self):
        """Registry.add 只影响运行时词典，不改全局 RELATION_VOCAB/RELATION_NAMES."""
        reg = RelationRegistry()
        reg.add("临时词")
        assert "临时词" not in RELATION_NAMES
        assert len(RELATION_VOCAB) == 10

    def test_all_specs_includes_seed_and_added(self):
        reg = RelationRegistry()
        reg.add("共鸣")
        specs = reg.all_specs()
        assert len(specs) == 11  # 10 seed + 1 added
        assert any(s.name == "共鸣" for s in specs)
