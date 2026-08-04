"""Unit tests for GraphExtractor — AI-driven knowledge graph generation.

Tests the full pipeline from LLM text output → JSON parsing → normalization →
KnowledgeGraph object construction, covering:

1. _try_parse_json: JSON repair strategies (direct, code-fence, brace extraction, failure)
2. _normalize: schema validation (missing keys, visual_description sanitization)
3. to_knowledge_graph: dict → KnowledgeGraph conversion (parent_serial→TREE, CROSS edges, orphan skip)
4. extract_from_text: end-to-end with mock LLM (normal, chat fallback, invalid JSON)
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.provider import LLMProvider
from app.models.knowledge_graph import EdgeType, KnowledgeGraph
from app.domains.creation.graph.graph_extractor import GraphExtractor, _try_parse_json


# ===========================================================================
# 1. _try_parse_json — JSON repair strategies
# ===========================================================================


class TestTryParseJson:
    """Test the JSON parsing helper with various LLM output formats."""

    def test_direct_json(self) -> None:
        """Strategy 1: clean JSON string parses directly."""
        raw = '{"background": {}, "nodes": [], "edges": []}'
        result = _try_parse_json(raw)
        assert result["background"] == {}
        assert result["nodes"] == []

    def test_code_fence_json(self) -> None:
        """Strategy 2: JSON wrapped in markdown ```json fences."""
        raw = '```json\n{"background": {}, "nodes": [], "edges": []}\n```'
        result = _try_parse_json(raw)
        assert result["nodes"] == []

    def test_code_fence_without_lang_tag(self) -> None:
        """Strategy 2 variant: fence without 'json' language tag."""
        raw = '```\n{"background": {}, "nodes": [], "edges": []}\n```'
        result = _try_parse_json(raw)
        assert result["background"] == {}

    def test_brace_extraction(self) -> None:
        """Strategy 3: JSON embedded in surrounding text — extract by braces."""
        raw = 'Here is the graph:\n{"background": {}, "nodes": [], "edges": []}\nDone.'
        result = _try_parse_json(raw)
        assert result["nodes"] == []

    def test_brace_extraction_with_nested(self) -> None:
        """Strategy 3 with nested braces inside string values."""
        raw = 'output: {"background": {"description": "a {nested} brace"}, "nodes": []}'
        result = _try_parse_json(raw)
        assert result["background"]["description"] == "a {nested} brace"

    def test_all_strategies_fail_raises(self) -> None:
        """When all repair strategies fail, ValueError is raised."""
        with pytest.raises(ValueError, match="Failed to parse LLM response as JSON"):
            _try_parse_json("this is not json at all")

    def test_empty_string_raises(self) -> None:
        """Empty string input raises ValueError."""
        with pytest.raises(ValueError, match="Failed to parse LLM response as JSON"):
            _try_parse_json("")

    def test_partial_json_raises(self) -> None:
        """Truncated JSON without closing brace raises ValueError."""
        with pytest.raises(ValueError, match="Failed to parse LLM response as JSON"):
            _try_parse_json('{"background": {"description": "incomplete')

    def test_multiple_code_fences_picks_first_valid(self) -> None:
        """When multiple fenced blocks exist, first valid JSON wins."""
        raw = '```json\n{"valid": true}\n```\n```json\n{"other": 1}\n```'
        result = _try_parse_json(raw)
        assert result == {"valid": True}


# ===========================================================================
# 2. _normalize — schema validation
# ===========================================================================


class TestNormalize:
    """Test the _normalize static method for LLM output validation."""

    def test_valid_full_structure(self) -> None:
        """Complete dict with background, nodes, edges passes through."""
        data = {
            "background": {"description": "forest"},
            "nodes": [{"serial": "1", "description": "bg", "parent_serial": None}],
            "edges": [],
        }
        result = GraphExtractor._normalize(data)
        assert result["background"]["description"] == "forest"
        assert len(result["nodes"]) == 1

    def test_missing_background_raises(self) -> None:
        """Missing 'background' key raises ValueError."""
        with pytest.raises(ValueError, match="missing required keys"):
            GraphExtractor._normalize({"nodes": []})

    def test_missing_nodes_raises(self) -> None:
        """Missing 'nodes' key raises ValueError."""
        with pytest.raises(ValueError, match="missing required keys"):
            GraphExtractor._normalize({"background": {}})

    def test_missing_edges_defaults_to_empty(self) -> None:
        """Missing 'edges' key is auto-filled with empty list."""
        data = {
            "background": {"description": "scene"},
            "nodes": [{"serial": "1", "description": "bg", "parent_serial": None}],
        }
        result = GraphExtractor._normalize(data)
        assert result["edges"] == []

    def test_edge_visual_description_forced_empty(self) -> None:
        """All edge visual_descriptions are forced to empty string."""
        data = {
            "background": {"description": "scene"},
            "nodes": [{"serial": "1", "description": "bg", "parent_serial": None}],
            "edges": [
                {
                    "from": "1",
                    "to": "1",
                    "edge_type": "cross",
                    "visual_description": "LLM hallucinated description",
                }
            ],
        }
        result = GraphExtractor._normalize(data)
        assert result["edges"][0]["visual_description"] == ""

    def test_edge_without_visual_description_gets_empty(self) -> None:
        """Edge missing visual_description key gets empty string."""
        data = {
            "background": {"description": "scene"},
            "nodes": [{"serial": "1", "description": "bg", "parent_serial": None}],
            "edges": [{"from": "1", "to": "1", "edge_type": "cross"}],
        }
        result = GraphExtractor._normalize(data)
        assert result["edges"][0]["visual_description"] == ""

    def test_multiple_edges_all_sanitized(self) -> None:
        """Every edge in a multi-edge list gets visual_description cleared."""
        data = {
            "background": {"description": "scene"},
            "nodes": [
                {"serial": "1", "description": "bg", "parent_serial": None},
                {"serial": "2", "description": "obj", "parent_serial": None},
            ],
            "edges": [
                {"from": "1", "to": "2", "edge_type": "cross", "visual_description": "a"},
                {"from": "2", "to": "1", "edge_type": "cross", "visual_description": "b"},
            ],
        }
        result = GraphExtractor._normalize(data)
        for edge in result["edges"]:
            assert edge["visual_description"] == ""


# ===========================================================================
# 3. to_knowledge_graph — dict → KnowledgeGraph conversion
# ===========================================================================


class TestToKnowledgeGraph:
    """Test conversion from normalized dict to KnowledgeGraph object."""

    def test_single_background_node(self) -> None:
        """Graph with only a background node has 1 node, 0 edges."""
        data = {
            "background": {"description": "empty room"},
            "nodes": [{"serial": "1", "description": "empty room", "parent_serial": None}],
            "edges": [],
        }
        graph = GraphExtractor.to_knowledge_graph(data, scene_id="test")
        assert isinstance(graph, KnowledgeGraph)
        assert graph.scene_id == "test"
        assert graph.background_node_id == "1"
        assert len(graph.nodes) == 1
        assert len(graph.edges) == 0

    def test_parent_serial_creates_tree_edges(self) -> None:
        """parent_serial relationships produce TREE edges automatically."""
        data = {
            "background": {"description": "scene"},
            "nodes": [
                {"serial": "1", "description": "bg", "parent_serial": None},
                {"serial": "1-1", "description": "child", "parent_serial": "1"},
                {"serial": "1-1-1", "description": "grandchild", "parent_serial": "1-1"},
            ],
            "edges": [],
        }
        graph = GraphExtractor.to_knowledge_graph(data)

        # 3 nodes, 2 tree edges (1→1-1, 1-1→1-1-1)
        assert len(graph.nodes) == 3
        assert len(graph.edges) == 2
        assert all(e.edge_type == EdgeType.TREE for e in graph.edges)

        # Verify parent-child relationships
        edge_pairs = {(e.from_node_id, e.to_node_id) for e in graph.edges}
        assert ("1", "1-1") in edge_pairs
        assert ("1-1", "1-1-1") in edge_pairs

    def test_cross_edges_from_explicit_edges_list(self) -> None:
        """Explicit CROSS edges in edges list are added correctly."""
        data = {
            "background": {"description": "scene"},
            "nodes": [
                {"serial": "1", "description": "bg", "parent_serial": None},
                {"serial": "1-1", "description": "lock", "parent_serial": "1"},
                {"serial": "2", "description": "panel", "parent_serial": None},
                {"serial": "2-1", "description": "password", "parent_serial": "2"},
            ],
            "edges": [
                {"from": "2-1", "to": "1-1", "edge_type": "cross", "visual_description": ""},
            ],
        }
        graph = GraphExtractor.to_knowledge_graph(data)

        # 4 nodes, 2 tree edges (parent_serial) + 1 cross edge
        assert len(graph.nodes) == 4
        assert len(graph.edges) == 3

        cross_edges = [e for e in graph.edges if e.edge_type == EdgeType.CROSS]
        assert len(cross_edges) == 1
        assert cross_edges[0].from_node_id == "2-1"
        assert cross_edges[0].to_node_id == "1-1"

    def test_tree_edges_in_edges_list_skipped(self) -> None:
        """edge_type='tree' in explicit edges list is skipped (parent_serial handles it)."""
        data = {
            "background": {"description": "scene"},
            "nodes": [
                {"serial": "1", "description": "bg", "parent_serial": None},
                {"serial": "1-1", "description": "child", "parent_serial": "1"},
            ],
            "edges": [
                {"from": "1", "to": "1-1", "edge_type": "tree", "visual_description": ""},
            ],
        }
        graph = GraphExtractor.to_knowledge_graph(data)

        # Only 1 edge from parent_serial, the explicit tree edge is not duplicated
        assert len(graph.edges) == 1
        assert graph.edges[0].from_node_id == "1"
        assert graph.edges[0].to_node_id == "1-1"

    def test_edge_to_nonexistent_node_skipped(self) -> None:
        """CROSS edge referencing non-existent node ID is silently skipped."""
        data = {
            "background": {"description": "scene"},
            "nodes": [
                {"serial": "1", "description": "bg", "parent_serial": None},
            ],
            "edges": [
                {"from": "1", "to": "999", "edge_type": "cross", "visual_description": ""},
                {"from": "999", "to": "1", "edge_type": "cross", "visual_description": ""},
            ],
        }
        graph = GraphExtractor.to_knowledge_graph(data)

        assert len(graph.nodes) == 1
        assert len(graph.edges) == 0  # both edges reference nonexistent "999"

    def test_parent_serial_to_nonexistent_skipped(self) -> None:
        """parent_serial pointing to non-existent parent does not create edge."""
        data = {
            "background": {"description": "scene"},
            "nodes": [
                {"serial": "1", "description": "bg", "parent_serial": None},
                {"serial": "1-1", "description": "orphan", "parent_serial": "999"},
            ],
            "edges": [],
        }
        graph = GraphExtractor.to_knowledge_graph(data)

        # Node 1-1 is still added, but no edge (parent "999" doesn't exist)
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 0

    def test_background_auto_detected_from_first_level1_node(self) -> None:
        """background_node_id is auto-set to the first level-1 node added."""
        data = {
            "background": {"description": "scene"},
            "nodes": [
                {"serial": "1", "description": "bg", "parent_serial": None},
            ],
            "edges": [],
        }
        graph = GraphExtractor.to_knowledge_graph(data)
        assert graph.background_node_id == "1"

    def test_empty_nodes_list(self) -> None:
        """Empty nodes list produces empty graph with no background."""
        data = {
            "background": {"description": "void"},
            "nodes": [],
            "edges": [],
        }
        graph = GraphExtractor.to_knowledge_graph(data, scene_id="empty")
        assert len(graph.nodes) == 0
        assert graph.background_node_id is None

    def test_multi_tree_structure_with_cross_dependency(self) -> None:
        """Full multi-tree structure with cross-tree dependency."""
        data = {
            "background": {"description": "dungeon entrance"},
            "nodes": [
                {"serial": "1", "description": "bg", "parent_serial": None},
                {"serial": "1-1", "description": "locked door", "parent_serial": "1"},
                {"serial": "2", "description": "side wall", "parent_serial": None},
                {"serial": "2-1", "description": "key on hook", "parent_serial": "2"},
            ],
            "edges": [
                {"from": "2-1", "to": "1-1", "edge_type": "cross", "visual_description": ""},
            ],
        }
        graph = GraphExtractor.to_knowledge_graph(data, scene_id="dungeon")

        # 4 nodes
        assert len(graph.nodes) == 4
        # 3 edges: 2 tree (1→1-1, 2→2-1) + 1 cross (2-1→1-1)
        assert len(graph.edges) == 3

        tree_edges = {(e.from_node_id, e.to_node_id) for e in graph.edges if e.edge_type == EdgeType.TREE}
        cross_edges = {(e.from_node_id, e.to_node_id) for e in graph.edges if e.edge_type == EdgeType.CROSS}

        assert ("1", "1-1") in tree_edges
        assert ("2", "2-1") in tree_edges
        assert ("2-1", "1-1") in cross_edges


# ===========================================================================
# 4. extract_from_text — end-to-end with mock LLM provider
# ===========================================================================


@pytest.fixture
def mock_provider() -> AsyncMock:
    """Create a mock LLMProvider for injection."""
    provider = AsyncMock(spec=LLMProvider)
    return provider


@pytest.fixture
def extractor_with_mock(mock_provider: AsyncMock) -> GraphExtractor:
    """Create a GraphExtractor with pre-injected mock provider."""
    extractor = GraphExtractor()
    extractor._provider = mock_provider
    return extractor


class TestExtractFromText:
    """Test the full extract_from_text pipeline with mock LLM."""

    @pytest.mark.asyncio
    async def test_normal_extraction(
        self, extractor_with_mock: GraphExtractor, mock_provider: AsyncMock
    ) -> None:
        """Normal LLM response produces valid normalized dict."""
        mock_provider.chat_json.return_value = {
            "background": {"description": "forest clearing"},
            "nodes": [
                {"serial": "1", "description": "forest floor", "parent_serial": None},
                {"serial": "1-1", "description": "ancient tree", "parent_serial": "1"},
            ],
            "edges": [],
        }

        result = await extractor_with_mock.extract_from_text("a forest with a big tree")

        assert "background" in result
        assert "nodes" in result
        assert len(result["nodes"]) == 2
        assert result["nodes"][0]["serial"] == "1"
        assert result["nodes"][1]["parent_serial"] == "1"

    @pytest.mark.asyncio
    async def test_extraction_with_cross_edges(
        self, extractor_with_mock: GraphExtractor, mock_provider: AsyncMock
    ) -> None:
        """LLM response with cross edges preserves them."""
        mock_provider.chat_json.return_value = {
            "background": {"description": "temple"},
            "nodes": [
                {"serial": "1", "description": "altar", "parent_serial": None},
                {"serial": "1-1", "description": "idol", "parent_serial": "1"},
                {"serial": "2", "description": "wall", "parent_serial": None},
                {"serial": "2-1", "description": "torch", "parent_serial": "2"},
            ],
            "edges": [
                {"from": "2-1", "to": "1-1", "edge_type": "cross", "visual_description": ""},
            ],
        }

        result = await extractor_with_mock.extract_from_text("temple scene")
        assert len(result["edges"]) == 1
        assert result["edges"][0]["from"] == "2-1"
        assert result["edges"][0]["to"] == "1-1"
        assert result["edges"][0]["edge_type"] == "cross"

    @pytest.mark.asyncio
    async def test_chat_json_fails_fallback_to_chat(
        self, extractor_with_mock: GraphExtractor, mock_provider: AsyncMock
    ) -> None:
        """When chat_json raises, falls back to plain chat() and parses result."""
        mock_provider.chat_json.side_effect = RuntimeError("endpoint unavailable")
        mock_provider.chat.return_value = json.dumps({
            "background": {"description": "cave"},
            "nodes": [{"serial": "1", "description": "cave wall", "parent_serial": None}],
            "edges": [],
        })

        result = await extractor_with_mock.extract_from_text("dark cave")
        assert result["background"]["description"] == "cave"
        assert len(result["nodes"]) == 1

    @pytest.mark.asyncio
    async def test_chat_returns_markdown_fenced_json(
        self, extractor_with_mock: GraphExtractor, mock_provider: AsyncMock
    ) -> None:
        """Fallback chat() returning markdown-fenced JSON is parsed correctly."""
        mock_provider.chat_json.side_effect = RuntimeError("fail")
        mock_provider.chat.return_value = '''```json
{
    "background": {"description": "throne room"},
    "nodes": [{"serial": "1", "description": "throne", "parent_serial": null}],
    "edges": []
}
```'''

        result = await extractor_with_mock.extract_from_text("throne room")
        assert result["background"]["description"] == "throne room"

    @pytest.mark.asyncio
    async def test_both_chat_methods_fail_raises(
        self, extractor_with_mock: GraphExtractor, mock_provider: AsyncMock
    ) -> None:
        """When both chat_json and chat fail, ValueError propagates."""
        mock_provider.chat_json.side_effect = RuntimeError("json fail")
        mock_provider.chat.side_effect = RuntimeError("chat fail")

        with pytest.raises(RuntimeError, match="chat fail"):
            await extractor_with_mock.extract_from_text("test")

    @pytest.mark.asyncio
    async def test_invalid_json_response_raises_value_error(
        self, extractor_with_mock: GraphExtractor, mock_provider: AsyncMock
    ) -> None:
        """LLM returning non-JSON text raises ValueError after repair attempts."""
        mock_provider.chat_json.side_effect = RuntimeError("fail")
        mock_provider.chat.return_value = "I cannot generate a graph for this."

        with pytest.raises(ValueError, match="Failed to parse"):
            await extractor_with_mock.extract_from_text("nonsense input")

    @pytest.mark.asyncio
    async def test_missing_background_key_raises(
        self, extractor_with_mock: GraphExtractor, mock_provider: AsyncMock
    ) -> None:
        """LLM output missing 'background' key raises ValueError in normalize."""
        mock_provider.chat_json.return_value = {
            "nodes": [{"serial": "1", "description": "x", "parent_serial": None}],
        }

        with pytest.raises(ValueError, match="missing required keys"):
            await extractor_with_mock.extract_from_text("test")

    @pytest.mark.asyncio
    async def test_visual_description_sanitized_in_output(
        self, extractor_with_mock: GraphExtractor, mock_provider: AsyncMock
    ) -> None:
        """LLM-generated visual_descriptions on edges are wiped to empty string."""
        mock_provider.chat_json.return_value = {
            "background": {"description": "scene"},
            "nodes": [
                {"serial": "1", "description": "a", "parent_serial": None},
                {"serial": "2", "description": "b", "parent_serial": None},
            ],
            "edges": [
                {
                    "from": "1",
                    "to": "2",
                    "edge_type": "cross",
                    "visual_description": "LLM wrote this, should be erased",
                },
            ],
        }

        result = await extractor_with_mock.extract_from_text("test")
        assert result["edges"][0]["visual_description"] == ""


# ===========================================================================
# 5. Integration: extract_from_text → to_knowledge_graph full chain
# ===========================================================================


class TestExtractionToGraphChain:
    """Test the full chain from text input to KnowledgeGraph object."""

    @pytest.mark.asyncio
    async def test_full_chain_produces_valid_graph(
        self, extractor_with_mock: GraphExtractor, mock_provider: AsyncMock
    ) -> None:
        """End-to-end: text → extract_from_text → to_knowledge_graph → valid graph."""
        mock_provider.chat_json.return_value = {
            "background": {"description": "abandoned shrine"},
            "nodes": [
                {"serial": "1", "description": "stone floor", "parent_serial": None},
                {"serial": "1-1", "description": "cracked statue", "parent_serial": "1"},
                {"serial": "1-1-1", "description": "missing head", "parent_serial": "1-1"},
                {"serial": "2", "description": "overgrown wall", "parent_serial": None},
                {"serial": "2-1", "description": "glowing rune", "parent_serial": "2"},
            ],
            "edges": [
                {"from": "2-1", "to": "1-1", "edge_type": "cross", "visual_description": ""},
            ],
        }

        raw = await extractor_with_mock.extract_from_text("abandoned shrine with runes")
        graph = GraphExtractor.to_knowledge_graph(raw, scene_id="shrine")

        # Structural assertions
        assert graph.scene_id == "shrine"
        assert graph.background_node_id == "1"
        assert len(graph.nodes) == 5
        # 3 tree edges (1→1-1, 1-1→1-1-1, 2→2-1) + 1 cross (2-1→1-1) = 4
        assert len(graph.edges) == 4

        # Topological sanity: no cycles
        import sys
        from pathlib import Path

        project_root = str(Path(__file__).resolve().parents[3])
        graph_algo_dir = str(Path(__file__).resolve().parents[3] / "tests" / "graph_algorithm")
        for p in (project_root, graph_algo_dir):
            if p not in sys.path:
                sys.path.insert(0, p)

        from cycle_detector import validate_graph

        is_valid, cycles = validate_graph(graph)
        assert is_valid is True
        assert cycles == []

    @pytest.mark.asyncio
    async def test_chain_with_only_background(
        self, extractor_with_mock: GraphExtractor, mock_provider: AsyncMock
    ) -> None:
        """Minimal scene: only background, no children."""
        mock_provider.chat_json.return_value = {
            "background": {"description": "void"},
            "nodes": [{"serial": "1", "description": "empty void", "parent_serial": None}],
            "edges": [],
        }

        raw = await extractor_with_mock.extract_from_text("empty room")
        graph = GraphExtractor.to_knowledge_graph(raw)

        assert len(graph.nodes) == 1
        assert len(graph.edges) == 0
        assert graph.background_node_id == "1"
