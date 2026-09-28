# -*- coding: utf-8 -*-
"""D20 动态模块调用（2026-09-25 产品方裁决）——TDD 契约测试。

产品方原话（逐字）："是用户提及世界观设定的时候，调用世界观模块！"

设计要点（逐条锚定测试）：
- A1Session.invited_modules: list[str] = []（零迁移，G3）
- 检测 = LLM 提议（interview JSON 可选键 worldview_invites）+ 确定性校验
  （guide_engine 单消费：闭集=世界建构族、去重、跳过已在游走清单、
  每会话 ≤4、插入点=当前模块之后）
- 门禁零强制（DN1）：invited 模块绝不进 missing_sections / finalizable
- 披露：回复追加确定性模板通知；审计事件 worldview_invoked 全留痕
- 故事线默认纯故事（D19/055da41 灵魂契约）：未 invite 前，故事会话
  字段清单零世界建构字段（G5 liveness 双向锚定）
"""
from __future__ import annotations

from pydantic import BaseModel

from app.domains.creation.a1.guide_engine import (
    A1Session,
    core_recipe_modules,
    handle_message,
    progress,
    sync_position,
)
from app.domains.creation.a1.interviewer import (
    FakeInterviewer,
    InterviewFill,
    RealLLMInterviewer,
)
from app.domains.creation.shared.module_registry import MODULE_POOL, RECIPES
from app.domains.creation.seed.a1_question_tree import all_subfield_keys

STORY_RECIPE = list(RECIPES["plot"].module_ids)  # ["剧情", "角色"]


def _story_session() -> A1Session:
    s = A1Session(
        session_id="t-invite",
        user_id="u",
        recipe_id="plot",
        recipe_modules=list(STORY_RECIPE),
    )
    sync_position(s)
    return s


class TestSessionContract:
    """invited_modules 默认 [] 零迁移 + model_validate roundtrip。"""

    def test_default_empty_zero_migration(self):
        s = A1Session(session_id="s", user_id="u")
        assert s.invited_modules == []

    def test_legacy_payload_roundtrip(self):
        # 存量 JSON（无 invited_modules 键）→ validate 通过（G3）
        s = A1Session.model_validate({
            "session_id": "s", "user_id": "u",
            "recipe_id": "plot", "recipe_modules": STORY_RECIPE,
        })
        assert s.invited_modules == []

    def test_roundtrip_preserves_invited(self):
        s = _story_session()
        s.invited_modules = ["力量体系"]
        dump = s.model_dump()
        s2 = A1Session.model_validate(dump)
        assert s2.invited_modules == ["力量体系"]


class TestDetectionParse:
    """LLM 提议解析：interview JSON 可选键 worldview_invites（向前兼容）。"""

    def _parse(self, raw: dict) -> object:
        return RealLLMInterviewer(provider=None)._parse(raw, "text", recipe=STORY_RECIPE)

    def test_invites_key_parsed(self):
        r = self._parse({
            "guidance_reply": "好", "fills": [],
            "worldview_invites": ["力量体系"],
        })
        assert r.worldview_invites == ["力量体系"]

    def test_missing_key_no_change_forward_compat(self):
        r = self._parse({"guidance_reply": "好", "fills": []})
        assert r.worldview_invites == []

    def test_non_string_items_dropped_at_parse(self):
        r = self._parse({
            "guidance_reply": "好", "fills": [],
            "worldview_invites": ["力量体系", 42, None, ""],
        })
        assert r.worldview_invites == ["力量体系"]


