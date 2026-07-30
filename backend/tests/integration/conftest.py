"""Pytest configuration and fixtures for graph API integration tests."""

import sys
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Add project root to sys.path for imports
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Add graph_algorithm test directory for algorithm imports
_GRAPH_ALGO_DIR = _PROJECT_ROOT / "tests" / "graph_algorithm"
if str(_GRAPH_ALGO_DIR) not in sys.path:
    sys.path.insert(0, str(_GRAPH_ALGO_DIR))

from app.main import app
from app.models.knowledge_graph import EdgeType, GraphNode, KnowledgeGraph, NodeStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_root() -> Path:
    """Provide project root directory path."""
    return _PROJECT_ROOT


@pytest.fixture
def temp_db_path(project_root: Path, tmp_path) -> Path:
    """Provide a temporary database path for isolated tests."""
    return tmp_path / "test_graph.db"


@pytest.fixture
async def test_client(temp_db_path: Path) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client with mocked database path."""
    
    # Mock the database path to use temporary test database
    with patch("app.state.graph_store._DEFAULT_DB_PATH", temp_db_path):
        with patch("app.api.graph_routes._store") as mock_store:
            # Configure mock store to use test database
            from app.state.graph_store import GraphStore
            test_store = GraphStore(db_path=temp_db_path)
            await test_store.init_db()
            
            # Replace the singleton store with our test store
            mock_store.init_db = test_store.init_db
            mock_store.save_graph = test_store.save_graph
            mock_store.load_graph = test_store.load_graph
            mock_store.delete_graph = test_store.delete_graph
            mock_store._db_path = str(temp_db_path)
            
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                yield client
                
            # Cleanup
            await test_store.close()


@pytest.fixture
def mock_graph_store(temp_db_path: Path):
    """Provide a mocked GraphStore for direct testing."""
    from app.state.graph_store import GraphStore
    
    async def _get_store():
        store = GraphStore(db_path=temp_db_path)
        await store.init_db()
        return store
    
    return _get_store


@pytest.fixture
def sample_graph_data():
    """Provide sample graph data for testing."""
    return {
        "scene_id": "test_scene",
        "background_node_id": "1",
        "nodes": {
            "1": {
                "id": "1",
                "serial_number": "1",
                "level": 1,
                "description": "Background scene",
                "status": "pending"
            },
            "1-1": {
                "id": "1-1",
                "serial_number": "1-1",
                "level": 2,
                "description": "Tree",
                "status": "pending"
            },
            "1-2": {
                "id": "1-2",
                "serial_number": "1-2",
                "level": 2,
                "description": "Rock",
                "status": "pending"
            },
            "1-1-1": {
                "id": "1-1-1",
                "serial_number": "1-1-1",
                "level": 3,
                "description": "Branch",
                "status": "pending"
            }
        },
        "edges": [
            {
                "from_node_id": "1",
                "to_node_id": "1-1",
                "edge_type": "tree",
                "visual_description": "grows from ground"
            },
            {
                "from_node_id": "1",
                "to_node_id": "1-2",
                "edge_type": "tree",
                "visual_description": "sits on ground"
            },
            {
                "from_node_id": "1-1",
                "to_node_id": "1-1-1",
                "edge_type": "tree",
                "visual_description": "extends from trunk"
            }
        ]
    }


@pytest.fixture
def cyclic_graph_data():
    """Provide graph data with cycles for testing cycle detection."""
    return {
        "scene_id": "cyclic_scene",
        "background_node_id": "1",
        "nodes": {
            "1": {
                "id": "1",
                "serial_number": "1",
                "level": 1,
                "description": "Background",
                "status": "pending"
            },
            "2": {
                "id": "2",
                "serial_number": "2",
                "level": 1,
                "description": "Node A",
                "status": "pending"
            },
            "3": {
                "id": "3",
                "serial_number": "3",
                "level": 1,
                "description": "Node B",
                "status": "pending"
            }
        },
        "edges": [
            {
                "from_node_id": "1",
                "to_node_id": "2",
                "edge_type": "cross",
                "visual_description": ""
            },
            {
                "from_node_id": "2",
                "to_node_id": "3",
                "edge_type": "cross",
                "visual_description": ""
            },
            {
                "from_node_id": "3",
                "to_node_id": "1",  # Creates cycle
                "edge_type": "cross",
                "visual_description": ""
            }
        ]
    }


@pytest.fixture
def mock_llm_provider():
    """Provide a mocked LLM provider for testing graph extraction."""
    mock_provider = AsyncMock()
    
    # Mock successful extraction response
    mock_response = {
        "background": {"description": "Forest background"},
        "nodes": [
            {"serial": "1", "description": "Background scene", "parent_serial": None},
            {"serial": "1-1", "description": "Tree", "parent_serial": "1"}
        ],
        "edges": [
            {"from": "1", "to": "1-1", "edge_type": "tree", "visual_description": ""}
        ]
    }
    
    mock_provider.chat_json.return_value = mock_response
    return mock_provider


@pytest.fixture
def mock_image_generator():
    """Provide a mocked ImageGenerator for testing generation."""
    mock_gen = AsyncMock()
    mock_gen.generate.return_value = None  # Successful generation
    mock_gen.close.return_value = None
    return mock_gen


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def create_knowledge_graph(scene_id: str = "test") -> KnowledgeGraph:
    """Helper to create a basic knowledge graph for testing."""
    graph = KnowledgeGraph(scene_id=scene_id)
    
    # Add background node
    graph.add_node("1", "Background scene")
    
    # Add child nodes
    graph.add_node("1-1", "Tree")
    graph.add_node("1-2", "Rock")
    
    # Add edges
    graph.add_edge("1", "1-1", "grows from ground", EdgeType.TREE)
    graph.add_edge("1", "1-2", "sits on ground", EdgeType.TREE)
    
    return graph


def create_cyclic_graph(scene_id: str = "cyclic") -> KnowledgeGraph:
    """Helper to create a cyclic knowledge graph for testing."""
    graph = KnowledgeGraph(scene_id=scene_id)
    
    graph.add_node("1", "Background")
    graph.add_node("2", "Node A")
    graph.add_node("3", "Node B")
    
    # Create cycle: 1 -> 2 -> 3 -> 1
    graph.add_edge("1", "2", "", EdgeType.CROSS)
    graph.add_edge("2", "3", "", EdgeType.CROSS)
    graph.add_edge("3", "1", "", EdgeType.CROSS)
    
    return graph
