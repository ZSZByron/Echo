"""波次二批 E-2：存量兼容全检——43 字段时代旧 payload 端到端重放。

fixture = 预部署序列化会话（T1 契约 _A1SESSION_OLD_FIELDS 43 枚全量、
无 material_pool/list_thread/mirror_thread 五枚新字段、无结构化形状
fills——answers 全纯文本 ●、进行中状态）→ 存储文件直写 → 加载
（A1Store/A1Session.model_validate 直通）→ 继续访谈一轮（新答案按 ●
落库）→ 定稿（missing_sections 与 fixture 手工预计算一致）→ graphify+
编译（graph 输出形状与 T9 回归锁语义一致：无形状 → 零 transition/linkage
新边、● 现行路径不变形）。

端到端走 TestClient 四端点（file GET → chat → finalize → graph），
LLM 零真实调用（chat 用确定性 stub；graphify 由 conftest autouse
provider stub 降级为纯 TREE 图——既有 finalize 测试同一范式）。
"""
from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api import a1_routes
from app.domains.creation.a1.guide_engine import A1Session
from app.domains.creation.a1.interviewer import InterviewFill, InterviewResult
from app.domains.creation.seed.a1_question_tree import get_module
from app.main import app

# ---------------------------------------------------------------------------
# 43 字段时代旧 payload fixture（对照 T1 契约测试 _A1SESSION_OLD_FIELDS）
# ---------------------------------------------------------------------------

_LEGACY_SESSION_ID = "a1_legacy43"
_LEGACY_FILE_ID = "legacy_file_e2"

#: 43 旧字段全量清单（T1 契约测试同源，逐字对照）
_LEGACY_43_FIELDS: frozenset[str] = frozenset({
    "session_id", "user_id", "ip_code", "current_module", "current_subfield",
    "answers", "phase", "seed_name", "seed_genre", "seed_description",
    "creator_primary", "creator_secondary", "creator_profile_source",
    "recipe_id", "recipe_modules", "stall_subfield", "stall_count",
    "pending_suggestions", "knowledge_thread_active", "knowledge_thread_turns",
    "pending_proposals", "merge_counts", "answer_clips", "prefill_fields",
    "field_sources", "creator_confidence", "character_sketch",
    "deflect_counts", "open_question_archive", "impulse_coords",
    "message_rounds", "invited_modules", "closing_step", "closing_settled",
    "closing_answers", "resume_later", "pending_alignments", "draft_alpha",
    "auto_merge_log", "merge_undo", "current_options", "options_key",
    "reroll_streak",
})

#: 批A-C additive 五枚新字段（旧 payload 必须不含）
_POST_FIELDS: frozenset[str] = frozenset({
    "material_pool", "list_thread_key", "list_thread_turns",
    "mirror_thread_active", "mirror_thread_turns",
})


def _legacy_payload() -> dict[str, Any]:
    """构造 43 字段旧 payload：进行中状态、无形状 fills、配方限定角色。"""
    session = A1Session(
        session_id=_LEGACY_SESSION_ID,
        user_id="u_legacy",
        ip_code="IP0042",
        phase="asking",  # 进行中
        recipe_id="plot",
        recipe_modules=["角色"],
        message_rounds=7,
    )
    # 旧宇宙纯文本答案：6 字段中已答 2（= 33%，严格低于 >50% 定稿门禁）
    session.answers["角色.identity"] = "边城义庄的守夜人"
    session.answers["角色.key_relations"] = "与叛出师门的师兄互为唯一软肋"
    payload = session.model_dump()
    # 手工剥离五枚新字段 → 纯 43 字段时代序列化形态
    for key in _POST_FIELDS:
        payload.pop(key, None)
    return payload


def _legacy_file_rec() -> dict[str, Any]:
    """43 字段时代的 file 记录（与 start_session 现行形态同构的 draft 态）。"""
    return {
        "session_id": _LEGACY_SESSION_ID, "status": "draft",
        "ip": 42, "graph_code": None, "graph_json": None,
        "confirmed_edges": {}, "rejected_edges": {},
        "open_questions": [], "edge_stats": {
            "semantic_total": 0, "semantic_confirmed": 0,
            "rule_total": 0, "structure_total": 0, "pending_review": 0,
        },
    }


def _seed_legacy_store() -> None:
    """把旧 payload 直写进 conftest autouse 绑定的 tmp store 文件。"""
    doc = {
        "version": 1,
        "sessions": {_LEGACY_SESSION_ID: _legacy_payload()},
        "files": {_LEGACY_FILE_ID: _legacy_file_rec()},
    }
    a1_routes._STORE.path.write_text(
        json.dumps(doc, ensure_ascii=False), encoding="utf-8",
    )
    # 触发下一次端点访问时懒加载
    a1_routes._loaded = False
    a1_routes._SESSIONS.clear()
    a1_routes._FILES.clear()


