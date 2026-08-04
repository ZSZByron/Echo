"""6维约束体系数据模型。

Defines ConstraintDimension (RED/LAW/ACT/NAR/WST/SOC) and CreationLayer
(world/region/scene/campaign/npc/asset) enums, weight matrix models, and
6 typed DimensionOutput sub-models.

This module is SEPARATE from constraint.py (ConstraintType HARD/SOFT).
See SYSTEM_DESIGN_SPEC_v4.md §18.9 for naming collision resolution.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ConstraintDimension(StrEnum):
    """6维约束维度 — 语义类别。不允许添加或修改。"""
    RED = "RED"  # 内容红线
    LAW = "LAW"  # 物理法则
    ACT = "ACT"  # 行为规则
    NAR = "NAR"  # 叙事约束
    WST = "WST"  # 世界状态
    SOC = "SOC"  # 社交生态


class CreationLayer(StrEnum):
    """6个创作层级。不允许添加或修改。"""
    WORLD = "world"
    REGION = "region"
    SCENE = "scene"
    CAMPAIGN = "campaign"
    NPC = "npc"
    ASSET = "asset"


# ---------------------------------------------------------------------------
# Dimension metadata
# ---------------------------------------------------------------------------

class DimensionInfo(BaseModel):
    """维度元信息。"""
    name: str
    desc: str
    data_essence: str


DIMENSION_INFO: dict[ConstraintDimension, DimensionInfo] = {
    ConstraintDimension.RED: DimensionInfo(
        name="内容红线",
        desc="这个对象不能包含什么（禁止清单）",
        data_essence="禁止的内容条目",
    ),
    ConstraintDimension.LAW: DimensionInfo(
        name="物理法则",
        desc="这个对象服从什么世界规则（重力/魔法体系/科技水平）",
        data_essence="规则函数",
    ),
    ConstraintDimension.ACT: DimensionInfo(
        name="行为规则",
        desc="作用于这个对象的行为怎么判定（技能检定/社交反馈/伤害计算）",
        data_essence="判定逻辑",
    ),
    ConstraintDimension.NAR: DimensionInfo(
        name="叙事约束",
        desc="描述这个对象时遵循什么风格（文风/词汇/氛围/基调）",
        data_essence="风格指令文本",
    ),
    ConstraintDimension.WST: DimensionInfo(
        name="世界状态",
        desc="这个对象携带什么动态状态效果（天气/环境修正/buff/debuff）",
        data_essence="修正值/状态效果",
    ),
    ConstraintDimension.SOC: DimensionInfo(
        name="社交生态",
        desc="这个对象和谁有关系、什么关系（阵营/声望/亲缘/敌对）",
        data_essence="关系边",
    ),
}

LAYER_NAMES: dict[CreationLayer, str] = {
    CreationLayer.WORLD: "世界观",
    CreationLayer.REGION: "区域文化",
    CreationLayer.SCENE: "场景/地点",
    CreationLayer.CAMPAIGN: "战役/剧情",
    CreationLayer.NPC: "NPC",
    CreationLayer.ASSET: "资产/物品",
}


# ---------------------------------------------------------------------------
# Weight matrix models
# ---------------------------------------------------------------------------

class WeightMatrixError(Exception):
    """权重矩阵验证异常。

    Attributes:
        row: 出错的层级名 (None = 文件级错误)
        detail: 具体错误描述
    """

    def __init__(self, row: str | None = None, detail: str = "") -> None:
        self.row = row
        self.detail = detail
        super().__init__(f"[row={row}] {detail}")


class WeightMatrixEntry(BaseModel):
    """单层权重条目 — ConstraintDimension → int 映射的 typed wrapper。

    验证: 6维齐全，每值>=0，行和=100。
    """

    RED: int = 0
    LAW: int = 0
    ACT: int = 0
    NAR: int = 0
    WST: int = 0
    SOC: int = 0

    def sum(self) -> int:
        return self.RED + self.LAW + self.ACT + self.NAR + self.WST + self.SOC

    def to_dict(self) -> dict[ConstraintDimension, int]:
        return {
            ConstraintDimension.RED: self.RED,
            ConstraintDimension.LAW: self.LAW,
            ConstraintDimension.ACT: self.ACT,
            ConstraintDimension.NAR: self.NAR,
            ConstraintDimension.WST: self.WST,
            ConstraintDimension.SOC: self.SOC,
        }

    @model_validator(mode="after")
    def _validate_sum(self) -> WeightMatrixEntry:
        if self.sum() != 100:
            raise WeightMatrixError(
                row="(unknown)",
                detail=f"row sum is {self.sum()}, expected 100",
            )
        for dim in ConstraintDimension:
            val = getattr(self, dim.name)
            if val < 0:
                raise WeightMatrixError(
                    row="(unknown)",
                    detail=f"negative weight for {dim.value}",
                )
        return self


class WeightMatrix(BaseModel):
    """完整权重矩阵 — CreationLayer → WeightMatrixEntry 映射。"""

    world: WeightMatrixEntry
    region: WeightMatrixEntry
    scene: WeightMatrixEntry
    campaign: WeightMatrixEntry
    npc: WeightMatrixEntry
    asset: WeightMatrixEntry

    def get_entry(self, layer: CreationLayer) -> WeightMatrixEntry:
        return getattr(self, layer.value)


# ---------------------------------------------------------------------------
# 6 DimensionOutput sub-models
# ---------------------------------------------------------------------------

class RedOutput(BaseModel):
    """内容红线输出。"""
    forbidden: list[str] = Field(default_factory=list)
    note: str = ""


class LawOutput(BaseModel):
    """物理法则输出。"""
    rules: list[str] = Field(default_factory=list)
    mechanism: str = ""


class ActOutput(BaseModel):
    """行为规则输出。每个action有 trigger/check/success/failure。"""
    actions: list[dict[str, Any]] = Field(default_factory=list)


class NarOutput(BaseModel):
    """叙事约束输出。"""
    style: str = ""
    keywords: list[str] = Field(default_factory=list)
    tone: str = ""


class WstOutput(BaseModel):
    """世界状态输出。每个effect有 name/type/magnitude。"""
    effects: list[dict[str, Any]] = Field(default_factory=list)


class SocOutput(BaseModel):
    """社交生态输出。每个relation有 target/type/value。"""
    relations: list[dict[str, Any]] = Field(default_factory=list)


class DimensionResultSet(BaseModel):
    """6维约束结果集容器。"""
    RED: RedOutput = Field(default_factory=RedOutput)
    LAW: LawOutput = Field(default_factory=LawOutput)
    ACT: ActOutput = Field(default_factory=ActOutput)
    NAR: NarOutput = Field(default_factory=NarOutput)
    WST: WstOutput = Field(default_factory=WstOutput)
    SOC: SocOutput = Field(default_factory=SocOutput)
