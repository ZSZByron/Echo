"""E1-Lite T1: creator_profile 字段组落库测试。

覆盖：
1. happy：合法 impulse_primary 开局 → A1Session 三字段写入 + store round-trip
2. 降级：未知主冲动 → HTTP 200 + 三字段全空 + warning；次冲动==主 → secondary 空；
   次冲动未知 → secondary 空
3. 回归：无 impulse 字段（E0 旧客户端）→ 三字段空、响应结构基线一致
4. 存量反序列化：不含新键的旧 session JSON → model_validate 成功
"""
from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from app.api import a1_routes
from app.domains.creation.a1.guide_engine import A1Session
from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _start(client: TestClient, **extra) -> dict:
    payload = {"user_id": "u_cp", "custom_idea": "测试世界观"}
    payload.update(extra)
    resp = client.post("/api/a1/session/start", json=payload)
    assert resp.status_code == 200
    return resp.json()


class TestCreatorProfileHappy:
    def test_valid_primary_persists(self, client: TestClient) -> None:
        data = _start(client, impulse_primary="plot", impulse_secondary="romance")
        session = a1_routes._SESSIONS[data["session_id"]]
        assert session.creator_primary == "plot"
        assert session.creator_secondary == "romance"
        assert session.creator_profile_source == "impulse_cards"

    def test_store_round_trip_contains_fields(
        self, client: TestClient, tmp_path
    ) -> None:
        import json

        data = _start(client, impulse_primary="plot")
        store_path = tmp_path / "a1_store.json"
        raw = json.loads(store_path.read_text(encoding="utf-8"))
        dumped = raw["sessions"][data["session_id"]]
        assert dumped["creator_primary"] == "plot"
        assert dumped["creator_secondary"] == ""
        assert dumped["creator_profile_source"] == "impulse_cards"

        # round-trip: save -> load 语义等价
        sessions = {
            sid: A1Session.model_validate(s) for sid, s in raw["sessions"].items()
        }
        assert sessions[data["session_id"]].creator_primary == "plot"


class TestUnknownEnumDegrade:
    def test_unknown_primary_degrades(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="app.api.a1_routes"):
            data = _start(client, impulse_primary="hacker_vibes")
        session = a1_routes._SESSIONS[data["session_id"]]
        assert session.creator_primary == ""
        assert session.creator_secondary == ""
        assert session.creator_profile_source == ""
        assert any("hacker_vibes" in r.message for r in caplog.records)
        # 降级不报错：正常返回 first_question
        assert data["first_question"]["question"]

    def test_secondary_equals_primary_ignored(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="app.api.a1_routes"):
            data = _start(client, impulse_primary="plot", impulse_secondary="plot")
        session = a1_routes._SESSIONS[data["session_id"]]
        assert session.creator_primary == "plot"
        assert session.creator_secondary == ""
        assert session.creator_profile_source == "impulse_cards"
        assert any("plot" in r.message for r in caplog.records)

    def test_unknown_secondary_ignored(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="app.api.a1_routes"):
            data = _start(client, impulse_primary="romance", impulse_secondary="wtf_99")
        session = a1_routes._SESSIONS[data["session_id"]]
        assert session.creator_primary == "romance"
        assert session.creator_secondary == ""
        assert session.creator_profile_source == "impulse_cards"
        assert any("wtf_99" in r.message for r in caplog.records)


class TestRegressionNoImpulse:
    def test_legacy_payload_baseline(self, client: TestClient) -> None:
        data = _start(client)
        session = a1_routes._SESSIONS[data["session_id"]]
        assert session.creator_primary == ""
        assert session.creator_secondary == ""
        assert session.creator_profile_source == ""
        # 响应结构基线：顶层键不变
        assert set(data.keys()) == {
            "session_id", "file_id", "ip_code",
            "first_question", "file", "seed",
        }
        assert data["first_question"]["question"]


class TestLegacyDeserialization:
    def test_old_session_json_without_new_keys(self) -> None:
        old = {
            "session_id": "a1_old",
            "user_id": "u_old",
            "ip_code": "IP0001",
            "answers": {},
        }
        session = A1Session.model_validate(old)
        assert session.creator_primary == ""
        assert session.creator_secondary == ""
        assert session.creator_profile_source == ""
