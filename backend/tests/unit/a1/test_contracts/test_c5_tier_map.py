"""C5 contract: tier 映射全静态（10 模块全覆盖、tier∈[0,6]）。

治理文档 §6 C5：tier 0-6 七层，封闭集合恰为 a1_question_tree 的 10 个模块 id。

T3 的 tier_map.py 已在 —— 直接写真断言。
"""
from __future__ import annotations

from app.domains.creation.a1.tier_map import (
    MAX_TIER,
    MIN_TIER,
    TIER_MAP,
    module_tier_coverage,
)
from app.domains.creation.seed.a1_question_tree import module_ids


def test_c5_all_10_modules_covered() -> None:
    assert set(TIER_MAP) == set(module_ids())
    assert len(TIER_MAP) == 10
    assert module_tier_coverage() == []


def test_c5_tier_values_within_closed_range() -> None:
    assert MIN_TIER == 0
    assert MAX_TIER == 6
    for module, tier in TIER_MAP.items():
        assert MIN_TIER <= tier <= MAX_TIER, f"{module} tier={tier} 超出 [0,6]"


def test_c5_no_11th_module() -> None:
    assert len(module_ids()) == 10, "禁止新增第 11 个模块 tier"
