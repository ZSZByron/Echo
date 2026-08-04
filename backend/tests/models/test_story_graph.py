"""Unit tests for story_graph models (6 classes)."""
from __future__ import annotations

import json

import pytest

from app.models.story_graph import (
    StoryChoice,
    StoryCondition,
    StoryEdge,
    StoryGraph,
    StoryNode,
    StoryNodeType,
)


# ── StoryNodeType enum tests ────────────────────────────────────


class TestStoryNodeType:
    def test_values(self) -> None:
        assert StoryNodeType.START.value == "start"
        assert StoryNodeType.END.value == "end"
        assert StoryNodeType.CHOICE.value == "choice"
        assert StoryNodeType.EVENT.value == "event"
        assert StoryNodeType.CONDITION.value == "condition"

    def test_is_str_enum(self) -> None:
        assert isinstance(StoryNodeType.START, str)
        assert StoryNodeType.START == "start"

    def test_construct_from_string(self) -> None:
        assert StoryNodeType("start") == StoryNodeType.START
        assert StoryNodeType("end") == StoryNodeType.END
        assert StoryNodeType("choice") == StoryNodeType.CHOICE
        assert StoryNodeType("event") == StoryNodeType.EVENT
        assert StoryNodeType("condition") == StoryNodeType.CONDITION

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            StoryNodeType("invalid")

    def test_all_members(self) -> None:
        assert len(list(StoryNodeType)) == 5


# ── StoryCondition tests ─────────────────────────────────────────


class TestStoryCondition:
    def test_string_requirement(self) -> None:
        c = StoryCondition(type="item_required", requirement="key")
        assert c.type == "item_required"
        assert c.requirement == "key"

    def test_dict_requirement(self) -> None:
        c = StoryCondition(
            type="stat_check",
            requirement={"stat": "strength", "threshold": 10},
        )
        assert isinstance(c.requirement, dict)
        assert c.requirement["stat"] == "strength"
        assert c.requirement["threshold"] == 10

    def test_custom_type(self) -> None:
        c = StoryCondition(type="custom", requirement="player_visited_temple")
        assert c.type == "custom"

    def test_serialization_round_trip(self) -> None:
        c = StoryCondition(
            type="stat_check",
            requirement={"stat": "wisdom", "threshold": 5},
        )
        c2 = StoryCondition.model_validate_json(c.model_dump_json())
        assert c2.type == "stat_check"
        assert isinstance(c2.requirement, dict)
        assert c2.requirement["stat"] == "wisdom"


# ── StoryChoice tests ────────────────────────────────────────────


class TestStoryChoice:
    def test_basic_choice(self) -> None:
        ch = StoryChoice(text="Open door", target_node="n2")
        assert ch.text == "Open door"
        assert ch.target_node == "n2"
        assert ch.conditions == []

    def test_choice_with_conditions(self) -> None:
        cond = StoryCondition(type="item_required", requirement="key")
        ch = StoryChoice(text="Open door", target_node="n2", conditions=[cond])
        assert len(ch.conditions) == 1
        assert ch.conditions[0].type == "item_required"

    def test_multiple_conditions(self) -> None:
        c1 = StoryCondition(type="item_required", requirement="key")
        c2 = StoryCondition(type="stat_check", requirement={"stat": "strength", "threshold": 5})
        ch = StoryChoice(text="Force door", target_node="n3", conditions=[c1, c2])
        assert len(ch.conditions) == 2

    def test_mutation_safety(self) -> None:
        ch1 = StoryChoice(text="A", target_node="n1")
        ch2 = StoryChoice(text="B", target_node="n2")
        ch1.conditions.append(StoryCondition(type="custom", requirement="x"))
        assert len(ch2.conditions) == 0


# ── StoryEdge tests ─────────────────────────────────────────────


