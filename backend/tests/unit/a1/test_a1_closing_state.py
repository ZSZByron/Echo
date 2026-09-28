"""T1 (D21 前端 phase) 契约测试 — closing-state GET 端点 + chat closing 信号。

四例先红后绿：
① 未触发会话 GET → step=0 / triggered=False / preview 结构到具体键
② 触发中会话（closing_step=2）→ step=2 / triggered=True
③ settled 会话 → triggered=False
④ chat 响应 additive 含 closing 键，既有键清单逐字齐全
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
        "/api/a1/session/start", json={"user_id": "u_closing", "seed_id": 1}
    )
    assert resp.status_code == 200
    return client, resp.json()


PREVIEW_KEYS = {
    "file_id",
    "exists",
    "closing",
    "module_coverage",
    "gaps",
    "version_chain",
    "stale",
    "stale_warning",
    "consumers",
}

# chat 响应既有键（Task 6 形状稳定契约 + C7 open-question），逐字清单
CHAT_PREEXISTING_KEYS = {
    "reply",
    "next_question",
    "file_diff",
    "progress",
    "phase",
    "proposals",
    "divergent_question",
}


class TestClosingStateEndpoint:
    def test_untriggered_session_step0_not_triggered_preview_structured(
        self, started
    ):
        client, payload = started
        resp = client.get(
            f"/api/a1/file/{payload['file_id']}/closing-state"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert set(body.keys()) == {
            "file_id",
            "closing_step",
            "closing_settled",
            "triggered",
            "preview",
        }
        assert body["file_id"] == payload["file_id"]
        assert body["closing_step"] == 0
        assert body["closing_settled"] is False
        assert body["triggered"] is False
        # preview 结构断言到具体键（build_output_preview 真实形状）
        preview = body["preview"]
        assert PREVIEW_KEYS.issubset(set(preview.keys()))
        assert preview["exists"] is True
        assert isinstance(preview["module_coverage"], list)
        assert preview["module_coverage"]
        assert {"module_id", "done_ratio", "done_fields", "total_fields"} \
            == set(preview["module_coverage"][0].keys())
        assert isinstance(preview["gaps"], list)
        assert isinstance(preview["consumers"], list)
        assert preview["consumers"]

    def test_triggered_session_step2_triggered_true(self, started):
        client, payload = started
        session = a1_routes._SESSIONS[payload["session_id"]]
        session.closing_step = 2
        resp = client.get(
            f"/api/a1/file/{payload['file_id']}/closing-state"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["closing_step"] == 2
        assert body["closing_settled"] is False
        assert body["triggered"] is True

    def test_settled_session_not_triggered(self, started):
        client, payload = started
        session = a1_routes._SESSIONS[payload["session_id"]]
        session.closing_step = 0
        session.closing_settled = True
        resp = client.get(
            f"/api/a1/file/{payload['file_id']}/closing-state"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["closing_step"] == 0
        assert body["closing_settled"] is True
        assert body["triggered"] is False

    def test_nonexistent_file_404(self, client):
        resp = client.get("/api/a1/file/nonexistent/closing-state")
        assert resp.status_code == 404


class TestChatClosingSignal:
    def test_chat_response_contains_closing_and_preexisting_keys(
        self, started
    ):
        client, payload = started
        resp = client.post(
            "/api/a1/chat",
            json={"session_id": payload["session_id"], "message": "跳过"},
        )
        assert resp.status_code == 200
        body = resp.json()
        # 既有键逐字齐全（additive 不动既有字段）
        assert CHAT_PREEXISTING_KEYS.issubset(set(body.keys()))
        # additive closing 信号
        assert body["closing"] == {"step": 0, "settled": False, "triggered": False}
