"""Regression tests for the 'blind recording' bug fix (2026-08-26).

Three code paths were recording user input without LLM judgment:
  PATH 1 — prompt rule 3 forced blind fills on every message.
  PATH 2 — stall guard raw-filled at stall 2/3 without LLM judgment.
  PATH 3 — DegradingInterviewer blind-filled on LLM exception.

All tests are written FIRST (TDD RED) and expected to fail against the
old code. They pass once the fix is applied.
"""
from app.domains.creation.a1.guide_engine import (
    A1Session,
    handle_message,
)
from app.domains.creation.a1.interviewer import (
    DegradingInterviewer,
    FakeInterviewer,
    InterviewFill,
    InterviewResult,
)


def make_session() -> A1Session:
    return A1Session(session_id="s1", user_id="u1", ip_code="IP0001")


# =====================================================================
# PATH 3 — DegradingInterviewer must NOT blind-fill on exception
# =====================================================================


class TestDegradingInterviewerNoBlindFill:
    """On LLM failure, DegradingInterviewer must return empty fills and
    ask the user to retry — never record raw text as an answer."""

    def test_degrade_returns_empty_fills_on_exception(self):
        """When inner raises, fills must be empty, no answer written."""
        s = make_session()
        deg = DegradingInterviewer(FakeInterviewer(raise_error=True))
        out = handle_message(s, "星陨大陆", deg)
        assert s.answers == {}
        assert out["file_diff"] == []

    def test_degrade_reply_mentions_unavailable(self):
        """The guidance_reply should tell the user LLM is unavailable."""
        deg = DegradingInterviewer(FakeInterviewer(raise_error=True))
        result = deg.interview(None, "任何输入")
        assert result.fills == []
        assert "不可用" in result.guidance_reply

    def test_degrade_forced_allocate_no_blind_fill(self):
        """forced_allocate on exception must also not blind-fill."""
        deg = DegradingInterviewer(FakeInterviewer(raise_error=True))
        s = make_session()
        result = deg.forced_allocate(s, "任何输入")
        assert result.fills == []
        assert "不可用" in result.guidance_reply


# =====================================================================
# PATH 2 — Stall guard fixes
# =====================================================================


