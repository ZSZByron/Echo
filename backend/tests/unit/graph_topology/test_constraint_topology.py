"""Test file for constraint_topology.py (breakpoint T-F).

Tests the apply_constraints function which creates Constraint nodes and
topology edges from DimensionResultSet structured fields.
"""
from __future__ import annotations

import pytest

from app.domains.creation.graph.constraint_topology import apply_constraints
from app.models.dimension import (
    DimensionResultSet,
    LawOutput,
    WstOutput,
    ActOutput,
)
from app.models.knowledge_graph import (
    EdgeType,
    GraphNode,
    GraphEdge,
    KnowledgeGraph,
)


class TestApplyConstraintsCreatesNodes:
    """① Structured constraints -> cst_ nodes appear in graph."""

    def test_creates_constraint_node_for_law_world_structure(self):
        graph = KnowledgeGraph(scene_id="test-scene")
        graph.add_node("1", description="Background")
        result_set = DimensionResultSet(
            LAW=LawOutput(world_structure="FLOATING_ISLANDS"),
        )
        out = apply_constraints(graph, result_set, stage="A1")

        assert "cst_LAW_world_structure" in out.nodes
        node = out.nodes["cst_LAW_world_structure"]
        assert "FLOATING_ISLANDS" in node.description

    def test_creates_constraint_node_for_wst_power_saturation(self):
        graph = KnowledgeGraph(scene_id="test-scene")
        result_set = DimensionResultSet(
            WST=WstOutput(power_saturation="HIGH"),
        )
        out = apply_constraints(graph, result_set, stage="A1")

        assert "cst_WST_power_saturation" in out.nodes


class TestEdgeTypesAndLabels:
    """② Edge type is CROSS, visual_description carries RULE_* semantic label."""

    def test_edge_has_correct_semantic_label(self):
        graph = KnowledgeGraph(scene_id="test-scene")
        graph.add_node("1", description="Background")
        result_set = DimensionResultSet(
            LAW=LawOutput(world_structure="FLOATING_ISLANDS"),
        )
        out = apply_constraints(graph, result_set, stage="A1")

        assert len(out.edges) == 1
        edge = out.edges[0]
        assert edge.edge_type == EdgeType.CROSS
        assert "RULE_SHAPES_GEO" in edge.visual_description

    def test_multiple_structured_fields_create_multiple_edges(self):
        graph = KnowledgeGraph(scene_id="test-scene")
        graph.add_node("1", description="Background")
        result_set = DimensionResultSet(
            LAW=LawOutput(world_structure="FLOATING_ISLANDS", gravity="ZERO"),
            WST=WstOutput(power_saturation="HIGH"),
        )
        out = apply_constraints(graph, result_set, stage="A1")

        assert len(out.edges) >= 3
        semantic_labels = [e.visual_description for e in out.edges]
        assert any("RULE_SHAPES_GEO" in s for s in semantic_labels)
        assert any("RULE_POWER_SATURATION" in s for s in semantic_labels)


class TestIdempotency:
    """③ Applying twice does not duplicate nodes or edges."""

    def test_idempotent_apply(self):
        graph = KnowledgeGraph(scene_id="test-scene")
        graph.add_node("1", description="Background")
        result_set = DimensionResultSet(
            LAW=LawOutput(world_structure="FLOATING_ISLANDS"),
            ACT=ActOutput(dice_mode="LINEAR_D20"),
        )

        out1 = apply_constraints(graph, result_set, stage="A1")
        node_count = len(out1.nodes)
        edge_count = len(out1.edges)

        out2 = apply_constraints(out1, result_set, stage="A1")
        assert len(out2.nodes) == node_count
        assert len(out2.edges) == edge_count


class TestEmptyConstraints:
    """④ All-None structured fields -> graph unchanged."""

    def test_no_nodes_or_edges_when_all_none(self):
        graph = KnowledgeGraph(scene_id="test-scene")
        graph.add_node("1", description="Background")
        result_set = DimensionResultSet()  # all defaults, all structured fields None

        out = apply_constraints(graph, result_set, stage="A1")

        # Only the pre-existing background node remains
        assert set(out.nodes.keys()) == {"1"}
        assert len(out.edges) == 0


class TestSourceStageMarker:
    """⑤ source_stage encoded in node description and edge visual_description."""

    def test_node_description_contains_stage(self):
        graph = KnowledgeGraph(scene_id="test-scene")
        graph.add_node("1", description="Background")
        result_set = DimensionResultSet(
            LAW=LawOutput(world_structure="FLOATING_ISLANDS"),
        )
        out = apply_constraints(graph, result_set, stage="A1")

        node = out.nodes["cst_LAW_world_structure"]
        assert "A1" in node.description

    def test_edge_visual_description_contains_stage(self):
        graph = KnowledgeGraph(scene_id="test-scene")
        graph.add_node("1", description="Background")
        result_set = DimensionResultSet(
            LAW=LawOutput(world_structure="FLOATING_ISLANDS"),
        )
        out = apply_constraints(graph, result_set, stage="A1")

        edge = out.edges[0]
        assert edge.visual_description.startswith("A1")


class TestReturnsGraph:
    """⑥ Returns the graph object."""

    def test_returns_knowledge_graph_instance(self):
        graph = KnowledgeGraph(scene_id="test-scene")
        result_set = DimensionResultSet()

        out = apply_constraints(graph, result_set, stage="A1")

        assert isinstance(out, KnowledgeGraph)
        assert out.scene_id == "test-scene"

    def test_no_background_node_only_creates_nodes_no_edges(self):
        graph = KnowledgeGraph(scene_id="test-scene")
        # No nodes added -> no background_node_id
        result_set = DimensionResultSet(
            LAW=LawOutput(world_structure="FLOATING_ISLANDS"),
        )
        out = apply_constraints(graph, result_set, stage="A1")

        assert "cst_LAW_world_structure" in out.nodes
        assert len(out.edges) == 0  # no target node available


class TestConstraintNodeProperties:
    """Extra: verify node structure details."""

    def test_constraint_node_level_is_zero(self):
        graph = KnowledgeGraph(scene_id="test-scene")
        graph.add_node("1", description="Background")
        result_set = DimensionResultSet(
            LAW=LawOutput(world_structure="FLOATING_ISLANDS"),
        )
        out = apply_constraints(graph, result_set, stage="A1")

        node = out.nodes["cst_LAW_world_structure"]
        assert node.level == 0

    def test_constraint_node_serial_number_matches_id(self):
        graph = KnowledgeGraph(scene_id="test-scene")
        graph.add_node("1", description="Background")
        result_set = DimensionResultSet(
            LAW=LawOutput(world_structure="FLOATING_ISLANDS"),
        )
        out = apply_constraints(graph, result_set, stage="A1")

        node = out.nodes["cst_LAW_world_structure"]
        assert node.serial_number == "cst_LAW_world_structure"
