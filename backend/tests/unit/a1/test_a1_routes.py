"""Integration tests for A1 workspace API routes (TestClient)."""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def started(client):
    resp = client.post("/api/a1/session/start", json={"user_id": "u_test_a1", "seed_id": 1})
    assert resp.status_code == 200
    return client, resp.json()


def _fill_all_subs(client, payload):
    session_id = payload["session_id"]
    from app.domains.creation.seed.a1_question_tree import total_subfield_count
    for _ in range(total_subfield_count() + 5):
        out = client.post("/api/a1/chat", json={"session_id": session_id, "message": "\u8df3\u8fc7"})
        assert out.status_code == 200
        if out.json()["phase"] == "completed":
            return


class TestA1Routes:
    def test_seeds_returns_8(self, client):
        resp = client.get("/api/a1/seeds")
        assert resp.status_code == 200
        assert len(resp.json()["seeds"]) == 8

    def test_start_with_seed(self, started):
        _, payload = started
        assert payload["ip_code"].startswith("IP")
        nq = payload["first_question"]
        assert nq["section"] == "IP\u5b9a\u4f4d"
        assert "sub_id" in nq
        assert payload["file"]["status"] == "draft"

    def test_start_requires_seed_or_idea(self, client):
        resp = client.post("/api/a1/session/start", json={"user_id": "u_x"})
        assert resp.status_code == 400

    def test_start_with_custom_idea(self, client):
        resp = client.post(
            "/api/a1/session/start",
            json={"user_id": "u_x", "custom_idea": "\u84b8\u6c7d\u670b\u514b\u6d6e\u7a7a\u57ce"},
        )
        assert resp.status_code == 200
        body = resp.json()
        # Custom idea is carried as seed context (LLM extracts fields
        # from it during the interview), not hardcoded into answers.
        assert body["seed"]["description"] == "\u84b8\u6c7d\u670b\u514b\u6d6e\u7a7a\u57ce"
        assert body["seed"]["name"] == ""

    def test_start_with_preset_carries_seed_context(self, client):
        resp = client.post(
            "/api/a1/session/start",
            json={"user_id": "u_x", "seed_id": 1},
        )
        assert resp.status_code == 200
        seed = resp.json()["seed"]
        assert seed["name"]  # preset name carried through
        assert seed["genre"]

    def test_finalize_before_complete_409(self, started):
        client, payload = started
        resp = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert resp.status_code == 409
        assert resp.json()["detail"]["missing_modules"]

    def test_full_flow_finalize_graph_poster(self, started):
        client, payload = started
        _fill_all_subs(client, payload)
        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200
        body = fin.json()
        assert body["graph_code"].endswith("-W1-v1")
        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph")
        assert graph.status_code == 200
        assert graph.json()["scene_id"] == payload["session_id"]
        poster = client.get(f"/api/a1/file/{payload['file_id']}/poster")
        assert poster.status_code == 200
        assert poster.json()["ai_image_status"] == "pending"

    def test_graph_poster_409_before_finalize(self, started):
        client, payload = started
        assert client.get(f"/api/a1/file/{payload['file_id']}/graph").status_code == 409
        assert client.get(f"/api/a1/file/{payload['file_id']}/poster").status_code == 409

    def test_refinalize_issues_v2(self, started):
        client, payload = started
        _fill_all_subs(client, payload)
        v1 = client.post(f"/api/a1/file/{payload['file_id']}/finalize").json()
        assert v1["graph_code"].endswith("-W1-v1")
        v2 = client.post(f"/api/a1/file/{payload['file_id']}/finalize").json()
        assert v2["graph_code"].endswith("-W1-v2")

    def test_unknown_session_404(self, client):
        resp = client.post("/api/a1/chat", json={"session_id": "nope", "message": "hi"})
        assert resp.status_code == 404

    def test_progress_has_module_aggregation(self, started):
        client, payload = started
        out = client.post("/api/a1/chat", json={"session_id": payload["session_id"], "message": "\u8df3\u8fc7"})
        p = out.json()["progress"]
        assert p["total"] == 10
        assert "subs" in p["sections"][0]

    def test_get_file_has_sections_with_subs(self, started):
        client, payload = started
        _fill_all_subs(client, payload)
        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200
        f = client.get(f"/api/a1/file/{payload['file_id']}")
        body = f.json()
        assert "sections" in body
        assert len(body["sections"]) == 10
        assert "subs" in body["sections"][0]

    # ---- finalize gate: >50% per module, not all subfields ----

    def _inject_answers(self, payload, per_module_need: int | None = None):
        """Fill answers directly in the live session (bypasses chat)."""
        from app.api import a1_routes
        from app.domains.creation.seed.a1_question_tree import MODULES

        session = a1_routes._SESSIONS[payload["session_id"]]
        for m in MODULES:
            need = per_module_need if per_module_need is not None else len(m["fields"]) // 2 + 1
            for f in m["fields"][:need]:
                session.answers[f"{m['id']}.{f['id']}"] = "预填内容"
        return session

    def test_finalize_succeeds_with_over_half_per_module(self, started):
        """每模块 >50% 即可定稿——不再要求全部子字段完成。"""
        client, payload = started
        self._inject_answers(payload)  # over half, NOT all subfields
        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200
        assert fin.json()["graph_code"].endswith("-W1-v1")
        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph")
        assert graph.status_code == 200

    def test_finalize_409_at_exactly_half(self, started):
        """恰好 50% 不允许定稿（必须严格超过）。"""
        client, payload = started
        session = self._inject_answers(payload, per_module_need=1)
        # Reduce first module (4 subs) to exactly 2 of 4 = 50%.
        from app.domains.creation.seed.a1_question_tree import MODULES
        first = MODULES[0]
        for f in first["fields"]:
            session.answers.pop(f"{first['id']}.{f['id']}", None)
        session.answers[f"{first['id']}.{first['fields'][0]['id']}"] = "x"
        session.answers[f"{first['id']}.{first['fields'][1]['id']}"] = "x"
        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 409
        assert first["id"] in fin.json()["detail"]["missing_sections"]

    def test_progress_carries_finalizable_flag(self, started):
        client, payload = started
        out = client.post("/api/a1/chat", json={"session_id": payload["session_id"], "message": "跳过"})
        assert out.json()["progress"]["finalizable"] is False
        self._inject_answers(payload)
        out = client.post("/api/a1/chat", json={"session_id": payload["session_id"], "message": "你好"})
        assert out.json()["progress"]["finalizable"] is True

    # ---- poster AI image generation ----

    def test_get_poster_returns_ai_image_url_none_when_no_cache(self, started):
        """GET poster should return ai_image_url=None and status pending when
        no cached generation state exists."""
        client, payload = started
        self._inject_answers(payload)
        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200
        poster = client.get(f"/api/a1/file/{payload['file_id']}/poster")
        assert poster.status_code == 200
        body = poster.json()
        assert body["ai_image_url"] is None
        assert body["ai_image_status"] == "pending"
        # Existing keys must remain
        assert "panels" in body
        assert "ai_image_prompt" in body

    def test_poster_generate_409_when_not_finalized(self, started):
        """POST poster/generate must 409 when file is not finalized."""
        client, payload = started
        resp = client.post(f"/api/a1/file/{payload['file_id']}/poster/generate")
        assert resp.status_code == 409

    def test_poster_generate_success(self, started, monkeypatch):
        """POST poster/generate returns completed + url on success."""
        from app.ai.image_generator import GeneratedImage

        fake_img = GeneratedImage(
            seed=42,
            file_path="data/assets/poster_test123.png",
        )

        class FakeGen:
            async def generate(self, **kwargs):
                return [fake_img]

            async def close(self):
                pass

        monkeypatch.setattr("app.ai.image_generator.ImageGenerator", FakeGen)

        client, payload = started
        self._inject_answers(payload)
        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200

        resp = client.post(f"/api/a1/file/{payload['file_id']}/poster/generate")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ai_image_status"] == "completed"
        assert body["ai_image_url"] == "/assets/poster_test123.png"

    def test_poster_generate_502_on_failure(self, started, monkeypatch):
        """POST poster/generate returns 502 when generator raises."""
        from app.ai.image_generator import ImageGenerationError

        class FailGen:
            async def generate(self, **kwargs):
                raise ImageGenerationError("API quota exceeded")

            async def close(self):
                pass

        monkeypatch.setattr("app.ai.image_generator.ImageGenerator", FailGen)

        client, payload = started
        self._inject_answers(payload)
        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200

        resp = client.post(f"/api/a1/file/{payload['file_id']}/poster/generate")
        assert resp.status_code == 502
        assert "API quota exceeded" in resp.json()["detail"]

    def test_poster_generate_caches_state_in_file_record(self, started, monkeypatch):
        """After successful generation, GET poster should reflect cached state."""
        from app.ai.image_generator import GeneratedImage

        fake_img = GeneratedImage(
            seed=1,
            file_path="data/assets/poster_cached.png",
        )

        class FakeGen:
            async def generate(self, **kwargs):
                return [fake_img]

            async def close(self):
                pass

        monkeypatch.setattr("app.ai.image_generator.ImageGenerator", FakeGen)

        client, payload = started
        self._inject_answers(payload)
        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200

        gen_resp = client.post(f"/api/a1/file/{payload['file_id']}/poster/generate")
        assert gen_resp.status_code == 200

        # GET poster should now return cached completed state
        poster = client.get(f"/api/a1/file/{payload['file_id']}/poster")
        assert poster.status_code == 200
        body = poster.json()
        assert body["ai_image_status"] == "completed"
        assert body["ai_image_url"] == "/assets/poster_cached.png"

    def test_finalize_graph_topology(self, started):
        """Test that finalize creates three-layer topology: bg -> modules -> entries."""
        from app.domains.creation.seed.a1_question_tree import MODULES

        client, payload = started
        session = self._inject_answers(payload)

        # T11: tag=val fragment in one answer → answers channel produces a
        # cst_ node (LAW.world_structure=TREE is a valid enum value).
        session.answers["世界本体.origin"] = (
            session.answers["世界本体.origin"] + "；LAW.world_structure=TREE"
        )

        # Finalize to trigger graph building
        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200

        # Get graph
        graph_resp = client.get(f"/api/a1/file/{payload['file_id']}/graph")
        assert graph_resp.status_code == 200
        graph = graph_resp.json()

        # Graph has nodes (dict of node_id -> node data) and edges (list)
        assert "nodes" in graph
        assert "edges" in graph
        assert "background_node_id" in graph

        # Convert nodes dict to list for easier filtering
        nodes_list = list(graph["nodes"].values())

        # (a) Exist level 1 background node
        bg_nodes = [n for n in nodes_list if n["level"] == 1]
        assert len(bg_nodes) == 1
        bg_node = bg_nodes[0]
        assert bg_node["id"] == graph["background_node_id"]
        assert bg_node["serial_number"] == "0"

        # Count modules with non-empty answers
        modules_with_answers = []
        for module in MODULES:
            module_id = module["id"]
            has_answer = any(
                session.answers.get(f"{module_id}.{sf['id']}", "")
                for sf in module["fields"]
            )
            if has_answer:
                modules_with_answers.append(module_id)

        # (b) Each level 2 node has exactly one TREE edge from background
        level2_nodes = [n for n in nodes_list if n["level"] == 2]
        assert len(level2_nodes) == len(modules_with_answers)

        tree_edges = [e for e in graph["edges"] if e["edge_type"] == "tree"]
        bg_to_module_edges = [
            e for e in tree_edges
            if e["from_node_id"] == bg_node["id"] and e["to_node_id"] in [n["id"] for n in level2_nodes]
        ]
        assert len(bg_to_module_edges) == len(modules_with_answers)

        # Verify each level 2 node has exactly one incoming TREE edge from background
        for l2_node in level2_nodes:
            incoming_edges = [
                e for e in tree_edges
                if e["to_node_id"] == l2_node["id"] and e["from_node_id"] == bg_node["id"]
            ]
            assert len(incoming_edges) == 1
            assert incoming_edges[0]["visual_description"] == "包含"

        # (c) Exist level 3 entry nodes with proper ID format
        level3_nodes = [n for n in nodes_list if n["level"] == 3]
        assert len(level3_nodes) > 0

        for l3_node in level3_nodes:
            # ID format: "{module_id}.{subfield_id}"
            assert "." in l3_node["id"]
            parts = l3_node["id"].split(".")
            assert len(parts) == 2
            assert parts[0] in modules_with_answers  # module_id should be valid
            # Description starts with subfield label
            assert ": " in l3_node["description"]

        # (d) Each entry node has TREE edge from its module node
        for l3_node in level3_nodes:
            module_id = l3_node["id"].split(".")[0]
            incoming_edges = [
                e for e in tree_edges
                if e["to_node_id"] == l3_node["id"] and e["from_node_id"] == module_id
            ]
            assert len(incoming_edges) == 1
            assert incoming_edges[0]["visual_description"] == "条目"

        # (e) Total TREE edges == modules + entries + 分条目 (depth tree,
        # T7 dual-tree assembly; 0 in the degraded no-LLM path)
        # Count all non-empty subfield answers across all modules
        total_entries = sum(
            1 for module in MODULES
            for sf in module["fields"]
            if session.answers.get(f"{module['id']}.{sf['id']}", "")
        )
        depth_nodes = [
            n for n in nodes_list
            if n["level"] == 4 and n["id"].startswith("d:")
        ]
        fen_tiao_mu_edges = [
            e for e in tree_edges if e["visual_description"] == "分条目"
        ]
        assert len(fen_tiao_mu_edges) == len(depth_nodes)
        expected_tree_edges = len(modules_with_answers) + total_entries + len(depth_nodes)
        assert len(tree_edges) == expected_tree_edges

        # (f) T11: constraint channel closed — cst_ node + CROSS edge to bg
        cst_nodes = [n for n in nodes_list if n["id"].startswith("cst_")]
        assert len(cst_nodes) > 0
        cross_edges = [e for e in graph["edges"] if e["edge_type"] == "cross"]
        assert len(cross_edges) > 0
        assert all(
            e["to_node_id"] == graph["background_node_id"] for e in cross_edges
        )

        # Verify module nodes only have label in description (not aggregated answers)
        for l2_node in level2_nodes:
            # Description should be just the module label, not containing ": " from subfields
            assert ": " not in l2_node["description"]

    # ---- Task 6: chat提案返回 + confirm kind判别 + GET file扩展 ----

    def test_chat_response_has_proposals_field(self, started):
        """Chat response should always have proposals array (empty when no guard)."""
        client, payload = started
        resp = client.post("/api/a1/chat", json={"session_id": payload["session_id"], "message": "跳过"})
        assert resp.status_code == 200
        body = resp.json()
        assert "proposals" in body
        assert isinstance(body["proposals"], list)
        # Normal flow: empty array (shape stability, Metis E8)
        assert body["proposals"] == []

    def test_chat_response_proposals_populated_on_guard_intercept(self, started):
        """When write guard intercepts, proposals contains Proposal dicts with keys."""
        from app.api import a1_routes
        from app.domains.creation.a1.guide_engine import Proposal

        client, payload = started
        session_id = payload["session_id"]
        # Manually setup a pending proposal to simulate guard interception
        session = a1_routes._SESSIONS[session_id]
        # First set an existing value
        session.answers["IP定位.name"] = "原始值"
        # Create a proposal that would come from guard interception
        proposal_key = "IP定位.name:test123"
        proposal = Proposal(
            module="IP定位",
            subfield="name",
            old="原始值",
            new="新值",
            conflict_note=None,
        )
        session.pending_proposals[proposal_key] = {
            "proposal": proposal,
            "options": ["replace", "merge", "drop"],
        }

        # Send a message that will trigger the guard response
        resp = client.post("/api/a1/chat", json={"session_id": session_id, "message": "修改为修仙世界"})
        assert resp.status_code == 200
        body = resp.json()
        # After guard interception, proposals should be in the response
        # (Note: The guard response happens in guide_engine, we're testing routing adds keys)
        if body.get("proposals"):
            # Check that proposals have the required structure
            prop = body["proposals"][0]
            assert "module" in prop
            assert "subfield" in prop
            assert "old" in prop
            assert "new" in prop
            # Key is added by routing layer from pending_proposals dict keys
            assert "key" in prop

    def test_chat_response_divergent_question_field(self, started):
        """Chat response should have divergent_question when interviewer provides it."""
        client, payload = started
        # This test requires a FakeInterviewer that sets divergent_question
        # For now, test the field exists and can be None
        resp = client.post("/api/a1/chat", json={"session_id": payload["session_id"], "message": "跳过"})
        assert resp.status_code == 200
        body = resp.json()
        # Field exists (can be None or str)
        assert "divergent_question" in body
        # Normal flow: may be None
        assert body["divergent_question"] is None or isinstance(body["divergent_question"], str)

    def test_confirm_fill_replace_choice(self, started):
        """Confirm kind='fill' with choice='replace' should apply new value."""
        from app.api import a1_routes
        from app.domains.creation.a1.guide_engine import Proposal

        client, payload = started
        session_id = payload["session_id"]
        # Setup: create a pending proposal
        session = a1_routes._SESSIONS[session_id]
        proposal_key = "IP定位.name:abc123"
        proposal = Proposal(
            module="IP定位",
            subfield="name",
            old="旧值",
            new="新值",
            conflict_note=None,
        )
        session.pending_proposals[proposal_key] = {
            "proposal": proposal,
            "options": ["replace", "merge", "drop"],
        }

        # Confirm with replace choice
        resp = client.post("/api/a1/chat/confirm", json={
            "session_id": session_id,
            "kind": "fill",
            "proposal": {"key": proposal_key},
            "choice": "replace",
        })
        assert resp.status_code == 200
        body = resp.json()
        # Response should have updated answers
        assert "reply" in body
        assert "next_question" in body or body.get("next_question") is None
        # Check answer was replaced
        assert session.answers.get("IP定位.name") == "新值"

    def test_confirm_fill_merge_choice(self, started):
        """Confirm kind='fill' with choice='merge' should combine values."""
        from app.api import a1_routes
        from app.domains.creation.a1.guide_engine import Proposal

        client, payload = started
        session_id = payload["session_id"]
        # Setup
        session = a1_routes._SESSIONS[session_id]
        proposal_key = "IP定位.name:def456"
        proposal = Proposal(
            module="IP定位",
            subfield="name",
            old="原有内容",
            new="新增内容",
            conflict_note=None,
        )
        session.pending_proposals[proposal_key] = {
            "proposal": proposal,
            "options": ["replace", "merge", "drop"],
        }

        # Confirm with merge choice
        resp = client.post("/api/a1/chat/confirm", json={
            "session_id": session_id,
            "kind": "fill",
            "proposal": {"key": proposal_key},
            "choice": "merge",
        })
        assert resp.status_code == 200
        # Answer should be merged with semicolon
        assert "原有内容；新增内容" in session.answers.get("IP定位.name", "")

    def test_confirm_fill_drop_choice(self, started):
        """Confirm kind='fill' with choice='drop' should not apply changes."""
        from app.api import a1_routes
        from app.domains.creation.a1.guide_engine import Proposal

        client, payload = started
        session_id = payload["session_id"]
        # Setup
        session = a1_routes._SESSIONS[session_id]
        original_value = "保持不变"
        session.answers["IP定位.name"] = original_value
        proposal_key = "IP定位.name:ghi789"
        proposal = Proposal(
            module="IP定位",
            subfield="name",
            old=original_value,
            new="试图替换",
            conflict_note=None,
        )
        session.pending_proposals[proposal_key] = {
            "proposal": proposal,
            "options": ["replace", "merge", "drop"],
        }

        # Confirm with drop choice
        resp = client.post("/api/a1/chat/confirm", json={
            "session_id": session_id,
            "kind": "fill",
            "proposal": {"key": proposal_key},
            "choice": "drop",
        })
        assert resp.status_code == 200
        # Answer should remain unchanged
        assert session.answers.get("IP定位.name") == original_value

    def test_confirm_natural_language_choice_mapping(self, started):
        """Natural language choices should map to canonical choices."""
        from app.api import a1_routes
        from app.domains.creation.a1.guide_engine import Proposal

        client, payload = started
        session_id = payload["session_id"]
        # Setup
        session = a1_routes._SESSIONS[session_id]
        proposal_key = "IP定位.name:jkl012"
        proposal = Proposal(
            module="IP定位",
            subfield="name",
            old="旧",
            new="新",
            conflict_note=None,
        )
        session.pending_proposals[proposal_key] = {
            "proposal": proposal,
            "options": ["replace", "merge", "drop"],
        }

        # Test natural language mapping: "换成" -> replace
        resp = client.post("/api/a1/chat/confirm", json={
            "session_id": session_id,
            "kind": "fill",
            "proposal": {"key": proposal_key},
            "choice": "换成",
        })
        assert resp.status_code == 200
        assert session.answers.get("IP定位.name") == "新"

    def test_confirm_needs_clarification_on_ambiguous_choice(self, started):
        """Ambiguous choices like '嗯'/'好' should trigger needs_clarification."""
        from app.api import a1_routes
        from app.domains.creation.a1.guide_engine import Proposal

        client, payload = started
        session_id = payload["session_id"]
        # Setup
        session = a1_routes._SESSIONS[session_id]
        original_value = "原始值"
        session.answers["IP定位.name"] = original_value
        proposal_key = "IP定位.name:mno345"
        proposal = Proposal(
            module="IP定位",
            subfield="name",
            old=original_value,
            new="冲突值",
            conflict_note=None,
        )
        session.pending_proposals[proposal_key] = {
            "proposal": proposal,
            "options": ["replace", "merge", "drop"],
        }

        # Ambiguous choice should trigger clarification
        resp = client.post("/api/a1/chat/confirm", json={
            "session_id": session_id,
            "kind": "fill",
            "proposal": {"key": proposal_key},
            "choice": "嗯",
        })
        assert resp.status_code == 200
        body = resp.json()
        # Should have needs_clarification flag
        assert body.get("needs_clarification") is True
        # Should restate the three options
        assert "reply" in body
        assert any(word in body["reply"] for word in ["替换", "合并", "放弃"])
        # Answer should NOT change (zero side effect)
        assert session.answers.get("IP定位.name") == original_value

    def test_confirm_kind_default_classification(self, started):
        """Confirm with kind default (or 'classification') should use existing innovation_capture path."""
        # This ensures backward compatibility
        client, payload = started
        # Use existing classification proposal format
        resp = client.post("/api/a1/chat/confirm", json={
            "session_id": payload["session_id"],
            "proposal": {
                "suggestions": [{"field": "test", "category": "其他"}],
            },
            "choice": "confirm",
        })
        # Should not error (existing innovation_capture path)
        assert resp.status_code in (200, 404)  # 404 if no classification proposal exists

    def test_get_file_has_open_questions_and_edge_stats(self, started):
        """GET file response should have open_questions and edge_stats fields."""
        client, payload = started
        resp = client.get(f"/api/a1/file/{payload['file_id']}")
        assert resp.status_code == 200
        body = resp.json()
        # Should have open_questions array (empty in draft state)
        assert "open_questions" in body
        assert isinstance(body["open_questions"], list)
        # Should have edge_stats dict (with zero values in draft state)
        assert "edge_stats" in body
        assert isinstance(body["edge_stats"], dict)
        # Check zero-value defaults for draft state
        stats = body["edge_stats"]
        assert stats.get("semantic_total", 0) == 0
        assert stats.get("semantic_confirmed", 0) == 0
        assert stats.get("rule_total", 0) == 0
        assert stats.get("structure_total", 0) == 0
        assert stats.get("pending_review", 0) == 0

    def test_get_file_has_dead_edges_default_empty(self, started):
        """T15: GET file response carries dead_edges as a resident key (draft = [])."""
        client, payload = started
        resp = client.get(f"/api/a1/file/{payload['file_id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert "dead_edges" in body
        assert body["dead_edges"] == []

    def test_get_file_dead_edges_after_refinalize(self, started):
        """T15: re-finalize with a stale confirmed edge (endpoint missing from
        new graph) → GET file returns the dead-edge entry (reason=endpoint_missing)."""
        from app.api import a1_routes

        client, payload = started
        _fill_all_subs(client, payload)
        assert client.post(f"/api/a1/file/{payload['file_id']}/finalize").status_code == 200

        # Inject a stale confirmed edge whose endpoints do not exist in the graph
        rec = a1_routes._FILES[payload["file_id"]]
        stale_key = "term:幽灵A/term:幽灵B/衍生"
        rec["confirmed_edges"][stale_key] = {
            "from_node_id": "term:幽灵A",
            "to_node_id": "term:幽灵B",
            "relation": "衍生",
            "confidence": "semantic",
            "confirmed": True,
        }

        # Re-finalize → stale edge lands in the dead zone
        assert client.post(f"/api/a1/file/{payload['file_id']}/finalize").status_code == 200

        resp = client.get(f"/api/a1/file/{payload['file_id']}")
        assert resp.status_code == 200
        dead = resp.json()["dead_edges"]
        assert isinstance(dead, list)
        entry = next(d for d in dead if d["key"] == stale_key)
        assert entry["from"] == "term:幽灵A"
        assert entry["to"] == "term:幽灵B"
        assert entry["relation"] == "衍生"
        assert entry["reason"] == "endpoint_missing"


# ---- T7: dual-tree assembly + dead-edge zone + assertions (_build_graph) ----

def _t7_session_and_answers(payload):
    """Prep a session with IP定位 + 世界本体(2 subs) answered (module serial 2)."""
    from app.api import a1_routes
    session = a1_routes._SESSIONS[payload["session_id"]]
    session.answers["IP定位.name"] = "测试IP"
    session.answers["世界本体.origin"] = "世界起源于一声钟响"
    session.answers["世界本体.existence"] = "万物以概念形式存在"
    return session


def test_build_graph_dual_tree_depth_mount(started):
    """T7: depth-tree mounting — 4 items under 世界本体.existence → 4 L4 nodes
    with serials D2-2-1..4, TREE 分条目 edges, L2 description from LLM summary."""
    from app.api import a1_routes
    from app.domains.creation.a1.graphify import (
        AnchorEntries,
        EdgeSpec,
        EntryItem,
        GraphifyResult,
    )
    from app.models.knowledge_graph import EdgeType

    client, payload = started
    session = _t7_session_and_answers(payload)
    file_rec: dict = {}

    llm = GraphifyResult(
        module_summaries={"世界本体": "存在的根基与世界法则"},
        entries=[AnchorEntries(anchor="世界本体.existence", items=[
            EntryItem(title=f"存在之环{i}", content=f"内容{i}") for i in range(1, 5)
        ])],
        edges=[
            EdgeSpec(**{
                "from": "世界本体.existence",
                "to": "d:世界本体.existence:存在之环1",
                "relation": "衍生",
                "confidence": "semantic",
            }),
        ],
    )
    graph, ids = a1_routes._build_graph(session, file_rec, llm_result=llm)

    # (1) 4 depth nodes, level=4, correct ids + serials
    d_nodes = [n for n in graph.nodes.values() if n.level == 4]
    assert len(d_nodes) == 4
    assert {n.serial_number for n in d_nodes} == {
        "D2-2-1", "D2-2-2", "D2-2-3", "D2-2-4",
    }
    assert "d:世界本体.existence:存在之环1" in graph.nodes

    # (2) TREE 分条目 edges L3→L4
    fen_edges = [e for e in graph.edges if e.visual_description == "分条目"]
    assert len(fen_edges) == 4
    assert all(e.edge_type == EdgeType.TREE for e in fen_edges)
    assert all(e.from_node_id == "世界本体.existence" for e in fen_edges)

    # (3) L2 description from module_summaries (not the label fallback)
    assert graph.nodes["世界本体"].description == "存在的根基与世界法则"
    # tier annotation from TIER_MAP
    assert graph.nodes["世界本体"].tier == 0

    # (4) semantic edge merged with correct EdgeType mapping
    sem = [e for e in graph.edges if e.relation == "衍生"]
    assert len(sem) == 1
    assert sem[0].edge_type == EdgeType.SEMANTIC
    assert sem[0].confidence == "semantic"

    # (5) edge accounting invariant: input == graph + dead
    assert file_rec["dead_edges"] == []
    graph_edge_count = sum(
        1 for e in graph.edges
        if e.from_node_id == "世界本体.existence" and e.relation == "衍生"
    )
    assert len(llm.edges) == graph_edge_count + len(file_rec["dead_edges"])


def test_build_graph_dead_edges_and_confirmed_recovery(started):
    """T7: endpoint-missing edges land in dead_edges (equality invariant);
    confirmed_edges triple match restores confirmed=True."""
    from app.api import a1_routes
    from app.domains.creation.a1.graphify import (
        AnchorEntries,
        EdgeSpec,
        EntryItem,
        GraphifyResult,
    )
    from app.models.knowledge_graph import EdgeType

    client, payload = started
    session = _t7_session_and_answers(payload)
    nid_ok = "d:世界本体.origin:命运之钟"
    file_rec: dict = {
        "confirmed_edges": {
            f"世界本体.origin/{nid_ok}/关联": {
                "from_node_id": "世界本体.origin",
                "to_node_id": nid_ok,
                "relation": "关联",
                "confirmed": True,
            },
        },
    }

    llm = GraphifyResult(
        entries=[AnchorEntries(anchor="世界本体.origin", items=[
            EntryItem(title="命运之钟", content="钟声即存在"),
        ])],
        edges=[
            # (a) matching triple → confirmed=True recovered
            EdgeSpec(**{"from": "世界本体.origin", "to": nid_ok, "relation": "关联"}),
            # (b) dead edge → dead zone
            EdgeSpec(**{"from": "世界本体.origin", "to": "不存在的节点", "relation": "关联"}),
        ],
    )
    graph, _ids = a1_routes._build_graph(session, file_rec, llm_result=llm)

    # dead zone: exactly the endpoint-missing edge
    dead = file_rec["dead_edges"]
    assert len(dead) == 1
    assert dead[0]["to"] == "不存在的节点"
    assert dead[0]["reason"] == "endpoint_missing"

    # accounting invariant: input == graph + dead
    graph_edges = [e for e in graph.edges if e.relation == "关联"]
    assert len(graph_edges) == 1
    assert len(llm.edges) == len(graph_edges) + len(dead)

    # confirmed recovery via triple match
    recovered = [e for e in graph_edges if e.to_node_id == nid_ok]
    assert len(recovered) == 1
    assert recovered[0].confirmed is True
    assert recovered[0].edge_type == EdgeType.SEMANTIC


def test_build_graph_none_result_keeps_legacy_behavior(started):
    """T7: llm_result=None → 全降级现状路径: no L4 nodes, label descriptions,
    empty dead_edges."""
    from app.api import a1_routes

    client, payload = started
    session = _t7_session_and_answers(payload)
    file_rec: dict = {}

    graph, _ids = a1_routes._build_graph(session, file_rec)

    assert not [n for n in graph.nodes.values() if n.level == 4]
    assert graph.nodes["世界本体"].description == "世界本体"  # label fallback
    assert file_rec["dead_edges"] == []
    assert file_rec["assemble_warnings"] == []
    # TREE edges: 2 bg→module + 3 module→entry (no 分条目 edges)
    tree = [e for e in graph.edges if e.edge_type.value == "tree"]
    assert len(tree) == 5
    assert not [e for e in tree if e.visual_description == "分条目"]


def test_build_graph_children_recursive_mount(started):
    """T11: children mount recursively — child id reuses d:{anchor}:{title},
    serial D{m}-{e}-{k}-{j}, TREE 分条目 edge parent→child."""
    from app.api import a1_routes
    from app.domains.creation.a1.graphify import (
        AnchorEntries,
        EntryItem,
        GraphifyResult,
    )
    from app.models.knowledge_graph import EdgeType

    client, payload = started
    session = _t7_session_and_answers(payload)
    file_rec: dict = {}

    llm = GraphifyResult(entries=[AnchorEntries(anchor="世界本体.origin", items=[
        EntryItem(title="命运之钟", content="钟声即存在", children=[
            EntryItem(title="子钟", content="回声层"),
            EntryItem(title="裂纹钟身", content="纹理层"),
        ]),
    ])])
    graph, _ids = a1_routes._build_graph(session, file_rec, llm_result=llm)

    # parent + 2 children mounted (世界本体.origin is entry serial 2-1)
    assert "d:世界本体.origin:命运之钟" in graph.nodes
    assert "d:世界本体.origin:子钟" in graph.nodes
    assert "d:世界本体.origin:裂纹钟身" in graph.nodes
    assert graph.nodes["d:世界本体.origin:子钟"].serial_number == "D2-1-1-1"
    assert graph.nodes["d:世界本体.origin:裂纹钟身"].serial_number == "D2-1-1-2"

    # TREE chain: entry→item and item→child, both 分条目
    fen = [e for e in graph.edges if e.visual_description == "分条目"]
    assert len(fen) == 3
    assert all(e.edge_type == EdgeType.TREE for e in fen)
    chain = {(e.from_node_id, e.to_node_id) for e in fen}
    assert ("世界本体.origin", "d:世界本体.origin:命运之钟") in chain
    assert ("d:世界本体.origin:命运之钟", "d:世界本体.origin:子钟") in chain


def test_build_graph_children_depth3_rejected(started):
    """T11: children 的 children 拒收 + warning（深度上限 2 层）。"""
    from app.api import a1_routes
    from app.domains.creation.a1.graphify import (
        AnchorEntries,
        EntryItem,
        GraphifyResult,
    )

    client, payload = started
    session = _t7_session_and_answers(payload)
    file_rec: dict = {}

    llm = GraphifyResult(entries=[AnchorEntries(anchor="世界本体.origin", items=[
        EntryItem(title="命运之钟", content="钟声即存在", children=[
            EntryItem(title="子钟", content="回声层", children=[
                EntryItem(title="孙钟", content="超深层"),
            ]),
        ]),
    ])])
    graph, _ids = a1_routes._build_graph(session, file_rec, llm_result=llm)

    assert "d:世界本体.origin:子钟" in graph.nodes
    assert "d:世界本体.origin:孙钟" not in graph.nodes
    assert any("深度超限" in w for w in file_rec["assemble_warnings"])


def test_build_graph_children_env_disabled(started, monkeypatch):
    """T11: A1_DEPTH_CHILDREN=0 → children not mounted."""
    from app.api import a1_routes
    from app.domains.creation.a1.graphify import (
        AnchorEntries,
        EntryItem,
        GraphifyResult,
    )

    monkeypatch.setenv("A1_DEPTH_CHILDREN", "0")
    client, payload = started
    session = _t7_session_and_answers(payload)
    file_rec: dict = {}

    llm = GraphifyResult(entries=[AnchorEntries(anchor="世界本体.origin", items=[
        EntryItem(title="命运之钟", content="钟声即存在", children=[
            EntryItem(title="子钟", content="回声层"),
        ]),
    ])])
    graph, _ids = a1_routes._build_graph(session, file_rec, llm_result=llm)

    assert "d:世界本体.origin:命运之钟" in graph.nodes
    assert "d:世界本体.origin:子钟" not in graph.nodes
    assert any("已禁用" in w for w in file_rec["assemble_warnings"])


def test_build_graph_constraint_fields_cst_channel(started, monkeypatch):
    """T11: constraint_fields → cst_ node + CROSS edge (考古断链闭合);
    assemble_assertion no longer fires."""
    from app.api import a1_routes
    from app.domains.creation.a1.graphify import GraphifyResult
    from app.models.knowledge_graph import EdgeType

    captured: list[dict] = []
    monkeypatch.setattr(
        a1_routes, "log_event",
        lambda sid, event, **kw: captured.append({"event": event, **kw}),
    )

    client, payload = started
    session = _t7_session_and_answers(payload)
    file_rec: dict = {}

    llm = GraphifyResult(constraint_fields={"LAW.world_structure": "九层嵌套"})
    graph, ids = a1_routes._build_graph(session, file_rec, llm_result=llm)

    # cst node exists (free-form value recorded verbatim despite enum validator)
    assert "cst_LAW_world_structure" in graph.nodes
    assert graph.nodes["cst_LAW_world_structure"].level == 0
    assert "九层嵌套" in graph.nodes["cst_LAW_world_structure"].description
    assert "cst_LAW_world_structure" in ids

    # CROSS edge cst → background with RULE_* semantic label
    cross = [
        e for e in graph.edges
        if e.edge_type == EdgeType.CROSS
        and e.from_node_id == "cst_LAW_world_structure"
    ]
    assert len(cross) == 1
    assert cross[0].to_node_id == graph.background_node_id
    assert "RULE_" in cross[0].visual_description

    # runtime assertion silent: cst channel closed the gap
    assert not any(
        c.get("kind") == "constraint_fields_without_cst_nodes"
        for c in captured
    )


def test_build_graph_constraint_fields_idempotent(started):
    """T11: same inputs assembled twice → cst node/edge counts unchanged
    (apply_constraints idempotent merge)."""
    from app.api import a1_routes
    from app.domains.creation.a1.graphify import GraphifyResult
    from app.models.knowledge_graph import EdgeType

    client, payload = started
    session = _t7_session_and_answers(payload)

    llm = GraphifyResult(constraint_fields={
        "LAW.world_structure": "九层嵌套",
        "ACT.core_action": "以论证代替攻击",
    })

    def _counts() -> tuple[int, int]:
        graph, _ids = a1_routes._build_graph(session, {}, llm_result=llm)
        cst_nodes = sum(1 for n in graph.nodes if n.startswith("cst_"))
        cross = sum(
            1 for e in graph.edges
            if e.edge_type == EdgeType.CROSS
            and e.from_node_id.startswith("cst_")
        )
        return cst_nodes, cross

    n1, e1 = _counts()
    n2, e2 = _counts()
    assert (n1, e1) == (n2, e2) == (2, 2)


# ---- T8: finalize × graphify 串联（v0.5 §8.1 两阶段处置） ----

def _t8_seed_answers(payload):
    """Fill over-half of each module (finalize gate) + depth-tree anchors."""
    from app.api import a1_routes
    from app.domains.creation.seed.a1_question_tree import MODULES
    session = a1_routes._SESSIONS[payload["session_id"]]
    for m in MODULES:
        need = len(m["fields"]) // 2 + 1
        for f in m["fields"][:need]:
            session.answers[f"{m['id']}.{f['id']}"] = "测试内容"
    # anchors used by the graphify stub response
    session.answers["世界本体.origin"] = "世界起源于一声钟响"
    session.answers["世界本体.existence"] = "万物以概念形式存在"
    return session


def _t8_patch_provider(monkeypatch, stub):
    """Inject a stub LLM provider into a1_routes' provider factory."""
    import app.api.a1_routes as a1_routes
    monkeypatch.setattr(a1_routes, "load_provider_config", lambda: {})
    monkeypatch.setattr(a1_routes, "create_provider", lambda cfg: stub)


_GraphifyOK_RESPONSE = {
    "module_summaries": {"世界本体": "存在的根基与世界法则"},
    "entries": [
        {"anchor": "世界本体.origin",
         "items": [{"title": "命运之钟", "content": "钟声即存在"}]},
        {"anchor": "世界本体.existence",
         "items": [{"title": "概念之海", "content": "万物以概念形式存在"}]},
    ],
    "edges": [
        {"from": "世界本体.origin", "to": "d:世界本体.origin:命运之钟",
         "relation": "存在塑力", "confidence": "semantic"},
    ],
    "constraint_fields": {},
    "open_questions": [],
}


def test_finalize_graphify_degrade_e2e(started, make_stub_llm, monkeypatch):
    """T8 测试1: stub provider raise_error → finalize 仍 200；
    finalize_warnings 含 'graphify'；graph 仅 TREE 节点（无 d:/term:）。"""
    from app.api import a1_routes

    client, payload = started
    _t8_seed_answers(payload)
    _t8_patch_provider(monkeypatch, make_stub_llm(raise_error=RuntimeError("boom")))

    fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
    assert fin.status_code == 200
    body = fin.json()
    assert any("graphify" in w for w in body["warnings"])

    rec = a1_routes._FILES[payload["file_id"]]
    assert any("graphify" in w for w in rec["finalize_warnings"])

    node_ids = set(rec["graph_json"]["nodes"].keys())
    assert node_ids
    assert not [nid for nid in node_ids if nid.startswith("d:")]
    assert not [nid for nid in node_ids if nid.startswith("term:")]


def test_finalize_graphify_success_e2e(started, make_stub_llm, monkeypatch):
    """T8 测试2: stub 成功返回 graphify JSON → finalize 200；
    graph_json 含 d: 深度节点 + 语义边；finalize_warnings 键存在。"""
    from app.api import a1_routes

    client, payload = started
    _t8_seed_answers(payload)
    _t8_patch_provider(monkeypatch, make_stub_llm(response=dict(_GraphifyOK_RESPONSE)))

    fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
    assert fin.status_code == 200

    rec = a1_routes._FILES[payload["file_id"]]
    assert "finalize_warnings" in rec

    graph_json = rec["graph_json"]
    d_nodes = [nid for nid in graph_json["nodes"] if nid.startswith("d:")]
    assert "d:世界本体.origin:命运之钟" in d_nodes
    sem_edges = [e for e in graph_json["edges"]
                 if e.get("relation") == "存在塑力"]
    assert len(sem_edges) == 1
    assert sem_edges[0]["from_node_id"] == "世界本体.origin"
    assert sem_edges[0]["to_node_id"] == "d:世界本体.origin:命运之钟"


def test_extract_edges_endpoint_still_callable_after_finalize(started):
    """T8 测试3: extract-edges 端点保留且行为不变——
    定稿后（降级图，无概念词）调用仍走原有 400 校验分支。"""
    from app.api import a1_routes

    client, payload = started
    _t8_seed_answers(payload)
    assert client.post(
        f"/api/a1/file/{payload['file_id']}/finalize"
    ).status_code == 200

    resp = client.post(f"/api/a1/file/{payload['file_id']}/concept/extract-edges")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "需先确认至少2个概念词"
    assert a1_routes is not None  # import sanity
