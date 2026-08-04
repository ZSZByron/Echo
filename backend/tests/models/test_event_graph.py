"""Tests for event_graph model (8 classes)."""
from __future__ import annotations

import json

import pytest

from app.models.event_graph import (
    EventAction,
    EventGraph,
    EventNode,
    EventNodeType,
    EventReward,
    EventRewardType,
    EventTrigger,
    EventTriggerType,
)


# ── Enum value tests ──────────────────────────────────────────


class TestEventNodeType:
    def test_values(self) -> None:
        assert EventNodeType.COMBAT.value == "combat"
        assert EventNodeType.QUEST.value == "quest"
        assert EventNodeType.EXPLORATION.value == "exploration"
        assert EventNodeType.SOCIAL.value == "social"

    def test_is_str_enum(self) -> None:
        assert isinstance(EventNodeType.COMBAT, str)
        assert EventNodeType.COMBAT == "combat"


class TestEventTriggerType:
    def test_values(self) -> None:
        assert EventTriggerType.TIME.value == "time"
        assert EventTriggerType.LOCATION.value == "location"
        assert EventTriggerType.STATE.value == "state"
        assert EventTriggerType.CUSTOM.value == "custom"

    def test_is_str_enum(self) -> None:
        assert isinstance(EventTriggerType.TIME, str)


class TestEventRewardType:
    def test_values(self) -> None:
        assert EventRewardType.ITEM.value == "item"
        assert EventRewardType.EXPERIENCE.value == "experience"
        assert EventRewardType.STORY_UNLOCK.value == "story_unlock"

    def test_is_str_enum(self) -> None:
        assert isinstance(EventRewardType.ITEM, str)


# ── EventTrigger tests ─────────────────────────────────────────


class TestEventTrigger:
    def test_string_condition(self) -> None:
        t = EventTrigger(type=EventTriggerType.TIME, condition="night")
        assert t.condition == "night"
        assert t.priority == 1

    def test_dict_condition(self) -> None:
        t = EventTrigger(
            type=EventTriggerType.LOCATION,
            condition={"zone": "forest", "radius": 10},
        )
        assert t.condition["zone"] == "forest"

    def test_custom_priority(self) -> None:
        t = EventTrigger(type=EventTriggerType.STATE, condition="low_hp", priority=5)
        assert t.priority == 5


# ── EventAction tests ──────────────────────────────────────────


class TestEventAction:
    def test_action_parameters(self) -> None:
        action = EventAction(type="move", parameters={"target": "location1", "speed": 5})
        assert action.parameters["speed"] == 5
        assert action.parameters["target"] == "location1"

    def test_empty_parameters_default(self) -> None:
        action = EventAction(type="idle")
        assert action.parameters == {}


# ── EventReward tests ──────────────────────────────────────────


class TestEventReward:
    def test_probability_default(self) -> None:
        r = EventReward(type=EventRewardType.EXPERIENCE, value=50)
        assert r.probability == 1.0

    def test_probability_explicit(self) -> None:
        r = EventReward(type=EventRewardType.ITEM, value="sword", probability=0.5)
        assert r.probability == 0.5

    def test_int_value(self) -> None:
        r = EventReward(type=EventRewardType.EXPERIENCE, value=100)
        assert r.value == 100

    def test_str_value(self) -> None:
        r = EventReward(type=EventRewardType.ITEM, value="potion")
        assert r.value == "potion"


# ── EventNode tests ───────────────────────────────────────────


class TestEventNode:
    def test_defaults_empty_lists_and_dict(self) -> None:
        n = EventNode(id="n1", type=EventNodeType.COMBAT, name="Wolf")
        assert n.trigger_conditions == []
        assert n.actions == []
        assert n.rewards == []
        assert n.assets == []
        assert n.metadata == {}

    def test_with_trigger(self) -> None:
        t = EventTrigger(type=EventTriggerType.TIME, condition="night")
        n = EventNode(id="n1", type=EventNodeType.COMBAT, name="Wolf", trigger_conditions=[t])
        assert len(n.trigger_conditions) == 1
        assert n.trigger_conditions[0].type == EventTriggerType.TIME

    def test_with_reward(self) -> None:
        r = EventReward(type=EventRewardType.EXPERIENCE, value=50)
        n = EventNode(id="n1", type=EventNodeType.QUEST, name="Quest1", rewards=[r])
        assert n.rewards[0].probability == 1.0

    def test_mutation_safety(self) -> None:
        """Default list factories must produce independent instances."""
        n1 = EventNode(id="a", type=EventNodeType.SOCIAL, name="A")
        n2 = EventNode(id="b", type=EventNodeType.SOCIAL, name="B")
        n1.assets.append("asset1")
        assert "asset1" not in n2.assets


# ── EventGraph tests ──────────────────────────────────────────


class TestEventGraph:
    def test_event_graph_serialization(self) -> None:
        t = EventTrigger(type=EventTriggerType.TIME, condition="night")
        n = EventNode(id="e1", type=EventNodeType.COMBAT, name="Wolf", trigger_conditions=[t])
        g = EventGraph(id="eg1", name="Events", description="desc", nodes={n.id: n})
        j = g.model_dump_json()
        g2 = EventGraph.model_validate_json(j)
        assert g2.nodes["e1"].trigger_conditions[0].type == EventTriggerType.TIME

    def test_round_trip_preserves_all_fields(self) -> None:
        t = EventTrigger(type=EventTriggerType.STATE, condition="low_hp", priority=3)
        r = EventReward(type=EventRewardType.ITEM, value="shield", probability=0.8)
        a = EventAction(type="defend", parameters={"stance": "block"})
        n = EventNode(
            id="n1",
            type=EventNodeType.EXPLORATION,
            name="Cave",
            trigger_conditions=[t],
            actions=[a],
            rewards=[r],
            assets=["cave_bg"],
            metadata={"difficulty": "hard"},
        )
        g = EventGraph(
            id="g1",
            name="Dungeon",
            description="A dark dungeon",
            nodes={"n1": n},
            global_triggers=[t],
            metadata={"version": 1},
        )
        g2 = EventGraph.model_validate_json(g.model_dump_json())
        assert g2.name == "Dungeon"
        assert g2.nodes["n1"].rewards[0].probability == 0.8
        assert g2.global_triggers[0].priority == 3

    def test_defaults(self) -> None:
        g = EventGraph(id="g1", name="Empty", description="none")
        assert g.nodes == {}
        assert g.global_triggers == []
        assert g.metadata == {}

    def test_empty_graph_serialization(self) -> None:
        g = EventGraph(id="g1", name="Empty", description="none")
        data = json.loads(g.model_dump_json())
        assert data["nodes"] == {}
        assert data["global_triggers"] == []

    def test_dict_mutation_safety(self) -> None:
        """Default dict factories must produce independent instances."""
        g1 = EventGraph(id="a", name="A", description="a")
        g2 = EventGraph(id="b", name="B", description="b")
        g1.metadata["key"] = "val"
        assert "key" not in g2.metadata
