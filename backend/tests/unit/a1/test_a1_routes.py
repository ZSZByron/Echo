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
