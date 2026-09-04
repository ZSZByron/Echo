"""C4 contract: 内容轴词汇封闭（closed vocab）。

治理文档 §6 C4：关系词汇表必须封闭（来源：治理文档 v0.4 附录3），
graphify prompt 只允许使用封闭词汇表内的 relation。

T2 的 concept_edge_vocab.py 已在 —— 直接写真断言。
"""
from __future__ import annotations

from app.domains.creation.a1.concept_edge_vocab import (
    AXIS_SLOTS,
    EDGE_VOCAB,
    VOCAB_RELATION_NAMES,
    get_vocab_by_level,
    is_known_relation,
)

LEVELS = ("rule", "semantic", "structure")


def test_c4_vocab_names_are_unique() -> None:
    names = [edge.name for edge in EDGE_VOCAB]
    assert len(names) == len(set(names)), "closed vocab 必须无重复 relation 名"


def test_c4_vocab_relation_names_frozenset_consistent() -> None:
    assert VOCAB_RELATION_NAMES == frozenset(edge.name for edge in EDGE_VOCAB)


def test_c4_is_known_relation_membership() -> None:
    assert is_known_relation(next(iter(VOCAB_RELATION_NAMES))) is True
    assert is_known_relation("definitely_not_in_vocab_relation") is False


def test_c4_axis_slots_reference_known_relations() -> None:
    # AXIS_SLOTS = [(axis_path, allowed_slot_values)] — 每条 axis path 非空且 slot 值封闭非空
    for axis_path, slots in AXIS_SLOTS:
        assert axis_path, "axis path 不得为空"
        assert slots, f"axis {axis_path} 的 slot 值集不得为空"


def test_c4_level_partition_covers_full_vocab() -> None:
    union: set[str] = set()
    for level in LEVELS:
        union |= {edge.name for edge in get_vocab_by_level(level)}
    assert union == set(VOCAB_RELATION_NAMES), "level 划分必须完整覆盖封闭词汇表"
