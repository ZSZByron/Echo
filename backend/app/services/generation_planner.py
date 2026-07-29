"""Planning middle layer for LOD-aware asset generation.

Orchestrates SceneGraph + PuzzleGraph + PromptBuilder to create ordered
generation plans with proper LOD awareness and reference asset selection.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Dict, List

from pydantic import BaseModel

from app.models.puzzle_graph import PuzzleGraph
from app.models.scene_graph import SceneGraph


# Depth field from YAML -> LOD level
_DEPTH_TO_LOD: Dict[str, str] = {
    "near": "near",
    "mid": "mid",
    "mid_far": "far",
    "far": "far",
}

# LOD -> sort priority (lower = generated first)
_LOD_PRIORITY: Dict[str, int] = {"near": 0, "mid": 1, "far": 2, "bg": 3}


class AssetGenerationSpec(BaseModel):
    """Generation specification for a single asset."""

    asset_id: str
    lod_level: str | None = None  # "near" | "mid" | "far" | None for bg
    prompt: str
    reference_asset_ids: List[str]


class GenerationPlan(BaseModel):
    """Complete generation plan for a scene."""

    scene_id: str
    order: List[str]  # Ordered asset IDs for generation
    specs: Dict[str, AssetGenerationSpec]  # asset_id -> spec


class GenerationPlanner:
    """Planning middle layer for LOD-aware asset generation.

    Combines SceneGraph (spatial dependencies) + PuzzleGraph (puzzle
    dependencies) into a single generation order with LOD priority,
    reference selection, and per-asset prompts.

    Does NOT call the image generator -- planning only, not execution.
    """

    def __init__(self) -> None:
        pass

    def create_plan(self, scene_id: str) -> GenerationPlan:
        """Create generation plan combining SceneGraph + PuzzleGraph + LOD awareness.

        Process:
        1. Load SceneGraph for spatial dependencies
        2. Load PuzzleGraph for puzzle dependencies
        3. Combine dependencies with LOD priority
        4. Select reference_asset_ids for each asset
        5. Select appropriate prompts for LOD level
        """
        scene_graph = SceneGraph.from_yaml(scene_id)
        puzzle_graph = PuzzleGraph.from_yaml(scene_id)

        combined_deps = self._build_combined_dependencies(scene_graph, puzzle_graph)
        order = self._lod_aware_topological_sort(combined_deps, scene_graph)

        specs: Dict[str, AssetGenerationSpec] = {}
        for asset_id in order:
            specs[asset_id] = self._create_spec(asset_id, scene_graph, combined_deps)

        return GenerationPlan(
            scene_id=scene_id,
            order=order,
            specs=specs,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_combined_dependencies(
        self, scene_graph: SceneGraph, puzzle_graph: PuzzleGraph
    ) -> Dict[str, List[str]]:
        """Combine spatial (style_sources) and puzzle dependencies."""
        combined: Dict[str, List[str]] = {}

        # Start with spatial dependencies from SceneGraph
        for asset_id, style_sources in scene_graph.style_sources.items():
            combined[asset_id] = list(style_sources)

        # Add puzzle dependencies (nodes that must be generated before)
        for node_id, node in puzzle_graph.nodes.items():
            asset_id = f"{scene_graph.scene_id}_{node_id}"
            if asset_id not in combined:
                combined[asset_id] = []

            for req in node.requires:
                resolved_id = self._resolve_puzzle_requirement(req, puzzle_graph)
                req_asset_id = f"{scene_graph.scene_id}_{resolved_id}"
                if req_asset_id not in combined[asset_id]:
                    combined[asset_id].append(req_asset_id)

        return combined

    @staticmethod
    def _resolve_puzzle_requirement(req: str, puzzle_graph: PuzzleGraph) -> str:
        """Resolve a puzzle requirement to a node ID.

        The requirement may be a direct node ID or a produced item name.
        """
        if req in puzzle_graph.nodes:
            return req
        for nid, node in puzzle_graph.nodes.items():
            if node.produces == req:
                return nid
        return req  # fallback

    def _lod_aware_topological_sort(
        self, combined_deps: Dict[str, List[str]], scene_graph: SceneGraph
    ) -> List[str]:
        """Topological sort with LOD priority: near -> mid -> far -> bg.

        Background is always placed last regardless of dependency order.
        """
        depth_map = self._load_depth_map(scene_graph.scene_id)
        bg_id = f"{scene_graph.scene_id}_bg"

        def get_lod(asset_id: str) -> str:
            node_id = asset_id.replace(f"{scene_graph.scene_id}_", "", 1)
            depth = depth_map.get(node_id)
            if depth:
                return _DEPTH_TO_LOD.get(depth, "mid")
            return "mid"

        # Separate bg -- it is always appended last
        object_deps = {k: v for k, v in combined_deps.items() if k != bg_id}

        # Build Kahn's algorithm structure (objects only)
        all_ids = set(object_deps.keys())
        for deps in object_deps.values():
            all_ids.update(d for d in deps if d in object_deps)

        children: Dict[str, List[str]] = {aid: [] for aid in all_ids}
        indegree: Dict[str, int] = {aid: 0 for aid in all_ids}

        for asset_id, deps in object_deps.items():
            for dep in deps:
                if dep in children:
                    children[dep].append(asset_id)
                    indegree[asset_id] += 1

        ready = sorted(
            (aid for aid, deg in indegree.items() if deg == 0),
            key=lambda aid: (_LOD_PRIORITY.get(get_lod(aid), 1), aid),
        )

        order: List[str] = []
        queue: deque[str] = deque(ready)

        while queue:
            asset_id = queue.popleft()
            order.append(asset_id)

            for child in children[asset_id]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)

            if len(queue) > 1:
                items = sorted(
                    list(queue),
                    key=lambda aid: (_LOD_PRIORITY.get(get_lod(aid), 1), aid),
                )
                queue.clear()
                queue.extend(items)

        if len(order) != len(object_deps):
            raise ValueError("Generation plan has circular dependencies")

        # BG is always last
        if bg_id in combined_deps:
            order.append(bg_id)

        return order

    def _create_spec(
        self,
        asset_id: str,
        scene_graph: SceneGraph,
        combined_deps: Dict[str, List[str]],
    ) -> AssetGenerationSpec:
        """Create generation spec for a single asset."""
        if asset_id.endswith("_bg"):
            lod_level: str | None = None
        else:
            lod_level = "mid"  # default; refined when Asset.views is implemented

        ref_assets = combined_deps.get(asset_id, [])

        # Placeholder prompt -- PromptBuilder integration in later task
        prompt = f"Generate {asset_id}"

        return AssetGenerationSpec(
            asset_id=asset_id,
            lod_level=lod_level,
            prompt=prompt,
            reference_asset_ids=ref_assets,
        )

    @staticmethod
    def _load_depth_map(scene_id: str) -> Dict[str, str]:
        """Load node_id -> depth mapping from scene YAML."""
        from pathlib import Path

        import yaml

        project_root = Path(__file__).resolve().parent.parent.parent.parent
        path = project_root / "data" / "scenes" / f"{scene_id}.yaml"
        if not path.exists():
            return {}

        with open(path, encoding="utf-8") as f:
            data: Any = yaml.safe_load(f)

        depth_map: Dict[str, str] = {}
        for obj in data.get("accessible_objects", []):
            if "id" in obj and "depth" in obj:
                depth_map[obj["id"]] = obj["depth"]
        return depth_map
