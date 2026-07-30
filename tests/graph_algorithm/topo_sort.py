"""Layered topological sort for knowledge graph-driven asset generation.

Implements Kahn's algorithm with background-first priority and serial_asc
tie-breaking for deterministic ordering. Also provides wave-based grouping
for parallel generation scheduling.
"""
from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from serial_parser import get_generation_priority

if TYPE_CHECKING:
    from models import KnowledgeGraph


def layered_topological_sort(graph: KnowledgeGraph) -> list[str]:
    """Topological sort with background node first and serial_asc tie-breaking.

    Algorithm:
    1. Place background_node_id first (level 0, regardless of in-degree).
    2. Run Kahn's algorithm on remaining nodes:
       - Compute in-degree (number of incoming edges) for each node.
       - At each step, pick the in-degree-0 node with smallest serial.
       - Decrement in-degree of successors; repeat.
    3. Uses get_generation_priority() for deterministic ordering.

    Args:
        graph: KnowledgeGraph with nodes, edges, and background_node_id.

    Returns:
        Ordered list of node IDs for generation.
    """
    bg_id = graph.background_node_id
    if not bg_id or bg_id not in graph.nodes:
        raise ValueError("Graph must have a valid background_node_id in nodes")

    # Build adjacency and in-degree for non-background nodes
    non_bg_ids = [nid for nid in graph.nodes if nid != bg_id]

    # children: node -> list of successors
    children: dict[str, list[str]] = {nid: [] for nid in non_bg_ids}
    # in_degree: node -> number of incoming edges (from non-bg sources)
    in_degree: dict[str, int] = {nid: 0 for nid in non_bg_ids}

    for edge in graph.edges:
        src, dst = edge.from_node_id, edge.to_node_id
        # Skip edges from bg (bg is already processed)
        if src == bg_id:
            # bg->dst edge: counts as dependency but bg is already done,
            # so don't count it in in_degree for Kahn's (bg is pre-processed)
            continue
        if dst == bg_id:
            # Edge pointing to background — skip (background already done)
            continue
        if src in children and dst in in_degree:
            children[src].append(dst)
            in_degree[dst] += 1

    # Initialize ready queue with in-degree-0 nodes, sorted by serial
    ready = sorted(
        (nid for nid, deg in in_degree.items() if deg == 0),
        key=lambda nid: get_generation_priority(nid, 0),
    )

    queue: deque[str] = deque(ready)
    order: list[str] = [bg_id]

    while queue:
        node_id = queue.popleft()
        order.append(node_id)

        for child in children[node_id]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

        # Re-sort remaining queue for deterministic serial ordering
        if len(queue) > 1:
            items = sorted(
                list(queue),
                key=lambda nid: get_generation_priority(nid, in_degree[nid]),
            )
            queue.clear()
            queue.extend(items)

    if len(order) != len(graph.nodes):
        raise ValueError("Graph contains a cycle — cannot produce topological order")

    return order


def get_generation_waves(graph: KnowledgeGraph) -> list[list[str]]:
    """Return generation waves for parallel scheduling.

    Wave 0: [background_node_id] — background always alone in first wave.
    Wave N (N>=1): all nodes with in-degree 0 at that step (excluding bg).

    Nodes within the same wave have no dependencies on each other and
    can be generated in parallel. Waves must be processed sequentially.

    Args:
        graph: KnowledgeGraph with nodes, edges, and background_node_id.

    Returns:
        List of waves, where each wave is a list of node IDs.
    """
    bg_id = graph.background_node_id
    if not bg_id or bg_id not in graph.nodes:
        raise ValueError("Graph must have a valid background_node_id in nodes")

    waves: list[list[str]] = [[bg_id]]

    # Build adjacency and in-degree for non-background nodes
    non_bg_ids = [nid for nid in graph.nodes if nid != bg_id]
    children: dict[str, list[str]] = {nid: [] for nid in non_bg_ids}
    in_degree: dict[str, int] = {nid: 0 for nid in non_bg_ids}

    for edge in graph.edges:
        src, dst = edge.from_node_id, edge.to_node_id
        if src == bg_id or dst == bg_id:
            continue
        if src in children and dst in in_degree:
            children[src].append(dst)
            in_degree[dst] += 1

    while non_bg_ids:
        # Collect all nodes with in-degree 0
        wave = [nid for nid in non_bg_ids if in_degree[nid] == 0]
        if not wave:
            raise ValueError("Graph contains a cycle — cannot produce waves")

        wave.sort(key=lambda nid: get_generation_priority(nid, 0))
        waves.append(wave)

        # Remove processed nodes and update in-degrees
        for nid in wave:
            non_bg_ids.remove(nid)
            for child in children[nid]:
                in_degree[child] -= 1

    return waves
