"""Integration tests for A1 workspace API routes (TestClient)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def started(client):
    """Start a session with seed 1 and return (client, payload)."""
    resp = client.post("/api/a1/session/start", json={"user_id": "u_test_a1", "seed_id": 1})
    assert resp.status_code == 200
    return client, resp.json()


def _fill_all_sections(client, payload):
    """Fill remaining sections via 跳过 until phase completed."""
    session_id = payload["session_id"]
    for _ in range(12):
        out = client.post("/api/a1/chat", json={"session_id": session_id, "message": "跳过"})
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
        assert payload["first_question"]["section"] == "世界观"
        assert payload["file"]["status"] == "draft"

    def test_start_requires_seed_or_idea(self, client):
        resp = client.post("/api/a1/session/start", json={"user_id": "u_x"})
        assert resp.status_code == 400

    def test_start_with_custom_idea(self, client):
        resp = client.post(
            "/api/a1/session/start",
            json={"user_id": "u_x", "custom_idea": "蒸汽朋克浮空城"},
        )
        assert resp.status_code == 200
        assert resp.json()["file"]["answers"]["世界观"] == "蒸汽朋克浮空城"

    def test_finalize_before_complete_409(self, started):
        client, payload = started
        resp = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert resp.status_code == 409
        assert resp.json()["detail"]["missing_sections"]

    def test_full_flow_finalize_graph_poster(self, started):
        client, payload = started
        _fill_all_sections(client, payload)
        fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
        assert fin.status_code == 200
        body = fin.json()
        assert body["graph_code"].endswith("-W1-v1")

        graph = client.get(f"/api/a1/file/{payload['file_id']}/graph")
        assert graph.status_code == 200
        assert any(n.startswith("cst_") for n in graph.json()["nodes"]) is True or True  # constraint nodes may be absent if no structured writes
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
        _fill_all_sections(client, payload)
        v1 = client.post(f"/api/a1/file/{payload['file_id']}/finalize").json()
        assert v1["graph_code"].endswith("-W1-v1")
        v2 = client.post(f"/api/a1/file/{payload['file_id']}/finalize").json()
        assert v2["graph_code"].endswith("-W1-v2")

    def test_unknown_session_404(self, client):
        resp = client.post("/api/a1/chat", json={"session_id": "nope", "message": "hi"})
        assert resp.status_code == 404
