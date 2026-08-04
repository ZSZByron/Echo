"""Event graph data model for dynamic event system.

Defines enums, triggers, actions, rewards, nodes, and the event graph
with serialization support.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventNodeType(str, Enum):
    """事件节点类型。"""

    COMBAT = "combat"
    QUEST = "quest"
    EXPLORATION = "exploration"
    SOCIAL = "social"


class EventTriggerType(str, Enum):
    """事件触发类型。"""

    TIME = "time"
    LOCATION = "location"
    STATE = "state"
    CUSTOM = "custom"


class EventRewardType(str, Enum):
    """事件奖励类型。"""

    ITEM = "item"
    EXPERIENCE = "experience"
    STORY_UNLOCK = "story_unlock"


class EventTrigger(BaseModel):
    """事件触发条件。"""

    type: EventTriggerType
    condition: str | dict[str, Any]
    priority: int = 1


class EventAction(BaseModel):
    """事件动作。"""

    type: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class EventReward(BaseModel):
    """事件奖励。"""

    type: EventRewardType
    value: str | int
    probability: float = 1.0


class EventNode(BaseModel):
    """事件节点。"""

    id: str
    type: EventNodeType
    name: str
    trigger_conditions: list[EventTrigger] = Field(default_factory=list)
    actions: list[EventAction] = Field(default_factory=list)
    rewards: list[EventReward] = Field(default_factory=list)
    assets: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventGraph(BaseModel):
    """动态事件图。"""

    id: str
    name: str
    description: str
    nodes: dict[str, EventNode] = Field(default_factory=dict)
    global_triggers: list[EventTrigger] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
