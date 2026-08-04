"""ConceptNode — 双向概念映射的中间表示。

ConceptNode 是概念瓶颈层 (Concept Bottleneck)：任意输入（文本/标签）
在此被解析为统一的五维状态容器，后续的 Gap Detector、Rule Mapper、
Backward Generator、Cycle Checker 全部围绕 ConceptNode 运转。

五维 (Five Dimensions):
    story      — 剧情/叙事
    asset      — 视觉资产/物体
    event      — 动态事件/遭遇
    culture    — 文化/阵营/价值观
    constraint — 规则约束/物理法则
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 五维名称 — 全系统统一引用，不允许散落字符串字面量
# ---------------------------------------------------------------------------

STORY_DIM = "story"
ASSET_DIM = "asset"
EVENT_DIM = "event"
CULTURE_DIM = "culture"
CONSTRAINT_DIM = "constraint"

FIVE_DIMENSIONS: tuple[str, ...] = (
    STORY_DIM,
    ASSET_DIM,
    EVENT_DIM,
    CULTURE_DIM,
    CONSTRAINT_DIM,
)


class SeedType(str, Enum):
    """输入种子的检测类型。"""

    STORY = "story"
    ASSET = "asset"
    EVENT = "event"
    CULTURE = "culture"
    CONSTRAINT = "constraint"
    MIXED = "mixed"  # 多维度混合输入


class DimensionFillLevel(str, Enum):
    """单个维度的填充程度。"""

    EMPTY = "empty"        # 无任何内容
    PARTIAL = "partial"    # 有部分内容但不完整
    FILLED = "filled"      # 已完整填充


class ContentSource(str, Enum):
    """维度内容的来源 — 用于追踪生成链路。"""

    INPUT = "input"                  # 用户直接输入
    RULE_MAPPED = "rule_mapped"      # 规则映射表确定性推导
    LLM_GENERATED = "llm_generated"  # LLM 补全生成
    BACKWARD_INFERRED = "backward"   # 反向推理得出
    USER_CONFIRMED = "user_confirmed"  # 用户确认/修改
    CYCLE_VERIFIED = "cycle_verified"  # 循环一致性校验通过


# ---------------------------------------------------------------------------
# 核心模型
# ---------------------------------------------------------------------------

class DimensionStatus(BaseModel):
    """单个维度的状态快照。

    Attributes:
        fill_level: 填充程度 (empty/partial/filled)。
        content: 维度具体内容，结构由维度类型决定（dict 或 None）。
        source: 内容来源，用于追溯生成链路。
        confidence: 置信度 [0.0, 1.0]，规则映射=1.0，LLM≈0.7。
    """

    fill_level: DimensionFillLevel = DimensionFillLevel.EMPTY
    content: Any | None = None
    source: ContentSource | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    def is_empty(self) -> bool:
        """是否为空维度。"""
        return self.fill_level == DimensionFillLevel.EMPTY

    def is_filled(self) -> bool:
        """是否已完整填充。"""
        return self.fill_level == DimensionFillLevel.FILLED


class ConceptNode(BaseModel):
    """双向概念映射的核心中间表示 (Concept Bottleneck Layer)。

    任意用户输入经过 Concept Parser 后生成 ConceptNode，
    随后贯穿 Gap Detector → Rule Mapper → Backward Generator →
    Cycle Checker 全流程，最终成为五维闭环世界。

    Attributes:
        raw_input: 用户原始输入文本。
        detected_type: 解析后的种子类型。
        tags: 语义标签列表（用于规则映射表匹配）。
        dimensions: 五维状态字典，key 为 FIVE_DIMENSIONS 成员。
        confidence: 整体解析置信度。
        preset_id: 关联的 TRPG 预设 ID（可选，影响生成风格）。
        metadata: 扩展元数据（LLM 模型名、时间戳等）。
    """

    raw_input: str
    detected_type: SeedType = SeedType.MIXED
    tags: list[str] = Field(default_factory=list)
    dimensions: dict[str, DimensionStatus] = Field(
        default_factory=lambda: {dim: DimensionStatus() for dim in FIVE_DIMENSIONS}
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    preset_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    # --- 便捷查询 ---

    def filled_dimensions(self) -> list[str]:
        """返回所有已填充的维度名称。"""
        return [d for d in FIVE_DIMENSIONS if self.dimensions[d].is_filled()]

    def empty_dimensions(self) -> list[str]:
        """返回所有空维度名称。"""
        return [d for d in FIVE_DIMENSIONS if self.dimensions[d].is_empty()]

    def get_seed_dimension(self) -> str | None:
        """获取种子输入所在的维度（用户直接提供的维度）。

        如果 detected_type 是 MIXED 或无法映射则返回 None。
        """
        if self.detected_type == SeedType.MIXED:
            return None
        return self.detected_type.value

    def get_content(self, dim: str) -> Any | None:
        """安全获取某维度内容。"""
        status = self.dimensions.get(dim)
        return status.content if status else None

    def set_content(
        self,
        dim: str,
        content: Any,
        source: ContentSource,
        confidence: float = 1.0,
        fill_level: DimensionFillLevel = DimensionFillLevel.FILLED,
    ) -> None:
        """设置维度内容并标记来源。

        Args:
            dim: 目标维度名称（必须是 FIVE_DIMENSIONS 之一）。
            content: 维度内容。
            source: 内容来源。
            confidence: 置信度。
            fill_level: 填充程度。
        """
        if dim not in self.dimensions:
            raise ValueError(f"Unknown dimension: {dim!r}. Expected one of {FIVE_DIMENSIONS}")
        self.dimensions[dim] = DimensionStatus(
            fill_level=fill_level,
            content=content,
            source=source,
            confidence=confidence,
        )
