"""Tests for Task 7: finalize概念边集成 + 确认态持久化 + edge审核API.

RED phase: All tests written BEFORE implementation.
Tests cover:
1. finalize后graph_json含概念边（mock extract_concept_edges）
2. 确认态持久化（confirm 3 边 reject 2 边 → re-finalize → 状态保留）
3. 降级（extractor抛异常 → finalize仍200，纯TREE图，warnings含concept_edge）
4. edge confirm/reject API（_FILES更新）
5. EdgeType向后兼容（旧graph_json无relation/confidence/confirmed字段零报错）
6. open_questions写入_FILES并经GET file暴露
7. 节点引用校验（from/to引用不存在的节点→丢弃该边）
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.domains.creation.a1.concept_edge_extractor import (
    ExtractResult,
    ExtractedEdge,
    AxisAssignment,
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


def _make_extract_result(
    edges=None,
    open_questions=None,
    success=True,
    warning="",
    axis_assignments=None,
):
    """Helper to create an ExtractResult with sensible defaults."""
    return ExtractResult(
        edges=edges or [],
        axis_assignments=axis_assignments or [],
        open_questions=open_questions or [],
        success=success,
        warning=warning,
    )


# Pick a real vocab relation name for tests
_VOCAB_RELATION = "DERIVES→骰子.概率分布"
_VOCAB_RELATION2 = "CONSTRAINS→玩法.主要行为"
_VOCAB_RELATION3 = "INFLUENCES→视觉.建筑风格"


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
            relation=_VOCAB_RELATION,
            confidence="semantic",
            confirmed=False,
        )
        assert e.relation == _VOCAB_RELATION
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
                          relation="测试关系", confidence="semantic", confirmed=False),
            ],
        )
        d = graph.to_dict()
        edge_data = d["edges"][0]
        assert edge_data["relation"] == "测试关系"
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
                    "relation": _VOCAB_RELATION,
                    "confidence": "semantic", "confirmed": False,
                },
            ],
        }
        graph = KnowledgeGraph.from_dict(data)
        assert graph.edges[0].relation == _VOCAB_RELATION
        assert graph.edges[0].confidence == "semantic"
        assert graph.edges[0].confirmed is False


class TestFinalizeConceptEdges:
    """Test 1: finalize后graph_json含概念边."""

    def test_finalize_includes_concept_edges(self, started, monkeypatch):
        """finalize后graph_json含概念边（3 semantic + 1 rule）."""
        client, payload = started
        session = _inject_answers(payload)

        # Use answer keys that will match existing nodes in the graph
        # (module.subfield format, matching _build_graph entry IDs)
        first_module_id = None
        first_sf_id = None
        second_module_id = None
        second_sf_id = None
        from app.domains.creation.seed.a1_question_tree import MODULES
        for m in MODULES:
            if first_module_id is None:
                first_module_id = m["id"]
                first_sf_id = m["fields"][0]["id"]
            elif second_module_id is None:
                second_module_id = m["id"]
                second_sf_id = m["fields"][0]["id"]
                break

        node_a = f"{first_module_id}.{first_sf_id}"
        node_b = f"{second_module_id}.{second_sf_id}"

        mock_edges = [
            ExtractedEdge(from_slot=node_a, to_slot=node_b,
                          relation=_VOCAB_RELATION, confidence="semantic",
                          rationale="test", confirmed=False),
            ExtractedEdge(from_slot=node_b, to_slot=node_a,
                          relation=_VOCAB_RELATION2, confidence="semantic",
                          rationale="test2", confirmed=False),
            ExtractedEdge(from_slot=node_a, to_slot=node_b,
                          relation=_VOCAB_RELATION3, confidence="semantic",
                          rationale="test3", confirmed=False),
            ExtractedEdge(from_slot=node_a, to_slot=node_b,
                          relation=_VOCAB_RELATION, confidence="rule",
                          rationale="rule edge", confirmed=True),
        ]
        mock_result = _make_extract_result(
            edges=mock_edges,
            open_questions=["关于XXX的关系？"],
        )
        monkeypatch.setattr("app.api.a1_routes.extract_concept_edges", lambda *a, **kw: mock_result)

        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200

        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph").json()
        edges = graph["edges"]
        semantic_edges = [e for e in edges if e.get("edge_type") == "semantic"]
        rule_edges = [e for e in edges if e.get("edge_type") == "rule"]
        assert len(semantic_edges) == 3
        assert len(rule_edges) == 1
        # Check fields on semantic edge
        se = semantic_edges[0]
        assert se["relation"] == _VOCAB_RELATION
        assert se["confidence"] == "semantic"
        assert se["confirmed"] is False
        # Check rule edge
        re_ = rule_edges[0]
        assert re_["confirmed"] is True

    def test_finalize_concept_edges_preserve_tree_edges(self, started, monkeypatch):
        """概念边是追加到TREE边之后的，TREE边不动."""
        client, payload = started
        session = _inject_answers(payload)

        from app.domains.creation.seed.a1_question_tree import MODULES
        node_a = f"{MODULES[0]['id']}.{MODULES[0]['fields'][0]['id']}"
        node_b = f"{MODULES[1]['id']}.{MODULES[1]['fields'][0]['id']}"

        mock_edges = [
            ExtractedEdge(from_slot=node_a, to_slot=node_b,
                          relation=_VOCAB_RELATION, confidence="semantic",
                          rationale="test", confirmed=False),
        ]
        mock_result = _make_extract_result(edges=mock_edges)
        monkeypatch.setattr("app.api.a1_routes.extract_concept_edges", lambda *a, **kw: mock_result)

        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200

        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph").json()
        tree_edges = [e for e in graph["edges"] if e.get("edge_type") == "tree"]
        cross_edges = [e for e in graph["edges"] if e.get("edge_type") == "cross"]
        semantic_edges = [e for e in graph["edges"] if e.get("edge_type") == "semantic"]
        assert len(tree_edges) > 0
        assert len(semantic_edges) == 1


class TestConfirmStatePersistence:
    """Metis AC-M6: 确认态持久化——confirm/reject后re-finalize保留状态."""

    def _setup_finalize_with_edges(self, client, payload, monkeypatch):
        """Helper: inject answers, mock extractor, finalize."""
        session = _inject_answers(payload)

        from app.domains.creation.seed.a1_question_tree import MODULES
        node_a = f"{MODULES[0]['id']}.{MODULES[0]['fields'][0]['id']}"
        node_b = f"{MODULES[1]['id']}.{MODULES[1]['fields'][0]['id']}"

        mock_edges = [
            ExtractedEdge(from_slot=node_a, to_slot=node_b,
                          relation=_VOCAB_RELATION, confidence="semantic",
                          rationale="test", confirmed=False),
            ExtractedEdge(from_slot=node_b, to_slot=node_a,
                          relation=_VOCAB_RELATION2, confidence="semantic",
                          rationale="test2", confirmed=False),
            ExtractedEdge(from_slot=node_a, to_slot=node_b,
                          relation=_VOCAB_RELATION3, confidence="semantic",
                          rationale="test3", confirmed=False),
            ExtractedEdge(from_slot=node_a, to_slot=node_b,
                          relation=_VOCAB_RELATION, confidence="rule",
                          rationale="rule edge", confirmed=True),
        ]
        mock_result = _make_extract_result(edges=mock_edges, open_questions=["问题1"])
        monkeypatch.setattr("app.api.a1_routes.extract_concept_edges", lambda *a, **kw: mock_result)

        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200
        return session

    def test_confirm_state_persists_across_refinalize(self, started, monkeypatch):
        """confirm边 → re-finalize → confirmed状态保留."""
        client, payload = started
        self._setup_finalize_with_edges(client, payload, monkeypatch)

        from app.api import a1_routes
        file_rec = a1_routes._FILES[payload["file_id"]]

        # Confirm first edge
        key = list(file_rec["confirmed_edges"].keys())[0]
        resp = client.post(f"/api/a1/file/{payload['file_id']}/edge/{key}/confirm")
        assert resp.status_code == 200

        # Re-finalize with same mock
        mock_edges_2 = [
            ExtractedEdge(from_slot="IP定位.name", to_slot="世界本体.现实规则",
                          relation=_VOCAB_RELATION, confidence="semantic",
                          rationale="test", confirmed=False),
        ]
        mock_result_2 = _make_extract_result(edges=mock_edges_2)
        monkeypatch.setattr("app.api.a1_routes.extract_concept_edges", lambda *a, **kw: mock_result_2)

        fin2 = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin2.status_code == 200

        # The confirmed edge from confirmed_edges should have confirmed=True
        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph").json()
        # Check that confirmed_edges were restored in the new graph
        assert len(a1_routes._FILES[payload["file_id"]]["confirmed_edges"]) >= 1

    def test_rejected_edges_not_re_appearing(self, started, monkeypatch):
        """rejected_edges中的边在re-finalize时不再出现."""
        client, payload = started
        self._setup_finalize_with_edges(client, payload, monkeypatch)

        from app.api import a1_routes
        file_rec = a1_routes._FILES[payload["file_id"]]

        # Reject one edge
        key = list(file_rec["confirmed_edges"].keys())[0]
        resp = client.post(f"/api/a1/file/{payload['file_id']}/edge/{key}/reject")
        assert resp.status_code == 200

        # Re-finalize with same edge
        from app.domains.creation.seed.a1_question_tree import MODULES
        node_a = f"{MODULES[0]['id']}.{MODULES[0]['fields'][0]['id']}"
        node_b = f"{MODULES[1]['id']}.{MODULES[1]['fields'][0]['id']}"
        mock_edges = [
            ExtractedEdge(from_slot=node_a, to_slot=node_b,
                          relation=_VOCAB_RELATION, confidence="semantic",
                          rationale="test", confirmed=False),
        ]
        mock_result = _make_extract_result(edges=mock_edges)
        monkeypatch.setattr("app.api.a1_routes.extract_concept_edges", lambda *a, **kw: mock_result)

        fin2 = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin2.status_code == 200

        # The rejected edge should not be in the graph
        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph").json()
        rejected_keys = set(a1_routes._FILES[payload["file_id"]].get("rejected_edges", {}).keys())
        for edge in graph["edges"]:
            edge_key = f"{edge.get('from_node_id')}/{edge.get('to_node_id')}/{edge.get('relation', '')}"
            assert edge_key not in rejected_keys


class TestDegradation:
    """Metis AC-M7: 降级——extractor异常/success=False → finalize仍200，纯TREE图."""

    def test_extractor_exception_degrades(self, started, monkeypatch):
        """mock extractor抛异常 → finalize仍200，graph纯TREE，warnings含concept_edge."""
        client, payload = started
        _inject_answers(payload)

        def _raise(*a, **kw):
            raise RuntimeError("LLM unavailable")

        monkeypatch.setattr("app.api.a1_routes.extract_concept_edges", _raise)

        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200
        body = fin.json()
        assert any("concept_edge" in w for w in body.get("warnings", []))

        # Graph should be pure TREE/CROSS
        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph").json()
        non_tree = [e for e in graph["edges"] if e.get("edge_type") not in ("tree", "cross")]
        assert len(non_tree) == 0

    def test_extractor_success_false_degrades(self, started, monkeypatch):
        """extractor返回success=False → finalize仍200，warnings含concept_edge."""
        client, payload = started
        _inject_answers(payload)

        mock_result = _make_extract_result(success=False, warning="concept_edge extraction failed: timeout")
        monkeypatch.setattr("app.api.a1_routes.extract_concept_edges", lambda *a, **kw: mock_result)

        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200
        body = fin.json()
        assert any("concept_edge" in w for w in body.get("warnings", []))

        # Graph should be pure TREE/CROSS
        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph").json()
        non_tree = [e for e in graph["edges"] if e.get("edge_type") not in ("tree", "cross")]
        assert len(non_tree) == 0


class TestEdgeConfirmRejectAPI:
    """Test 4: edge confirm/reject API."""

    def _finalize_with_edges(self, client, payload, monkeypatch):
        """Helper: finalize with known concept edges."""
        session = _inject_answers(payload)

        from app.domains.creation.seed.a1_question_tree import MODULES
        node_a = f"{MODULES[0]['id']}.{MODULES[0]['fields'][0]['id']}"
        node_b = f"{MODULES[1]['id']}.{MODULES[1]['fields'][0]['id']}"

        mock_edges = [
            ExtractedEdge(from_slot=node_a, to_slot=node_b,
                          relation=_VOCAB_RELATION, confidence="semantic",
                          rationale="test", confirmed=False),
            ExtractedEdge(from_slot=node_b, to_slot=node_a,
                          relation=_VOCAB_RELATION2, confidence="rule",
                          rationale="test2", confirmed=True),
        ]
        mock_result = _make_extract_result(
            edges=mock_edges,
            open_questions=["关于XXX的关系？"],
        )
        monkeypatch.setattr("app.api.a1_routes.extract_concept_edges", lambda *a, **kw: mock_result)

        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200
        return fin.json()

    def test_edge_confirm_updates_confirmed_edges(self, started, monkeypatch):
        """POST edge/confirm → _FILES confirmed_edges更新."""
        client, payload = started
        self._finalize_with_edges(client, payload, monkeypatch)

        from app.api import a1_routes
        file_rec = a1_routes._FILES[payload["file_id"]]
        assert len(file_rec.get("confirmed_edges", {})) > 0

        # Confirm first edge
        key = list(file_rec["confirmed_edges"].keys())[0]
        resp = client.post(f"/api/a1/file/{payload['file_id']}/edge/{key}/confirm")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("confirmed") is True
        assert key in file_rec["confirmed_edges"]

    def test_edge_reject_removes_from_graph(self, started, monkeypatch):
        """POST edge/reject → rejected_edges记录."""
        client, payload = started
        self._finalize_with_edges(client, payload, monkeypatch)

        from app.api import a1_routes
        file_rec = a1_routes._FILES[payload["file_id"]]

        # Reject first edge
        key = list(file_rec.get("confirmed_edges", {}).keys())[0]
        resp = client.post(f"/api/a1/file/{payload['file_id']}/edge/{key}/reject")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("rejected") is True

        # Check _FILES
        assert key in file_rec.get("rejected_edges", {})

    def test_edge_reject_then_confirm_restores(self, started, monkeypatch):
        """reject后同key confirm → 从rejected_edges移除（恢复语义）."""
        client, payload = started
        self._finalize_with_edges(client, payload, monkeypatch)

        from app.api import a1_routes
        file_rec = a1_routes._FILES[payload["file_id"]]
        key = list(file_rec["confirmed_edges"].keys())[0]

        # Reject
        client.post(f"/api/a1/file/{payload['file_id']}/edge/{key}/reject")
        assert key in file_rec["rejected_edges"]
        assert key not in file_rec["confirmed_edges"]

        # Confirm (restore)
        resp = client.post(f"/api/a1/file/{payload['file_id']}/edge/{key}/confirm")
        assert resp.status_code == 200
        assert key not in file_rec["rejected_edges"]
        assert key in file_rec["confirmed_edges"]

    def test_edge_reject_list_queryable_via_get_file(self, started, monkeypatch):
        """reject后GET file可查已拒绝清单."""
        client, payload = started
        self._finalize_with_edges(client, payload, monkeypatch)

        from app.api import a1_routes
        file_rec = a1_routes._FILES[payload["file_id"]]
        key = list(file_rec["confirmed_edges"].keys())[0]

        # Reject
        client.post(f"/api/a1/file/{payload['file_id']}/edge/{key}/reject")

        # GET file should expose rejected_edges
        resp = client.get(f"/api/a1/file/{payload['file_id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert "rejected_edges" in body
        assert key in body["rejected_edges"]


class TestOpenQuestionsInFiles:
    """Test 6: open_questions写入_FILES并经GET file暴露."""

    def test_finalize_writes_open_questions(self, started, monkeypatch):
        """finalize后open_questions写入_FILES."""
        client, payload = started
        _inject_answers(payload)

        mock_result = _make_extract_result(
            open_questions=["关于力量与骰子的关系？", "视觉风格如何影响建筑？"],
        )
        monkeypatch.setattr("app.api.a1_routes.extract_concept_edges", lambda *a, **kw: mock_result)

        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200

        from app.api import a1_routes
        file_rec = a1_routes._FILES[payload["file_id"]]
        assert file_rec["open_questions"] == ["关于力量与骰子的关系？", "视觉风格如何影响建筑？"]

    def test_open_questions_exposed_via_get_file(self, started, monkeypatch):
        """GET file暴露open_questions."""
        client, payload = started
        _inject_answers(payload)

        mock_result = _make_extract_result(open_questions=["问题A"])
        monkeypatch.setattr("app.api.a1_routes.extract_concept_edges", lambda *a, **kw: mock_result)

        client.post(f"/api/a1/file/{payload['file_id']}/finalize")

        resp = client.get(f"/api/a1/file/{payload['file_id']}")
        assert resp.status_code == 200
        assert resp.json()["open_questions"] == ["问题A"]

    def test_edge_stats_exposed_via_get_file(self, started, monkeypatch):
        """GET file暴露edge_stats（finalized后有真实数据）."""
        client, payload = started
        session = _inject_answers(payload)

        from app.domains.creation.seed.a1_question_tree import MODULES
        node_a = f"{MODULES[0]['id']}.{MODULES[0]['fields'][0]['id']}"
        node_b = f"{MODULES[1]['id']}.{MODULES[1]['fields'][0]['id']}"

        mock_edges = [
            ExtractedEdge(from_slot=node_a, to_slot=node_b, relation=_VOCAB_RELATION,
                          confidence="semantic", rationale="", confirmed=False),
            ExtractedEdge(from_slot=node_a, to_slot=node_b, relation=_VOCAB_RELATION2,
                          confidence="semantic", rationale="", confirmed=True),
            ExtractedEdge(from_slot=node_a, to_slot=node_b, relation=_VOCAB_RELATION,
                          confidence="rule", rationale="", confirmed=True),
            ExtractedEdge(from_slot=node_a, to_slot=node_b, relation="SUPPORTS→视觉.材质偏好",
                          confidence="structure", rationale="", confirmed=True),
        ]
        mock_result = _make_extract_result(edges=mock_edges)
        monkeypatch.setattr("app.api.a1_routes.extract_concept_edges", lambda *a, **kw: mock_result)

        client.post(f"/api/a1/file/{payload['file_id']}/finalize")

        resp = client.get(f"/api/a1/file/{payload['file_id']}")
        stats = resp.json()["edge_stats"]
        assert stats["semantic_total"] == 2
        assert stats["semantic_confirmed"] == 1
        assert stats["rule_total"] == 1
        assert stats["structure_total"] == 1
        assert stats["pending_review"] == 1


class TestNodeReferenceValidation:
    """Test 7: 节点引用校验——from/to引用不存在的节点→丢弃该边."""

    def test_edge_with_nonexistent_node_dropped(self, started, monkeypatch):
        """概念边from/to引用不存在的节点→丢弃该边."""
        client, payload = started
        session = _inject_answers(payload)

        from app.domains.creation.seed.a1_question_tree import MODULES
        node_a = f"{MODULES[0]['id']}.{MODULES[0]['fields'][0]['id']}"

        mock_edges = [
            ExtractedEdge(from_slot=node_a, to_slot=f"{MODULES[0]['id']}.{MODULES[0]['fields'][1]['id']}",
                          relation=_VOCAB_RELATION, confidence="semantic",
                          rationale="valid edge", confirmed=False),
            ExtractedEdge(from_slot="完全不存在的模块.不存在的字段", to_slot="另一个假的.字段",
                          relation=_VOCAB_RELATION2, confidence="semantic",
                          rationale="invalid nodes", confirmed=False),
        ]
        mock_result = _make_extract_result(edges=mock_edges)
        monkeypatch.setattr("app.api.a1_routes.extract_concept_edges", lambda *a, **kw: mock_result)

        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200

        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph").json()
        semantic_edges = [e for e in graph["edges"] if e.get("edge_type") == "semantic"]
        assert len(semantic_edges) == 1
        assert semantic_edges[0]["from_node_id"] == node_a


class TestEdgeKeyFormat:
    """Edge key format and URL encoding compatibility."""

    def test_edge_key_format(self, started, monkeypatch):
        """Edge key is (from, to, relation) triple string."""
        client, payload = started
        _inject_answers(payload)

        from app.domains.creation.seed.a1_question_tree import MODULES
        node_a = f"{MODULES[0]['id']}.{MODULES[0]['fields'][0]['id']}"
        node_b = f"{MODULES[1]['id']}.{MODULES[1]['fields'][0]['id']}"

        mock_edges = [
            ExtractedEdge(from_slot=node_a, to_slot=node_b,
                          relation=_VOCAB_RELATION, confidence="semantic",
                          rationale="test", confirmed=False),
        ]
        mock_result = _make_extract_result(edges=mock_edges)
        monkeypatch.setattr("app.api.a1_routes.extract_concept_edges", lambda *a, **kw: mock_result)

        client.post(f"/api/a1/file/{payload['file_id']}/finalize")

        from app.api import a1_routes
        file_rec = a1_routes._FILES[payload["file_id"]]
        keys = list(file_rec.get("confirmed_edges", {}).keys())
        assert len(keys) == 1
        assert _VOCAB_RELATION in keys[0]
        assert node_a in keys[0]
        assert node_b in keys[0]

    def test_edge_key_url_encoded_works(self, started, monkeypatch):
        """Edge key with / and . works with URL encoding (encodeURIComponent compatible)."""
        client, payload = started
        _inject_answers(payload)

        from app.domains.creation.seed.a1_question_tree import MODULES
        node_a = f"{MODULES[0]['id']}.{MODULES[0]['fields'][0]['id']}"
        node_b = f"{MODULES[1]['id']}.{MODULES[1]['fields'][0]['id']}"

        mock_edges = [
            ExtractedEdge(from_slot=node_a, to_slot=node_b,
                          relation=_VOCAB_RELATION2, confidence="semantic",
                          rationale="test", confirmed=False),
        ]
        mock_result = _make_extract_result(edges=mock_edges)
        monkeypatch.setattr("app.api.a1_routes.extract_concept_edges", lambda *a, **kw: mock_result)

        client.post(f"/api/a1/file/{payload['file_id']}/finalize")

        from app.api import a1_routes
        file_rec = a1_routes._FILES[payload["file_id"]]
        key = list(file_rec["confirmed_edges"].keys())[0]

        # URL-encode the key
        import urllib.parse
        encoded_key = urllib.parse.quote(key, safe='')

        resp = client.post(f"/api/a1/file/{payload['file_id']}/edge/{encoded_key}/confirm")
        assert resp.status_code == 200
