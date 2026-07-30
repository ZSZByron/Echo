"""Knowledge graph data model for graph-driven asset pipeline.

Defines GraphNode, GraphEdge, and KnowledgeGraph with level parsing,
dependency queries, and serialization.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional


from pydantic import BaseModel, Field


class NodeStatus(str, Enum):
    """Lifecycle status of a graph node."""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class EdgeType(str, Enum):
    """Type of edge between nodes."""

    TREE = "tree"  # parent-child in hierarchy
    CROSS = "cross"  # cross-reference / visual dependency


class GraphNode(BaseModel):
    """Single node in the knowledge graph.

    Attributes:
        id: Unique node identifier derived from serial_number.
        serial_number: Hierarchical serial like "1-1-1".
        level: Depth level (1-indexed by segment count).
        description: Visual description of the asset.
        status: Current lifecycle status.
    """

    id: str
    serial_number: str
    level: int
    description: str = ""
    status: NodeStatus = NodeStatus.PENDING


class GraphEdge(BaseModel):
    """Directed edge between two nodes.

    Attributes:
        from_node_id: Source node ID.
        to_node_id: Target node ID.
        edge_type: Tree (hierarchy) or cross (visual dependency).
        visual_description: User-written visual relationship description.
    """

    from_node_id: str
    to_node_id: str
    edge_type: EdgeType = EdgeType.TREE
    visual_description: str = ""


class KnowledgeGraph(BaseModel):
    """Knowledge graph for a scene with nodes, edges, and queries.

    Attributes:
        scene_id: Scene this graph belongs to.
        nodes: Dict of node_id -> GraphNode.
        edges: List of GraphEdge.
        background_node_id: ID of the background root node (level 1).
    """

    scene_id: str
    nodes: dict[str, GraphNode] = Field(default_factory=dict)
    edges: list[GraphEdge] = Field(default_factory=list)
    background_node_id: Optional[str] = None

    @staticmethod
    def _parse_level(serial_number: str) -> int:
        """Parse level from serial number.

        "1" -> 1, "1-1" -> 2, "1-1-1" -> 3, etc.
        """
        if not serial_number:
            return 0
        return serial_number.count("-") + 1

    def add_node(
        self, serial: str, description: str = ""
    ) -> GraphNode:
        """Add a node with auto-parsed level.

        Args:
            serial: Hierarchical serial number (e.g. "1-1-1").
            description: Visual description of the asset.

        Returns:
            The created GraphNode.
        """
        level = self._parse_level(serial)
        node = GraphNode(
            id=serial,
            serial_number=serial,
            level=level,
            description=description,
        )
        self.nodes[serial] = node

        # Auto-detect background (first added, level 1)
        if self.background_node_id is None and level == 1:
            self.background_node_id = serial

        return node

    def add_edge(
        self,
        from_id: str,
        to_id: str,
        visual_desc: str = "",
        edge_type: EdgeType = EdgeType.TREE,
    ) -> GraphEdge:
        """Add an edge between two nodes.

        Args:
            from_id: Source node ID.
            to_id: Target node ID.
            visual_desc: Visual relationship description.
            edge_type: Tree or cross edge.

        Returns:
            The created GraphEdge.
        """
        edge = GraphEdge(
            from_node_id=from_id,
            to_node_id=to_id,
            edge_type=edge_type,
            visual_description=visual_desc,
        )
        self.edges.append(edge)
        return edge

    def get_dependencies(self, node_id: str) -> list[str]:
        """Return all source node IDs for incoming edges to this node."""
        return [e.from_node_id for e in self.edges if e.to_node_id == node_id]

    def get_dependents(self, node_id: str) -> list[str]:
        """Return all target node IDs for outgoing edges from this node."""
        return [e.to_node_id for e in self.edges if e.from_node_id == node_id]

    def to_dict(self) -> dict:
        """Serialize knowledge graph to dict."""
        return {
            "scene_id": self.scene_id,
            "background_node_id": self.background_node_id,
            "nodes": {
                nid: {
                    "id": n.id,
                    "serial_number": n.serial_number,
                    "level": n.level,
                    "description": n.description,
                    "status": n.status.value,
                }
                for nid, n in self.nodes.items()
            },
            "edges": [
                {
                    "from_node_id": e.from_node_id,
                    "to_node_id": e.to_node_id,
                    "edge_type": e.edge_type.value,
                    "visual_description": e.visual_description,
                }
                for e in self.edges
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> KnowledgeGraph:
        """Deserialize knowledge graph from dict."""
        graph = cls(
            scene_id=data["scene_id"],
            background_node_id=data.get("background_node_id"),
        )

        for nid, ndata in data.get("nodes", {}).items():
            node = GraphNode(
                id=ndata["id"],
                serial_number=ndata["serial_number"],
                level=ndata["level"],
                description=ndata.get("description", ""),
                status=NodeStatus(ndata.get("status", "pending")),
            )
            graph.nodes[nid] = node

        for edata in data.get("edges", []):
            edge = GraphEdge(
                from_node_id=edata["from_node_id"],
                to_node_id=edata["to_node_id"],
                edge_type=EdgeType(edata.get("edge_type", "tree")),
                visual_description=edata.get("visual_description", ""),
            )
            graph.edges.append(edge)

        return graph
