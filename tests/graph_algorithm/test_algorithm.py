"""Comprehensive test suite for graph algorithms.

Tests topological sort, cycle detection, and generation wave algorithms
across all critical graph structures: empty, single node, pure chain,
pure star, multi-tree with cross edges, and cyclic graphs.

Detail-first ordering: nodes with no outgoing edges (nothing to depend on)
are generated first. Background ends up last because it depends on everything.
"""
from __future__ import annotations

import pytest

from models import KnowledgeGraph, EdgeType
from topo_sort import layered_topological_sort, get_generation_waves
from cycle_detector import detect_cycle, find_all_cycles, validate_graph


# ===========================================================================
# Test Case 1: Empty Graph
# ===========================================================================


class TestEmptyGraph:
    """Empty KnowledgeGraph with no nodes or edges."""

    def test_topo_sort_empty_graph(self) -> None:
        """Topological sort on empty graph raises ValueError (no background)."""
        graph = KnowledgeGraph(scene_id="empty")
        with pytest.raises(ValueError, match="must have a valid background_node_id"):
            layered_topological_sort(graph)

    def test_cycle_detection_empty_graph(self) -> None:
        """Cycle detection on empty graph returns None (no cycles)."""
        graph = KnowledgeGraph(scene_id="empty")
        assert detect_cycle(graph) is None

    def test_validate_empty_graph(self) -> None:
        """Validation on empty graph returns (True, [])."""
        graph = KnowledgeGraph(scene_id="empty")
        is_valid, cycles = validate_graph(graph)
        assert is_valid is True
        assert cycles == []

    def test_generation_waves_empty_graph(self) -> None:
        """Generation waves on empty graph raises ValueError (no background)."""
        graph = KnowledgeGraph(scene_id="empty")
        with pytest.raises(ValueError, match="must have a valid background_node_id"):
            get_generation_waves(graph)


# ===========================================================================
# Test Case 2: Single Node (Background Only)
# ===========================================================================


class TestSingleNode:
    """Graph with only level 0 background node."""

    def test_topo_sort_single_node(self) -> None:
        """Topological sort on single-node graph returns [bg_id]."""
        graph = KnowledgeGraph(scene_id="single")
        bg = graph.add_node("0", "background scene")
        assert graph.background_node_id == "0"

        order = layered_topological_sort(graph)
        assert order == ["0"]

    def test_cycle_detection_single_node(self) -> None:
        """Cycle detection on single-node graph returns None."""
        graph = KnowledgeGraph(scene_id="single")
        graph.add_node("0", "background")
        assert detect_cycle(graph) is None

    def test_validate_single_node(self) -> None:
        """Validation on single-node graph returns (True, [])."""
        graph = KnowledgeGraph(scene_id="single")
        graph.add_node("0", "background")
        is_valid, cycles = validate_graph(graph)
        assert is_valid is True
        assert cycles == []

    def test_generation_waves_single_node(self) -> None:
        """Generation waves on single-node graph returns [[bg_id]]."""
        graph = KnowledgeGraph(scene_id="single")
        graph.add_node("0", "background")
        waves = get_generation_waves(graph)
        assert waves == [["0"]]


# ===========================================================================
# Test Case 3: Pure Chain (Linear Dependency)
# ===========================================================================


class TestPureChain:
    """Linear chain: 0 -> 1 -> 1-1 -> 1-1-1 (serial_asc order)."""

    @pytest.fixture
    def chain_graph(self) -> KnowledgeGraph:
        """Build chain: 0 -> 1 -> 1-1 -> 1-1-1."""
        graph = KnowledgeGraph(scene_id="chain")
        graph.add_node("0", "background")
        graph.add_node("1", "level 1 core")
        graph.add_node("1-1", "level 2 object")
        graph.add_node("1-1-1", "level 3 detail")

        # Create chain edges
        graph.add_edge("0", "1", "", EdgeType.TREE)
        graph.add_edge("1", "1-1", "", EdgeType.TREE)
        graph.add_edge("1-1", "1-1-1", "", EdgeType.TREE)
        return graph

    def test_topo_sort_chain(self, chain_graph: KnowledgeGraph) -> None:
        """Detail-first: deepest leaf first, background last."""
        order = layered_topological_sort(chain_graph)
        assert order == ["1-1-1", "1-1", "1", "0"]

    def test_cycle_detection_chain(self, chain_graph: KnowledgeGraph) -> None:
        """Chain has no cycles."""
        assert detect_cycle(chain_graph) is None

    def test_validate_chain(self, chain_graph: KnowledgeGraph) -> None:
        """Chain validation returns (True, [])."""
        is_valid, cycles = validate_graph(chain_graph)
        assert is_valid is True
        assert cycles == []

    def test_generation_waves_chain(self, chain_graph: KnowledgeGraph) -> None:
        """Chain generates sequential waves, one node per wave, bg last."""
        waves = get_generation_waves(chain_graph)
        assert waves == [["1-1-1"], ["1-1"], ["1"], ["0"]]


