"""T3 (D21 前端 phase) 契约测试 — impulse-coords/signal POST 端点。

四例先红后绿：
① 三值用户直纠信号：user_nudge_story 轴向叙事端（+）、user_nudge_builder
   向建构端（-）方向相反、user_nudge_confirm 轴不动仅升置信度；
② 非法信号（白名单外，如 slider_0.7）→ 400；
③ 阻尼路径（冷却轮内二次信号）→ applied=false 且 HTTP 200（护栏语义
   诚实透传，不隐藏）；
④ 404：不存在 file_id。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import a1_routes
from app.main import app

#: 端点白名单逐字清单（T3 三值，离散 only——无连续滑杆值）
NUDGE_SIGNALS = ("user_nudge_story", "user_nudge_builder", "user_nudge_confirm")


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def started(client):
    resp = client.post(
        "/api/a1/session/start", json={"user_id": "u_nudge", "seed_id": 1}
    )
    assert resp.status_code == 200
    return client, resp.json()


def _coords(client, file_id: str) -> dict:
    resp = client.get(f"/api/a1/file/{file_id}/impulse-coords")
    assert resp.status_code == 200
    return resp.json()


def _post_signal(client, file_id: str, signal: str):
    return client.post(
        f"/api/a1/file/{file_id}/impulse-coords/signal",
        json={"signal": signal},
    )


class TestNudgeSignalDirection:
    def test_user_nudge_story_moves_axis_toward_narrative(self, started):
        client, payload = started
        before = _coords(client, payload["file_id"])
        resp = _post_signal(client, payload["file_id"], "user_nudge_story")
        assert resp.status_code == 200
        body = resp.json()
        assert set(body.keys()) == {"file_id", "session_id", "applied",
                                    "axis", "confidence"}
        assert body["applied"] is True
        assert body["axis"] > before["axis"]  # 100=纯叙事端
        assert body["confidence"] > before["confidence"]

    def test_user_nudge_builder_moves_axis_toward_constructive(self, started):
        client, payload = started
        before = _coords(client, payload["file_id"])
        resp = _post_signal(client, payload["file_id"], "user_nudge_builder")
        assert resp.status_code == 200
        body = resp.json()
        assert body["applied"] is True
        assert body["axis"] < before["axis"]  # 0=纯建构端（与 story 相反）

    def test_user_nudge_confirm_confidence_only_axis_unmoved(self, started):
        client, payload = started
        before = _coords(client, payload["file_id"])
        resp = _post_signal(client, payload["file_id"], "user_nudge_confirm")
        assert resp.status_code == 200
        body = resp.json()
        assert body["applied"] is True
        assert body["axis"] == before["axis"]  # 差不多：轴不动
        assert body["confidence"] > before["confidence"]  # 只升置信度

    def test_existing_five_signals_untouched(self):
        # 既有五信号逐字不动（additive 纪律）
        from app.domains.creation.a1 import impulse_coords as ic

        assert set(ic.SIGNALS) == {
            "pack_applied", "pack_rejected", "fill_confirmed",
            "fill_rejected", "skipped",
            *NUDGE_SIGNALS,
        }
        assert ic.SIGNALS["pack_applied"] == {"axis_base": 0.0, "conf_d": 0.10}
        assert ic.SIGNALS["fill_confirmed"] == {"axis_base": 3.0, "conf_d": 0.02}


class TestIllegalSignal:
    def test_unknown_signal_returns_400(self, started):
        client, payload = started
        resp = _post_signal(client, payload["file_id"], "slider_0.7")
        assert resp.status_code == 400

    def test_existing_internal_signal_not_on_whitelist(self, started):
        # 既有五信号走内部动作面，不经用户直纠端点
        client, payload = started
        resp = _post_signal(client, payload["file_id"], "fill_confirmed")
        assert resp.status_code == 400


class TestDampingPassthrough:
    def test_cooldown_second_signal_applied_false_200(self, started):
        client, payload = started
        first = _post_signal(client, payload["file_id"], "user_nudge_story")
        assert first.status_code == 200
        assert first.json()["applied"] is True
        # 冷却轮内（COOLDOWN_ROUNDS=3）二次信号 → 阻尼但诚实 200
        second = _post_signal(client, payload["file_id"], "user_nudge_story")
        assert second.status_code == 200
        body = second.json()
        assert body["applied"] is False
        assert isinstance(body["axis"], float)

    def test_nonexistent_file_404(self, client):
        resp = client.post(
            "/api/a1/file/nonexistent/impulse-coords/signal",
            json={"signal": "user_nudge_story"},
        )
        assert resp.status_code == 404
