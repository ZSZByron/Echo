"""Constraint → topology node/edge creation (breakpoint T-F / 断点F修复).

Creates Constraint nodes (id=cst_{dim}_{tag}) from DimensionResultSet
structured fields and topology edges (CROSS, RULE_* semantic labels in
visual_description) linking them to the graph's background node.

This is an in-place operation on the passed graph — the same Pydantic
model instance is returned for convenience.

Edge type semantics (from .sisyphus/drafts/A模块层级图-含断点.md L299-314):
  - RULE_SHAPES_GEO:     Constraint → Geography (rule shapes geography)
  - POWER_SATURATES_GEO:  Concept → Geography (power saturates geography)
  - POWER_SOURCES_FROM_GEO: Geography → Concept (geography sources power)

Edge types are stored as semantic labels in GraphEdge.visual_description.
The actual GraphEdge.edge_type is always EdgeType.CROSS (legal enum value).

Must NOT modify GraphNode/GraphEdge model definitions.
"""
from __future__ import annotations

from app.domains.creation.constraint.application_tree import (
    ApplicationTreeLoader,
    DIMENSIONS,
    LAYERS,
)
from app.models.dimension import DimensionResultSet
from app.models.knowledge_graph import EdgeType, GraphNode, GraphEdge, KnowledgeGraph

# Structured field names per dimension (T-B breakpoint, 21 fields total).
# Only these fields are iterated; unstructured fields (rules, actions,
# forbidden, effects, relations, style, keywords, tone, mechanism, note)
# are excluded.
STRUCTURED_FIELDS: dict[str, list[str]] = {
    "LAW": ["world_structure", "gravity", "conservation", "divine_intervention", "afterlife"],
    "ACT": ["dice_mode", "check_direction", "cost_function", "core_action"],
    "NAR": ["era_stage", "time_mode", "trajectory", "success_granularity"],
    "WST": ["cost_type", "feedback_loop", "climate_zone", "power_saturation"],
    "SOC": ["political_type", "access_topology", "threshold", "economy_type"],
    # RED has no structured fields (only forbidden list + note).
}

# Constraint level in the graph (above background level 1).
CONSTRAINT_LEVEL = 0

# Cache for the application tree loader singleton.
_tree_loader: ApplicationTreeLoader | None = None


def _get_tree_loader() -> ApplicationTreeLoader:
    """Lazily load and cache the application tree."""
    global _tree_loader
    if _tree_loader is None:
        _tree_loader = ApplicationTreeLoader()
    return _tree_loader


def _build_edge_type_map() -> dict[str, str]:
    """Build source_field -> target_edge_type mapping from application tree.

    For structured fields that appear in multiple layers, we pick the
    first (world layer) mapping. This is sufficient for A1 skeleton edges.
    """
    loader = _get_tree_loader()
    rules = loader.get_all_rules()
    seen: dict[str, str] = {}
    for rule in rules:
        field_key = rule.source_field  # e.g. "LAW.world_structure"
        if field_key not in seen:
            seen[field_key] = rule.target_edge_type
    return seen


def _field_exists(edge_type_map: dict[str, str], dim: str, tag: str) -> str | None:
    """Return the RULE_* semantic label if the (dim, tag) pair has a
    mapping in the application tree, else None."""
    key = f"{dim}.{tag}"
    return edge_type_map.get(key)


def apply_constraints(
    graph: KnowledgeGraph,
    dimension_result_set: DimensionResultSet,
    stage: str = "A1",
) -> KnowledgeGraph:
    """Create Constraint nodes and topology edges from structured fields.

    For each non-None structured field in the 6-dim DimensionResultSet:
    1. Create a Constraint node with id=cst_{dim}_{tag}.
    2. If a matching InjectionRule exists in application_tree.yaml and
       the graph has a background_node_id, create a CROSS edge from the
       constraint node to the background node. The RULE_* semantic label
       from target_edge_type is stored in visual_description formatted
       as "{stage} | {RULE_LABEL}".

    Idempotent: nodes/edges that already exist (by id / from+to+label)
    are skipped.

    Args:
        graph: Existing knowledge graph (mutated in-place, returned).
        dimension_result_set: 6-dim constraint output.
        stage: Source stage marker (e.g. "A1").

    Returns:
        The same graph instance, with new nodes/edges added.
    """
    edge_type_map = _build_edge_type_map()
    target_id = graph.background_node_id

    for dim, tags in STRUCTURED_FIELDS.items():
        output = getattr(dimension_result_set, dim, None)
        if output is None:
            continue

        for tag in tags:
            value = getattr(output, tag, None)
            if value is None:
                continue

            node_id = f"cst_{dim}_{tag}"

            # Idempotent: skip if node already exists
            if node_id in graph.nodes:
                continue

            # Create Constraint node
            graph.nodes[node_id] = GraphNode(
                id=node_id,
                serial_number=node_id,
                level=CONSTRAINT_LEVEL,
                description=f"[{stage}] Constraint({dim}.{tag}={value})",
            )

            # Create edge if target exists and rule mapping found
            if target_id is None:
                continue

            semantic_label = _field_exists(edge_type_map, dim, tag)
            if semantic_label is None:
                continue

            edge_label = f"{stage} | {semantic_label}"

            # Idempotent: skip if edge already exists
            already_exists = any(
                e.from_node_id == node_id
                and e.to_node_id == target_id
                and e.visual_description == edge_label
                for e in graph.edges
            )
            if already_exists:
                continue

            graph.edges.append(
                GraphEdge(
                    from_node_id=node_id,
                    to_node_id=target_id,
                    edge_type=EdgeType.CROSS,
                    visual_description=edge_label,
                )
            )

    return graph