# ===========================================================================
# Test Case 4: Pure Star (Leaf Concurrency)
# ===========================================================================


class TestPureStar:
    """Star structure: 0 -> 1, with leaves 1-1,1-2,1-3 pointing to 1.

    Expected wave order: [0] -> [1-1,1-2,1-3] -> [1]
    Leaves are independent (in-degree 0) and can run in parallel.
    Core node waits for all leaves.
    """

    @pytest.fixture
    def star_graph(self) -> KnowledgeGraph:
        """Build star: 0->1, leaves->1."""
        graph = KnowledgeGraph(scene_id="star")
        graph.add_node("0", "background")
        graph.add_node("1", "core object")
        graph.add_node("1-1", "leaf 1")
        graph.add_node("1-2", "leaf 2")
        graph.add_node("1-3", "leaf 3")

        # Background to core
        graph.add_edge("0", "1", "", EdgeType.TREE)
        # Leaves point to core (visual dependency)
        graph.add_edge("1-1", "1", "", EdgeType.TREE)
        graph.add_edge("1-2", "1", "", EdgeType.TREE)
        graph.add_edge("1-3", "1", "", EdgeType.TREE)
        return graph

    def test_topo_sort_star(self, star_graph: KnowledgeGraph) -> None:
        """Core first (out-degree 0), then bg + leaves together."""
        order = layered_topological_sort(star_graph)
        # Core has out-degree 0, comes first
        assert order[0] == "1"
        # Leaves are after core, sorted by serial
        leaf_indices = [order.index("1-1"), order.index("1-2"), order.index("1-3")]
        assert leaf_indices == sorted(leaf_indices)
        # Bg is after core (edge 0->1: 0 depends on 1)
        assert order.index("1") < order.index("0")

    def test_cycle_detection_star(self, star_graph: KnowledgeGraph) -> None:
        """Star has no cycles."""
        assert detect_cycle(star_graph) is None

    def test_validate_star(self, star_graph: KnowledgeGraph) -> None:
        """Star validation returns (True, [])."""
        is_valid, cycles = validate_graph(star_graph)
        assert is_valid is True
        assert cycles == []

    def test_generation_waves_star(self, star_graph: KnowledgeGraph) -> None:
        """Star waves: core first, then leaves + bg together."""
        waves = get_generation_waves(star_graph)
        # Wave 0: core (out-degree 0)
        assert waves[0] == ["1"]
        # Wave 1: bg + leaves (all out-degree 0 after core resolved)
        assert set(waves[1]) == {"0", "1-1", "1-2", "1-3"}
        assert len(waves) == 2


# ===========================================================================
# Test Case 5: Multi-Tree with Cross Edges
# ===========================================================================