class TestStoryEdge:
    def test_basic_edge(self) -> None:
        edge = StoryEdge(from_node="n1", to_node="n2")
        assert edge.from_node == "n1"
        assert edge.to_node == "n2"
        assert edge.condition is None

    def test_edge_with_condition(self) -> None:
        cond = StoryCondition(type="stat_check", requirement={"stat": "charisma", "threshold": 3})
        edge = StoryEdge(from_node="n1", to_node="n2", condition=cond)
        assert edge.condition is not None
        assert edge.condition.type == "stat_check"

    def test_serialization_round_trip(self) -> None:
        edge = StoryEdge(from_node="a", to_node="b")
        edge2 = StoryEdge.model_validate_json(edge.model_dump_json())
        assert edge2.from_node == "a"
        assert edge2.condition is None

    def test_condition_serialization_round_trip(self) -> None:
        cond = StoryCondition(type="item_required", requirement="amulet")
        edge = StoryEdge(from_node="n1", to_node="n3", condition=cond)
        edge2 = StoryEdge.model_validate_json(edge.model_dump_json())
        assert edge2.condition is not None
        assert edge2.condition.requirement == "amulet"


# ── StoryNode tests ─────────────────────────────────────────────


class TestStoryNode:
    def test_basic_node(self) -> None:
        n = StoryNode(
            id="n1",
            type=StoryNodeType.START,
            name="Start",
            description="The beginning",
        )
        assert n.id == "n1"
        assert n.type == StoryNodeType.START
        assert n.required_assets == []
        assert n.conditions == []
        assert n.choices == []
        assert n.scene_link is None
        assert n.metadata == {}

    def test_node_with_assets(self) -> None:
        n = StoryNode(
            id="n1",
            type=StoryNodeType.EVENT,
            name="Temple",
            description="Ancient temple",
            required_assets=["temple_bg", "key_obj"],
        )
        assert len(n.required_assets) == 2

    def test_node_with_choices(self) -> None:
        ch = StoryChoice(text="Enter", target_node="n2")
        n = StoryNode(
            id="n1",
            type=StoryNodeType.CHOICE,
            name="Crossroads",
            description="Choose path",
            choices=[ch],
        )
        assert len(n.choices) == 1
        assert n.choices[0].target_node == "n2"

    def test_node_with_scene_link(self) -> None:
        n = StoryNode(
            id="n1",
            type=StoryNodeType.EVENT,
            name="Scene",
            description="Links to a scene",
            scene_link="temple_ruins",
        )
        assert n.scene_link == "temple_ruins"

    def test_node_with_metadata(self) -> None:
        n = StoryNode(
            id="n1",
            type=StoryNodeType.EVENT,
            name="Event",
            description="Has meta",
            metadata={"difficulty": "hard", "level": 3},
        )
        assert n.metadata["difficulty"] == "hard"
        assert n.metadata["level"] == 3

    def test_mutation_safety_lists(self) -> None:
        n1 = StoryNode(id="a", type=StoryNodeType.START, name="A", description="a")
        n2 = StoryNode(id="b", type=StoryNodeType.START, name="B", description="b")
        n1.required_assets.append("asset1")
        n1.choices.append(StoryChoice(text="X", target_node="y"))
        assert "asset1" not in n2.required_assets
        assert len(n2.choices) == 0

    def test_mutation_safety_dict(self) -> None:
        n1 = StoryNode(id="a", type=StoryNodeType.START, name="A", description="a")
        n2 = StoryNode(id="b", type=StoryNodeType.START, name="B", description="b")
        n1.metadata["key"] = "val"
        assert "key" not in n2.metadata

    def test_serialization_round_trip(self) -> None:
        cond = StoryCondition(type="item_required", requirement="sword")
        ch = StoryChoice(text="Fight", target_node="n3", conditions=[cond])
        n = StoryNode(
            id="n1",
            type=StoryNodeType.CHOICE,
            name="Battle",
            description="A battle node",
            required_assets=["sword_obj"],
            conditions=[cond],
            choices=[ch],
            scene_link="arena",
            metadata={"music": "battle_theme"},
        )
        n2 = StoryNode.model_validate_json(n.model_dump_json())
        assert n2.type == StoryNodeType.CHOICE
        assert n2.choices[0].conditions[0].requirement == "sword"
        assert n2.metadata["music"] == "battle_theme"


