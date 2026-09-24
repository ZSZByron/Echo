"""C5 contract: tier 映射契约（M1 池语义重锚，DN2 默认）。

原封闭集形态（10 模块 == TIER_MAP 闭集）自甲计划 M1 起重锚：
- 池语义：MODULE_POOL 内模块必有 tier（module_tier_coverage 为空）；
- 层值闭集：tier 值域 [0, 6] 七层保持封闭——新入池模块复用既有层值，
  不新增第 8 层（翻案记录归 D14 / decision-log 治理批次 G）。
问卷树 10 模块仍是 TIER_MAP 的真子集基线（default 配方行为零变化）。
"""
from __future__ import annotations

from app.domains.creation.a1.tier_map import (
    MAX_TIER,
    MIN_TIER,
    TIER_MAP,
    module_tier_coverage,
)
from app.domains.creation.seed.a1_question_tree import module_ids
from app.domains.creation.shared.module_registry import MODULE_POOL


def test_c5_pool_modules_have_tier() -> None:
    # 池语义：池内模块必有 tier；问卷树 10 模块仍是 TIER_MAP 基线子集。
    assert module_tier_coverage() == []
    assert set(MODULE_POOL) <= set(TIER_MAP)
    assert set(module_ids()) <= set(TIER_MAP)
    assert set(module_ids()) == set(MODULE_POOL)  # M1 池 == 树（M2/M3 入池后放宽）


def test_c5_tier_values_within_closed_range() -> None:
    assert MIN_TIER == 0
    assert MAX_TIER == 6
    for module, tier in TIER_MAP.items():
        assert MIN_TIER <= tier <= MAX_TIER, f"{module} tier={tier} 超出 [0,6]"


def test_c5_tier_range_stays_seven_layers() -> None:
    # 层值闭集（DN2 默认）：range [0,6] 封闭，新模块复用既有层值不新增层。
    assert set(range(MIN_TIER, MAX_TIER + 1)) == {0, 1, 2, 3, 4, 5, 6}
