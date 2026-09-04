"""C2 contract: graphify 输出字段 schema + 节点引用治理（d: 可解析锚点 + confirmed 匹配）。

治理文档 §6 C2 五类负向用例（全部必须走 warning 降级，不得 crash）：
1. 伪造 anchor（引用不存在的锚点）
2. 表外 relation（不在 relation vocab 白名单）
3. 超白名单 DIM.tag
4. Phase1 越权 children 嵌套
5. 幻觉节点引用（引用 graph 中不存在的节点 id）

全链注入：stub LLM 原始输出 → T6 ``parse_graphify_raw`` +
``apply_graphify_validation``（经 ``graphify_llm``）→ T7 ``_build_graph``。
"""
from __future__ import annotations

import pytest

from app.api.a1_routes import A1Session, _build_graph
from app.domains.creation.a1.graphify import (
    depth_id,
    graphify_llm,
    parse_graphify_raw,
)

#: 26 条封闭词表中的一条合法关系名（逐字）。
VALID_RELATION = "DERIVES→IP.类型"

#: 合法锚点（module.subfield，逐字来自 a1_question_tree）。
VALID_ANCHOR = "IP定位.name"

#: 合法 DIM.tag（STRUCTURED_FIELDS 白名单内）。
VALID_DIM_TAG = "LAW.world_structure"


def _make_session() -> A1Session:
    return A1Session(
        session_id="a1_c2test0001",
        user_id="u_c2",
        ip_code="IP0001",
        answers={VALID_ANCHOR: "灰烬大陆，天空永远燃烧"},
    )


def _valid_raw() -> dict:
    return {
        "module_summaries": {"IP定位": "一个燃烧的大陆世界观"},
        "entries": [
            {
                "anchor": VALID_ANCHOR,
                "items": [
                    {"title": "灰烬大陆", "content": "天空永远燃烧", "children": []}
                ],
            }
        ],
        "edges": [
            {
                "from": VALID_ANCHOR,
                "to": f"d:{VALID_ANCHOR}:灰烬大陆",
                "relation": VALID_RELATION,
                "rationale": "条目属于该锚点",
                "confidence": "semantic",
            }
        ],
        "constraint_fields": {VALID_DIM_TAG: "天空燃烧不可熄灭"},
        "open_questions": [],
    }


# =============================================================================
# Positive: valid SIR schema passes end-to-end (stub → parse → validate → assemble)
# =============================================================================


def test_c2_valid_sir_schema_passes(make_stub_llm) -> None:
    session = _make_session()
    stub = make_stub_llm(response=_valid_raw())

    result = graphify_llm(session, stub)

    assert result.success is True
    assert result.warning == ""  # no domain warnings on clean output
    assert len(result.entries) == 1
    assert result.entries[0].anchor == VALID_ANCHOR
    assert len(result.edges) == 1

    # T7 assembly: depth node mounted, LLM edge merged
    graph, node_ids = _build_graph(session, {}, result)
    expected_did = depth_id(VALID_ANCHOR, "灰烬大陆")
    assert expected_did in node_ids
    merged = [e for e in graph.edges if e.relation == VALID_RELATION]
    assert len(merged) == 1
    assert merged[0].confirmed is False


# =============================================================================
# Negative case 1: forged anchor → group dropped + [entries] domain warning
# =============================================================================


def test_c2_negative_forged_anchor_degrades_to_warning(make_stub_llm) -> None:
    session = _make_session()
    raw = _valid_raw()
    raw["entries"].append(
        {
            "anchor": "伪造模块.fake_subfield",  # forged anchor
            "items": [{"title": "幻觉条目", "content": "", "children": []}],
        }
    )
    stub = make_stub_llm(response=raw)

    result = graphify_llm(session, stub)

    assert result.success is True  # degrade, never crash
    assert "[entries]" in result.warning
    assert "非法锚点已丢弃" in result.warning
    assert "伪造模块.fake_subfield" in result.warning
    # forged group dropped, valid group kept (partial acceptance)
    anchors = [g.anchor for g in result.entries]
    assert anchors == [VALID_ANCHOR]

    graph, node_ids = _build_graph(session, {}, result)
    assert all("伪造" not in nid for nid in node_ids)


# =============================================================================
# Negative case 2: off-vocab relation → edge removed, moved to open_questions
# =============================================================================


def test_c2_negative_offvocab_relation_degrades_to_warning(make_stub_llm) -> None:
    session = _make_session()
    raw = _valid_raw()
    raw["edges"].append(
        {
            "from": VALID_ANCHOR,
            "to": f"d:{VALID_ANCHOR}:灰烬大陆",
            "relation": "心灵感应",  # off-vocab
            "rationale": "",
            "confidence": "semantic",
        }
    )
    stub = make_stub_llm(response=raw)

    result = graphify_llm(session, stub)

    assert result.success is True
    assert "[edges]" in result.warning
    assert "词表外关系已转为开放问题" in result.warning
    assert "心灵感应" in result.warning
    # off-vocab edge removed; valid relation kept
    assert [e.relation for e in result.edges] == [VALID_RELATION]
    # off-vocab relation translated into a world-building question
    assert any("心灵感应" in q.question for q in result.open_questions)

    graph, _ = _build_graph(session, {}, result)
    assert all(e.relation != "心灵感应" for e in graph.edges)