class TestStallGuardNoBlindFill:
    """Stall guard must never raw-fill without LLM judgment."""

    def test_stall_2_suggestions_unavailable_no_raw_fill(self):
        """When suggest_examples returns [] at stall 2, must NOT raw-fill.
        Instead, should reply asking user to rephrase / 跳过.
        """
        s = make_session()
        s.answers["IP定位.name"] = "x"
        s.current_subfield = "concept"

        misroute = FakeInterviewer(
            fills=[InterviewFill(module="IP定位", subfield="core_experience", value="决斗")],
            guidance_reply="已记录。",
            examples=[],  # suggestions unavailable
        )
        user_text = "高魔科技世界"

        handle_message(s, user_text, misroute)  # stall 1
        out2 = handle_message(s, user_text, misroute)  # stall 2, suggestions []

        # CRITICAL: concept must NOT be filled with raw text
        assert "IP定位.concept" not in s.answers
        assert s.current_subfield == "concept"  # position unchanged
        # Should NOT contain raw-fill message
        assert "已按原文直接记录" not in out2["reply"]
        # Should mention rephrase/跳过 options
        assert "跳过" in out2["reply"] or "重新" in out2["reply"] or "换" in out2["reply"]

    def test_stall_3_forced_allocate_returns_fills(self):
        """At stall 3, forced_allocate is called; if it returns fills,
        they are applied with correct file_diff entries.
        """
        s = make_session()
        s.answers["IP定位.name"] = "x"
        s.current_subfield = "concept"

        # This FakeInterviewer will be used for both interview() and forced_allocate()
        # We need a way to make forced_allocate return fills.
        # We'll use a configurable FakeInterviewer.
        fi = FakeInterviewer(
            fills=[InterviewFill(module="IP定位", subfield="core_experience", value="决斗")],
            guidance_reply="已记录。",
            forced_allocate_result=InterviewResult(
                fills=[InterviewFill(module="IP定位", subfield="concept", value="因果轮回")],
                guidance_reply="已通过强制分配记录。",
                is_innovative=False,
            ),
        )
        user_text = "先手必赢的世界"

        handle_message(s, user_text, fi)  # stall 1
        handle_message(s, user_text, fi)  # stall 2 -> suggestions offered
        # Stall 3: forced_allocate should fire and fill concept
        out3 = handle_message(s, user_text, fi)

        assert "IP定位.concept" in s.answers
        assert s.answers["IP定位.concept"] == "因果轮回"
        # file_diff should have the forced-allocated fill
        diff_fields = [d["field"] for d in out3["file_diff"]]
        assert "核心概念" in diff_fields
        assert "已按原文直接记录" not in out3["reply"]

    def test_stall_3_forced_allocate_returns_no_fills(self):
        """At stall 3, if forced_allocate returns no fills, nothing is
        recorded and reply offers options (suggestion numbers / rephrase / 跳过).
        """
        s = make_session()
        s.answers["IP定位.name"] = "x"
        s.current_subfield = "concept"

        fi = FakeInterviewer(
            fills=[InterviewFill(module="IP定位", subfield="core_experience", value="决斗")],
            guidance_reply="已记录。",
            forced_allocate_result=InterviewResult(
                fills=[],
                guidance_reply="请选择一个示例序号、换种说法或回复「跳过」。",
                is_innovative=False,
            ),
        )
        user_text = "嗯"

        handle_message(s, user_text, fi)  # stall 1
        handle_message(s, user_text, fi)  # stall 2 -> suggestions
        out3 = handle_message(s, user_text, fi)  # stall 3 -> forced_allocate, no fills

        assert "IP定位.concept" not in s.answers
        assert out3["file_diff"] == []
        assert "跳过" in out3["reply"] or "重新" in out3["reply"] or "换" in out3["reply"]
        # Stall count should be capped at 3, not incrementing forever
        assert s.stall_count <= 3

    def test_stall_3_no_longer_raw_fills(self):
        """The old '已按原文直接记录' raw-fill at stall 3 must be gone."""
        s = make_session()
        s.answers["IP定位.name"] = "x"
        s.current_subfield = "concept"

        fi = FakeInterviewer(
            fills=[InterviewFill(module="IP定位", subfield="core_experience", value="决斗")],
            guidance_reply="已记录。",
            forced_allocate_result=InterviewResult(
                fills=[],
                guidance_reply="请选序号或跳过。",
                is_innovative=False,
            ),
        )
        user_text = "先手必赢的世界"

        handle_message(s, user_text, fi)  # stall 1
        handle_message(s, user_text, fi)  # stall 2 -> suggestions
        out3 = handle_message(s, user_text, fi)  # stall 3

        # The old blind-fill text must never appear
        assert "已按原文直接记录" not in out3["reply"]


# =====================================================================
# PATH 1 — Prompt rule rewrite
# =====================================================================