# ── StoryGraph tests ────────────────────────────────────────────


class TestStoryGraph:
    def test_basic_graph(self) -> None:
        g = StoryGraph(id="g1", name="Test", description="A test graph")
        assert g.id == "g1"
        assert g.nodes == {}
        assert g.edges == []
        assert g.metadata == {}
        assert g.version == "1.0"

    def test_graph_with_nodes(self) -> None:
        n1 = StoryNode(id="n1", type=StoryNodeType.START, name="Start", description="Start node")
        n2 = StoryNode(id="n2", type=StoryNodeType.END, name="End", description="End node")
        g = StoryGraph(id="g1", name="Test", description="Test", nodes={"n1": n1, "n2": n2})
        assert len(g.nodes) == 2

    def test_graph_with_edges(self) -> None:
        edge = StoryEdge(from_node="n1", to_node="n2")
        g = StoryGraph(id="g1", name="Test", description="Test", edges=[edge])
        assert len(g.edges) == 1
        assert g.edges[0].from_node == "n1"

    def test_serialization_round_trip(self) -> None:
        n = StoryNode(id="n1", type=StoryNodeType.START, name="Start", description="desc")
        g = StoryGraph(id="g1", name="Test", description="Test graph")
        g.nodes[n.id] = n
        json_str = g.model_dump_json()
        g2 = StoryGraph.model_validate_json(json_str)
        assert g2.nodes["n1"].type == StoryNodeType.START
        assert g2.name == "Test"

    def test_full_round_trip_with_nested_models(self) -> None:
        cond = StoryCondition(type="item_required", requirement="key")
        ch = StoryChoice(text="Open", target_node="n2", conditions=[cond])
        n1 = StoryNode(
            id="n1",
            type=StoryNodeType.CHOICE,
            name="Door",
            description="A locked door",
            choices=[ch],
            required_assets=["door_obj"],
            metadata={"locked": True},
        )
        n2 = StoryNode(
            id="n2",
            type=StoryNodeType.END,
            name="Inside",
            description="Behind the door",
        )
        edge = StoryEdge(from_node="n1", to_node="n2", condition=cond)
        g = StoryGraph(
            id="g1",
            name="DoorPuzzle",
            description="A door puzzle story",
            nodes={"n1": n1, "n2": n2},
            edges=[edge],
            metadata={"chapter": 1},
        )
        g2 = StoryGraph.model_validate_json(g.model_dump_json())
        assert g2.nodes["n1"].choices[0].conditions[0].requirement == "key"
        assert g2.edges[0].condition is not None
        assert g2.metadata["chapter"] == 1
        assert g2.version == "1.0"

    def test_datetime_defaults(self) -> None:
        g = StoryGraph(id="g1", name="Test", description="Test")
        assert g.created_at is not None
        assert g.updated_at is not None

    def test_datetime_preserved_in_round_trip(self) -> None:
        g = StoryGraph(id="g1", name="Test", description="Test")
        original_created = g.created_at
        g2 = StoryGraph.model_validate_json(g.model_dump_json())
        assert g2.created_at == original_created

    def test_empty_graph_json(self) -> None:
        g = StoryGraph(id="g1", name="Empty", description="none")
        data = json.loads(g.model_dump_json())
        assert data["nodes"] == {}
        assert data["edges"] == []
        assert data["metadata"] == {}

    def test_mutation_safety(self) -> None:
        g1 = StoryGraph(id="a", name="A", description="a")
        g2 = StoryGraph(id="b", name="B", description="b")
        g1.metadata["key"] = "val"
        g1.nodes["x"] = StoryNode(
            id="x", type=StoryNodeType.EVENT, name="X", description="x"
        )
        assert "key" not in g2.metadata
        assert "x" not in g2.nodes

    def test_custom_version(self) -> None:
        g = StoryGraph(id="g1", name="Test", description="Test", version="2.0")
        assert g.version == "2.0"
