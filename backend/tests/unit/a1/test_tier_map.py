"""C5: tier mapping contract tests — full 10-module coverage, tier range [0,6]."""
from __future__ import annotations

from app.domains.creation.a1.tier_map import (
    MAX_TIER,
    MIN_TIER,
    TIER_MAP,
    module_tier_coverage,
)
from app.domains.creation.seed.a1_question_tree import module_ids
from app.models.knowledge_graph import GraphNode


def test_tier_map_keys_match_module_ids() -> None:
    """TIER_MAP key set must equal the authoritative module_ids() set (verbatim Chinese ids)."""
    assert set(TIER_MAP) == set(module_ids())


def test_tier_map_full_coverage_no_extra() -> None:
    """Exactly 10 modules, no 11th module tier (closed set)."""
    assert len(TIER_MAP) == 10
    assert len(module_ids()) == 10


def test_tier_values_within_range() -> None:
    """All tier values within [0, 6]."""
    for module_id, tier in TIER_MAP.items():
        assert MIN_TIER <= tier <= MAX_TIER, f"{module_id} tier={tier} out of range"


def test_module_tier_coverage_helper() -> None:
    """Coverage assertion helper passes and returns no missing ids."""
    assert module_tier_coverage() == []


def test_graph_node_backward_compat_without_tier() -> None:
    """Legacy node dict without tier deserializes fine with tier=None."""
    node = GraphNode.model_validate(
        {"id": "n1", "serial_number": "1-1", "level": 2, "description": "legacy"}
    )
    assert node.tier is None


def test_graph_node_accepts_tier() -> None:
    """New nodes can carry a tier value."""
    node = GraphNode(id="n2", serial_number="1-2", level=2, tier=4)
    assert node.tier == 4
