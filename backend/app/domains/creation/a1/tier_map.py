"""A1 v0.5 content-tier mapping (C5 contract data plane).

Authority: docs/governance/2-A1-v0.5-内容图谱化统一模型与契约.md §3.
Closed set: exactly the 10 module ids from a1_question_tree.module_ids().
Tier values are within [0, 6]. Do not add an 11th module tier.
"""
from __future__ import annotations

from app.domains.creation.seed.a1_question_tree import module_ids

# tier 0-6 七层：存在基座 / 动力学 / 显现 / 时间 / 表达 / 命题 / 治理
TIER_MAP: dict[str, int] = {
    "世界本体": 0,
    "力量体系": 1,
    "地理空间": 2,
    "文明与社会": 2,
    "历史时间线": 3,
    "视觉设计": 4,
    "玩法设计DNA": 4,
    "骰子设定": 4,
    "IP定位": 5,
    "设定边界": 6,
}

MIN_TIER = 0
MAX_TIER = 6


def module_tier_coverage() -> list[str]:
    """Assert TIER_MAP keys == module_ids() set; return missing ids (empty when full coverage)."""
    tree_ids = set(module_ids())
    map_ids = set(TIER_MAP)
    assert map_ids == tree_ids, (
        f"TIER_MAP keys do not match a1 module_ids(): "
        f"missing_from_map={sorted(tree_ids - map_ids)}, "
        f"extra_in_map={sorted(map_ids - tree_ids)}"
    )
    return []
