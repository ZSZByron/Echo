"""Layered topological sort for graph-driven asset generation.

Detail-first ordering: nodes with no outgoing edges (nothing left to
depend on) are generated first. Background node is generated last
because it depends on everything else.

Edge semantics: A→B means "A depends on B's generated image".
Out-degree = number of unresolved dependencies. Out-degree 0 = ready.
"""
from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from serial_parser import get_generation_priority

if TYPE_CHECKING:
    from models import KnowledgeGraph


def layered_topological_sort(graph: KnowledgeGraph) -> list[str]:
    """Detail-first topological sort — leaves first, background last.

    Edge A→B: A depends on B. B must be generated before A.
    A node is ready when its out-degree reaches 0 (all dependencies resolved).

    Background is NOT special-cased — it participates in the same
    out-degree elimination as every other node. It ends up last because
    it typically has the most dependencies.

    Args:
        graph: KnowledgeGraph with nodes, edges, and background_node_id.

    Returns:
        Ordered list of node IDs — deepest leaves first, background last.
    """
    bg_id = graph.background_node_id
    if not bg_id or bg_id not in graph.nodes:
        raise ValueError("Graph must have a valid background_node_id in nodes")

    # Build out-degree and predecessor map for ALL nodes (including bg)
    out_degree: dict[str, int] = {nid: 0 for nid in graph.nodes}
    predecessors: dict[str, list[str]] = {nid: [] for nid in graph.nodes}

    for edge in graph.edges:
        src, dst = edge.from_node_id, edge.to_node_id
        if src in out_degree and dst in predecessors:
            out_degree[src] += 1
            predecessors[dst].append(src)

    # Ready = out-degree 0 (no unresolved dependencies)
    ready = sorted(
        (nid for nid in graph.nodes if out_degree[nid] == 0),
        key=lambda nid: get_generation_priority(nid, 0),
    )

    queue: deque[str] = deque(ready)
    order: list[str] = []

    while queue:
        node_id = queue.popleft()
        order.append(node_id)

        # This node is resolved; decrement out-degree of dependents
        for dep_id in predecessors[node_id]:
            out_degree[dep_id] -= 1
            if out_degree[dep_id] == 0:
                queue.append(dep_id)

        # Re-sort for deterministic serial ordering
        if len(queue) > 1:
            items = sorted(
                list(queue),
                key=lambda nid: get_generation_priority(nid, 0),
            )
            queue.clear()
            queue.extend(items)

    if len(order) != len(graph.nodes):
        raise ValueError("Graph contains a cycle — cannot produce topological order")

    return order


def get_generation_waves(graph: KnowledgeGraph) -> list[list[str]]:
    """Detail-first generation waves — background naturally in the last wave.

    Wave 0: nodes with out-degree 0 (no dependencies).
    Wave N: nodes whose dependencies are all in earlier waves.

    Background participates normally — no special-casing.

    Args:
        graph: KnowledgeGraph with nodes, edges, and background_node_id.

    Returns:
        List of waves, each a list of node IDs.
    """
    bg_id = graph.background_node_id
    if not bg_id or bg_id not in graph.nodes:
        raise ValueError("Graph must have a valid background_node_id in nodes")

    # Build out-degree and predecessor map for ALL nodes
    out_degree: dict[str, int] = {nid: 0 for nid in graph.nodes}
    predecessors: dict[str, list[str]] = {nid: [] for nid in graph.nodes}

    for edge in graph.edges:
        src, dst = edge.from_node_id, edge.to_node_id
        if src in out_degree and dst in predecessors:
            out_degree[src] += 1
            predecessors[dst].append(src)

    remaining = list(graph.nodes)
    waves: list[list[str]] = []

    while remaining:
        # All nodes with out-degree 0 (all dependencies resolved)
        wave = [nid for nid in remaining if out_degree[nid] == 0]
        if not wave:
            raise ValueError("Graph contains a cycle — cannot produce waves")

        wave.sort(key=lambda nid: get_generation_priority(nid, 0))
        waves.append(wave)

        for nid in wave:
            remaining.remove(nid)
            for dep_id in predecessors[nid]:
                out_degree[dep_id] -= 1

    return waves
