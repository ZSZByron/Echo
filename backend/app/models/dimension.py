"""六维输出数据模型（遗留资产生成线专用）。

Defines the 6 typed DimensionOutput sub-models (RED/LAW/ACT/NAR/WST/SOC)
and the DimensionResultSet aggregator. Consumed by the legacy asset
generation chain (a1_routes / constraint_topology).

2026-09-24 M1a dead-code cleanup: removed ConstraintDimension / CreationLayer
enums, DimensionInfo, WeightMatrix trio (zero production references);
RedOutput retained (referenced by DimensionResultSet.RED).
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.tag_dictionary import get_enum_values

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

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
    # Structured fields (Breakpoint B)
    world_structure: str | None = None
    gravity: str | None = None
    conservation: str | None = None
    divine_intervention: str | None = None
    afterlife: str | None = None

    @field_validator("world_structure")
    @classmethod
    def validate_world_structure(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("LAW", "world_structure")
        if v not in valid_values:
            raise ValueError(f"Invalid world_structure '{v}'. Valid values: {valid_values}")
        return v

    @field_validator("gravity")
    @classmethod
    def validate_gravity(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("LAW", "gravity")
        if v not in valid_values:
            raise ValueError(f"Invalid gravity '{v}'. Valid values: {valid_values}")
        return v

    @field_validator("conservation")
    @classmethod
    def validate_conservation(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("LAW", "conservation")
        if v not in valid_values:
            raise ValueError(f"Invalid conservation '{v}'. Valid values: {valid_values}")
        return v

    @field_validator("divine_intervention")
    @classmethod
    def validate_divine_intervention(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("LAW", "divine_intervention")
        if v not in valid_values:
            raise ValueError(f"Invalid divine_intervention '{v}'. Valid values: {valid_values}")
        return v

    @field_validator("afterlife")
    @classmethod
    def validate_afterlife(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("LAW", "afterlife")
        if v not in valid_values:
            raise ValueError(f"Invalid afterlife '{v}'. Valid values: {valid_values}")
        return v
    # Structured fields for T-B breakpoint - all Optional with default None for backward compatibility
    world_structure: str | None = None  # 世界结构枚举
    gravity: str | None = None  # 重力类型枚举
    conservation: str | None = None  # 守恒定律枚举
    divine_intervention: str | None = None  # 神王干涉枚举
    afterlife: str | None = None  # 来世设置枚举


class ActOutput(BaseModel):
    """行为规则输出。每个action有 trigger/check/success/failure。"""
    actions: list[dict[str, Any]] = Field(default_factory=list)
    # Structured fields (Breakpoint B)
    dice_mode: str | None = None
    check_direction: str | None = None
    cost_function: str | None = None
    core_action: str | None = None

    @field_validator("dice_mode")
    @classmethod
    def validate_dice_mode(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("ACT", "dice_mode")
        if v not in valid_values:
            raise ValueError(f"Invalid dice_mode '{v}'. Valid values: {valid_values}")
        return v

    @field_validator("check_direction")
    @classmethod
    def validate_check_direction(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("ACT", "check_direction")
        if v not in valid_values:
            raise ValueError(f"Invalid check_direction '{v}'. Valid values: {valid_values}")
        return v

    @field_validator("cost_function")
    @classmethod
    def validate_cost_function(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("ACT", "cost_function")
        if v not in valid_values:
            raise ValueError(f"Invalid cost_function '{v}'. Valid values: {valid_values}")
        return v

    @field_validator("core_action")
    @classmethod
    def validate_core_action(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("ACT", "core_action")
        if v not in valid_values:
            raise ValueError(f"Invalid core_action '{v}'. Valid values: {valid_values}")
        return v
    # Structured fields for T-B breakpoint - all Optional with default None for backward compatibility
    dice_mode: str | None = None  # 骰子模式枚举
    check_direction: str | None = None  # 检定方向枚举
    cost_function: str | None = None  # 消耗函数枚举
    core_action: str | None = None  # 核心行动枚举


class NarOutput(BaseModel):
    """叙事约束输出。"""
    style: str = ""
    keywords: list[str] = Field(default_factory=list)
    tone: str = ""
    # Structured fields (Breakpoint B)
    era_stage: str | None = None
    time_mode: str | None = None
    trajectory: str | None = None
    success_granularity: str | None = None

    @field_validator("era_stage")
    @classmethod
    def validate_era_stage(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("NAR", "era_stage")
        if v not in valid_values:
            raise ValueError(f"Invalid era_stage '{v}'. Valid values: {valid_values}")
        return v

    @field_validator("time_mode")
    @classmethod
    def validate_time_mode(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("NAR", "time_mode")
        if v not in valid_values:
            raise ValueError(f"Invalid time_mode '{v}'. Valid values: {valid_values}")
        return v

    @field_validator("trajectory")
    @classmethod
    def validate_trajectory(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("NAR", "trajectory")
        if v not in valid_values:
            raise ValueError(f"Invalid trajectory '{v}'. Valid values: {valid_values}")
        return v

    @field_validator("success_granularity")
    @classmethod
    def validate_success_granularity(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("NAR", "success_granularity")
        if v not in valid_values:
            raise ValueError(f"Invalid success_granularity '{v}'. Valid values: {valid_values}")
        return v
    # Structured fields for T-B breakpoint - all Optional with default None for backward compatibility
    era_stage: str | None = None  # 时代阶段枚举
    time_mode: str | None = None  # 时间模式枚举
    trajectory: str | None = None  # 轨迹类型枚举
    success_granularity: str | None = None  # 成功粒度枚举


class WstOutput(BaseModel):
    """世界状态输出。每个effect有 name/type/magnitude。"""
    effects: list[dict[str, Any]] = Field(default_factory=list)
    # Structured fields (Breakpoint B)
    cost_type: str | None = None
    feedback_loop: str | None = None
    climate_zone: str | None = None
    power_saturation: str | None = None

    @field_validator("cost_type")
    @classmethod
    def validate_cost_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("WST", "cost_type")
        if v not in valid_values:
            raise ValueError(f"Invalid cost_type '{v}'. Valid values: {valid_values}")
        return v

    @field_validator("feedback_loop")
    @classmethod
    def validate_feedback_loop(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("WST", "feedback_loop")
        if v not in valid_values:
            raise ValueError(f"Invalid feedback_loop '{v}'. Valid values: {valid_values}")
        return v

    @field_validator("climate_zone")
    @classmethod
    def validate_climate_zone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("WST", "climate_zone")
        if v not in valid_values:
            raise ValueError(f"Invalid climate_zone '{v}'. Valid values: {valid_values}")
        return v

    @field_validator("power_saturation")
    @classmethod
    def validate_power_saturation(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("WST", "power_saturation")
        if v not in valid_values:
            raise ValueError(f"Invalid power_saturation '{v}'. Valid values: {valid_values}")
        return v


class SocOutput(BaseModel):
    """社交生态输出。每个relation有 target/type/value。"""
    relations: list[dict[str, Any]] = Field(default_factory=list)
    # Structured fields (Breakpoint B)
    political_type: str | None = None
    access_topology: str | None = None
    threshold: str | None = None
    economy_type: str | None = None

    @field_validator("political_type")
    @classmethod
    def validate_political_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("SOC", "political_type")
        if v not in valid_values:
            raise ValueError(f"Invalid political_type '{v}'. Valid values: {valid_values}")
        return v

    @field_validator("access_topology")
    @classmethod
    def validate_access_topology(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("SOC", "access_topology")
        if v not in valid_values:
            raise ValueError(f"Invalid access_topology '{v}'. Valid values: {valid_values}")
        return v

    @field_validator("threshold")
    @classmethod
    def validate_threshold(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("SOC", "threshold")
        if v not in valid_values:
            raise ValueError(f"Invalid threshold '{v}'. Valid values: {valid_values}")
        return v

    @field_validator("economy_type")
    @classmethod
    def validate_economy_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_values = get_enum_values("SOC", "economy_type")
        if v not in valid_values:
            raise ValueError(f"Invalid economy_type '{v}'. Valid values: {valid_values}")
        return v


class DimensionResultSet(BaseModel):
    """6维约束结果集容器。"""
    RED: RedOutput = Field(default_factory=RedOutput)
    LAW: LawOutput = Field(default_factory=LawOutput)
    ACT: ActOutput = Field(default_factory=ActOutput)
    NAR: NarOutput = Field(default_factory=NarOutput)
    WST: WstOutput = Field(default_factory=WstOutput)
    SOC: SocOutput = Field(default_factory=SocOutput)
