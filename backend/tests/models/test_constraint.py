"""Unit tests for constraint models."""

import pytest

from app.models.constraint import ConstraintNode, ConstraintTree, ConstraintType


def test_constraint_type_enum() -> None:
    """Test ConstraintType enum values."""
    assert ConstraintType.HARD.value == "hard"
    assert ConstraintType.SOFT.value == "soft"


def test_constraint_node_priority_default() -> None:
    """Test ConstraintNode priority defaults to 0."""
    n = ConstraintNode(id="c1", type=ConstraintType.SOFT, rule="prefer wood")
    assert n.priority == 0


def test_constraint_global_scene_id_none() -> None:
    """Test global constraint has scene_id=None."""
    t = ConstraintTree(id="global", name="Global")
    assert t.scene_id is None


def test_constraint_instantiation() -> None:
    """Test ConstraintTree complete serialization round-trip."""
    n = ConstraintNode(id="c1", type=ConstraintType.HARD, rule="no metal")
    t = ConstraintTree(id="t1", name="Temple", nodes=[n], scene_id="temple_ruins")
    j = t.model_dump_json()
    t2 = ConstraintTree.model_validate_json(j)
    assert t2.nodes[0].type == ConstraintType.HARD
    assert t2.scene_id == "temple_ruins"