class TestMultiTreeCrossEdges:
    """Two subtrees with cross-dependency: password -> lock.

    Tree 1: 0 -> 1 -> 1-1
    Tree 2: 0 -> 2 -> 2-1
    Cross edge: 2-1 (password) -> 1 (lock)

    Expected order respects cross dependency: 2-1 must precede 1.
    """

    @pytest.fixture
    def multi_tree_graph(self) -> KnowledgeGraph:
        """Build multi-tree with cross edge."""
        graph = KnowledgeGraph(scene_id="multi_tree")
        graph.add_node("0", "background")
        graph.add_node("1", "locked door")
        graph.add_node("1-1", "door handle")
        graph.add_node("2", "password panel")
        graph.add_node("2-1", "password hologram")

        # Tree 1 edges
        graph.add_edge("0", "1", "", EdgeType.TREE)
        graph.add_edge("1", "1-1", "", EdgeType.TREE)

        # Tree 2 edges
        graph.add_edge("0", "2", "", EdgeType.TREE)
        graph.add_edge("2", "2-1", "", EdgeType.TREE)

        # Cross edge: password unlocks lock
        graph.add_edge("2-1", "1", "password reveals lock mechanism", EdgeType.CROSS)
        return graph

    def test_topo_sort_multi_tree(self, multi_tree_graph: KnowledgeGraph) -> None:
        """Detail-first topo sort respects edge dependencies."""
        order = layered_topological_sort(multi_tree_graph)

        # Background is last
        assert order[-1] == "0"

        # Edge 1->1-1: 1 depends on 1-1, so 1-1 first
        assert order.index("1-1") < order.index("1")

        # Edge 2->2-1: 2 depends on 2-1, so 2-1 first
        assert order.index("2-1") < order.index("2")

        # Cross edge 2-1->1: 2-1 depends on 1, so 1 first
        assert order.index("1") < order.index("2-1")

    def test_cycle_detection_multi_tree(self, multi_tree_graph: KnowledgeGraph) -> None:
        """Multi-tree has no cycles."""
        assert detect_cycle(multi_tree_graph) is None

    def test_validate_multi_tree(self, multi_tree_graph: KnowledgeGraph) -> None:
        """Multi-tree validation returns (True, [])."""
        is_valid, cycles = validate_graph(multi_tree_graph)
        assert is_valid is True
        assert cycles == []

    def test_generation_waves_multi_tree(self, multi_tree_graph: KnowledgeGraph) -> None:
        """Multi-tree waves respect edge dependencies."""
        waves = get_generation_waves(multi_tree_graph)

        # Wave 0: 1-1 (out-degree 0, no dependencies)
        assert waves[0] == ["1-1"]

        # Wave 1: 1 (depends on 1-1, now resolved)
        assert waves[1] == ["1"]

        # Wave 2: 2-1 (depends on 1 via cross edge, now resolved)
        assert "2-1" in waves[2]

        # Last wave: background
        assert waves[-1] == ["0"]


# ===========================================================================
# Test Case 6: Cyclic Graph
# ===========================================================================


class TestCyclicGraph:
    """Graph with cycle: A -> B -> C -> A (deadlock).

    Expected behavior:
    - topo_sort raises ValueError
    - detect_cycle returns cycle path
    - validate_graph returns (False, [cycle])
    - get_generation_waves raises ValueError
    """

    @pytest.fixture
    def cyclic_graph(self) -> KnowledgeGraph:
        """Build cycle A->B->C->A."""
        graph = KnowledgeGraph(scene_id="cycle")
        graph.add_node("0", "background")
        graph.add_node("A", "node A")
        graph.add_node("B", "node B")
        graph.add_node("C", "node C")

        # Background to A
        graph.add_edge("0", "A", "", EdgeType.TREE)

        # Cycle edges
        graph.add_edge("A", "B", "", EdgeType.TREE)
        graph.add_edge("B", "C", "", EdgeType.TREE)
        graph.add_edge("C", "A", "", EdgeType.TREE)
        return graph

    def test_topo_sort_cycle_raises(self, cyclic_graph: KnowledgeGraph) -> None:
        """Topological sort on cyclic graph raises ValueError."""
        with pytest.raises(ValueError, match="contains a cycle"):
            layered_topological_sort(cyclic_graph)

    def test_detect_cycle_returns_path(self, cyclic_graph: KnowledgeGraph) -> None:
        """Cycle detection returns the cycle path."""
        cycle = detect_cycle(cyclic_graph)
        assert cycle is not None
        # Cycle should return to starting node
        assert cycle[0] == cycle[-1]
        # Check that A, B, C are in the cycle
        cycle_nodes = set(cycle)
        assert "A" in cycle_nodes
        assert "B" in cycle_nodes
        assert "C" in cycle_nodes

    def test_validate_cycle_graph(self, cyclic_graph: KnowledgeGraph) -> None:
        """Validation on cyclic graph returns (False, [cycles])."""
        is_valid, cycles = validate_graph(cyclic_graph)
        assert is_valid is False
        assert len(cycles) > 0
        # Each cycle should start and end with same node
        for cycle in cycles:
            assert cycle[0] == cycle[-1]

    def test_generation_waves_cycle_raises(self, cyclic_graph: KnowledgeGraph) -> None:
        """Generation waves on cyclic graph raises ValueError."""
        with pytest.raises(ValueError, match="contains a cycle"):
            get_generation_waves(cyclic_graph)


