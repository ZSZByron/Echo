"""C5: tier mapping contract tests — pool-semantics coverage (M1 re-anchor,
DN2 默认), tier RANGE stays closed [0, 6].

M1 起：模块池开放（故事/产出模块后续入池），tier 值闭集——池内模块必复用
既有 [0,6] 层值；TIER_MAP 可加键（池覆盖），"第 8 层"仍禁止（翻案记录归 D14）。
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
from app.models.knowledge_graph import GraphNode


def test_tier_map_covers_every_pool_module() -> None:
    """Pool semantics (M1): every MODULE_POOL module must have a tier key.

    问卷树 10 模块是池的初始子集——TIER_MAP 必须覆盖它们；后续批次入池
    模块同样受此约束（module_tier_coverage 池语义断言）。
    """
    assert set(module_ids()) <= set(TIER_MAP)
    assert set(MODULE_POOL) <= set(TIER_MAP)


def test_tier_values_within_range() -> None:
    """All tier values within [0, 6]."""
    for module_id, tier in TIER_MAP.items():
        assert MIN_TIER <= tier <= MAX_TIER, f"{module_id} tier={tier} out of range"


def test_module_tier_coverage_helper() -> None:
    """Coverage assertion helper passes and returns no missing ids."""
    assert module_tier_coverage() == []


def test_graph_node_backward_compat_without_tier() -> None:
    """Legacy node dict without tier deserializes fine with tier=None."""
    node = GraphNode.model_validate(
        {"id": "n1", "serial_number": "1-1", "level": 2, "description": "legacy"}
    )
    assert node.tier is None


def test_graph_node_accepts_tier() -> None:
    """New nodes can carry a tier value."""
    node = GraphNode(id="n2", serial_number="1-2", level=2, tier=4)
    assert node.tier == 4