class _LegacyChatStub:
    """存量续访 stub：一轮 4 条 ● 纯文本 fills（无 relation=无形状语义）。"""

    def interview(self, session: Any, text: str) -> InterviewResult:  # noqa: ARG002
        fills = [
            InterviewFill(module="角色", subfield=sf, value=f"旧友-{sf}")
            for sf in ("desire", "flaw", "arc_direction", "character_visual")
        ]
        return InterviewResult.model_construct(
            fills=fills, guidance_reply="记下了。",
        )

    def classify_confirm_intent(self, old: str, new: str, reply: str) -> str:  # noqa: ARG002
        return "other"

    def set_pending_open_question(self, question: dict) -> None:  # noqa: ARG002
        pass

    def take_open_question_answered(self) -> dict | None:
        return None

    def suggest_examples(self, session: Any, module_id: str, subfield_id: str) -> list[str]:  # noqa: ARG002
        return []

    def forced_allocate(self, session: Any, text: str) -> InterviewResult:  # noqa: ARG002
        return InterviewResult.model_construct(fills=[], guidance_reply="再说说？")


@pytest.fixture()
def legacy_loaded(client):  # noqa: ARG002 - ordering only
    _seed_legacy_store()
    # 任意端点触发 _load_once → model_validate 直通
    resp = client.get(f"/api/a1/file/{_LEGACY_FILE_ID}")
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def client():
    return TestClient(app)


class TestLegacyPayloadShape:
    def test_fixture_is_pure_43_field_era(self):
        """fixture 自检：恰 43 字段、五枚新字段零渗入。"""
        payload = _legacy_payload()
        assert frozenset(payload) == _LEGACY_43_FIELDS
        assert not (frozenset(payload) & _POST_FIELDS)
        # 无形状 fills：answers 全纯文本
        assert all(isinstance(v, str) for v in payload["answers"].values())

    def test_model_validate_passes_through(self):
        """旧 payload → 现行 A1Session：additive 默认值直通零迁移。"""
        restored = A1Session.model_validate(_legacy_payload())
        assert restored.material_pool == []
        assert restored.list_thread_key == ""
        assert restored.list_thread_turns == 0
        assert restored.mirror_thread_active is False
        assert restored.mirror_thread_turns == 0
        assert restored.answers["角色.identity"] == "边城义庄的守夜人"


class TestLegacyEndToEnd:
    def test_load_interview_finalize_graph_full_chain(
        self, client, legacy_loaded, monkeypatch,
    ):
        # -- 1. 加载直通：会话与文件都回来了，值逐字一致 --
        session = a1_routes._SESSIONS[_LEGACY_SESSION_ID]
        assert isinstance(session, A1Session)
        assert session.answers["角色.identity"] == "边城义庄的守夜人"
        assert session.material_pool == []  # additive 默认
        assert legacy_loaded["status"] == "draft"

        # -- 2. 定稿门禁预计算：2/6 = 33% ≤ half → 409 恰 ["角色"] --
        fin = client.post(f"/api/a1/file/{_LEGACY_FILE_ID}/finalize")
        assert fin.status_code == 409
        assert fin.json()["detail"]["missing_sections"] == ["角色"]

        # -- 3. 继续访谈一轮：新答案按 ● 纯文本落库 --
        monkeypatch.setattr(a1_routes, "_get_interviewer", lambda: _LegacyChatStub())
        chat = client.post(
            "/api/a1/chat",
            json={"session_id": _LEGACY_SESSION_ID, "message": "继续补全他"},
        )
        assert chat.status_code == 200, chat.text
        body = chat.json()
        assert body["proposals"] == []
        for sf in ("desire", "flaw", "arc_direction", "character_visual"):
            val = session.answers[f"角色.{sf}"]
            assert isinstance(val, str)  # ● 现行路径：不变形、不升级
        assert session.list_thread_key == ""  # 非 complement 不停驻
        assert session.material_pool == []

        # -- 4. 定稿：6/6 全答 → 200 --
        fin2 = client.post(f"/api/a1/file/{_LEGACY_FILE_ID}/finalize")
        assert fin2.status_code == 200, fin2.text
        assert fin2.json()["status"] == "finalized"

        # -- 5. graph：无形状 → 零 transition/linkage 新边（T9 回归锁语义）--
        graph = client.get(f"/api/a1/file/{_LEGACY_FILE_ID}/graph")
        assert graph.status_code == 200
        gjson = graph.json()
        assert gjson["scene_id"] == _LEGACY_SESSION_ID
        assert gjson["nodes"], "纯 TREE 投影至少有节点"
        edge_types = {e["edge_type"] for e in gjson["edges"]}
        assert "transition" not in edge_types
        assert "linkage" not in edge_types
        # answers 在 finalize 全链后仍是纯文本（序列化往返零形变）
        assert isinstance(session.answers["角色.identity"], str)

        # -- 6. 再序列化直通：定稿后的会话仍可 model_validate 往返 --
        redumped = session.model_dump()
        A1Session.model_validate(redumped)  # 不抛即过

    def test_store_roundtrip_via_endpoint_view(self, legacy_loaded):
        """GET file 视图与 fixture 值一致（旧 payload 加载后读侧投影不变）。"""
        assert legacy_loaded["answers"]["角色.identity"] == "边城义庄的守夜人"
        mod = get_module("角色")
        assert mod is not None  # 旧宇宙模块现行注册表仍可定位
