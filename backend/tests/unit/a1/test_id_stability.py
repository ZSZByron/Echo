"""T13: id 稳定性快照 + 锚点漂移 + 混合版本死区洪泛 + 边核算不变量测试.

Governance contract: docs/governance/2-A1-v0.5-内容图谱化统一模型与契约.md
- §2 不变量5: 同 answers + 同 LLM 输出 → 组装结果节点 id 集合确定（byte-identical）
- §4 匹配键: confirmed edge key = from/to/relation 三元组；无模糊语义合并 ——
  锚点子树 id 漂移后旧 confirmed 边按设计落入 dead_edges（D1 预期行为，非 bug）
- D1: 旧 term: 快照 confirmed_edges 在新 d: 组装下全部进死区（预期洪泛）

全部同步 def（graphify_llm 内部 asyncio.run，不可在 event loop 内调用）。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import a1_routes
from app.main import app
from app.domains.creation.a1.graphify import (
    AnchorEntries,
    EdgeSpec,
    EntryItem,
    GraphifyResult,
    depth_id,
    graphify_llm,
)


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def started(client):
    resp = client.post("/api/a1/session/start", json={"user_id": "u_test_t13", "seed_id": 1})
    assert resp.status_code == 200
    return client, resp.json()

# fixed anchors used across tests (verbatim module.subfield keys)
ANCHOR_A = "世界本体.origin"
ANCHOR_B = "世界本体.existence"


def _prep_session(payload, *, origin: str = "世界起源于一声钟响",
                  existence: str = "万物以概念形式存在"):
    """Fill a stable two-anchor answer set on the live session."""
    session = a1_routes._SESSIONS[payload["session_id"]]
    session.answers["IP定位.name"] = "测试IP"
    session.answers[ANCHOR_A] = origin
    session.answers[ANCHOR_B] = existence
    return session


def _stub_graphify_payload():
    """Deterministic stub LLM graphify response (valid anchors, d: refs)."""
    return {
        "module_summaries": {"世界本体": "存在的根基与世界法则"},
        "entries": [
            {"anchor": ANCHOR_A, "items": [
                {"title": "命运之钟", "content": "钟声即存在", "children": []},
            ]},
            {"anchor": ANCHOR_B, "items": [
                {"title": "存在之环", "content": "环环相扣", "children": []},
                {"title": "概念之海", "content": "万物漂浮其上", "children": []},
            ]},
        ],
        "edges": [
            {"from": ANCHOR_A, "to": depth_id(ANCHOR_A, "命运之钟"),
             "relation": "存在塑力", "confidence": "semantic"},
            {"from": depth_id(ANCHOR_B, "存在之环"), "to": depth_id(ANCHOR_A, "命运之钟"),
             "relation": "存在塑力", "confidence": "semantic"},
        ],
        "open_questions": [],
        "constraint_fields": {},
    }


def _d_nodes(graph) -> set[str]:
    return {n.id for n in graph.nodes.values() if n.id.startswith("d:")}


def _complete_answers(payload):
    """Fill >50% of every module so finalize's gate passes."""
    from app.domains.creation.seed.a1_question_tree import MODULES

    session = a1_routes._SESSIONS[payload["session_id"]]
    for m in MODULES:
        need = len(m["fields"]) // 2 + 1
        for f in m["fields"][:need]:
            session.answers[f"{m['id']}.{f['id']}"] = "预填内容"
    return session


def _stub_finalize(monkeypatch, make_stub_llm, response):
    """Route finalize's provider factory to a deterministic stub LLM."""
    stub = make_stub_llm(response=response)
    monkeypatch.setattr(a1_routes, "load_provider_config", lambda: {})
    monkeypatch.setattr(a1_routes, "create_provider", lambda cfg: stub)
    return stub


# ---------------------------------------------------------------------------
# 1. 不变量5 — id 快照：同 answers + 同 stub 固定响应 → 两次全链组装 id 集合一致
# ---------------------------------------------------------------------------


def test_id_snapshot_two_full_chain_runs_byte_identical(started, make_stub_llm):
    """不变量5: graphify_llm → _build_graph 跑两遍，节点 id 集合（含 d:）逐字节一致。"""
    client, payload = started
    stub1 = make_stub_llm(response=_stub_graphify_payload())
    stub2 = make_stub_llm(response=_stub_graphify_payload())

    snapshots = []
    for stub in (stub1, stub2):
        session = _prep_session(payload)
        result = graphify_llm(session, stub)  # full chain, sync def
        assert result.success, f"graphify_llm degraded: {result.warning}"
        file_rec: dict = {}
        graph, ids = a1_routes._build_graph(session, file_rec, llm_result=result)
        snapshots.append((frozenset(graph.nodes.keys()), _d_nodes(graph)))

    ids1, d1 = snapshots[0]
    ids2, d2 = snapshots[1]
    # node id sets byte-identical across runs
    assert ids1 == ids2
    # depth (d:) nodes present and identical
    assert d1 == d2
    assert len(d1) == 3  # 命运之钟 / 存在之环 / 概念之海
    assert depth_id(ANCHOR_A, "命运之钟") in d1


