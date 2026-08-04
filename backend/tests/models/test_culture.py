"""Tests for CultureTree models."""

from app.models.culture import CultureNode, CultureTree


def test_culture_recursive_nesting():
    """Test CultureNode recursive structure serialization round-trip"""
    child = CultureNode(id='c1', name='Child', description='d')
    root = CultureNode(id='root', name='Root', description='d', child_nodes=[child])
    tree = CultureTree(id='t1', name='Tree', root=root)
    j = tree.model_dump_json()
    t2 = CultureTree.model_validate_json(j)
    assert t2.root.child_nodes[0].id == 'c1'


def test_culture_default_empty_lists():
    """Test all list fields default to empty lists"""
    n = CultureNode(id='n', name='n', description='d')
    assert n.values == []
    assert n.aesthetic_principles == []
    assert n.child_nodes == []
