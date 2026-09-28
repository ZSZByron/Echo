"""Contract tests for closing_flow — 收尾三连问状态机 + 可生成物按动机排序 (D21 Task 10).

Pure-state contracts, zero LLM:

1. Transition matrix (spec v1.3 §5.4 L69-72, D21⑧):
   untriggered → triggered（双条件命中）→ 三问逐一作答 → settled；
   中途输入设定内容 = 「继续」自由流（不打断），条件仍满足 → 重新提示；
   settled 后不再重触发。
2. 「改天继续」= 同会话持久化标记（D21⑨，不建新会话）——经 A1Store
   save/load 往返保留。
3. Preview ordering (D22⑤): 可生成物按会话动机（creator_primary 三线
   分类，spec v1.3 §5.2）排序——故事线 story_outline 打头 / 设定线
   world_bible 打头 / 通用线通用投影三件按声明序打头；跑团件恒排末并
   标「进阶可用」。
4. Wiring: guide_engine._handle_message_impl 轮末消费本模块（尾部接线）；
   D20 接缝（invited_modules 不阻塞双条件）复用 T6 契约。
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.domains.creation.a1.closing_flow import (
    QUESTIONS,
    advance_answer,
    closing_settled,
    creator_line,
    interject,
    maybe_trigger,
    order_artifacts,
)
from app.domains.creation.a1.closing_gate import is_preset_phase_complete
from app.domains.creation.a1.guide_engine import (
    A1Session,
    PHASE_ASKING,
    PHASE_COMPLETED,
    _handle_message_impl,
)
from app.domains.creation.a1.store import A1Store


# ── fixtures ─────────────────────────────────────────────────────────────────


def _completed_session(**kw) -> A1Session:
    """双条件已满足的会话（问题树走查态 + pending 清零）。"""
    s = A1Session(session_id="s1", user_id="u1", phase=PHASE_COMPLETED, **kw)
    return s


def _chat_result(reply: str = "好的，聊聊。"):
    """Fake interviewer result: chat/off-topic branch（零 fills）。"""
    return SimpleNamespace(
        deflect=False,
        story_material=None,
        fills=[],
        is_innovative=False,
        guidance_reply=reply,
        worldview_invites=[],
        divergent_question=None,
    )


class _FakeInterviewer:
    def interview(self, session, text):
        return _chat_result()


# ── 1. transition matrix ─────────────────────────────────────────────────────


class TestTransitionMatrix:
    def test_untriggered_stays_silent_when_asking(self):
        s = A1Session(session_id="s1", user_id="u1", phase=PHASE_ASKING)
        assert maybe_trigger(s) is None
        assert s.closing_step == 0

    def test_dual_condition_hit_enters_q1(self):
        s = _completed_session()
        q = maybe_trigger(s)
        assert q is not None and "生成文档" in q
        assert s.closing_step == 1

    def test_trigger_is_idempotent(self):
        s = _completed_session()
        maybe_trigger(s)
        # 已在收尾态：再次调用不重置进度
        assert maybe_trigger(s) is None
        assert s.closing_step == 1

    def test_three_answers_generate_doc_path_settles(self):
        s = _completed_session()
        maybe_trigger(s)
        out1 = advance_answer(s, "生成文档")
        assert s.closing_step == 2
        assert s.closing_answers["q1"] == "generate_doc"
        assert "文档" in out1
        out2 = advance_answer(s, "让 AI 补")
        assert s.closing_step == 3
        assert s.closing_answers["q2"] == "ai_fill_yes"
        out3 = advance_answer(s, "改天吧")
        assert closing_settled(s) is True
        assert s.closing_step == 0
        assert s.resume_later is True
        assert "改天" in out3

    def test_continue_choice_also_advances_sequence(self):
        s = _completed_session()
        maybe_trigger(s)
        advance_answer(s, "继续访谈录入设定")
        assert s.closing_answers["q1"] == "continue"
        assert s.closing_step == 2
        assert s.resume_later is False

    def test_mid_deviation_stays_free_flow_and_reprompts(self):
        """设定内容 = 「继续」自由流：不打断、不推进；条件仍满足 → 重提示。"""
        s = _completed_session()
        maybe_trigger(s)
        ans = advance_answer(s, "主角叫李雷，他有一把祖传的长剑")
        assert ans is None  # 非显式选择 → 交回自由流
        assert s.closing_step == 1  # 状态机未推进
        out = {"reply": "已记录你的设定。"}
        out2 = interject(s, "主角叫李雷，他有一把祖传的长剑", out)
        assert out2["reply"].startswith("已记录你的设定。")  # 原回复保留
        assert "生成文档" in out2["reply"]  # 重提示当前问题

    def test_settled_never_reprompts(self):
        s = _completed_session()
        maybe_trigger(s)
        for ans in ("生成文档", "不用", "今天就到这"):
            advance_answer(s, ans)
        assert closing_settled(s) is True
        out = {"reply": "x"}
        assert interject(s, "再来一句", out) == out
        assert out["reply"] == "x"

    def test_invited_modules_do_not_block_trigger(self):
        """D20 接缝：invited 问题不计入双条件（复用 T6 契约）。"""
        s = _completed_session(invited_modules=["力量体系"])
        assert is_preset_phase_complete(s) is True
        assert maybe_trigger(s) is not None


class TestExplicitAnswers:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("生成文档", "generate_doc"),
            ("想导出文档", "generate_doc"),
            ("继续", "continue"),
            ("再补充点设定", "continue"),
        ],
    )
    def test_q1(self, text, expected):
        s = _completed_session()
        maybe_trigger(s)
        advance_answer(s, text)
        assert s.closing_answers["q1"] == expected

    @pytest.mark.parametrize(
        ("text", "expected"),
        [("让 AI 补", "ai_fill_yes"), ("好的帮我补", "ai_fill_yes"), ("不用", "ai_fill_no"), ("先不用了", "ai_fill_no")],
    )
    def test_q2(self, text, expected):
        s = _completed_session()
        s.closing_step = 2
        advance_answer(s, text)
        assert s.closing_answers["q2"] == expected

    @pytest.mark.parametrize(
        ("text", "expected", "resume"),
        [("改天继续", "resume_later", True), ("好，下次再来", "resume_later", True), ("今天就到这", "today_end", False), ("不用了", "today_end", False)],
    )
    def test_q3(self, text, expected, resume):
        s = _completed_session()
        s.closing_step = 3
        advance_answer(s, text)
        assert s.closing_answers["q3"] == expected
        assert s.resume_later is resume

    def test_non_answer_text_is_none(self):
        s = _completed_session()
        maybe_trigger(s)
        assert advance_answer(s, "这个世界的货币叫晶币") is None


# ── 2. preview ordering (D22⑤ 按动机排序) ────────────────────────────────────


class TestPreviewOrdering:
    def test_story_line_story_outline_first(self):
        s = _completed_session(creator_primary="plot")
        ids = [c["id"] for c in order_artifacts(s)]
        assert ids[0] == "story_outline"

    def test_story_line_romance_also_story_outline_first(self):
        s = _completed_session(creator_primary="romance")
        assert [c["id"] for c in order_artifacts(s)][0] == "story_outline"

    def test_setting_line_world_bible_first(self):
        s = _completed_session(creator_primary="setting_heavy")
        ids = [c["id"] for c in order_artifacts(s)]
        assert ids[0] == "world_bible"

    def test_general_line_d22_trio_first_in_declared_order(self):
        s = _completed_session(creator_primary="unsure")
        ids = [c["id"] for c in order_artifacts(s)]
        assert ids[:3] == ["world_bible", "character_codex", "story_outline"]

    def test_empty_profile_general_line(self):
        s = _completed_session()  # 存量/无 profile → 通用线兜底
        ids = [c["id"] for c in order_artifacts(s)]
        assert ids[:3] == ["world_bible", "character_codex", "story_outline"]

    def test_trpg_always_last_and_marked_advanced(self):
        for primary in ("plot", "setting_heavy", "unsure", ""):
            s = _completed_session(creator_primary=primary)
            arts = order_artifacts(s)
            trpg = [c for c in arts if c["kind"] == "trpg"]
            d22 = [c for c in arts if c["kind"] == "d22"]
            assert arts[: len(d22)] == d22  # d22 在前
            assert all(c.get("note") == "进阶可用" for c in trpg)

    def test_creator_line_classification_closes_over_ten_types(self):
        assert creator_line(_completed_session(creator_primary="plot")) == "story"
        assert creator_line(_completed_session(creator_primary="romance")) == "story"
        assert (
            creator_line(_completed_session(creator_primary="character_driven"))
            == "story"
        )
        assert creator_line(_completed_session(creator_primary="unsure")) == "general"
        for t in (
            "setting_heavy", "philosophy", "exploration",
            "nostalgia", "healing",
        ):
            assert creator_line(_completed_session(creator_primary=t)) == "setting"
        assert creator_line(_completed_session()) == "general"


# ── 3. persistence（D21⑨ 改天继续 = 同会话持久化） ───────────────────────────


class TestPersistence:
    def test_resume_later_marker_survives_store_roundtrip(self, tmp_path):
        store = A1Store(tmp_path / "store.json")
        s = _completed_session()
        s.closing_step = 3
        advance_answer(s, "改天继续")
        assert s.resume_later is True
        store.save({"s1": s}, {})
        sessions, _ = store.load()
        loaded = sessions["s1"]
        assert loaded.resume_later is True
        assert loaded.closing_settled is True
        assert loaded.closing_answers["q3"] == "resume_later"
        # 不再重触发（同一会话，非新会话）
        assert maybe_trigger(loaded) is None

    def test_default_fields_zero_migration(self):
        """存量会话 model_validate 直通（G3 先例）。"""
        s = A1Session.model_validate({"session_id": "old", "user_id": "u"})
        assert s.closing_step == 0
        assert s.closing_settled is False
        assert s.resume_later is False
        assert s.closing_answers == {}


# ── 4. wiring（_handle_message_impl 尾部） ───────────────────────────────────


class TestWiring:
    def test_round_end_triggers_closing_prompt(self):
        s = _completed_session()
        out = _handle_message_impl(s, "随便聊聊", _FakeInterviewer())
        assert s.closing_step == 1
        assert "生成文档" in out["reply"]

    def test_explicit_answer_via_chat_overrides_reply(self):
        s = _completed_session()
        s.closing_step = 1
        out = _handle_message_impl(s, "生成文档", _FakeInterviewer())
        assert s.closing_answers["q1"] == "generate_doc"
        assert s.closing_step == 2
        # 覆盖闲聊噪声回复，说人话告知文档去向
        assert "文档" in out["reply"]
        assert "世界圣经" in out["reply"] or "story_outline" not in out["reply"]

    def test_setting_content_keeps_interview_reply_and_reprompts(self):
        s = _completed_session()
        s.closing_step = 1
        out = _handle_message_impl(s, "继续聊聊主角", _FakeInterviewer())
        # 非显式选择 → 自由流原回复保留 + 尾部重提示
        assert out["reply"].startswith("好的，聊聊。")
        assert "生成文档" in out["reply"]

    def test_asking_phase_no_interference(self):
        s = A1Session(session_id="s1", user_id="u1", phase=PHASE_ASKING)
        out = _handle_message_impl(s, "随便聊聊", _FakeInterviewer())
        assert s.closing_step == 0
        assert "生成文档" not in out["reply"]


# ── 契约面完整性 ─────────────────────────────────────────────────────────────


class TestQuestionCopy:
    def test_three_questions_no_module_ids(self):
        """三连问文案说人话：不得出现模块 id（M1/M11 等内部代号）。"""
        texts = [q["text"] for q in QUESTIONS]
        assert len(texts) == 3
        for t in texts:
            assert "." not in t
            assert not any(tok in t for tok in ("M1", "M11", "M12", "module"))
