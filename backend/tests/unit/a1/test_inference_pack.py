"""推断包（inference pack）契约测试（M4a，D12 冻结设计 ②）。

契约（impulse spec §8 L293-296 / 计划 TODO 4）：
- 单次 LLM 调用（同 interviewer 模式），输入=冲动类型+会话上下文，输出 3-5 条建议；
- 复用 pending_proposals + confirm 交互（不发明新确认机制）；
- 判定双写：confirm 后 creator_profile 置信修正 + fills 通道写入（J1 拦截占位）；
- **绝不直写 answers**（断言测试）；
- 零 LLM（无 provider）→ 空包 + 披露 note，不 crash（M3 免费线范式）。

TDD RED：实现前本文件全部失败。
"""
import asyncio
from typing import Any

import pytest

from app.domains.creation.a1.guide_engine import (
    A1Session,
    resolve_proposal,
)
from app.domains.creation.a1.inference_pack import (
    InferencePacker,
    apply_pack_feedback,
)


class SyncStubProvider:
    """chat_json returns a canned dict synchronously."""

    def __init__(self, payload: Any) -> None:
        self._payload = payload
        self.calls = 0

    def chat_json(self, messages: Any) -> Any:  # noqa: ARG002
        self.calls += 1
        return self._payload


class AsyncStubProvider(SyncStubProvider):
    async def chat_json(self, messages: Any) -> Any:  # noqa: ARG002
        return super().chat_json(messages)


def make_session() -> A1Session:
    s = A1Session(session_id="s1", user_id="u1", ip_code="IP0001")
    s.creator_primary = "setting_heavy"
    return s


def _payload() -> dict:
    return {
        "suggestions": [
            {"module": "IP定位", "subfield": "name", "value": "星陨大陆",
             "reason": "种子基调推演"},
            {"module": "IP定位", "subfield": "concept", "value": "因果轮回",
             "reason": "呼应主线"},
            {"module": "世界本体", "subfield": "reality_rule", "value": "意志扭曲物质",
             "reason": "力量体系对齐"},
            {"module": "世界本体", "subfield": "existence", "value": "有机宇宙",
             "reason": "基调延伸"},
            {"module": "IP定位", "subfield": "tone", "value": "待补充",
             "reason": "占位——应被 J1 拦截"},
            {"module": "不存在的模块", "subfield": "x", "value": "zzz",
             "reason": "配方外——应被过滤"},
        ],
    }


class TestBuild:
    def test_single_llm_call_produces_up_to_five_suggestions(self):
        p = SyncStubProvider(_payload())
        pack = InferencePacker(p).build(make_session())
        assert p.calls == 1  # 单次调用
        assert 3 <= len(pack.suggestions) <= 5
        # 占位与配方外建议被过滤（J1 + 配方并集）
        keys = {(x.module, x.subfield) for x in pack.suggestions}
        assert ("IP定位", "tone") not in keys
        assert ("不存在的模块", "x") not in keys

    def test_async_provider_supported(self):
        pack = InferencePacker(AsyncStubProvider(_payload())).build(make_session())
        assert len(pack.suggestions) >= 3

    def test_zero_llm_degrades_to_empty_pack_with_note(self):
        pack = InferencePacker(None).build(make_session())
        assert pack.suggestions == []
        assert pack.note  # 有披露
        assert "provider" in pack.note.lower() or "降级" in pack.note

    def test_malformed_payload_degrades_gracefully(self):
        pack = InferencePacker(SyncStubProvider({"oops": True})).build(make_session())
        assert pack.suggestions == []
        assert pack.note

    def test_already_answered_fields_excluded(self):
        s = make_session()
        s.answers["IP定位.name"] = "已有名"
        pack = InferencePacker(SyncStubProvider(_payload())).build(s)
        assert all(x.subfield != "name" for x in pack.suggestions)


