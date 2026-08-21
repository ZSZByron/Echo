"""Constraint application tree (breakpoint C).

Connects the 6-dimension constraint system to the generation pipeline:
a 6-dim x 6-layer (36-rule) injection mapping table loaded from
``app/config/application_tree.yaml``.

Rule fields (verbatim from hierarchy diagram, breakpoint C section):
    source_field / target_prompt_layer / target_node_field /
    target_edge_type / transform / priority

This table is the mapping data source for T-F (constraint -> topology edges).
"""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

# 6 constraint dimensions (RED/LAW/ACT/NAR/WST/SOC)
DIMENSIONS: tuple[str, ...] = ("RED", "LAW", "ACT", "NAR", "WST", "SOC")

# 6 creation layers (must mirror weight_matrix.yaml row keys)
LAYERS: tuple[str, ...] = (
    "world",
    "region",
    "scene",
    "campaign",
    "npc",
    "asset",
)

# PromptBuilder 8 layers (asset/prompt_builder.py)
PROMPT_LAYERS: frozenset[str] = frozenset(
    {
        "world",
        "location",
        "camera",
        "subject",
        "gameplay",
        "interaction",
        "material",
        "lighting",
    }
)

# Legal target_node_field values: real GraphNode / GraphEdge fields
# (app/models/knowledge_graph.py) — never invent fields.
LEGAL_NODE_FIELDS: frozenset[str] = frozenset(
    {
        # GraphNode
        "id",
        "serial_number",
        "level",
        "description",
        "status",
        # GraphEdge
        "from_node_id",
        "to_node_id",
        "edge_type",
        "visual_description",
    }
)

DEFAULT_YAML_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "application_tree.yaml"
)


class InjectionRule(BaseModel):
    """One constraint-dimension -> generation-layer injection mapping."""

    source_field: str  # e.g. "LAW.world_structure"
    target_prompt_layer: str  # e.g. "World"
    target_node_field: str  # e.g. "Geography.vertical_layer"
    target_edge_type: str  # e.g. "GEO_ABOVE"
    transform: str  # e.g. "map_to_vertical_layer_enum"
    priority: int = Field(ge=1)  # injection priority within the layer

    # Derived (not stored in YAML): dimension from source_field prefix,
    # layer assigned by the YAML section the rule lives under.
    dimension: str = ""
    layer: str = ""


class ApplicationTreeLoader:
    """Load and validate the constraint application tree YAML."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else DEFAULT_YAML_PATH
        self._rules: list[InjectionRule] = []
        self._load()

    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(f"application tree not found: {self.path}")
        data = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("application tree root must be a mapping")

        missing_layers = [l for l in LAYERS if l not in data]
        if missing_layers:
            raise ValueError(f"missing layers: {missing_layers}")

        rules: list[InjectionRule] = []
        for layer, entries in data.items():
            if layer not in LAYERS:
                raise ValueError(f"unknown layer: {layer!r}")
            for entry in entries:
                rule = InjectionRule.model_validate(entry)
                rule.dimension = rule.source_field.split(".", 1)[0]
                rule.layer = layer
                rules.append(rule)

        self._validate(rules)
        self._rules = rules

    def _validate(self, rules: list[InjectionRule]) -> None:
        # Dimension completeness
        for dim in DIMENSIONS:
            if not any(r.dimension == dim for r in rules):
                raise ValueError(f"missing dimension in application tree: {dim}")

        # Exact completeness: 6 dims x 6 layers, no duplicates
        pairs = [(r.dimension, r.layer) for r in rules]
        if len(pairs) != len(set(pairs)):
            raise ValueError("duplicate (dimension, layer) rule in application tree")
        expected = {(d, l) for d in DIMENSIONS for l in LAYERS}
        if set(pairs) != expected:
            raise ValueError(
                f"application tree must contain exactly 36 rules "
                f"(6 dims x 6 layers); missing: {sorted(expected - set(pairs))}"
            )

        # Field legality
        for r in rules:
            if r.dimension not in DIMENSIONS:
                raise ValueError(f"unknown dimension: {r.dimension!r}")
            if r.target_prompt_layer not in PROMPT_LAYERS:
                raise ValueError(
                    f"illegal target_prompt_layer: {r.target_prompt_layer!r}"
                )
            if r.target_node_field not in LEGAL_NODE_FIELDS:
                raise ValueError(
                    f"illegal target_node_field: {r.target_node_field!r} "
                    f"(must be a real GraphNode/GraphEdge field)"
                )

        # Priority uniqueness within each layer
        by_layer: dict[str, list[int]] = {}
        for r in rules:
            by_layer.setdefault(r.layer, []).append(r.priority)
        for layer, priorities in by_layer.items():
            if len(priorities) != len(set(priorities)):
                raise ValueError(f"duplicate priority in layer {layer!r}")

    # ------------------------------------------------------------------
    def get_all_rules(self) -> list[InjectionRule]:
        return list(self._rules)

    def get_injections(self, layer: str) -> list[InjectionRule]:
        """Return injection rules for a creation layer, sorted by priority."""
        if layer not in LAYERS:
            raise ValueError(
                f"unknown layer: {layer!r} (expected one of {list(LAYERS)})"
            )
        rules = [r for r in self._rules if r.layer == layer]
        return sorted(rules, key=lambda r: r.priority)
