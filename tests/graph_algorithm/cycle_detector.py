"""Cycle detection using DFS three-color marking (White/Gray/Black).

White (0): unvisited
Gray  (1): on current DFS path (in progress)
Black (2): fully explored

Encountering a Gray node during DFS = cycle found.
"""

from __future__ import annotations

from models import KnowledgeGraph

WHITE, GRAY, BLACK = 0, 1, 2


def _build_adjacency(graph: KnowledgeGraph) -> dict[str, list[str]]:
    """Build directed adjacency list: node -> [successors]."""
    adj: dict[str, list[str]] = {nid: [] for nid in graph.nodes}
    for edge in graph.edges:
        adj.setdefault(edge.from_node_id, []).append(edge.to_node_id)
    return adj


def _dfs_detect(
    node: str,
    adj: dict[str, list[str]],
    color: dict[str, int],
    path: list[str],
) -> list[str] | None:
    """DFS from *node*, returns cycle path if found, else None."""
    color[node] = GRAY
    path.append(node)

    for neighbor in adj.get(node, []):
        if neighbor not in color:
            continue
        if color[neighbor] == GRAY:
            # Cycle: extract from neighbor's position in path back to neighbor
            idx = path.index(neighbor)
            cycle = path[idx:] + [neighbor]
            return cycle
        if color[neighbor] == WHITE:
            result = _dfs_detect(neighbor, adj, color, path)
            if result is not None:
                return result

    path.pop()
    color[node] = BLACK
    return None


def detect_cycle(graph: KnowledgeGraph) -> list[str] | None:
    """Detect a single cycle in the graph using DFS three-color marking.

    Returns the cycle as a list where first == last (e.g. ["A","B","C","A"]),
    or None if the graph is acyclic.
    """
    adj = _build_adjacency(graph)
    color: dict[str, int] = {nid: WHITE for nid in graph.nodes}

    for node in graph.nodes:
        if color[node] == WHITE:
            cycle = _dfs_detect(node, adj, color, [])
            if cycle is not None:
                return cycle
    return None


def find_all_cycles(graph: KnowledgeGraph) -> list[list[str]]:
    """Find all independent cycles in the graph.

    After a cycle is found, its edges are removed from consideration
    so subsequent iterations find *additional* independent cycles.
    Each returned cycle starts and ends with the same node ID.
    """
    adj = _build_adjacency(graph)
    all_cycles: list[list[str]] = []
    removed_edges: set[tuple[str, str]] = set()

    while True:
        # Build adjacency minus already-removed edges
        live_adj: dict[str, list[str]] = {nid: [] for nid in graph.nodes}
        for edge in graph.edges:
            key = (edge.from_node_id, edge.to_node_id)
            if key not in removed_edges:
                live_adj.setdefault(edge.from_node_id, []).append(edge.to_node_id)

        color: dict[str, int] = {nid: WHITE for nid in graph.nodes}
        found = False

        for node in graph.nodes:
            if color[node] == WHITE:
                cycle = _dfs_find_cycle_edges(node, live_adj, color, [])
                if cycle is not None:
                    all_cycles.append(cycle)
                    # Remove cycle edges so next iteration finds different cycles
                    for i in range(len(cycle) - 1):
                        removed_edges.add((cycle[i], cycle[i + 1]))
                    found = True
                    break

        if not found:
            break

    return all_cycles


def _dfs_find_cycle_edges(
    node: str,
    adj: dict[str, list[str]],
    color: dict[str, int],
    path: list[str],
) -> list[str] | None:
    """DFS variant that returns cycle path (same contract as _dfs_detect)."""
    color[node] = GRAY
    path.append(node)

    for neighbor in adj.get(node, []):
        if neighbor not in color:
            continue
        if color[neighbor] == GRAY:
            idx = path.index(neighbor)
            return path[idx:] + [neighbor]
        if color[neighbor] == WHITE:
            result = _dfs_find_cycle_edges(neighbor, adj, color, path)
            if result is not None:
                return result

    path.pop()
    color[node] = BLACK
    return None


def validate_graph(graph: KnowledgeGraph) -> tuple[bool, list[list[str]]]:
    """Validate graph for cycles.

    Returns:
        (is_valid, cycles) where is_valid is True iff no cycles exist,
        and cycles is a list of all independent cycle paths found.
    """
    cycles = find_all_cycles(graph)
    return (len(cycles) == 0, cycles)
