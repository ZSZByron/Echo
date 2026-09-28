"""T3 (D21 前端 phase) 契约测试 — draft-version GET 端点。

两态先红后绿（领域实际形状：session.draft_alpha = {baseline, round, step}，
版本串由 a1.draft_version.draft_label() 产出——α0.{round} / α0.{round}{n}；
**域现实胜于计划猜测**）：
① 默认会话（round=0 或 step=0 → draft_label None）→ available=false；
② 注入草稿态（round/step>0）→ available=true + version/baseline/round。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import a1_routes
from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def started(client):
    resp = client.post(
        "/api/a1/session/start", json={"user_id": "u_draftv", "seed_id": 1}
    )
    assert resp.status_code == 200
    return client, resp.json()


class TestDraftVersionEndpoint:
    def test_fresh_session_not_available(self, started):
        client, payload = started
        resp = client.get(f"/api/a1/file/{payload['file_id']}/draft-version")
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"available": False}

    def test_draft_state_available_with_version_baseline_round(self, started):
        client, payload = started
        session = a1_routes._SESSIONS[payload["session_id"]]
        # 模拟对齐循环内草稿态（α0.1）
        session.draft_alpha = {"baseline": 1, "round": 1, "step": 1}
        resp = client.get(f"/api/a1/file/{payload['file_id']}/draft-version")
        assert resp.status_code == 200
        body = resp.json()
        assert body["available"] is True
        assert body["version"] == "α0.1"  # draft_label 真实输出格式
        assert body["baseline"] == 1
        assert body["round"] == 1

    def test_in_round_iteration_step2_label_format(self, started):
        # 循环内迭代：α0.11（round=1, step=2 → α0.{r}{s-1}）
        client, payload = started
        session = a1_routes._SESSIONS[payload["session_id"]]
        session.draft_alpha = {"baseline": 1, "round": 1, "step": 2}
        resp = client.get(f"/api/a1/file/{payload['file_id']}/draft-version")
        assert resp.status_code == 200
        body = resp.json()
        assert body["version"] == "α0.11"

    def test_finalized_step_reset_not_available(self, started):
        # 收口后（step=0）不在草稿期 → available=false（round 跨收口保留）
        client, payload = started
        session = a1_routes._SESSIONS[payload["session_id"]]
        session.draft_alpha = {"baseline": 2, "round": 1, "step": 0}
        resp = client.get(f"/api/a1/file/{payload['file_id']}/draft-version")
        assert resp.status_code == 200
        assert resp.json() == {"available": False}

    def test_nonexistent_file_404(self, client):
        resp = client.get("/api/a1/file/nonexistent/draft-version")
        assert resp.status_code == 404
