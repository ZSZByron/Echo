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

        # (e) Total TREE edges == modules + entries
        # Count all non-empty subfield answers across all modules
        total_entries = sum(
            1 for module in MODULES
            for sf in module["fields"]
            if session.answers.get(f"{module['id']}.{sf['id']}", "")
        )
        expected_tree_edges = len(modules_with_answers) + total_entries
        assert len(tree_edges) == expected_tree_edges

        # Verify module nodes only have label in description (not aggregated answers)
        for l2_node in level2_nodes:
            # Description should be just the module label, not containing ": " from subfields
            assert ": " not in l2_node["description"]
