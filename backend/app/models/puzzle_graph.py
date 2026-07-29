"""Puzzle dependency graph with topological solving order.

Independent from SceneGraph — handles only puzzle logic dependencies
(clue → consumable → reward → obstacle).
"""
from __future__ import annotations

from collections import deque
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_SCENES_DIR = _PROJECT_ROOT / "data" / "scenes"


class PuzzleNodeType(str, Enum):
    CLUE = "clue"
    CONSUMABLE = "consumable"
    REWARD = "reward"
    OBSTACLE = "obstacle"


class PuzzleNode(BaseModel):
    """Single node in the puzzle dependency chain."""

    id: str
    type: PuzzleNodeType
    requires: list[str]  # puzzle node IDs required before this node
    produces: str  # abstract item produced (ritual_knowledge, quantum_key, etc.)
    interaction: str  # player action type (search, read, perform_ritual, etc.)


class PuzzleGraph(BaseModel):
    """Puzzle dependency graph with topologically sorted solving order."""

    scene_id: str
    nodes: dict[str, PuzzleNode]
    chain: list[str]  # topologically sorted node IDs

    @classmethod
    def from_yaml(cls, scene_id: str) -> PuzzleGraph:
        """Build from data/scenes/{scene_id}.yaml puzzle_chain section."""
        path = _SCENES_DIR / f"{scene_id}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Scene YAML not found: {path}")

        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f)

        puzzle_chain = data.get("puzzle_chain", [])
        if not puzzle_chain:
            raise ValueError(f"No puzzle_chain in {scene_id}.yaml")

        nodes: dict[str, PuzzleNode] = {}
        for node_data in puzzle_chain:
            node_id = node_data["node_id"]
            nodes[node_id] = PuzzleNode(
                id=node_id,
                type=PuzzleNodeType(node_data["type"]),
                requires=node_data.get("requires", []),
                produces=node_data["produces"],
                interaction=node_data["interaction"],
            )

        chain = _topological_sort(nodes)

        return cls(
            scene_id=scene_id,
            nodes=nodes,
            chain=chain,
        )


def _resolve_requires(
    node: PuzzleNode, nodes: dict[str, PuzzleNode]
) -> list[str]:
    """Resolve requires to actual node IDs.

    requires may contain either a node ID or a produced item name.
    If not a direct node ID, look up which node produces that item.
    """
    resolved: list[str] = []
    for req in node.requires:
        if req in nodes:
            resolved.append(req)
        else:
            # Find node that produces this item
            for other_id, other_node in nodes.items():
                if other_node.produces == req:
                    resolved.append(other_id)
                    break
    return resolved


def _topological_sort(nodes: dict[str, PuzzleNode]) -> list[str]:
    """Kahn's algorithm with puzzle type priority (clue→consumable→reward→obstacle)."""
    children: dict[str, list[str]] = {nid: [] for nid in nodes}
    indegree: dict[str, int] = {nid: 0 for nid in nodes}

    for nid, node in nodes.items():
        for req_id in _resolve_requires(node, nodes):
            children[req_id].append(nid)
            indegree[nid] += 1

    # Priority: type order then node ID for stable sorting
    type_order = {
        PuzzleNodeType.CLUE: 0,
        PuzzleNodeType.CONSUMABLE: 1,
        PuzzleNodeType.REWARD: 2,
        PuzzleNodeType.OBSTACLE: 3,
    }

    ready = sorted(
        (nid for nid, deg in indegree.items() if deg == 0),
        key=lambda nid: (type_order[nodes[nid].type], nid),
    )

    order: list[str] = []
    queue: deque[str] = deque(ready)

    while queue:
        node = queue.popleft()
        order.append(node)

        newly_ready = []
        for child in children[node]:
            indegree[child] -= 1
            if indegree[child] == 0:
                newly_ready.append(child)

        if newly_ready:
            newly_ready.sort(key=lambda nid: (type_order[nodes[nid].type], nid))
            queue.extend(newly_ready)

    if len(order) != len(nodes):
        raise ValueError("Puzzle graph has cycles")

    return order