def test_id_snapshot_deterministic_build_only(started):
    """不变量5（纯组装路径）: 同 GraphifyResult 重放两次 → id 集合一致。"""
    client, payload = started
    session = _prep_session(payload)

    llm = GraphifyResult(
        module_summaries={"世界本体": "根基"},
        entries=[AnchorEntries(anchor=ANCHOR_A, items=[
            EntryItem(title="命运之钟", content="钟声即存在"),
        ])],
        edges=[EdgeSpec(**{"from": ANCHOR_A, "to": depth_id(ANCHOR_A, "命运之钟"),
                           "relation": "存在塑力", "confidence": "semantic"})],
    )
    _, ids_a = a1_routes._build_graph(session, {}, llm_result=llm)
    _, ids_b = a1_routes._build_graph(session, {}, llm_result=llm)
    assert ids_a == ids_b
    assert any(i.startswith("d:") for i in ids_a)


# ---------------------------------------------------------------------------
# 2. 锚点漂移预期行为（v0.5 D1/R3）— 用户改一条 answer → 子树 id 变化 →
#    旧 confirmed 边进 dead_edges。断言 = 预期设计，非 bug；不做模糊语义合并。
# ---------------------------------------------------------------------------


def test_anchor_drift_confirmed_edges_fall_into_dead_zone(started, make_stub_llm, monkeypatch):
    """漂移：用户改一条 answer → 该锚点子树 id 变化 → 相关 confirmed 边
    经 finalize 快照循环落入 dead_edges（预期设计 D1/R3，非 bug；
    不做模糊语义合并「修复」）。"""
    client, payload = started
    session = _prep_session(payload)

    # ---- round 1: original extraction, user confirms an edge ----
    old_d = depth_id(ANCHOR_A, "命运之钟")
    llm_v1 = GraphifyResult(
        entries=[AnchorEntries(anchor=ANCHOR_A, items=[
            EntryItem(title="命运之钟", content="钟声即存在"),
        ])],
        edges=[EdgeSpec(**{"from": ANCHOR_A, "to": old_d,
                           "relation": "存在塑力", "confidence": "semantic"})],
    )
    file_rec: dict = {}
    graph1, _ = a1_routes._build_graph(session, file_rec, llm_result=llm_v1)
    assert old_d in graph1.nodes
    rec = a1_routes._FILES[payload["file_id"]]
    # user confirmed this edge in round 1 (snapshot on the file record)
    rec["confirmed_edges"][a1_routes._make_edge_key(ANCHOR_A, old_d, "关联")] = {
        "from_node_id": ANCHOR_A, "to_node_id": old_d,
        "relation": "关联", "confirmed": True,
    }

    # ---- round 2: user edits the answer → new extraction title ----
    session.answers[ANCHOR_A] = "世界起源于大爆炸的余烬"  # changed answer
    new_d = depth_id(ANCHOR_A, "起源余烬")
    _complete_answers(payload)
    _stub_finalize(monkeypatch, make_stub_llm, _stub_graphify_payload() | {
        "entries": [
            {"anchor": ANCHOR_A, "items": [
                {"title": "起源余烬", "content": "余烬即万物之始", "children": []},
            ]},
            {"anchor": ANCHOR_B, "items": []},
        ],
        "edges": [
            {"from": ANCHOR_A, "to": new_d,
             "relation": "存在塑力", "confidence": "semantic"},
        ],
    })
    fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
    assert fin.status_code == 200, fin.text
    graph2 = rec["graph_json"]
    node_ids = set(graph2["nodes"])

    # subtree id drift: old depth id gone, new depth id present
    assert old_d not in node_ids
    assert new_d in node_ids

    # old confirmed edge → dead zone with endpoint_missing (by design, NOT
    # resurrected, NOT fuzzy-matched to the new subtree)
    dead = rec["dead_edges"]
    assert len(dead) == 1
    assert dead[0]["from"] == ANCHOR_A
    assert dead[0]["to"] == old_d
    assert dead[0]["relation"] == "关联"
    assert dead[0]["reason"] == "endpoint_missing"

    # no fuzzy semantic merge: the only semantic edge targets the new id,
    # and the legacy confirmed triple is NOT re-matched onto it
    sem = [e for e in graph2["edges"]
           if e.get("relation") == "存在塑力" and e.get("confidence") == "semantic"]
    assert len(sem) == 1
    assert sem[0]["to_node_id"] == new_d
    assert not sem[0]["confirmed"]


# ---------------------------------------------------------------------------
# 3. 混合版本死区洪泛（D1 预期行为）— 旧 term: 快照 confirmed_edges +
#    新 d: 组装 → 旧边全部可见进 dead_zone
# ---------------------------------------------------------------------------


