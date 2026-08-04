"""Constraint models for asset generation rules."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ConstraintType(str, Enum):
    """约束类型。"""

    HARD = "hard"  # 硬约束：违反则资产生成失败
    SOFT = "soft"  # 软约束：影响优先级评分


class ConstraintNode(BaseModel):
    """约束节点。"""

    id: str
    type: ConstraintType
    rule: str  # 规则描述文本
    rule_config: dict[str, Any] | None = None
    priority: int = 0  # 0-100
    applicable_types: list[str] = Field(default_factory=list)


class ConstraintTree(BaseModel):
    """约束树。"""

    scene_id: str | None = None  # None = 全局约束
    id: str
    name: str
    nodes: list[ConstraintNode] = Field(default_factory=list)
