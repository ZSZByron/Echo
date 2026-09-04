"""C3 contract: graph_json 双树结构五条不变量。

治理文档 §6 C3（不变量 5 条）：
1. TREE 计数不变量（模块+条目+分条目节点数 == TREE 边数）
2. 序号同构（module→entry→depth 序号前缀同构）
3. d: 可解析（节点 id 的 d: 前缀深度编码可 round-trip 解析）
4. 引用存在（所有边端点均在节点集内）
5. id 无顺序成分（深度 id 内容寻址，不含 k 序号；同 answers 重装配 id 稳定）
"""
from __future__ import annotations

import pytest

from app.api.a1_routes import A1Session, _build_graph
from app.models.knowledge_graph import EdgeType
from app.domains.creation.a1.graphify import depth_id, parse_depth_id

ANSWERS = {
    "IP定位.name": "灰烬大陆",
    "IP定位.concept": "燃烧的天空下寻找最后的绿洲",
    "世界本体.origin": "创世火种爆炸",
}


def _make_session() -> A1Session:
    return A1Session(
        session_id="decaytest",
        user_id="u_c3",
        ip_code="IP0001",
        answers=dict(ANSWERS),
    )


def _llm_result():
    from app.domains.creation.a1.graphify import EntryItem, GraphifyResult

    return GraphifyResult(
        module_summaries={"IP定位": "燃烧大陆", "世界本体": "火种创世"},
        entries=[
            {
                "anchor": "IP定位.name",
                "items": [
                    {"title": "灰烬大陆", "content": "天空燃烧", "children": []},
                    {"title": "绿洲残响", "content": "最后的绿地", "children": []},
                ],
            },
            {
                "anchor": "世界本体.origin",
                "items": [
                    {"title": "创世火种", "content": "一切开始", "children": []},
                ],
            },
        ],
        edges=[
            {
                "from": "IP定位.name",
                "to": "d:IP定位.name:灰烬大陆",
                "relation": "DERIVES→IP.类型",
                "rationale": "",
                "confidence": "semantic",
            },
        ],
    )


def _build() -> tuple:
    session = _make_session()
    return _build_graph(session, {}, _llm_result())


# =============================================================================
# Invariant 1: TREE count (module + entry + depth nodes == TREE edges)
# =============================================================================


def test_c3_invariant_tree_count() -> None:
    graph, node_ids = _build()
    tree_edges = [e for e in graph.edges if e.edge_type == EdgeType.TREE]
    # module(2) + entry(3) + depth(3) nodes, all reached by exactly one TREE edge
    structured = [n for n in graph.nodes.values() if n.level >= 2]
    assert len(structured) == 8
    assert len(tree_edges) == 8  # bg→module×2, module→entry×3, entry→depth×3
    # every non-background node is the target of exactly one TREE edge
    targets = [e.to_node_id for e in tree_edges]
    assert sorted(targets) == sorted(n.id for n in structured)
    # background is the only node without an incoming TREE edge
    roots = {e.from_node_id for e in tree_edges} - set(targets)
    assert roots == {graph.background_node_id}


# =============================================================================
# Invariant 2: serial number isomorphism (module → entry → depth prefixes)
# =============================================================================


def test_c3_invariant_index_isomorphism() -> None:
    graph, _ = _build()
    nodes = graph.nodes
    modules = {n.id: n for n in nodes.values() if n.level == 2}
    entries = {n.id: n for n in nodes.values() if n.level == 3}
    depths = {n.id: n for n in nodes.values() if n.level == 4}

    assert set(modules) == {"IP定位", "世界本体"}
    module_serials = sorted(n.serial_number for n in modules.values())
    assert module_serials == ["1", "2"]  # dense 1..n, order = answer order

    # entry serial = "{module_serial}-{entry_serial}"
    for eid, entry in entries.items():
        m_serial = modules[eid.split(".")[0]].serial_number
        assert entry.serial_number.startswith(f"{m_serial}-")

    # depth serial = "D{module_serial}-{entry_serial}-{k}"
    for did, depth in depths.items():
        anchor, _title = parse_depth_id(did)
        e_serial = entries[anchor].serial_number
        assert depth.serial_number.startswith(f"D{e_serial}-")
        k = depth.serial_number[len(f"D{e_serial}-"):]
        assert k.isdigit() and int(k) >= 1


# =============================================================================
# Invariant 3: d: ids round-trip via parse_depth_id
# =============================================================================


def test_c3_invariant_depth_prefix_parseable() -> None:
    graph, node_ids = _build()
    depth_ids = [nid for nid in node_ids if nid.startswith("d:")]
    assert len(depth_ids) == 3
    for nid in depth_ids:
        anchor, title = parse_depth_id(nid)
        assert "." in anchor  # anchor is a module.subfield key
        assert depth_id(anchor, title) == nid  # round-trip stable
    # non-depth ids rejected
    try:
        parse_depth_id("IP定位.name")
        raised = False
    except ValueError:
        raised = True
    assert raised


# =============================================================================
# Invariant 4: every edge endpoint exists in the node set
# =============================================================================


def test_c3_invariant_references_exist() -> None:
    graph, node_ids = _build()
    for edge in graph.edges:
        assert edge.from_node_id in node_ids, edge
        assert edge.to_node_id in node_ids, edge


# =============================================================================
# Invariant 5: ids carry no ordering component (content-addressed)
# =============================================================================


def test_c3_invariant_id_content_addressed() -> None:
    graph, node_ids = _build()
    # depth ids contain the title, never the k ordinal — no digits at all
    for nid in node_ids:
        assert not any(ch.isdigit() for ch in nid), f"id 含顺序成分: {nid}"

    # same answers → same ids (re-finalize idempotence), independent of
    # insertion order: build a second graph from a fresh session
    graph2, node_ids2 = _build()
    assert node_ids == node_ids2

    # adding an entry does NOT shift existing ids (no positional encoding)
    from app.domains.creation.a1.graphify import EntryItem, GraphifyResult

    session = _make_session()
    result = _llm_result()
    result.entries[0].items.append(
        EntryItem(title="新增条目", content="")
    )
    _, node_ids3 = _build_graph(session, {}, result)
    assert node_ids <= node_ids3  # all original ids unchanged

# =============================================================================
# Runtime assembly assertion (governance §5, log-only) — T11 green scope.
# =============================================================================


def test_c3_runtime_assertion_constraint_fields_without_cst_logs_event(monkeypatch) -> None:
    """T11 green: constraint_fields 非空时 cst 通道产出 cst_ 节点，
    runtime assertion 不再触发 log_event。"""
    from app.api import a1_routes

    captured: list[dict] = []
    monkeypatch.setattr(
        a1_routes, "log_event",
        lambda sid, event, **kw: captured.append({"event": event, **kw}),
    )

    session = _make_session()
    result = _llm_result()
    result.constraint_fields = {"LAW.world_structure": "九层嵌套"}
    graph, node_ids = _build_graph(session, {}, result)

    # cst channel wired: node present in graph AND returned id set
    assert any(nid.startswith("cst_") for nid in graph.nodes)
    assert any(nid.startswith("cst_") for nid in node_ids)
    # assertion stayed silent
    assert not any(
        c.get("kind") == "constraint_fields_without_cst_nodes"
        for c in captured
    )