class TestDeterministicValidation:
    """确定性校验（LLM 不写状态）：闭集/去重/跳过已在清单/上限 4。"""

    def test_valid_invite_inserted_after_current_module(self):
        s = _story_session()
        out = handle_message(s, "魔法消耗什么？", FakeInterviewer(worldview_invites=["力量体系"]))
        assert s.invited_modules == ["力量体系"]
        # 插入点 = 当前模块（剧情）之后
        assert s.recipe_modules == ["剧情", "力量体系", "角色"]
        # 披露：回复含模块名与可跳过提示
        assert "力量体系" in out["reply"]
        assert "跳过" in out["reply"]

    def test_unknown_id_dropped(self):
        s = _story_session()
        handle_message(s, "x", FakeInterviewer(worldview_invites=["不存在的模块"]))
        assert s.invited_modules == []
        assert s.recipe_modules == STORY_RECIPE

    def test_story_module_id_never_invitable(self):
        s = _story_session()
        handle_message(s, "x", FakeInterviewer(worldview_invites=["剧情", "角色"]))
        assert s.invited_modules == []

    def test_output_module_id_never_invitable(self):
        s = _story_session()
        output_ids = [mid for mid, d in MODULE_POOL.items() if d.family == "output"]
        assert output_ids  # 前置：产出模块在池
        handle_message(s, "x", FakeInterviewer(worldview_invites=output_ids))
        assert s.invited_modules == []

    def test_closed_set_is_worldview_ten(self):
        from app.domains.creation.a1.guide_engine import WORLDVIEW_MODULE_IDS
        from app.domains.creation.seed.a1_question_tree import module_ids

        assert WORLDVIEW_MODULE_IDS == frozenset(module_ids())

    def test_second_mention_deduped(self):
        s = _story_session()
        handle_message(s, "x", FakeInterviewer(worldview_invites=["力量体系"]))
        handle_message(s, "y", FakeInterviewer(worldview_invites=["力量体系"]))
        assert s.invited_modules == ["力量体系"]
        assert s.recipe_modules.count("力量体系") == 1

    def test_cap_four_per_session(self):
        s = _story_session()
        handle_message(
            s, "x",
            FakeInterviewer(worldview_invites=[
                "力量体系", "地理空间", "文明与社会", "历史时间线", "视觉设计",
            ]),
        )
        assert s.invited_modules == ["力量体系", "地理空间", "文明与社会", "历史时间线"]
        assert len(s.invited_modules) == 4

    def test_multiple_invites_order_preserved(self):
        s = _story_session()
        handle_message(
            s, "x",
            FakeInterviewer(worldview_invites=["力量体系", "地理空间"]),
        )
        assert s.recipe_modules == ["剧情", "力量体系", "地理空间", "角色"]

    def test_default_session_invite_noop(self):
        # default 全集（recipe_modules 空 = 全集）：invites 全部已在你清单 → 跳过
        s = A1Session(session_id="s", user_id="u")
        sync_position(s)
        out = handle_message(s, "x", FakeInterviewer(worldview_invites=["力量体系"]))
        assert s.invited_modules == []
        assert "力量体系——我把它加入" not in out["reply"]

    def test_invite_resets_stall_tracking(self):
        s = _story_session()
        s.stall_subfield = "剧情.core_dilemma"
        s.stall_count = 2
        handle_message(s, "x", FakeInterviewer(worldview_invites=["力量体系"]))
        assert s.stall_count == 0
        assert s.stall_subfield == ""

    def test_audit_event_logged(self, monkeypatch):
        events: list[tuple] = []
        import app.domains.creation.a1.guide_engine as ge
        monkeypatch.setattr(
            ge, "log_event",
            lambda sid, event, **kw: events.append((sid, event, kw)),
        )
        s = _story_session()
        handle_message(s, "x", FakeInterviewer(worldview_invites=["力量体系"]))
        inv = [e for e in events if e[1] == "worldview_invoked"]
        assert len(inv) == 1
        assert inv[0][2]["modules"] == ["力量体系"]
        assert inv[0][2]["trigger"] == "user_mention"

    def test_no_audit_event_when_nothing_accepted(self, monkeypatch):
        events: list[tuple] = []
        import app.domains.creation.a1.guide_engine as ge
        monkeypatch.setattr(
            ge, "log_event",
            lambda sid, event, **kw: events.append((sid, event, kw)),
        )
        s = _story_session()
        handle_message(s, "x", FakeInterviewer(worldview_invites=["剧情"]))
        assert not [e for e in events if e[1] == "worldview_invoked"]


class TestWalkSemantics:
    """插入后游走覆盖 invited 模块；未 invite 前指针不动。"""

    def test_walk_covers_invited_module(self):
        s = _story_session()
        handle_message(s, "x", FakeInterviewer(worldview_invites=["力量体系"]))
        # 答完剧情全部字段（占位也算）→ 指针应到达 力量体系（在 角色 之前）
        m = [mod for mod in ("剧情",) for f in []]  # noqa: F841 — 占位说明
        from app.domains.creation.seed.a1_question_tree import get_module
        for f in get_module("剧情")["fields"]:
            s.answers[f"剧情.{f['id']}"] = "答案"
        sync_position(s)
        assert s.current_module == "力量体系"