class TestInstallProposalsOnly:
    """核心断言：推断包绝不直写 answers——只进 pending_proposals。"""

    def test_install_never_touches_answers(self):
        s = make_session()
        pack = InferencePacker(SyncStubProvider(_payload())).build(s)
        before = dict(s.answers)
        keys = InferencePacker(None).install(s, pack)
        assert len(keys) >= 3
        assert s.answers == before  # 不直写 answers
        for k in keys:
            entry = s.pending_proposals[k]
            assert entry.get("source") == "inference_pack"
            assert "replace" in entry["options"]

    def test_installed_proposal_confirms_through_existing_flow(self):
        s = make_session()
        pack = InferencePacker(SyncStubProvider(_payload())).build(s)
        keys = InferencePacker(None).install(s, pack)
        out = resolve_proposal(s, keys[0], "replace")
        assert out["applied"] is True
        # 经 fills 通道写入 → llm_fill 溯源（J1 已在 _apply_fills 同语义闸）
        assert list(s.field_sources.values()) == ["llm_fill"]


class TestConfirmFeedback:
    """判定双写：creator_profile 置信修正（确定性，只看不判）。"""

    def test_confirm_bumps_confidence(self):
        s = make_session()
        before = apply_pack_feedback(s, applied=True)
        assert before > 0.0
        assert s.creator_confidence["setting_heavy"] == pytest.approx(before)

    def test_drop_lowers_confidence_floored_at_zero(self):
        s = make_session()
        assert apply_pack_feedback(s, applied=False) == pytest.approx(0.4)
        assert apply_pack_feedback(s, applied=False) == pytest.approx(0.3)
        for _ in range(10):  # 棘轮触底不越界
            apply_pack_feedback(s, applied=False)
        assert s.creator_confidence["setting_heavy"] == 0.0

    def test_unprofiled_session_uses_fallback_bucket(self):
        s = make_session()
        s.creator_primary = ""
        apply_pack_feedback(s, applied=True)
        assert s.creator_confidence.get("unprofiled", 0) > 0


class TestRoutes:
    """API 面：触发端点 additive；confirm 复用既有 /chat/confirm。"""

    def test_inference_pack_endpoint_and_confirm_dual_write(self, client, monkeypatch):
        import app.api.a1_routes as routes
        from fastapi.testclient import TestClient

        # start a session through the real endpoint
        resp = client.post(
            "/api/a1/session/start",
            json={"user_id": "u1", "custom_idea": "星陨大陆的意志世界"},
        )
        assert resp.status_code == 200
        body = resp.json()
        sid, fid = body["session_id"], body["file_id"]

        monkeypatch.setattr(
            routes, "_get_inference_packer",
            lambda: InferencePacker(SyncStubProvider(_payload())),
        )
        resp = client.post(f"/api/a1/file/{fid}/inference-pack")
        assert resp.status_code == 200
        pack_body = resp.json()
        assert 3 <= len(pack_body["suggestions"]) <= 5
        assert all(p.get("key") for p in pack_body["suggestions"])

        # confirm via existing proposal endpoint
        session = routes._SESSIONS[sid]
        first = pack_body["suggestions"][0]
        resp = client.post("/api/a1/chat/confirm", json={
            "session_id": sid,
            "kind": "fill",
            "choice": "替换",
            "proposal": {"key": first["key"]},
        })
        assert resp.status_code == 200
        assert resp.json()["applied"] is True
        key = f"{first['module']}.{first['subfield']}"
        assert session.answers.get(key)
        assert session.creator_confidence.get("unprofiled", 0) > 0

    def test_file_status_exposes_field_sources(self, client):
        resp = client.post(
            "/api/a1/session/start",
            json={"user_id": "u1", "custom_idea": "星陨大陆的意志世界"},
        )
        fid = resp.json()["file_id"]
        body = client.get(f"/api/a1/file/{fid}").json()
        assert "field_sources" in body  # additive optional key
        assert isinstance(body["field_sources"], dict)
