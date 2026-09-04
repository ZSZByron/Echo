"""SIR contract (graphify five fields) unit tests.

Contract source: docs/governance/2-A1-v0.5-内容图谱化统一模型与契约.md §4
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domains.creation.a1.graphify import (
    GRAPHIFY_TIMEOUT,
    AnchorEntries,
    EdgeSpec,
    EntryItem,
    GraphifyResult,
    OpenQuestions,
    dedupe_items,
    depth_id,
    parse_depth_id,
    sanitize_title,
    validate_anchors,
    validate_children_depth,
    validate_constraint_fields,
    validate_relations,
)
from app.domains.creation.graph.constraint_topology import STRUCTURED_FIELDS
from app.domains.creation.seed.a1_question_tree import all_subfield_keys


# =============================================================================
# QA Scenario 1: legal payload round-trip
# =============================================================================


class TestRoundTrip:
    def test_legal_payload_parses(self) -> None:
        payload = {
            "module_summaries": {"力量体系": "力量源于脉轮共鸣"},
            "entries": [
                {
                    "anchor": "力量体系.source",
                    "items": [
                        {"title": "脉轮共鸣", "content": "力量来源"},
                        {"title": "枯竭症", "content": "代价"},
                    ],
                }
            ],
            "edges": [
                {
                    "from": "term:脉轮共鸣",
                    "to": "term:枯竭症",
                    "relation": "导致",
                    "rationale": "过度汲取引发枯竭",
                    "confidence": "semantic",
                }
            ],
            "constraint_fields": {"LAW.conservation": "力量守恒"},
            "open_questions": [{"question": "力量可以储存吗？"}],
        }
        result = GraphifyResult.model_validate(payload)
        assert result.success is True
        assert result.module_summaries == {"力量体系": "力量源于脉轮共鸣"}
        assert result.entries[0].anchor == "力量体系.source"
        assert [i.title for i in result.entries[0].items] == ["脉轮共鸣", "枯竭症"]
        assert result.edges[0].from_ == "term:脉轮共鸣"
        assert result.edges[0].relation == "导致"
        assert result.constraint_fields == {"LAW.conservation": "力量守恒"}
        assert result.open_questions[0].question == "力量可以储存吗？"

    def test_missing_fields_default_to_empty(self) -> None:
        result = GraphifyResult()
        assert result.module_summaries == {}
        assert result.entries == []
        assert result.edges == []
        assert result.constraint_fields == {}
        assert result.open_questions == []

    def test_edge_accepts_from_keyword(self) -> None:
        edge = EdgeSpec.model_validate({"from": "a", "to": "b", "relation": "导致"})
        assert edge.from_ == "a"

    def test_entry_item_children_nests_recursively(self) -> None:
        item = EntryItem.model_validate(
            {"title": "父", "children": [{"title": "子", "content": "x"}]}
        )
        assert item.children[0].title == "子"


# =============================================================================
# QA Scenario 2: D2 sanitization boundaries
# =============================================================================


class TestSanitizeTitle:
    def test_colons_removed_double_colon(self) -> None:
        assert sanitize_title("::") == "未命名"
        assert sanitize_title("a::b") == "ab"

    def test_whitespace_collapsed(self) -> None:
        assert sanitize_title("  力量   体系 \n") == "力量 体系"

    def test_truncated_to_32_chars(self) -> None:
        long = "长" * 40
        assert len(sanitize_title(long)) == 32

    def test_blank_returns_placeholder(self) -> None:
        assert sanitize_title("") == "未命名"
        assert sanitize_title("   \t\n ") == "未命名"


class TestDepthId:
    def test_depth_id_format(self) -> None:
        assert depth_id("力量体系.source", "脉轮共鸣") == "d:力量体系.source:脉轮共鸣"

    def test_depth_id_colon_in_title_sanitized(self) -> None:
        assert depth_id("力量体系.source", "a:b") == "d:力量体系.source:ab"

    def test_depth_id_parse_round_trip_with_dot_anchor(self) -> None:
        node_id = depth_id("力量体系.source", "a:b")
        anchor, title = parse_depth_id(node_id)
        assert anchor == "力量体系.source"
        assert title == "ab"

    def test_parse_rejects_non_depth_id(self) -> None:
        with pytest.raises(ValueError):
            parse_depth_id("term:力量")


# =============================================================================
# Dedup: same anchor + same title → keep first, duplicates reported
# =============================================================================


class TestDedupe:
    def test_keeps_first_and_reports_duplicates(self) -> None:
        items = [
            EntryItem(title="脉轮共鸣", content="first"),
            EntryItem(title="脉轮:共鸣", content="dup-same-after-sanitize"),
            EntryItem(title="枯竭症"),
        ]
        kept, duplicates = dedupe_items(items)
        assert [i.content for i in kept] == ["first", ""]
        assert duplicates == ["脉轮:共鸣"]


# =============================================================================
# Validation rules (four standalone functions)
# =============================================================================


class TestValidationRules:
    def test_rule1_illegal_anchor_flagged(self) -> None:
        legal = all_subfield_keys()[0]
        result = GraphifyResult(
            entries=[
                AnchorEntries(anchor=legal, items=[EntryItem(title="好")]),
                AnchorEntries(anchor="发明模块.发明字段", items=[]),
            ]
        )
        warnings = validate_anchors(result)
        assert warnings == ["非法锚点: '发明模块.发明字段'"]

    def test_rule2_relation_vocab_injected(self) -> None:
        edges = [
            EdgeSpec.model_validate({"from": "a", "to": "b", "relation": "导致"}),
            EdgeSpec.model_validate({"from": "a", "to": "c", "relation": "发明"}),
        ]
        warnings = validate_relations(edges, allowed_relations={"导致", "对抗"})
        assert len(warnings) == 1
        assert "发明" in warnings[0]

    def test_rule3_dim_tag_whitelist(self) -> None:
        dim, tag = next(iter(STRUCTURED_FIELDS.items()))[0], next(
            iter(next(iter(STRUCTURED_FIELDS.values())))
        )
        result = GraphifyResult(
            constraint_fields={
                f"{dim}.{tag}": "合法",
                "RED.not_structured": "RED无结构字段",
                "LAW.发明tag": "不存在",
            }
        )
        warnings = validate_constraint_fields(result)
        assert len(warnings) == 2
        assert any("RED.not_structured" in w for w in warnings)
        assert any("LAW.发明tag" in w for w in warnings)

    def test_rule4_children_phase1_warns_not_raises(self) -> None:
        result = GraphifyResult(
            entries=[
                AnchorEntries(
                    anchor=all_subfield_keys()[0],
                    items=[
                        EntryItem(
                            title="父",
                            children=[EntryItem(title="子")],
                        ),
                        EntryItem(title="平"),
                    ],
                )
            ]
        )
        warnings = validate_children_depth(result)
        assert len(warnings) == 1
        assert "Phase 1" in warnings[0]


# =============================================================================
# Timeout constant
# =============================================================================


class TestTimeout:
    def test_default_timeout_is_60(self) -> None:
        assert GRAPHIFY_TIMEOUT == 60

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import importlib

        import app.domains.creation.a1.graphify as mod

        monkeypatch.setenv("GRAPHIFY_TIMEOUT", "120")
        reloaded = importlib.reload(mod)
        assert reloaded.GRAPHIFY_TIMEOUT == 120
        monkeypatch.undo()
        importlib.reload(mod)
