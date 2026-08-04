"""Gap Detector — 缺失维度检测服务。

检查 ConceptNode 的五维状态，返回缺失维度列表 + 补全优先级 + 建议来源。

补全优先级逻辑：
    - 种子维度缺失的维度优先级最高（它们没有种子直接支撑）
    - 存在强依赖关系的维度优先（如 story 依赖 asset 的场景）
    - 参考维度越多 → 补全越容易 → 优先级越高

这是纯 Python 规则，零 LLM 调用。
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.models.concept import (
    CONSTRAINT_DIM,
    CULTURE_DIM,
    ASSET_DIM,
    EVENT_DIM,
    FIVE_DIMENSIONS,
    STORY_DIM,
    ConceptNode,
    DimensionStatus,
)

# ---------------------------------------------------------------------------
# 优先级权重表
# ---------------------------------------------------------------------------

# 每个维度作为"缺失维度"时的基础补全优先级（数字越大越优先）
# 经验值：constraint 最容易从其他维度推导 → 基础优先级最高
_DIM_PRIORITY: dict[str, int] = {
    STORY_DIM: 50,
    ASSET_DIM: 45,
    EVENT_DIM: 40,
    CULTURE_DIM: 35,
    CONSTRAINT_DIM: 55,  # 约束最容易从已有内容推导
}

# 维度间的强依赖关系：key 依赖 values 中至少一个
# 如果所有依赖都缺失 → 优先级降低（LLM 没有上下文可用）
_DIM_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    STORY_DIM: (ASSET_DIM,),        # 剧情需要物体来驱动
    EVENT_DIM: (STORY_DIM, ASSET_DIM),  # 事件需要剧情或物体来触发
    CULTURE_DIM: (STORY_DIM,),      # 文化需要叙事背景
    CONSTRAINT_DIM: (ASSET_DIM, EVENT_DIM),  # 约束作用于物体和事件
    ASSET_DIM: (),                   # 资产可独立存在
}

SuggestedSource = Literal["rule", "llm"]


class GapReport(BaseModel):
    """单个缺失维度的检测报告。

    Attributes:
        dimension: 缺失的维度名称。
        priority: 补全优先级 (0-100)，越大越优先。
        suggested_source: 建议来源 ("rule" 规则映射 / "llm" LLM 补全)。
        reason: 优先级判断的简要说明。
    """

    dimension: str
    priority: int = Field(ge=0, le=100)
    suggested_source: SuggestedSource
    reason: str = ""


class GapDetectionResult(BaseModel):
    """缺失检测的完整结果。"""

    gaps: list[GapReport] = Field(default_factory=list)
    filled_count: int = 0
    total_count: int = len(FIVE_DIMENSIONS)

    @property
    def has_gaps(self) -> bool:
        """是否存在缺失维度。"""
        return len(self.gaps) > 0

    @property
    def gap_dimensions(self) -> list[str]:
        """仅返回缺失维度名称列表（按优先级降序）。"""
        return [g.dimension for g in self.gaps]


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------

def detect_gaps(concept_node: ConceptNode) -> GapDetectionResult:
    """检查五维状态，返回缺失维度列表 + 补全优先级 + 建议来源。

    算法：
        1. 遍历 FIVE_DIMENSIONS，收集 fill_level == EMPTY 的维度
        2. 对每个空维度计算优先级：
           base_priority + filled_dependency_bonus - missing_dependency_penalty
        3. 根据种子维度和已有维度数量决定建议来源：
           - 如果已有维度 >= 2 → 建议 rule（有上下文可匹配规则）
           - 如果已有维度 < 2 → 建议 llm（规则覆盖不足）
        4. 按优先级降序排列

    Args:
        concept_node: 待检测的概念节点。

    Returns:
        GapDetectionResult: 缺失维度报告。
    """
    filled = concept_node.filled_dimensions()
    empty = concept_node.empty_dimensions()
    filled_count = len(filled)
    gaps: list[GapReport] = []

    for dim in empty:
        priority = _calculate_priority(dim, filled, filled_count)
        suggested = _suggest_source(dim, filled_count)
        reason = _build_reason(dim, filled, priority)

        gaps.append(GapReport(
            dimension=dim,
            priority=priority,
            suggested_source=suggested,
            reason=reason,
        ))

    # 降序排列
    gaps.sort(key=lambda g: g.priority, reverse=True)

    return GapDetectionResult(
        gaps=gaps,
        filled_count=filled_count,
        total_count=len(FIVE_DIMENSIONS),
    )


# ---------------------------------------------------------------------------
# 内部计算
# ---------------------------------------------------------------------------

def _calculate_priority(
    target_dim: str,
    filled_dims: list[str],
    filled_count: int,
) -> int:
    """计算单个缺失维度的补全优先级。

    优先级 = base + dependency_bonus + context_bonus

    Args:
        target_dim: 目标缺失维度。
        filled_dims: 已填充维度列表。
        filled_count: 已填充维度数量。

    Returns:
        优先级 0-100。
    """
    base = _DIM_PRIORITY.get(target_dim, 30)

    # 依赖奖励：已有的维度中有多少是 target 的依赖项
    deps = _DIM_DEPENDENCIES.get(target_dim, ())
    if deps:
        filled_deps = sum(1 for d in deps if d in filled_dims)
        dependency_bonus = filled_deps * 10
    else:
        dependency_bonus = 0

    # 上下文奖励：已有维度越多，补全越容易
    context_bonus = filled_count * 5

    raw = base + dependency_bonus + context_bonus
    return max(0, min(100, raw))


def _suggest_source(
    target_dim: str,
    filled_count: int,
) -> SuggestedSource:
    """决定建议的补全来源。

    经验规则：
        - 已有 >= 2 个维度 → rule（规则表有足够上下文匹配）
        - 已有 < 2 个维度 → llm（规则覆盖不足，需要 LLM 创造性补全）

    Args:
        target_dim: 目标缺失维度。
        filled_count: 已填充维度数量。

    Returns:
        "rule" 或 "llm"。
    """
    if filled_count >= 2:
        return "rule"
    return "llm"


def _build_reason(
    target_dim: str,
    filled_dims: list[str],
    priority: int,
) -> str:
    """生成优先级判断的简要说明。"""
    deps = _DIM_DEPENDENCIES.get(target_dim, ())
    if not deps:
        return f"基础优先级 {priority}（无前置依赖）"

    filled_deps = [d for d in deps if d in filled_dims]
    missing_deps = [d for d in deps if d not in filled_dims]

    parts = [f"基础 {_DIM_PRIORITY.get(target_dim, 30)}"]
    if filled_deps:
        parts.append(f"已有依赖 {filled_deps} +{len(filled_deps) * 10}")
    if missing_deps:
        parts.append(f"缺失依赖 {missing_deps}")

    parts.append(f"→ 最终 {priority}")
    return "，".join(parts)