class TestGateZeroForcing:
    """DN1：门禁只遍历核心配方（recipe_modules - invited_modules）。"""

    def test_core_recipe_excludes_invited(self):
        s = _story_session()
        s.recipe_modules = ["剧情", "力量体系", "角色"]
        s.invited_modules = ["力量体系"]
        assert core_recipe_modules(s) == ["剧情", "角色"]

    def test_invited_incomplete_still_finalizable(self):
        s = _story_session()
        handle_message(s, "x", FakeInterviewer(worldview_invites=["力量体系"]))
        # 核心配方（剧情+角色）过半填写；invited 力量体系零回答
        from app.domains.creation.seed.a1_question_tree import get_module
        for mid in ("剧情", "角色"):
            for f in get_module(mid)["fields"]:
                s.answers[f"{mid}.{f['id']}"] = "答案"
        p = progress(s)
        assert p["finalizable"] is True

    def test_invited_module_not_in_missing_sections(self, client, monkeypatch):
        from app.api import a1_routes

        resp = client.post("/api/a1/session/start", json={
            "user_id": "u", "custom_idea": "测试", "impulse_primary": "plot",
        })
        assert resp.status_code == 200
        sid = resp.json()["session_id"]
        file_id = resp.json()["file_id"]
        session = a1_routes._SESSIONS[sid]
        # 模拟确定性 handler 已应用 invite（单测已覆盖 handler 本身）
        session.recipe_modules.insert(1, "力量体系")
        session.invited_modules = ["力量体系"]
        # 核心配方过半填写
        from app.domains.creation.seed.a1_question_tree import get_module
        for mid in ("剧情", "角色"):
            for f in get_module(mid)["fields"]:
                session.answers[f"{mid}.{f['id']}"] = "答案"

        resp = client.post(f"/api/a1/file/{file_id}/finalize")
        assert resp.status_code == 200, resp.status_code
        # 对照：门禁视角若含 invited 会 409——missing 永不含 invited
        core = core_recipe_modules(session)
        missing = [
            mid for mid in session.recipe_modules
            if mid not in set(core) or True
        ]
        assert "力量体系" not in core

    def test_core_recipe_still_gated(self, client):
        from app.api import a1_routes

        resp = client.post("/api/a1/session/start", json={
            "user_id": "u", "custom_idea": "测试", "impulse_primary": "plot",
        })
        file_id = resp.json()["file_id"]
        resp = client.post(f"/api/a1/file/{file_id}/finalize")
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert set(detail["missing_sections"]) == {"剧情", "角色"}


class TestG5Liveness:
    """G5 双向锚定：invite 前故事清单零世界建构字段；invite 后下一轮即含。"""

    def _prompt(self, session: A1Session) -> str:
        from app.domains.creation.seed.a1_question_tree import (
            get_module, get_subfield,
        )
        m = get_module(session.current_module)
        sf = get_subfield(session.current_module, session.current_subfield)
        return RealLLMInterviewer(provider=None)._build_prompt(m, sf, session)

    def test_before_invite_zero_worldview_fields(self):
        # 055da41 灵魂契约：故事会话字段清单零世界建构字段
        s = _story_session()
        prompt = self._prompt(s)
        from app.domains.creation.seed.a1_question_tree import module_ids
        for mid in module_ids():
            assert f"{mid}." not in prompt

    def test_after_invite_catalog_contains_invited_fields_next_turn(self):
        s = _story_session()
        handle_message(s, "x", FakeInterviewer(worldview_invites=["力量体系"]))
        prompt = self._prompt(s)  # 下一轮 prompt = live 会话状态
        assert "力量体系.source" in prompt

    def test_fills_parse_accepts_invited_field_after_invite(self):
        s = _story_session()
        handle_message(s, "x", FakeInterviewer(worldview_invites=["力量体系"]))
        # 下一轮 LLM 返回 invited 字段的 fill → 合法键 = live 游走清单
        from tests.unit.a1.conftest import StubLLMProvider as SLP
        provider = SLP(response={
            "guidance_reply": "好",
            "fills": [{"module": "力量体系", "subfield": "source", "value": "古神"}],
        })
        result = RealLLMInterviewer(provider).interview(s, "力量来自古神")
        assert [("力量体系", "source")] in [
            [(f.module, f.subfield)] for f in result.fills
        ]


