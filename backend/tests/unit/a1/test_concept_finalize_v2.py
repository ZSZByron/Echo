"""Tests for Task T-B: finalize两阶段编排.

Covers:
1. finalize 后 graph 含 term: 节点（阶段1 mock 5词）+ TREE 不动 + 零概念边
2. 阶段1 降级：extract_concept_terms 抛异常 → 200 + warnings 含 concept_term + 无 term 节点
3. terms/confirm 端点：批量确认 → concept_terms.confirmed 更新
4. extract-edges 前置校验：confirmed < 2 → 400
5. extract-edges 成功：mock 3 边（含 1 is_new_relation）→ graph 边含 term: 引用 +
   confirmed=False；proposed_relations 有 1 条
6. 确认新词边 → registry 入典（_FILES.relation_registry 增加该词）+ proposed_relations 移除该条
7. 重定稿恢复：finalize→确认词→抽边→确认1边拒1边→改答案→re-finalize→
   词节点在 + confirmed 保留 + 边状态保留
8. GET file 常驻字段 concept_terms / proposed_relations
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.domains.creation.a1.concept_edge_extractor import (
    ConceptEdgeV2,
    ConceptTerm,
    EdgesV2Result,
    TermsResult,
)


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def started(client):
    resp = client.post("/api/a1/session/start", json={"user_id": "u_tb", "seed_id": 1})
    assert resp.status_code == 200
    return client, resp.json()


def _inject_answers(payload):
    """Fill answers directly in the live session (bypasses chat)."""
    from app.api import a1_routes
    from app.domains.creation.seed.a1_question_tree import MODULES

    session = a1_routes._SESSIONS[payload["session_id"]]
    for m in MODULES:
        need = len(m["fields"]) // 2 + 1
        for f in m["fields"][:need]:
            session.answers[f"{m['id']}.{f['id']}"] = "测试内容"
    return session


def _terms_result(terms, success=True, warning=""):
    return TermsResult(
        terms=[ConceptTerm(term=t, field_key="模块.字段") for t in terms],
        success=success,
        warning=warning,
    )


def _edges_v2_result(edges, success=True, warning=""):
    return EdgesV2Result(
        edges=[ConceptEdgeV2(**e) for e in edges],
        success=success,
        warning=warning,
    )


_MOCK_TERMS = ["死亡转生", "业报", "轮回之门", "星阶", "观星城"]

_MOCK_EDGES = [
    {"from_term": "死亡转生", "to_term": "业报", "relation": "引发",
     "is_new_relation": False, "rationale": "r1", "confidence": "semantic"},
    {"from_term": "业报", "to_term": "轮回之门", "relation": "依赖",
     "is_new_relation": False, "rationale": "r2", "confidence": "semantic"},
    {"from_term": "星阶", "to_term": "观星城", "relation": "反噬",
     "is_new_relation": True, "rationale": "r3", "confidence": "semantic"},
]


def _finalize_with_terms(client, payload, monkeypatch, terms=_MOCK_TERMS):
    _inject_answers(payload)
    monkeypatch.setattr(
        "app.api.a1_routes.extract_concept_terms",
        lambda *a, **kw: _terms_result(terms),
    )
    fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
    assert fin.status_code == 200
    return fin.json()


def _confirm_all_terms(client, payload):
    resp = client.post(
        f"/api/a1/file/{payload['file_id']}/terms/confirm", json={"all": True}
    )
    assert resp.status_code == 200


def _extract_edges(client, payload, monkeypatch, edges=_MOCK_EDGES):
    monkeypatch.setattr(
        "app.api.a1_routes.extract_concept_relations",
        lambda *a, **kw: _edges_v2_result(edges),
    )
    resp = client.post(f"/api/a1/file/{payload['file_id']}/concept/extract-edges")
    return resp


class TestFinalizeStage1:
    """Test 1: finalize 阶段1——概念词节点入图，零概念边."""

    def test_finalize_adds_term_nodes_no_concept_edges(self, started, monkeypatch):
        client, payload = started
        body = _finalize_with_terms(client, payload, monkeypatch)

        # concept_terms_count in finalize response
        assert body.get("concept_terms_count") == 5

        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph").json()

        # TREE edges untouched
        tree_edges = [e for e in graph["edges"] if e["edge_type"] == "tree"]
        assert len(tree_edges) > 0

        # term: nodes exist with level=4 + completed status
        term_nodes = {
            nid: n for nid, n in graph["nodes"].items() if nid.startswith("term:")
        }
        assert set(term_nodes) == {f"term:{t}" for t in _MOCK_TERMS}
        for n in term_nodes.values():
            assert n["level"] == 4
            assert n["status"] == "completed"

        # 零概念边（本阶段不抽）
        concept_edges = [
            e for e in graph["edges"]
            if e.get("from_node_id", "").startswith("term:")
            or e.get("to_node_id", "").startswith("term:")
        ]
        assert len(concept_edges) == 0

        # _FILES.concept_terms written, confirmed default False
        from app.api import a1_routes
        rec = a1_routes._FILES[payload["file_id"]]
        assert len(rec["concept_terms"]) == 5
        assert all(t["confirmed"] is False for t in rec["concept_terms"])


class TestFinalizeStage1Degradation:
    """Test 2: 阶段1 降级."""

    def test_stage1_exception_degrades(self, started, monkeypatch):
        client, payload = started
        _inject_answers(payload)

        def _raise(*a, **kw):
            raise RuntimeError("LLM unavailable")

        monkeypatch.setattr("app.api.a1_routes.extract_concept_terms", _raise)

        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200
        body = fin.json()
        assert any("concept_term" in w for w in body.get("warnings", []))

        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph").json()
        term_nodes = [nid for nid in graph["nodes"] if nid.startswith("term:")]
        assert len(term_nodes) == 0


class TestTermsConfirm:
    """Test 3: terms/confirm 批量确认."""

    def test_batch_confirm_updates_confirmed(self, started, monkeypatch):
        client, payload = started
        _finalize_with_terms(client, payload, monkeypatch)

        resp = client.post(
            f"/api/a1/file/{payload['file_id']}/terms/confirm",
            json={"terms": ["死亡转生", "业报"]},
        )
        assert resp.status_code == 200
        terms = {t["term"]: t for t in resp.json()["concept_terms"]}
        assert terms["死亡转生"]["confirmed"] is True
        assert terms["业报"]["confirmed"] is True
        assert terms["轮回之门"]["confirmed"] is False

        from app.api import a1_routes
        rec = a1_routes._FILES[payload["file_id"]]
        persisted = {t["term"]: t for t in rec["concept_terms"]}
        assert persisted["死亡转生"]["confirmed"] is True


class TestExtractEdgesGuard:
    """Test 4: extract-edges 前置校验 confirmed < 2 → 400."""

    def test_requires_two_confirmed_terms(self, started, monkeypatch):
        client, payload = started
        _finalize_with_terms(client, payload, monkeypatch)

        # no terms confirmed yet
        resp = client.post(f"/api/a1/file/{payload['file_id']}/concept/extract-edges")
        assert resp.status_code == 400
        assert resp.json()["detail"] == "需先确认至少2个概念词"


class TestExtractEdgesSuccess:
    """Test 5: extract-edges 成功——边入图 + proposed_relations."""

    def test_edges_added_with_proposal(self, started, monkeypatch):
        client, payload = started
        _finalize_with_terms(client, payload, monkeypatch)
        _confirm_all_terms(client, payload)

        resp = _extract_edges(client, payload, monkeypatch)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph").json()
        term_edges = [
            e for e in graph["edges"]
            if e["from_node_id"].startswith("term:")
        ]
        assert len(term_edges) == 3
        for e in term_edges:
            assert e["confirmed"] is False
            assert e["from_node_id"] in graph["nodes"]
            assert e["to_node_id"] in graph["nodes"]

        from app.api import a1_routes
        rec = a1_routes._FILES[payload["file_id"]]
        proposed = rec["proposed_relations"]
        assert len(proposed) == 1
        assert proposed[0]["name"] == "反噬"
        assert proposed[0]["from_term"] == "星阶"

        # known-relation edges' edge_type follows dictionary level mapping
        # 引发 is semantic → edge_type semantic
        e0 = [e for e in term_edges if e["relation"] == "引发"][0]
        assert e0["edge_type"] == "semantic"


class TestNewRelationInduction:
    """Test 6: 确认新词边 → 入典 + proposed 移除."""

    def test_confirming_new_relation_edge_adds_to_registry(self, started, monkeypatch):
        client, payload = started
        _finalize_with_terms(client, payload, monkeypatch)
        _confirm_all_terms(client, payload)
        _extract_edges(client, payload, monkeypatch)

        # Confirm the new-relation edge
        key = "term:星阶/term:观星城/反噬"
        resp = client.post(f"/api/a1/file/{payload['file_id']}/edge/{key}/confirm")
        assert resp.status_code == 200

        from app.api import a1_routes
        rec = a1_routes._FILES[payload["file_id"]]

        # registry persisted with the new word
        assert "反噬" in rec["relation_registry"]
        assert rec["relation_registry"]["反噬"]["level"] == "semantic"

        # proposal removed
        assert all(p["name"] != "反噬" for p in rec["proposed_relations"])

        # edge confirmed in graph
        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph").json()
        e = [
            e for e in graph["edges"]
            if e["from_node_id"] == "term:星阶" and e["relation"] == "反噬"
        ][0]
        assert e["confirmed"] is True


class TestRefinalizeRestore:
    """Test 7: 重定稿恢复——词节点 + confirmed 态 + 边状态."""

    def test_full_cycle_restore(self, started, monkeypatch):
        client, payload = started
        _finalize_with_terms(client, payload, monkeypatch)
        _confirm_all_terms(client, payload)
        _extract_edges(client, payload, monkeypatch)

        # confirm 1 edge, reject 1 edge
        client.post("/api/a1/file/{}/edge/{}/confirm".format(
            payload["file_id"], "term:死亡转生/term:业报/引发"))
        client.post("/api/a1/file/{}/edge/{}/reject".format(
            payload["file_id"], "term:业报/term:轮回之门/依赖"))

        # change answers then re-finalize (stage1 mocked again, returns same terms)
        from app.api import a1_routes
        session = a1_routes._SESSIONS[payload["session_id"]]
        first_key = next(iter(session.answers))
        session.answers[first_key] = "修改后的答案"

        monkeypatch.setattr(
            "app.api.a1_routes.extract_concept_terms",
            lambda *a, **kw: _terms_result(_MOCK_TERMS),
        )
        fin2 = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin2.status_code == 200

        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph").json()

        # term nodes restored
        term_nodes = {nid for nid in graph["nodes"] if nid.startswith("term:")}
        assert term_nodes == {f"term:{t}" for t in _MOCK_TERMS}

        # term confirmed state preserved
        persisted = {t["term"]: t for t in a1_routes._FILES[payload["file_id"]]["concept_terms"]}
        assert all(t["confirmed"] is True for t in persisted.values())

        # confirmed edge restored with confirmed=True
        edges_by_key = {
            f"{e['from_node_id']}/{e['to_node_id']}/{e.get('relation', '')}": e
            for e in graph["edges"]
        }
        assert edges_by_key["term:死亡转生/term:业报/引发"]["confirmed"] is True

        # rejected edge does not reappear
        assert "term:业报/term:轮回之门/依赖" not in edges_by_key


class TestGetFileResidentFields:
    """Test 8: GET file 常驻字段 concept_terms / proposed_relations."""

    def test_resident_fields_always_present(self, started, monkeypatch):
        client, payload = started
        _inject_answers(payload)

        # draft state (no finalize): fields present and empty
        resp = client.get(f"/api/a1/file/{payload['file_id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["concept_terms"] == []
        assert body["proposed_relations"] == []

        # after finalize + extract
        monkeypatch.setattr(
            "app.api.a1_routes.extract_concept_terms",
            lambda *a, **kw: _terms_result(["死亡转生", "业报"]),
        )
        client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        client.post(
            f"/api/a1/file/{payload['file_id']}/terms/confirm", json={"all": True}
        )
        monkeypatch.setattr(
            "app.api.a1_routes.extract_concept_relations",
            lambda *a, **kw: _edges_v2_result([
                {"from_term": "死亡转生", "to_term": "业报", "relation": "反噬",
                 "is_new_relation": True, "rationale": "", "confidence": "semantic"},
            ]),
        )
        client.post(f"/api/a1/file/{payload['file_id']}/concept/extract-edges")

        resp = client.get(f"/api/a1/file/{payload['file_id']}")
        body = resp.json()
        assert len(body["concept_terms"]) == 2
        assert len(body["proposed_relations"]) == 1
        assert body["proposed_relations"][0]["name"] == "反噬"
