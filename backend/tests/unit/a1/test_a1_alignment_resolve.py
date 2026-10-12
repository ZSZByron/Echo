"""T2 (D21 前端 phase) 契约测试 — chat pending_alignments 序列化 + resolve 端点。

五例先红后绿：
① 注入一条 pending_alignments → chat 响应 additive 序列化五字段逐字
   （含人话 content、绝不外露 target/graph_code）
② accept=True → applied=True 且 pending 清空
③ accept=False → 条目移除 + 零副作用（不碰 archive / registry，领域语义）
④ 未知 key → 200 + {applied: false, error: "not_found"}（幂等不抛错）
⑤ ALIGN_ACTIONS 四动作闭集逐字冻结 ∈ {link, dedupe, contradict, update}
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import a1_routes
from app.domains.creation.a1.alignment_flow import (
    ALIGN_ACTIONS,
    AlignProposal,
)
from app.main import app


def _make_proposal(**overrides) -> AlignProposal:
    defaults = dict(
        action="link",
        target="n_secret_node_id_42",  # G5 雷区：绝不外露
        content="这和你之前提到的「星陨教团」有关联，要合并成一条吗？",
        quote="星陨教团似乎隐藏着什么",
        graph_code="IP1-G0001-v1",
        stale_warning=["会使「旧版教团条目」过期"],
    )
    defaults.update(overrides)
    return AlignProposal(**defaults)


def _inject(session_id: str, key: str = "align-001", **overrides) -> None:
    a1_routes._SESSIONS[session_id].pending_alignments = {
        key: {"proposal": _make_proposal(**overrides), "source": "alignment_flow"},
    }


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def started(client):
    resp = client.post(
        "/api/a1/session/start", json={"user_id": "u_align", "seed_id": 1}
    )
    assert resp.status_code == 200
    return client, resp.json()


def _chat(client, session_id: str) -> dict:
    # skip 路径（message="跳过"）完全避开 LLM
    resp = client.post(
        "/api/a1/chat", json={"session_id": session_id, "message": "跳过"}
    )
    assert resp.status_code == 200
    return resp.json()


class TestChatSerialization:
    def test_chat_serializes_pending_alignments_five_fields_no_target(
        self, started
    ):
        client, payload = started
        # additive：空 pending → 空列表（字段恒在场）
        empty = _chat(client, payload["session_id"])
        assert empty["pending_alignments"] == []
        _inject(payload["session_id"])
        body = _chat(client, payload["session_id"])
        pa = body["pending_alignments"]
        assert isinstance(pa, list) and len(pa) == 1
        item = pa[0]
        # 五字段逐字（key = dict 键，resolve 端点惯例）
        assert set(item.keys()) == {
            "key", "action", "content", "quote", "stale_warning",
        }
        assert item["key"] == "align-001"
        assert item["action"] == "link"
        assert "星陨教团" in item["content"]  # 人话 content 在场
        assert item["quote"] == "星陨教团似乎隐藏着什么"
        assert item["stale_warning"] == ["会使「旧版教团条目」过期"]
        # G5 雷区：target（节点 id）/ graph_code 绝不外露
        assert "target" not in item
        assert "graph_code" not in item
        assert "n_secret_node_id_42" not in str(item)


class TestResolveEndpoint:
    def test_accept_true_applied_and_pending_cleared(self, started):
        client, payload = started
        _inject(payload["session_id"])
        resp = client.post(
            f"/api/a1/file/{payload['file_id']}/alignment/align-001/resolve",
            json={"accept": True},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["applied"] is True
        assert body["accept"] is True
        session = a1_routes._SESSIONS[payload["session_id"]]
        assert "align-001" not in session.pending_alignments
        # 接受副作用：open_question 归档一条（确定性应用①）
        assert any(
            r.get("id") == "oq-align-align-001"
            for r in session.open_question_archive
        )

    def test_accept_false_removed_with_zero_side_effects(self, started):
        client, payload = started
        _inject(payload["session_id"])
        session = a1_routes._SESSIONS[payload["session_id"]]
        archive_before = list(session.open_question_archive)
        resp = client.post(
            f"/api/a1/file/{payload['file_id']}/alignment/align-001/resolve",
            json={"accept": False},
        )
        assert resp.status_code == 200
        body = resp.json()
        # 领域真实语义：拒绝 = 丢弃，applied=False（applied 指「确定性应用」发生）
        assert body["applied"] is False
        assert body["accept"] is False
        # 条目移除（不复活）
        assert "align-001" not in session.pending_alignments
        # 零副作用：不碰 archive（图谱/registry 无写入路径）
        assert session.open_question_archive == archive_before

    def test_unknown_key_idempotent_not_found_200(self, started):
        client, payload = started
        resp = client.post(
            f"/api/a1/file/{payload['file_id']}/alignment/align-999/resolve",
            json={"accept": True},
        )
        assert resp.status_code == 200
        assert resp.json() == {
            "applied": False, "accept": True, "error": "not_found",
        }

    def test_double_resolve_idempotent(self, started):
        client, payload = started
        _inject(payload["session_id"])
        url = f"/api/a1/file/{payload['file_id']}/alignment/align-001/resolve"
        first = client.post(url, json={"accept": True}).json()
        assert first["applied"] is True
        second = client.post(url, json={"accept": True})
        assert second.status_code == 200
        assert second.json() == {
            "applied": False, "accept": True, "error": "not_found",
        }


class TestActionClosedSet:
    def test_align_actions_frozen_verbatim(self):
        # 闭集逐字冻结，不允许添加或修改
        assert ALIGN_ACTIONS == ("link", "dedupe", "contradict", "update")

    def test_serialized_action_within_closed_set(self, started):
        client, payload = started
        _inject(payload["session_id"], action="dedupe")
        body = _chat(client, payload["session_id"])
        assert body["pending_alignments"][0]["action"] == "dedupe"
        assert all(
            item["action"] in ALIGN_ACTIONS
            for item in body["pending_alignments"]
        )