class TestPromptJudgmentAllocation:
    """The prompt must use judgment-based allocation, not blind fill."""

    def test_prompt_no_blind_fill_mandate(self):
        """Prompt must NOT contain the old '当前字段必须有 fill' mandate."""
        from app.domains.creation.a1.interviewer import RealLLMInterviewer

        interviewer = RealLLMInterviewer(provider=None)
        prompt = interviewer._build_prompt(
            module={"label": "IP定位"},
            subfield={"label": "核心概念", "question": "核心概念是什么？", "example": ""},
            session=make_session(),
        )
        assert "当前字段必须有 fill" not in prompt
        assert "否则当前字段必须有 fill" not in prompt

    def test_prompt_contains_judgment_allocation_wording(self):
        """Prompt must contain judgment-based allocation wording."""
        from app.domains.creation.a1.interviewer import RealLLMInterviewer

        interviewer = RealLLMInterviewer(provider=None)
        prompt = interviewer._build_prompt(
            module={"label": "IP定位"},
            subfield={"label": "核心概念", "question": "核心概念是什么？", "example": ""},
            session=make_session(),
        )
        assert "判断" in prompt
        assert "真正回答" in prompt
        assert "真正属于" in prompt

    def test_prompt_preserves_anti_underfill_for_current_field(self):
        """If input answers the current field (even if non-standard), it must
        be filled into the current module.subfield — anti-underfill guarantee.
        """
        from app.domains.creation.a1.interviewer import RealLLMInterviewer

        interviewer = RealLLMInterviewer(provider=None)
        prompt = interviewer._build_prompt(
            module={"label": "IP定位"},
            subfield={"label": "核心概念", "question": "核心概念是什么？", "example": ""},
            session=make_session(),
        )
        # Must have the anti-underfill rule for current field
        assert "对当前问题的回答" in prompt
        assert "绝不允许只填其他字段而漏掉当前字段" in prompt

    def test_prompt_rule_8_softened(self):
        """Rule 8 must only apply '直接记录并推进' when input genuinely
        answers the current question."""
        from app.domains.creation.a1.interviewer import RealLLMInterviewer

        interviewer = RealLLMInterviewer(provider=None)
        prompt = interviewer._build_prompt(
            module={"label": "IP定位"},
            subfield={"label": "核心概念", "question": "核心概念是什么？", "example": ""},
            session=make_session(),
        )
        # The old unqualified version should be gone
        assert "用户已给出相似回答，直接记录并推进" not in prompt
        # Rule 8 rewritten for single-source questions (问句单源铁律, 2026-09-02 fix):
        # reply must not introduce new questions; next question comes from
        # the structured question card only.
        assert "问句单源铁律" in prompt
        assert "严禁出现任何新的疑问句" in prompt


# =====================================================================
# _apply_fills extraction — handle_message fills-path still works
# =====================================================================


class TestApplyFillsExtraction:
    """After extracting _apply_fills helper, multi-field fills still work."""

    def test_handle_message_multi_field_fills_still_work(self):
        """Multi-field fills are applied correctly after _apply_fills refactor."""
        s = make_session()
        interviewer = FakeInterviewer(
            fills=[
                InterviewFill(module="IP定位", subfield="name", value="星陨大陆"),
                InterviewFill(module="IP定位", subfield="concept", value="因果轮回"),
                InterviewFill(module="IP定位", subfield="world_type", value="高魔东方奇幻"),
            ],
        )
        out = handle_message(s, "星陨大陆，因果轮回，高魔东方奇幻", interviewer)
        assert s.answers["IP定位.name"] == "星陨大陆"
        assert s.answers["IP定位.concept"] == "因果轮回"
        assert s.answers["IP定位.world_type"] == "高魔东方奇幻"
        assert len(out["file_diff"]) == 3

    def test_handle_message_first_write_wins_dedup(self):
        """Duplicate fills in same turn: first write wins."""
        s = make_session()
        interviewer = FakeInterviewer(
            fills=[
                InterviewFill(module="IP定位", subfield="name", value="第一"),
                InterviewFill(module="IP定位", subfield="name", value="第二"),
            ],
        )
        out = handle_message(s, "test", interviewer)
        assert s.answers["IP定位.name"] == "第一"
        assert len(out["file_diff"]) == 1

    def test_handle_message_overwrite_emits_diff(self):
        """G1 写入守卫：覆盖已填字段被拦截转提案，不再直接写入。"""
        s = make_session()
        s.answers["IP定位.name"] = "旧名字"
        interviewer = FakeInterviewer(
            fills=[InterviewFill(module="IP定位", subfield="name", value="新名字")],
        )
        out = handle_message(s, "改成新名字", interviewer)
        # 守卫拦截：旧值保留，不产生 diff，生成提案
        assert s.answers["IP定位.name"] == "旧名字"
        assert out["file_diff"] == []
        assert out.get("proposals") and len(out["proposals"]) == 1
        assert out["proposals"][0]["old"] == "旧名字"
        assert out["proposals"][0]["new"] == "新名字"
        assert out["next_question"] is None  # 单问句铁律

    def test_handle_message_same_value_no_diff(self):
        """Refilling same value emits no diff."""
        s = make_session()
        s.answers["IP定位.name"] = "星陨大陆"
        interviewer = FakeInterviewer(
            fills=[InterviewFill(module="IP定位", subfield="name", value="星陨大陆")],
        )
        out = handle_message(s, "还是星陨大陆", interviewer)
        assert out["file_diff"] == []
