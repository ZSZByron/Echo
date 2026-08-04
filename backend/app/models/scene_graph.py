"""Scene graph with topological generation order via Kahn's algorithm."""
from __future__ import annotations

from collections import deque
from typing import Any

import yaml
from pydantic import BaseModel

from app.config.paths import SCENES_DIR as _SCENES_DIR


class AssetInfo(BaseModel):
    """Minimal node in the scene graph."""
    id: str
    name: str
    type: str  # background | object
    status: str
    is_future_anchor: bool = False


class SceneGraph(BaseModel):
    """Scene dependency graph with topologically sorted generation order."""
    scene_id: str
    nodes: dict[str, AssetInfo]
    generation_order: list[str]
    style_sources: dict[str, list[str]]

    @classmethod
    def from_yaml(cls, scene_id: str) -> "SceneGraph":
        """Build from data/scenes/{scene_id}.yaml."""
        path = _SCENES_DIR / f"{scene_id}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Scene YAML not found: {path}")

        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f)

        bg_id = f"{scene_id}_bg"
        nodes: dict[str, AssetInfo] = {
            bg_id: AssetInfo(
                id=bg_id,
                name=data.get("name", scene_id),
                type="background",
                status="pending",
            )
        }
        style_sources: dict[str, list[str]] = {bg_id: []}

        for obj in data.get("accessible_objects", []):
            obj_asset_id = f"{scene_id}_{obj['id']}"
            nodes[obj_asset_id] = AssetInfo(
                id=obj_asset_id,
                name=obj.get("name", obj["id"]),
                type="object",
                status="pending",
                is_future_anchor=obj.get("is_future_anchor", False),
            )
            style_sources[obj_asset_id] = [bg_id]

        # Build adjacency for Kahn's algorithm
        children: dict[str, list[str]] = {nid: [] for nid in nodes}
        indegree: dict[str, int] = {nid: 0 for nid in nodes}
        for nid in nodes:
            for src in style_sources.get(nid, []):
                if src in children:
                    children[src].append(nid)
                    indegree[nid] += 1

        generation_order = _kahn_sort(nodes, children, indegree)

        return cls(
            scene_id=scene_id,
            nodes=nodes,
            generation_order=generation_order,
            style_sources=style_sources,
        )


def _kahn_sort(
    nodes: dict[str, AssetInfo],
    children: dict[str, list[str]],
    indegree: dict[str, int],
) -> list[str]:
    """Kahn's topological sort with anchor priority."""
    ready = deque(
        sorted(
            (nid for nid, deg in indegree.items() if deg == 0),
            key=lambda nid: (not nodes[nid].is_future_anchor, nid),
        )
    )
    order: list[str] = []
    visited = 0
    while ready:
        node = ready.popleft()
        order.append(node)
        visited += 1
        for child in children.get(node, []):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                # Reorder: anchors first
                if len(ready) > 1:
                    items = sorted(ready, key=lambda nid: (not nodes[nid].is_future_anchor, nid))
                    ready.clear()
                    ready.extend(items)

    if visited != len(nodes):
        raise ValueError(f"Cycle detected: visited {visited}/{len(nodes)} nodes")
    return order
