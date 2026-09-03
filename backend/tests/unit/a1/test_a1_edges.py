"""Tests for Task 7 / T-B: finalize两阶段编排 + 确认态持久化 + edge审核API.

语义迁移说明 (Task T-B): finalize 不再抽取槽位级概念边，改为两阶段编排：
- 阶段1: finalize 时 extract_concept_terms → 概念词节点（term: 前缀, level=4）入图
- 阶段2: 节点确认后 POST /concept/extract-edges → 概念边逐条确认
旧槽位边测试已按新语义迁移（finalize 无概念边/只有 term 节点）。
edge confirm/reject API 端点不变，测试保留（改用新流程造边）。
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
    resp = client.post("/api/a1/session/start", json={"user_id": "u_test_edges", "seed_id": 1})
    assert resp.status_code == 200
    return client, resp.json()


def _inject_answers(payload, per_module_need=None):
    """Fill answers directly in the live session (bypasses chat)."""
    from app.api import a1_routes
    from app.domains.creation.seed.a1_question_tree import MODULES

    session = a1_routes._SESSIONS[payload["session_id"]]
    for m in MODULES:
        need = per_module_need if per_module_need is not None else len(m["fields"]) // 2 + 1
        for f in m["fields"][:need]:
            session.answers[f"{m['id']}.{f['id']}"] = "测试内容"
    return session


def _terms_result(terms, success=True, warning=""):
    return TermsResult(
        terms=[ConceptTerm(term=t, field_key="模块.字段") for t in terms],
        success=success, warning=warning,
    )


def _edges_v2_result(edges, success=True, warning=""):
    return EdgesV2Result(
        edges=[ConceptEdgeV2(**e) for e in edges],
        success=success, warning=warning,
    )


_MOCK_TERMS = ["死亡转生", "业报", "轮回之门"]


def _finalize_with_terms(client, payload, monkeypatch, terms=_MOCK_TERMS):
    """Helper: inject answers, mock stage-1 terms extraction, finalize."""
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


def _extract_edges(client, payload, monkeypatch, edges):
    monkeypatch.setattr(
        "app.api.a1_routes.extract_concept_relations",
        lambda *a, **kw: _edges_v2_result(edges),
    )
    resp = client.post(f"/api/a1/file/{payload['file_id']}/concept/extract-edges")
    assert resp.status_code == 200
    return resp


def _stage2_edges():
    """3 concept edges between confirmed mock terms (词典内关系)."""
    return [
        {"from_term": "死亡转生", "to_term": "业报", "relation": "引发",
         "is_new_relation": False, "rationale": "r1", "confidence": "semantic"},
        {"from_term": "业报", "to_term": "轮回之门", "relation": "依赖",
         "is_new_relation": False, "rationale": "r2", "confidence": "semantic"},
        {"from_term": "死亡转生", "to_term": "轮回之门", "relation": "转化",
         "is_new_relation": False, "rationale": "r3", "confidence": "semantic"},
    ]


class TestEdgeTypeExtension:
    """Metis AC-M5: EdgeType扩展SEMANTIC/RULE/STRUCTURE + GraphEdge新字段向后兼容."""

    def test_edge_type_new_values_exist(self):
        """EdgeType must have SEMANTIC, RULE, STRUCTURE in addition to TREE, CROSS."""
        from app.models.knowledge_graph import EdgeType
        assert EdgeType.TREE.value == "tree"
        assert EdgeType.CROSS.value == "cross"
        assert EdgeType.SEMANTIC.value == "semantic"
        assert EdgeType.RULE.value == "rule"
        assert EdgeType.STRUCTURE.value == "structure"

    def test_graph_edge_new_fields_default(self):
        """GraphEdge must have relation, confidence, confirmed fields with defaults."""
        from app.models.knowledge_graph import GraphEdge
        e = GraphEdge(from_node_id="a", to_node_id="b", edge_type="tree", visual_description="x")
        assert e.relation == ""
        assert e.confidence == ""
        assert e.confirmed is True

    def test_graph_edge_new_fields_settable(self):
        """New fields can be set explicitly."""
        from app.models.knowledge_graph import GraphEdge, EdgeType
        e = GraphEdge(
            from_node_id="a", to_node_id="b",
            edge_type=EdgeType.SEMANTIC,
            relation="引发",
            confidence="semantic",
            confirmed=False,
        )
        assert e.relation == "引发"
        assert e.confidence == "semantic"
        assert e.confirmed is False

    def test_old_graph_json_backward_compat(self):
        """旧graph_json（仅TREE/CROSS边、无relation/confidence/confirmed字段）反序列化零报错."""
        from app.models.knowledge_graph import KnowledgeGraph
        old_data = {
            "scene_id": "test_scene",
            "background_node_id": "bg_123",
            "nodes": {
                "bg_123": {"id": "bg_123", "serial_number": "0", "level": 1, "description": "bg", "status": "pending"},
                "mod1": {"id": "mod1", "serial_number": "1", "level": 2, "description": "mod", "status": "pending"},
            },
            "edges": [
                {"from_node_id": "bg_123", "to_node_id": "mod1", "edge_type": "tree", "visual_description": "包含"},
                {"from_node_id": "mod1", "to_node_id": "bg_123", "edge_type": "cross", "visual_description": "ref"},
            ],
        }
        graph = KnowledgeGraph.from_dict(old_data)
        assert len(graph.edges) == 2
        tree_edge = [e for e in graph.edges if e.edge_type.value == "tree"][0]
        assert tree_edge.relation == ""
        assert tree_edge.confidence == ""
        assert tree_edge.confirmed is True

    def test_graph_edge_serialization_includes_new_fields(self):
        """to_dict serialization includes relation, confidence, confirmed."""
        from app.models.knowledge_graph import GraphEdge, EdgeType, KnowledgeGraph, GraphNode
        graph = KnowledgeGraph(
            scene_id="s1",
            nodes={"a": GraphNode(id="a", serial_number="1", level=1)},
            edges=[
                GraphEdge(from_node_id="a", to_node_id="b", edge_type=EdgeType.SEMANTIC,
                          relation="引发", confidence="semantic", confirmed=False),
            ],
        )
        d = graph.to_dict()
        edge_data = d["edges"][0]
        assert edge_data["relation"] == "引发"
        assert edge_data["confidence"] == "semantic"
        assert edge_data["confirmed"] is False

    def test_graph_from_dict_with_new_fields(self):
        """from_dict handles relation, confidence, confirmed fields."""
        from app.models.knowledge_graph import KnowledgeGraph
        data = {
            "scene_id": "s1",
            "nodes": {
                "a": {"id": "a", "serial_number": "1", "level": 1, "description": "", "status": "pending"},
                "b": {"id": "b", "serial_number": "2", "level": 2, "description": "", "status": "pending"},
            },
            "edges": [
                {
                    "from_node_id": "a", "to_node_id": "b",
                    "edge_type": "semantic", "visual_description": "语义边",
                    "relation": "引发",
                    "confidence": "semantic", "confirmed": False,
                },
            ],
        }
        graph = KnowledgeGraph.from_dict(data)
        assert graph.edges[0].relation == "引发"
        assert graph.edges[0].confidence == "semantic"
        assert graph.edges[0].confirmed is False


class TestFinalizeConceptTerms:
    """T-B 新语义: finalize 只入概念词节点，零概念边."""

    def test_finalize_adds_term_nodes_zero_concept_edges(self, started, monkeypatch):
        """finalize后graph含term:节点（level=4）+ TREE不动 + 零概念边."""
        client, payload = started
        body = _finalize_with_terms(client, payload, monkeypatch)

        assert body.get("concept_terms_count") == 3

        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph").json()
        tree_edges = [e for e in graph["edges"] if e["edge_type"] == "tree"]
        assert len(tree_edges) > 0

        term_nodes = {nid: n for nid, n in graph["nodes"].items() if nid.startswith("term:")}
        assert set(term_nodes) == {f"term:{t}" for t in _MOCK_TERMS}
        for n in term_nodes.values():
            assert n["level"] == 4
            assert n["status"] == "completed"

        concept_edges = [
            e for e in graph["edges"]
            if e.get("from_node_id", "").startswith("term:")
            or e.get("to_node_id", "").startswith("term:")
        ]
        assert len(concept_edges) == 0

    def test_term_nodes_do_not_touch_tree(self, started, monkeypatch):
        """TREE边结构不动（数量与无概念词时一致）."""
        client, payload = started
        _inject_answers(payload)
        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200
        graph_plain = client.get(f"/api/a1/file/{payload['file_id']}/graph").json()
        tree_count_plain = len([e for e in graph_plain["edges"] if e["edge_type"] == "tree"])

        # re-finalize with terms mocked
        monkeypatch.setattr(
            "app.api.a1_routes.extract_concept_terms",
            lambda *a, **kw: _terms_result(_MOCK_TERMS),
        )
        fin2 = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin2.status_code == 200
        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph").json()
        tree_count = len([e for e in graph["edges"] if e["edge_type"] == "tree"])
        assert tree_count == tree_count_plain


class TestConfirmStatePersistence:
    """Metis AC-M6: 确认态持久化——confirm/reject边后re-finalize保留状态."""

    def _setup(self, client, payload, monkeypatch):
        _finalize_with_terms(client, payload, monkeypatch)
        _confirm_all_terms(client, payload)
        _extract_edges(client, payload, monkeypatch, _stage2_edges())

    def test_confirm_state_persists_across_refinalize(self, started, monkeypatch):
        """confirm边 → re-finalize → confirmed状态保留."""
        client, payload = started
        self._setup(client, payload, monkeypatch)

        resp = client.post(
            f"/api/a1/file/{payload['file_id']}/edge/term:死亡转生/term:业报/引发/confirm"
        )
        assert resp.status_code == 200

        # Re-finalize (stage1 mocked)
        monkeypatch.setattr(
            "app.api.a1_routes.extract_concept_terms",
            lambda *a, **kw: _terms_result(_MOCK_TERMS),
        )
        fin2 = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin2.status_code == 200

        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph").json()
        e = [
            e for e in graph["edges"]
            if e["from_node_id"] == "term:死亡转生" and e["relation"] == "引发"
        ][0]
        assert e["confirmed"] is True

    def test_rejected_edges_not_re_appearing(self, started, monkeypatch):
        """rejected_edges中的边在re-finalize时不再出现."""
        client, payload = started
        self._setup(client, payload, monkeypatch)

        from app.api import a1_routes
        key = "term:业报/term:轮回之门/依赖"
        assert key in a1_routes._FILES[payload["file_id"]]["confirmed_edges"]
        resp = client.post(f"/api/a1/file/{payload['file_id']}/edge/{key}/reject")
        assert resp.status_code == 200

        monkeypatch.setattr(
            "app.api.a1_routes.extract_concept_terms",
            lambda *a, **kw: _terms_result(_MOCK_TERMS),
        )
        fin2 = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin2.status_code == 200

        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph").json()
        for edge in graph["edges"]:
            edge_key = f"{edge.get('from_node_id')}/{edge.get('to_node_id')}/{edge.get('relation', '')}"
            assert edge_key != key


class TestDegradation:
    """Metis AC-M7: 降级——阶段1失败 → finalize仍200，纯TREE图，warnings含concept_term."""

    def test_stage1_exception_degrades(self, started, monkeypatch):
        """mock 阶段1抛异常 → finalize仍200，graph纯TREE，warnings含concept_term."""
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
        non_tree = [e for e in graph["edges"] if e.get("edge_type") not in ("tree", "cross")]
        assert len(non_tree) == 0

    def test_stage1_success_false_degrades(self, started, monkeypatch):
        """阶段1返回success=False → finalize仍200，warnings含concept_term."""
        client, payload = started
        _inject_answers(payload)

        monkeypatch.setattr(
            "app.api.a1_routes.extract_concept_terms",
            lambda *a, **kw: _terms_result([], success=False,
                                           warning="concept_term extraction failed: timeout"),
        )

        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200
        body = fin.json()
        assert any("concept_term" in w for w in body.get("warnings", []))

        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph").json()
        non_tree = [e for e in graph["edges"] if e.get("edge_type") not in ("tree", "cross")]
        assert len(non_tree) == 0

    def test_stage2_failure_degrades(self, started, monkeypatch):
        """阶段2失败 → 200 + success=false + warning 含 concept_edge（不抛）."""
        client, payload = started
        _finalize_with_terms(client, payload, monkeypatch)
        _confirm_all_terms(client, payload)

        monkeypatch.setattr(
            "app.api.a1_routes.extract_concept_relations",
            lambda *a, **kw: _edges_v2_result([], success=False,
                                              warning="concept_edge extraction failed: boom"),
        )
        resp = client.post(f"/api/a1/file/{payload['file_id']}/concept/extract-edges")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert "concept_edge" in body["warning"]


class TestEdgeConfirmRejectAPI:
    """Test 4: edge confirm/reject API（端点不变，新流程造边）."""

    def _finalize_with_edges(self, client, payload, monkeypatch):
        _finalize_with_terms(client, payload, monkeypatch)
        _confirm_all_terms(client, payload)
        _extract_edges(client, payload, monkeypatch, _stage2_edges())

    def test_edge_confirm_updates_confirmed_edges(self, started, monkeypatch):
        """POST edge/confirm → _FILES confirmed_edges更新."""
        client, payload = started
        self._finalize_with_edges(client, payload, monkeypatch)

        key = "term:死亡转生/term:业报/引发"
        resp = client.post(f"/api/a1/file/{payload['file_id']}/edge/{key}/confirm")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("confirmed") is True

        from app.api import a1_routes
        rec = a1_routes._FILES[payload["file_id"]]
        assert rec["confirmed_edges"][key]["confirmed"] is True

    def test_edge_reject_removes_from_graph(self, started, monkeypatch):
        """POST edge/reject → rejected_edges记录 + 从graph移除."""
        client, payload = started
        self._finalize_with_edges(client, payload, monkeypatch)

        key = "term:业报/term:轮回之门/依赖"
        resp = client.post(f"/api/a1/file/{payload['file_id']}/edge/{key}/reject")
        assert resp.status_code == 200
        assert resp.json().get("rejected") is True

        from app.api import a1_routes
        assert key in a1_routes._FILES[payload["file_id"]].get("rejected_edges", {})

        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph").json()
        assert not any(
            f"{e['from_node_id']}/{e['to_node_id']}/{e.get('relation', '')}" == key
            for e in graph["edges"]
        )

    def test_edge_reject_then_confirm_restores(self, started, monkeypatch):
        """reject后同key confirm → 从rejected_edges移除（恢复语义）."""
        client, payload = started
        self._finalize_with_edges(client, payload, monkeypatch)

        from app.api import a1_routes
        key = "term:死亡转生/term:业报/引发"

        client.post(f"/api/a1/file/{payload['file_id']}/edge/{key}/reject")
        assert key in a1_routes._FILES[payload["file_id"]]["rejected_edges"]
        assert key not in a1_routes._FILES[payload["file_id"]]["confirmed_edges"]

        resp = client.post(f"/api/a1/file/{payload['file_id']}/edge/{key}/confirm")
        assert resp.status_code == 200
        assert key not in a1_routes._FILES[payload["file_id"]]["rejected_edges"]
        assert key in a1_routes._FILES[payload["file_id"]]["confirmed_edges"]

    def test_edge_reject_list_queryable_via_get_file(self, started, monkeypatch):
        """reject后GET file可查已拒绝清单."""
        client, payload = started
        self._finalize_with_edges(client, payload, monkeypatch)

        key = "term:死亡转生/term:业报/引发"
        client.post(f"/api/a1/file/{payload['file_id']}/edge/{key}/reject")

        resp = client.get(f"/api/a1/file/{payload['file_id']}")
        assert resp.status_code == 200
        assert key in resp.json()["rejected_edges"]


class TestOpenQuestionsAndEdgeStats:
    """open_questions常驻（旧槽位抽取停用后恒为空）+ edge_stats经GET file暴露."""

    def test_open_questions_always_present_empty(self, started, monkeypatch):
        """旧槽位概念边抽取停用后，open_questions常驻且finalize后为空."""
        client, payload = started
        _finalize_with_terms(client, payload, monkeypatch)

        from app.api import a1_routes
        rec = a1_routes._FILES[payload["file_id"]]
        assert rec["open_questions"] == []

        resp = client.get(f"/api/a1/file/{payload['file_id']}")
        assert resp.status_code == 200
        assert resp.json()["open_questions"] == []

    def test_edge_stats_exposed_via_get_file(self, started, monkeypatch):
        """GET file暴露edge_stats（阶段2抽边后含概念边统计）."""
        client, payload = started
        _finalize_with_terms(client, payload, monkeypatch)
        _confirm_all_terms(client, payload)
        _extract_edges(client, payload, monkeypatch, _stage2_edges())

        # confirm 1 of 3 → semantic_total=3, confirmed=1, pending=2
        client.post(f"/api/a1/file/{payload['file_id']}/edge/term:死亡转生/term:业报/引发/confirm")

        resp = client.get(f"/api/a1/file/{payload['file_id']}")
        stats = resp.json()["edge_stats"]
        assert stats["semantic_total"] == 3
        assert stats["semantic_confirmed"] == 1
        assert stats["pending_review"] == 2


class TestNodeReferenceValidation:
    """Test 7: 节点引用校验——阶段2边引用未入图概念词→丢弃该边."""

    def test_edge_with_non_graph_term_dropped(self, started, monkeypatch):
        """extract-edges返回的边from/to不在已入图概念词节点内→丢弃."""
        client, payload = started
        _finalize_with_terms(client, payload, monkeypatch)
        _confirm_all_terms(client, payload)

        edges = [
            {"from_term": "死亡转生", "to_term": "业报", "relation": "引发",
             "is_new_relation": False, "rationale": "valid", "confidence": "semantic"},
            {"from_term": "不存在的词", "to_term": "另一个假词", "relation": "依赖",
             "is_new_relation": False, "rationale": "invalid", "confidence": "semantic"},
        ]
        _extract_edges(client, payload, monkeypatch, edges)

        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph").json()
        term_edges = [e for e in graph["edges"] if e["from_node_id"].startswith("term:")]
        assert len(term_edges) == 1
        assert term_edges[0]["from_node_id"] == "term:死亡转生"


class TestEdgeKeyFormat:
    """Edge key format and URL encoding compatibility (term:A/term:B/relation)."""

    def test_edge_key_format(self, started, monkeypatch):
        """概念边key = term:A/term:B/relation."""
        client, payload = started
        _finalize_with_terms(client, payload, monkeypatch)
        _confirm_all_terms(client, payload)
        _extract_edges(client, payload, monkeypatch, _stage2_edges())

        from app.api import a1_routes
        rec = a1_routes._FILES[payload["file_id"]]
        keys = set(rec.get("confirmed_edges", {}).keys())
        assert "term:死亡转生/term:业报/引发" in keys
        assert "term:业报/term:轮回之门/依赖" in keys

    def test_edge_key_url_encoded_works(self, started, monkeypatch):
        """Edge key with / and : works with URL encoding."""
        client, payload = started
        _finalize_with_terms(client, payload, monkeypatch)
        _confirm_all_terms(client, payload)
        _extract_edges(client, payload, monkeypatch, _stage2_edges())

        import urllib.parse
        key = "term:死亡转生/term:业报/引发"
        encoded_key = urllib.parse.quote(key, safe='')

        resp = client.post(f"/api/a1/file/{payload['file_id']}/edge/{encoded_key}/confirm")
        assert resp.status_code == 200


class TestFinalizeSignature:
    """Regression test: finalize endpoint must be sync (not async) to allow asyncio.run() inside."""

    def test_finalize_must_be_sync_function(self):
        """finalize endpoint must be a regular function (not async) so asyncio.run() works inside.

        This is a regression test for the bug where async def finalize crashed with:
        "asyncio.run() cannot be called from a running event loop"

        The fix: changing from 'async def finalize' to 'def finalize' allows FastAPI to run
        the endpoint in a thread pool (no event loop), making asyncio.run() legal inside
        extract_concept_terms().
        """
        import inspect
        from app.api.a1_routes import finalize

        # Verify finalize is NOT a coroutine function
        assert not inspect.iscoroutinefunction(finalize), \
            "finalize must be a sync function (def, not async def) to allow asyncio.run() inside"