# =============================================================================
# Negative case 3: DIM.tag off the whitelist → key dropped + domain warning
# =============================================================================


def test_c2_negative_outofwhitelist_dim_tag_degrades_to_warning(
    make_stub_llm,
) -> None:
    session = _make_session()
    raw = _valid_raw()
    raw["constraint_fields"]["RED.note"] = "禁止熄灭火焰"  # RED has no structured fields
    raw["constraint_fields"]["LAW.not_a_field"] = "越权字段"  # tag off whitelist
    stub = make_stub_llm(response=raw)

    result = graphify_llm(session, stub)

    assert result.success is True
    assert "[constraint_fields]" in result.warning
    assert result.warning.count("约束字段不在白名单") == 2
    # whitelist key kept, off-whitelist keys dropped
    assert set(result.constraint_fields) == {VALID_DIM_TAG}


# =============================================================================
# Negative case 4: Phase 1 children nesting → warning only, items kept
# =============================================================================


def test_c2_negative_phase1_children_nesting_degrades_to_warning(
    make_stub_llm,
) -> None:
    session = _make_session()
    raw = _valid_raw()
    raw["entries"][0]["items"][0]["children"] = [
        {"title": "越权子条目", "content": "Phase 1 不允许", "children": []}
    ]
    stub = make_stub_llm(response=raw)

    result = graphify_llm(session, stub)

    assert result.success is True
    assert "children 深度 Phase 1 不开放" in result.warning
    assert "灰烬大陆" in result.warning  # offending item named in warning
    # warning-only: parent item retained, children not consumed
    assert len(result.entries[0].items) == 1
    assert not any(
        "越权子条目" in it.title for g in result.entries for it in g.items
    )


# =============================================================================
# Negative case 5: hallucinated node reference
#   - validation layer: edge dropped + [edges] warning
#   - assembly layer (defense in depth): _build_graph routes it to
#     dead_edges with reason="endpoint_missing" (assert dead_edges, not raise)
# =============================================================================


def test_c2_negative_hallucinated_node_ref_degrades_to_warning(
    make_stub_llm,
) -> None:
    session = _make_session()
    raw = _valid_raw()
    raw["edges"].append(
        {
            "from": VALID_ANCHOR,
            "to": "d:IP定位.name:不存在的幻觉条目",  # hallucinated depth node
            "relation": VALID_RELATION,
            "rationale": "",
            "confidence": "semantic",
        }
    )
    raw["edges"].append(
        {
            "from": "不存在的模块",
            "to": VALID_ANCHOR,
            "relation": VALID_RELATION,
            "rationale": "",
            "confidence": "semantic",
        }
    )
    stub = make_stub_llm(response=raw)

    result = graphify_llm(session, stub)

    assert result.success is True
    assert "[edges]" in result.warning
    assert "引用了不存在的节点" in result.warning
    # only the edge with real endpoints survives
    assert [e.relation for e in result.edges] == [VALID_RELATION]
    assert result.edges[0].to == f"d:{VALID_ANCHOR}:灰烬大陆"


def test_c2_negative_hallucinated_ref_hits_dead_edges_in_assembly() -> None:
    """Defense in depth: a GraphifyResult that bypasses validation still
    cannot inject a dangling edge — _merge_llm_edges parks it in
    ``dead_edges`` (reason=endpoint_missing) instead of raising."""
    from app.domains.creation.a1.graphify import GraphifyResult

    session = _make_session()
    llm_result = GraphifyResult(
        edges=[
            {
                "from": "幽灵节点",
                "to": VALID_ANCHOR,
                "relation": VALID_RELATION,
                "rationale": "",
                "confidence": "semantic",
            }
        ],
    )
    file_rec: dict = {}
    graph, node_ids = _build_graph(session, file_rec, llm_result)

    assert "幽灵节点" not in node_ids
    assert all(e.relation != VALID_RELATION or e.to != VALID_ANCHOR
               for e in graph.edges)
    assert file_rec["dead_edges"] == [
        {
            "from": "幽灵节点",
            "to": VALID_ANCHOR,
            "relation": VALID_RELATION,
            "confidence": "semantic",
            "reason": "endpoint_missing",
        }
    ]


# =============================================================================
# parse layer guard: wrong container type must raise (caller degrades)
# =============================================================================


def test_c2_parse_wrong_container_type_raises() -> None:
    with pytest.raises(ValueError, match="entries 应为列表"):
        parse_graphify_raw({"entries": {"anchor": "IP定位.name"}})