class TestLivePropagation:
    """sections / 图谱合法锚点 / 溯源键空间 = live 游走清单（含 invited）。"""

    def test_build_sections_includes_invited(self):
        from app.api.a1_routes import _build_sections

        s = _story_session()
        handle_message(s, "x", FakeInterviewer(worldview_invites=["力量体系"]))
        ids = [sec["id"] for sec in _build_sections(s)]
        assert ids == ["剧情", "力量体系", "角色"]

    def test_graphify_legal_anchors_include_invited(self):
        from app.api.a1_routes import _recipe_legal_anchors

        s = _story_session()
        handle_message(s, "x", FakeInterviewer(worldview_invites=["力量体系"]))
        assert "力量体系.source" in _recipe_legal_anchors(s)

    def test_field_sources_keyspace_reanchored_to_live_walk(self):
        from app.domains.creation.a1.guide_engine import _apply_fills
        from app.domains.creation.seed.a1_question_tree import get_module

        s = _story_session()
        handle_message(s, "x", FakeInterviewer(worldview_invites=["力量体系"]))
        _apply_fills(s, [InterviewFill(module="力量体系", subfield="source", value="古神")])
        legal = set(all_subfield_keys(recipe=s.recipe_modules))
        assert set(s.field_sources) <= legal
        # invited 键在 live 并集内（契约重锚后成立）
        assert "力量体系.source" in legal

    def test_progress_sections_render_invited_live(self):
        s = _story_session()
        handle_message(s, "x", FakeInterviewer(worldview_invites=["力量体系"]))
        ids = [sec["id"] for sec in progress(s)["sections"]]
        assert "力量体系" in ids


class TestPromptContract:
    """prompt 契约：世界建构域目录 + invites 指令 + JSON 键文档化（D20）。"""

    def test_prompt_contains_domain_catalog_and_instruction(self):
        s = _story_session()
        from app.domains.creation.seed.a1_question_tree import (
            get_module, get_subfield,
        )
        m = get_module(s.current_module)
        sf = get_subfield(s.current_module, s.current_subfield)
        prompt = RealLLMInterviewer(provider=None)._build_prompt(m, sf, s)
        assert "worldview_invites" in prompt
        assert "力量体系" in prompt   # 域描述符逐模块一行
        assert "地理空间" in prompt
        assert "设定边界" in prompt

    def test_prompt_json_contract_documents_optional_key(self):
        s = _story_session()
        from app.domains.creation.seed.a1_question_tree import (
            get_module, get_subfield,
        )
        m = get_module(s.current_module)
        sf = get_subfield(s.current_module, s.current_subfield)
        prompt = RealLLMInterviewer(provider=None)._build_prompt(m, sf, s)
        # 契约增补文档化（G6b/M0 先例：可选键向前兼容）
        assert '"worldview_invites"' in prompt


class TestM0Unchanged:
    """M0 偏转/素材归档在 invited 模块内语义不变；门禁不受占位影响。"""

    def test_deflect_inside_invited_module_advances_and_not_counted(self):
        s = _story_session()
        handle_message(s, "x", FakeInterviewer(worldview_invites=["力量体系"]))
        from app.domains.creation.seed.a1_question_tree import get_module
        for f in get_module("剧情")["fields"]:
            s.answers[f"剧情.{f['id']}"] = "答案"
        sync_position(s)
        assert s.current_module == "力量体系"
        out = handle_message(s, "先跳过", FakeInterviewer(deflect=True))
        # 占位答案写入 → 门禁不计数（J1 真值闸），指针前进
        key = next(
            k for k in s.answers if k.startswith("力量体系.")
        )
        assert s.answers[key] == "（用户跳过）"
        assert out["phase"] in ("asking", "completed")

    def test_invited_placeholder_never_satisfies_gate(self):
        s = _story_session()
        handle_message(s, "x", FakeInterviewer(worldview_invites=["力量体系"]))
        from app.domains.creation.seed.a1_question_tree import get_module
        for mid in ("剧情", "角色"):
            for f in get_module(mid)["fields"]:
                s.answers[f"{mid}.{f['id']}"] = "答案"
        # invited 模块全部占位
        for f in get_module("力量体系")["fields"]:
            s.answers[f"力量体系.{f['id']}"] = "（用户跳过）"
        # 门禁 = 核心配方 → finalizable（占位在 invited 内也绝不阻塞）
        assert progress(s)["finalizable"] is True