def test_mixed_version_term_snapshot_floods_dead_zone(started, make_stub_llm, monkeypatch):
    """D1: v0.4 term: 词快照 confirmed 边在 v0.5 d: 组装下全部洪泛进死区。"""
    client, payload = started
    _prep_session(payload)
    rec = a1_routes._FILES[payload["file_id"]]

    # legacy v0.4 confirmed_edges snapshot: term: id triples
    for rel in ("关联", "衍生"):
        rec["confirmed_edges"][f"term:命运之钟/term:存在之环/{rel}"] = {
            "from_node_id": "term:命运之钟",
            "to_node_id": "term:存在之环",
            "relation": rel, "confirmed": True,
        }

    _complete_answers(payload)
    _stub_finalize(monkeypatch, make_stub_llm, _stub_graphify_payload())
    fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
    assert fin.status_code == 200, fin.text
    graph = rec["graph_json"]

    # flooding: every legacy confirmed edge visible in dead zone
    dead = rec["dead_edges"]
    assert len(dead) == 2
    dead_pairs = {(d["from"], d["to"], d["relation"]) for d in dead}
    assert dead_pairs == {
        ("term:命运之钟", "term:存在之环", "关联"),
        ("term:命运之钟", "term:存在之环", "衍生"),
    }
    assert all(d["reason"] == "endpoint_missing" for d in dead)
    assert all("key" in d for d in dead)  # snapshot-flood entries carry the triple key

    # new d: assembly unaffected by the flood
    node_ids = set(graph["nodes"])
    assert depth_id(ANCHOR_A, "命运之钟") in node_ids
    assert not any(i.startswith("term:") for i in node_ids)


# ---------------------------------------------------------------------------
# 4. 边核算不变量矩阵 — input_edges == graph_edges + dead_edges
# ---------------------------------------------------------------------------


def _count_semantic(graph) -> int:
    """Count LLM-merged edges (TREE assembly edges carry relation='')."""
    return sum(1 for e in graph.edges if e.relation)


def test_accounting_matrix(started):
    """全场景矩阵：无 LLM / 有边无失效 / 有失效 / 混合。"""
    client, payload = started
    session = _prep_session(payload)
    ok_d = depth_id(ANCHOR_A, "命运之钟")

    # (a) 无 LLM（llm_result=None）：input 0 == graph 0 + dead 0
    file_rec: dict = {}
    graph, _ = a1_routes._build_graph(session, file_rec)
    assert file_rec["dead_edges"] == []
    assert _count_semantic(graph) == 0

    # (b) 有边无失效：全部落图，dead 空
    llm_ok = GraphifyResult(
        entries=[AnchorEntries(anchor=ANCHOR_A, items=[
            EntryItem(title="命运之钟", content="钟声即存在"),
        ])],
        edges=[
            EdgeSpec(**{"from": ANCHOR_A, "to": ok_d,
                        "relation": "存在塑力", "confidence": "semantic"}),
            EdgeSpec(**{"from": ANCHOR_B, "to": ok_d,
                        "relation": "存在塑力", "confidence": "semantic"}),
        ],
    )
    file_rec = {}
    graph, _ = a1_routes._build_graph(session, file_rec, llm_result=llm_ok)
    assert file_rec["dead_edges"] == []
    assert len(llm_ok.edges) == _count_semantic(graph) + len(file_rec["dead_edges"])

    # (c) 有失效：全部端点缺失 → 全部进死区
    llm_dead = GraphifyResult(
        edges=[
            EdgeSpec(**{"from": ANCHOR_A, "to": "幽灵甲",
                        "relation": "存在塑力", "confidence": "semantic"}),
            EdgeSpec(**{"from": "幽灵乙", "to": ANCHOR_B,
                        "relation": "存在塑力", "confidence": "semantic"}),
        ],
    )
    file_rec = {}
    graph, _ = a1_routes._build_graph(session, file_rec, llm_result=llm_dead)
    dead = file_rec["dead_edges"]
    assert len(dead) == 2
    assert {d["to"] for d in dead} == {"幽灵甲", ANCHOR_B}
    assert {d["from"] for d in dead} == {ANCHOR_A, "幽灵乙"}
    assert all(d["reason"] == "endpoint_missing" for d in dead)
    assert len(llm_dead.edges) == _count_semantic(graph) + len(dead)

    # (d) 混合：一条落图 + 一条死区
    llm_mixed = GraphifyResult(
        entries=[AnchorEntries(anchor=ANCHOR_A, items=[
            EntryItem(title="命运之钟", content="钟声即存在"),
        ])],
        edges=[
            EdgeSpec(**{"from": ANCHOR_A, "to": ok_d,
                        "relation": "存在塑力", "confidence": "semantic"}),
            EdgeSpec(**{"from": ANCHOR_B, "to": "幽灵丙",
                        "relation": "存在塑力", "confidence": "semantic"}),
        ],
    )
    file_rec = {}
    graph, _ = a1_routes._build_graph(session, file_rec, llm_result=llm_mixed)
    dead = file_rec["dead_edges"]
    assert len(dead) == 1
    assert dead[0]["to"] == "幽灵丙"
    assert len(llm_mixed.edges) == _count_semantic(graph) + len(dead)


@pytest.mark.parametrize("scenario", ["matrix-done"])
def test_accounting_matrix_marker(scenario):
    """Marker test so the matrix above is discoverable in CI listing."""
    assert scenario == "matrix-done"
