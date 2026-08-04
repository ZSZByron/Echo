"""Story graph data model for cross-scene narrative branching.

Defines StoryNodeType, StoryCondition, StoryChoice, StoryEdge, StoryNode,
and StoryGraph for interactive story branching with conditions and choices.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StoryNodeType(str, Enum):
    """剧情节点类型。"""

    START = "start"
    END = "end"
    CHOICE = "choice"
    EVENT = "event"
    CONDITION = "condition"


class StoryCondition(BaseModel):
    """剧情条件。"""

    type: str  # "item_required" | "stat_check" | "custom"
    requirement: str | dict[str, Any]


class StoryChoice(BaseModel):
    """剧情选择支。"""

    text: str
    target_node: str
    conditions: list[StoryCondition] = Field(default_factory=list)


class StoryEdge(BaseModel):
    """剧情图边（类型化，替代裸 dict）。"""

    from_node: str
    to_node: str
    condition: StoryCondition | None = None


class StoryNode(BaseModel):
    """剧情节点。"""

    id: str
    type: StoryNodeType
    name: str
    description: str
    required_assets: list[str] = Field(default_factory=list)
    conditions: list[StoryCondition] = Field(default_factory=list)
    choices: list[StoryChoice] = Field(default_factory=list)
    scene_link: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StoryGraph(BaseModel):
    """跨场景剧情图。"""

    id: str
    name: str
    description: str
    nodes: dict[str, StoryNode] = Field(default_factory=dict)
    edges: list[StoryEdge] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    version: str = "1.0"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