# ===========================================================================
# Additional Edge Cases
# ===========================================================================


class TestEdgeCases:
    """Additional edge cases for robustness."""

    def test_disconnected_components(self) -> None:
        """Graph with disconnected components after background."""
        graph = KnowledgeGraph(scene_id="disconnected")
        graph.add_node("0", "background")
        graph.add_node("1", "tree root 1")
        graph.add_node("2", "tree root 2")

        graph.add_edge("0", "1", "", EdgeType.TREE)
        graph.add_edge("0", "2", "", EdgeType.TREE)

        order = layered_topological_sort(graph)
        # 1 and 2 (out-degree 0) first, then 0 (depends on both)
        assert order == ["1", "2", "0"]

    def test_self_loop(self) -> None:
        """Node with edge to itself (self-cycle)."""
        graph = KnowledgeGraph(scene_id="self_loop")
        graph.add_node("0", "background")
        graph.add_node("1", "self-referential")

        graph.add_edge("0", "1", "", EdgeType.TREE)
        graph.add_edge("1", "1", "", EdgeType.TREE)  # self-loop

        cycle = detect_cycle(graph)
        assert cycle is not None
        # Self-loop appears as [1, 1]
        assert cycle == ["1", "1"]

    def test_multiple_independent_cycles(self) -> None:
        """Graph with multiple independent cycles."""
        graph = KnowledgeGraph(scene_id="multi_cycle")
        graph.add_node("0", "background")
        graph.add_node("A", "node A")
        graph.add_node("B", "node B")
        graph.add_node("C", "node C")
        graph.add_node("D", "node D")

        graph.add_edge("0", "A", "", EdgeType.TREE)
        graph.add_edge("0", "C", "", EdgeType.TREE)

        # Cycle 1: A -> B -> A
        graph.add_edge("A", "B", "", EdgeType.TREE)
        graph.add_edge("B", "A", "", EdgeType.TREE)

        # Cycle 2: C -> D -> C
        graph.add_edge("C", "D", "", EdgeType.TREE)
        graph.add_edge("D", "C", "", EdgeType.TREE)

        cycles = find_all_cycles(graph)
        # Should find at least 2 cycles
        assert len(cycles) >= 2

        is_valid, _ = validate_graph(graph)
        assert is_valid is False

    def test_complex_dag(self) -> None:
        """Diamond structure: converge first, then branches, then root, bg last."""
        graph = KnowledgeGraph(scene_id="diamond")
        graph.add_node("0", "background")
        graph.add_node("1", "root")
        graph.add_node("1-1", "left")
        graph.add_node("1-2", "right")
        graph.add_node("2", "converge")

        graph.add_edge("0", "1", "", EdgeType.TREE)
        graph.add_edge("1", "1-1", "", EdgeType.TREE)
        graph.add_edge("1", "1-2", "", EdgeType.TREE)
        graph.add_edge("1-1", "2", "", EdgeType.TREE)
        graph.add_edge("1-2", "2", "", EdgeType.TREE)

        order = layered_topological_sort(graph)
        # Edge 1-1->2: 1-1 depends on 2, so 2 first
        assert order.index("2") < order.index("1-1")
        assert order.index("2") < order.index("1-2")
        # Edge 1->1-1: 1 depends on 1-1, so 1-1 first
        assert order.index("1-1") < order.index("1")
        assert order.index("1-2") < order.index("1")
        # Background is last
        assert order[-1] == "0"

        # Waves: converge, then left+right (parallel), then root, then bg
        waves = get_generation_waves(graph)
        assert waves[0] == ["2"]
        assert set(waves[1]) == {"1-1", "1-2"}
        assert waves[2] == ["1"]
        assert waves[-1] == ["0"]


