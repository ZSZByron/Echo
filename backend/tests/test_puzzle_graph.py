"""Tests for PuzzleGraph - puzzle dependency graph with topological sorting."""
from pathlib import Path

import pytest

from app.models.puzzle_graph import PuzzleGraph, PuzzleNode, PuzzleNodeType


class TestPuzzleGraph:
    """Test PuzzleGraph loading and functionality."""

    def test_from_yaml_returns_valid_graph(self) -> None:
        """Test that PuzzleGraph.from_yaml('temple_ruins') returns valid graph."""
        graph = PuzzleGraph.from_yaml("temple_ruins")

        assert graph.scene_id == "temple_ruins"
        assert isinstance(graph.nodes, dict)
        assert len(graph.nodes) > 0
        assert isinstance(graph.chain, list)
        assert len(graph.chain) > 0

    def test_chain_is_topologically_sorted(self) -> None:
        """Test that chain is topologically sorted (clue → consumable → reward)."""
        graph = PuzzleGraph.from_yaml("temple_ruins")

        # Verify type order: CLUE → CONSUMABLE → REWARD → OBSTACLE
        type_order = {
            PuzzleNodeType.CLUE: 0,
            PuzzleNodeType.CONSUMABLE: 1,
            PuzzleNodeType.REWARD: 2,
            PuzzleNodeType.OBSTACLE: 3,
        }

        for i in range(len(graph.chain) - 1):
            node_id = graph.chain[i]
            next_node_id = graph.chain[i + 1]
            current_type = graph.nodes[node_id].type
            next_type = graph.nodes[next_node_id].type

            # Current type should come before or equal to next type
            assert type_order[current_type] <= type_order[next_type], (
                f"Chain not topologically sorted: "
                f"{node_id}({current_type}) before {next_node_id}({next_type})"
            )

    def test_independence_from_scene_graph(self) -> None:
        """Test that PuzzleGraph is independent from SceneGraph (no imports)."""
        # Read the puzzle_graph.py source file
        puzzle_graph_path = Path(__file__).parent.parent / "app" / "models" / "puzzle_graph.py"
        source = puzzle_graph_path.read_text(encoding='utf-8')

        # Verify it doesn't import SceneGraph (check for import statements, not docstrings)
        assert "from app.models.scene_graph import" not in source
        assert "import scene_graph" not in source
        assert "import SceneGraph" not in source
        # Check that the module doesn't depend on scene_graph module
        lines = source.split('\n')
        import_lines = [line for line in lines if line.strip().startswith('import') or line.strip().startswith('from')]
        for line in import_lines:
            assert 'scene_graph' not in line.lower(), f"SceneGraph import found: {line}"

    def test_puzzle_node_type_enum_values(self) -> None:
        """Test PuzzleNodeType enum has correct values."""
        assert PuzzleNodeType.CLUE.value == "clue"
        assert PuzzleNodeType.CONSUMABLE.value == "consumable"
        assert PuzzleNodeType.REWARD.value == "reward"
        assert PuzzleNodeType.OBSTACLE.value == "obstacle"

    def test_puzzle_node_structure(self) -> None:
        """Test that PuzzleNode has correct structure and types."""
        graph = PuzzleGraph.from_yaml("temple_ruins")

        # Pick a node to test structure
        node_id = graph.chain[0]
        node = graph.nodes[node_id]

        assert isinstance(node, PuzzleNode)
        assert isinstance(node.id, str)
        assert isinstance(node.type, PuzzleNodeType)
        assert isinstance(node.requires, list)
        assert isinstance(node.produces, str)
        assert isinstance(node.interaction, str)

    def test_edge_case_missing_yaml(self) -> None:
        """Test edge case: missing YAML file."""
        with pytest.raises(FileNotFoundError):
            PuzzleGraph.from_yaml("nonexistent_scene")

    def test_edge_case_empty_puzzle_chain(self) -> None:
        """Test edge case: empty puzzle_chain in YAML."""
        # Create a minimal YAML with empty puzzle_chain
        import tempfile
        import yaml

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "empty_puzzle.yaml"
            yaml_path.write_text(yaml.dump({"puzzle_chain": []}))

            # Monkey-path _SCENES_DIR to point to temp directory
            from app.models import puzzle_graph
            original_dir = puzzle_graph._SCENES_DIR
            puzzle_graph._SCENES_DIR = Path(tmpdir)

            try:
                with pytest.raises(ValueError, match="No puzzle_chain"):
                    PuzzleGraph.from_yaml("empty_puzzle")
            finally:
                puzzle_graph._SCENES_DIR = original_dir

    def test_dependencies_resolved_correctly(self) -> None:
        """Test that node dependencies are resolved correctly."""
        graph = PuzzleGraph.from_yaml("temple_ruins")

        # Check that all requirements of each node are satisfied before it
        node_positions = {node_id: idx for idx, node_id in enumerate(graph.chain)}

        for node_id, node in graph.nodes.items():
            for req_id in node.requires:
                # Requirement should be a node ID or produced item
                assert req_id in graph.nodes or any(
                    n.produces == req_id for n in graph.nodes.values()
                ), f"Requirement {req_id} not found in nodes"

                # If it's a node ID, it should come before this node
                if req_id in graph.nodes:
                    assert node_positions[req_id] < node_positions[node_id], (
                        f"Dependency {req_id} should come before {node_id}"
                    )