# ===========================================================================
# Algorithm Property Tests
# ===========================================================================


class TestAlgorithmProperties:
    """Test generic algorithm properties across different graphs."""

    def test_topo_sort_is_topological_order(self) -> None:
        """For any edge (from->to), from appears after to in order.

        Edge from→to means from depends on to. So to is generated first.
        """
        graph = KnowledgeGraph(scene_id="property_test")
        graph.add_node("0", "bg")
        graph.add_node("1", "n1")
        graph.add_node("2", "n2")
        graph.add_node("3", "n3")

        graph.add_edge("0", "1", "", EdgeType.TREE)
        graph.add_edge("1", "2", "", EdgeType.TREE)
        graph.add_edge("0", "3", "", EdgeType.TREE)
        graph.add_edge("3", "2", "", EdgeType.CROSS)

        order = layered_topological_sort(graph)

        # Check all edges: from appears after to (to is generated first)
        for edge in graph.edges:
            src, dst = edge.from_node_id, edge.to_node_id
            if src in order and dst in order:
                assert order.index(dst) < order.index(src), \
                    f"Edge {src}->{dst}: {dst} should come before {src}"

    def test_waves_are_parallel_safe(self) -> None:
        """Nodes within same wave have no dependencies on each other."""
        graph = KnowledgeGraph(scene_id="wave_test")
        graph.add_node("0", "bg")
        graph.add_node("1", "core")
        graph.add_node("1-1", "leaf1")
        graph.add_node("1-2", "leaf2")
        graph.add_node("1-3", "leaf3")

        graph.add_edge("0", "1", "", EdgeType.TREE)
        graph.add_edge("1-1", "1", "", EdgeType.TREE)
        graph.add_edge("1-2", "1", "", EdgeType.TREE)
        graph.add_edge("1-3", "1", "", EdgeType.TREE)

        waves = get_generation_waves(graph)

        # For each wave, verify no internal dependencies
        for wave in waves:
            wave_set = set(wave)
            for node in wave:
                # Check dependencies of this node
                deps = [e.to_node_id for e in graph.edges if e.from_node_id == node]
                for dep in deps:
                    if dep in wave_set:
                        raise AssertionError(
                            f"Wave {wave} has internal dependency: {node} -> {dep}"
                        )

    def test_background_after_its_dependencies(self) -> None:
        """Background always appears after the nodes it depends on (via edges).

        Background may not be last if other nodes also have no remaining
        dependencies at the same time. But it must come after any node
        it points to via an edge.
        """
        test_cases = [
            "single", "chain", "star", "multi_tree"
        ]

        for case in test_cases:
            if case == "single":
                graph = KnowledgeGraph(scene_id=case)
                graph.add_node("0", "bg")
            elif case == "chain":
                graph = KnowledgeGraph(scene_id=case)
                graph.add_node("0", "bg")
                graph.add_node("1", "n1")
                graph.add_edge("0", "1", "", EdgeType.TREE)
            elif case == "star":
                graph = KnowledgeGraph(scene_id=case)
                graph.add_node("0", "bg")
                graph.add_node("1", "core")
                graph.add_node("1-1", "leaf")
                graph.add_edge("0", "1", "", EdgeType.TREE)
                graph.add_edge("1-1", "1", "", EdgeType.TREE)
            else:  # multi_tree
                graph = KnowledgeGraph(scene_id=case)
                graph.add_node("0", "bg")
                graph.add_node("1", "n1")
                graph.add_node("2", "n2")
                graph.add_edge("0", "1", "", EdgeType.TREE)
                graph.add_edge("0", "2", "", EdgeType.TREE)

            order = layered_topological_sort(graph)

            # For every edge from bg, bg must appear after the target
            bg = graph.background_node_id
            for edge in graph.edges:
                if edge.from_node_id == bg:
                    assert order.index(edge.to_node_id) < order.index(bg), \
                        f"Background should come after {edge.to_node_id}"
