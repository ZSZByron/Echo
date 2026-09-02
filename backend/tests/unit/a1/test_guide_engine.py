"""Tests for the A1 guide engine (LLM-interviewer state machine)."""
from app.domains.creation.a1.guide_engine import (
    PHASE_ASKING,
    PHASE_COMPLETED,
    A1Session,
    handle_message,
    progress,
)
from app.domains.creation.a1.interviewer import (
    FakeInterviewer,
    InterviewFill,
)
from app.domains.creation.seed.a1_question_tree import (
    all_subfield_keys,
)


def name_filler() -> FakeInterviewer:
    """Interviewer that understands a world name -> IP定位.name."""
    return FakeInterviewer(
        fills=[InterviewFill(module="IP定位", subfield="name", value="星陨大陆")],
        guidance_reply="好名字！「星陨大陆」已记录。",
    )


def make_session() -> A1Session:
    return A1Session(session_id="s1", user_id="u1", ip_code="IP0001")


class TestGuideEngine:
    def test_llm_fill_persists_and_advances(self):
        s = make_session()
        out = handle_message(s, "星陨大陆", name_filler())
        assert s.answers["IP定位.name"] == "星陨大陆"
        assert out["reply"] == "好名字！「星陨大陆」已记录。"
        assert out["file_diff"]
        assert s.phase == PHASE_ASKING
        # position jumps to the first unanswered subfield
        assert s.current_module == "IP定位"
        assert s.current_subfield == "concept"

    def test_multi_field_fills_jump_to_first_unanswered(self):
        s = make_session()
        interviewer = FakeInterviewer(
            fills=[
                InterviewFill(module="IP定位", subfield="name", value="星陨大陆"),
                InterviewFill(module="IP定位", subfield="concept", value="星坠之地的因果轮回"),
                InterviewFill(module="IP定位", subfield="world_type", value="高魔东方奇幻"),
            ],
        )
        handle_message(s, "名字叫星陨大陆，讲星坠因果，高魔东方奇幻", interviewer)
        assert "IP定位.name" in s.answers
        assert "IP定位.concept" in s.answers
        assert "IP定位.world_type" in s.answers
        # Gate-aware scheduling (2026-09-02: 有缺失，在窗口询问): IP定位 is
        # now over half (3/4), so the interviewer jumps to the NEXT
        # gate-failing module (世界本体.origin) instead of finishing
        # IP定位's remaining core_experience field.
        assert s.current_module == "世界本体"
        assert s.current_subfield == "origin"

    def test_genuine_innovation_pends_proposal(self):
        s = make_session()
        out = handle_message(
            s,
            "我想要一个梦境经济学体系",
            FakeInterviewer(is_innovative=True, innovative_category="梦境经济"),
        )
        assert "classification_proposal" in out
        assert out["classification_proposal"]["suggestions"][0]["category"] == "梦境经济"
        assert s.current_subfield == "name"  # unchanged
        assert s.answers == {}

    def test_chat_off_topic_replies_without_persisting(self):
        s = make_session()
        out = handle_message(
            s, "你好呀", FakeInterviewer(guidance_reply="你好！我们继续——")
        )
        assert "classification_proposal" not in out
        assert s.answers == {}
        assert s.current_subfield == "name"
        assert out["reply"] == "你好！我们继续——"
        assert out["next_question"] is not None

    def test_llm_failure_never_records_without_judgment(self):
        """LLM down must ask the user to retry — never blind-store text
        (blind-recording fix, 2026-08-26)."""
        s = make_session()
        from app.domains.creation.a1.interviewer import DegradingInterviewer

        out = handle_message(
            s,
            "星陨大陆",
            DegradingInterviewer(FakeInterviewer(raise_error=True)),
        )
        assert s.answers == {}
        assert s.current_subfield == "name"  # position unchanged
        assert out["file_diff"] == []
        assert "不可用" in out["reply"]
        assert "classification_proposal" not in out

    def test_skip_advances_without_value(self):
        s = make_session()
        out = handle_message(s, "跳过", FakeInterviewer())
        assert s.current_module == "IP定位"
        assert s.current_subfield == "concept"
        assert s.answers["IP定位.name"] == ""
        assert out["progress"]["done"] == 0

    def test_progress_has_sections_with_subs(self):
        s = make_session()
        handle_message(s, "星陨大陆", name_filler())
        p = progress(s)
        assert p["total"] == 10
        assert len(p["sections"]) == 10
        first_sec = p["sections"][0]
        assert "subs" in first_sec
        assert len(first_sec["subs"]) == 4  # IP定位 has 4 fields
        assert first_sec["done"] is False  # only 1 of 4 fields answered

    def test_all_subs_completed_enters_completed_phase(self):
        s = make_session()
        for key in all_subfield_keys():
            module_id, sub_id = key.split(".", 1)
            handle_message(
                s,
                "正常设定",
                FakeInterviewer(
                    fills=[InterviewFill(module=module_id, subfield=sub_id, value="正常设定")]
                ),
            )
        assert s.phase == PHASE_COMPLETED
        out = handle_message(s, "再说一句", FakeInterviewer())
        assert out["next_question"] is None

    def test_question_payload_has_sub_fields(self):
        s = make_session()
        out = handle_message(s, "跳过", FakeInterviewer())
        nq = out["next_question"]
        assert nq is not None
        assert "sub_id" in nq
        assert "sub_label" in nq
        assert "section_label" in nq
        assert nq["section"] == "IP定位"

    def test_file_diff_has_module_and_section(self):
        s = make_session()
        out = handle_message(s, "星陨大陆", name_filler())
        diff = out["file_diff"][0]
        assert "module" in diff
        assert "section" in diff
        assert diff["module"] == "IP定位"

    # ---- finalize gate (>50% per module) ----

    def test_progress_finalizable_false_initially(self):
        s = make_session()
        assert progress(s)["finalizable"] is False

    def test_progress_finalizable_true_when_all_modules_over_half(self):
        from app.domains.creation.seed.a1_question_tree import MODULES
        s = make_session()
        for m in MODULES:
            need = len(m["fields"]) // 2 + 1
            for f in m["fields"][:need]:
                s.answers[f"{m['id']}.{f['id']}"] = "x"
        assert progress(s)["finalizable"] is True

    # ---- completed phase stays open for refinement ----

    def test_completed_phase_allows_refinement(self):
        s = make_session()
        for key in all_subfield_keys():
            module_id, sub_id = key.split(".", 1)
            handle_message(
                s,
                "正常设定",
                FakeInterviewer(
                    fills=[InterviewFill(module=module_id, subfield=sub_id, value="正常设定")]
                ),
            )
        assert s.phase == PHASE_COMPLETED
        # Write guard (Task 4): overwrites in completed phase are intercepted
        # as proposals — the user confirms before the value changes.
        out = handle_message(
            s,
            "名字改成星穹大陆",
            FakeInterviewer(
                fills=[InterviewFill(module="IP定位", subfield="name", value="星穹大陆")],
                guidance_reply="已更新名字。",
            ),
        )
        # Guard intercepts: old value preserved, proposal generated
        assert s.answers["IP定位.name"] == "正常设定"
        assert "proposals" in out
        assert len(out["proposals"]) == 1
        assert out["proposals"][0]["old"] == "正常设定"
        assert out["proposals"][0]["new"] == "星穹大陆"
        # Reply is confirmation question, not direct write
        assert "正常设定" in out["reply"]
        assert "星穹大陆" in out["reply"]
        assert s.phase == PHASE_COMPLETED

    def test_completed_phase_refinement_via_proposal(self):
        """After resolving a proposal in completed phase, value updates."""
        from app.domains.creation.a1.guide_engine import resolve_proposal

        s = make_session()
        for key in all_subfield_keys():
            module_id, sub_id = key.split(".", 1)
            s.answers[key] = "正常设定"
        s.phase = PHASE_COMPLETED

        # Simulate guard interception via handle_message
        out = handle_message(
            s,
            "名字改成星穹大陆",
            FakeInterviewer(
                fills=[InterviewFill(module="IP定位", subfield="name", value="星穹大陆")],
            ),
        )
        assert len(s.pending_proposals) == 1
        key = list(s.pending_proposals.keys())[0]

        # Resolve: replace
        r = resolve_proposal(s, key, "replace")
        assert r["applied"] is True
        assert s.answers["IP定位.name"] == "星穹大陆"
        assert s.phase == PHASE_COMPLETED

    def test_same_value_refill_emits_no_diff(self):
        s = make_session()
        handle_message(s, "星陨大陆", name_filler())
        out = handle_message(s, "星陨大陆", name_filler())
        assert out["file_diff"] == []
        assert s.answers["IP定位.name"] == "星陨大陆"

    def test_duplicate_fill_same_turn_first_wins(self):
        s = make_session()
        out = handle_message(
            s,
            "星陨大陆",
            FakeInterviewer(
                fills=[
                    InterviewFill(module="IP定位", subfield="name", value="第一"),
                    InterviewFill(module="IP定位", subfield="name", value="第二"),
                ],
            ),
        )
        assert s.answers["IP定位.name"] == "第一"
        assert len(out["file_diff"]) == 1

    # ---- anti-stall guard ----

    def test_stall_suggests_examples_then_number_pick(self):
        """Stall 2 -> seed-referenced suggestions; number reply picks one."""
        s = make_session()
        # Advance past name to concept
        s.answers["IP定位.name"] = "x"
        s.current_subfield = "concept"
        assert s.current_module == "IP定位"

        misroute = FakeInterviewer(
            fills=[InterviewFill(module="IP定位", subfield="core_experience", value="决斗体验")],
            guidance_reply="已记录核心体验。",
        )
        user_text = "刹那生死，剑客决斗，先手必赢！"

        # Turn 1: misroute -> concept NOT filled, stall_count=1
        handle_message(s, user_text, misroute)
        assert "IP定位.concept" not in s.answers
        assert s.current_subfield == "concept"  # still on concept
        assert s.stall_count == 1
        assert s.pending_suggestions == []

        # Turn 2: same misroute -> suggestion mode (LLM-understanding first)
        out2 = handle_message(s, user_text, misroute)
        assert "IP定位.concept" not in s.answers  # NOT raw-filled yet
        assert s.current_subfield == "concept"  # position unchanged
        assert "示例" in out2["reply"]
        assert "序号" in out2["reply"]
        assert len(s.pending_suggestions) == 3
        assert s.stall_count == 2  # stays at 2 so next stall escalates

        # Turn 3: user replies "2" -> pick second example, advance
        out3 = handle_message(s, "2", misroute)
        assert s.answers["IP定位.concept"] == "示例二"  # second canned example
        assert "已按示例记录" in out3["reply"]
        assert s.current_subfield != "concept"  # advanced past concept
        assert s.pending_suggestions == []
        assert s.stall_count == 0
        diff_fields = [d["field"] for d in out3["file_diff"]]
        assert "核心概念" in diff_fields

    def test_stall_third_turn_never_raw_fills(self):
        """Stall 3 goes through LLM forced_allocate — never raw-text fill
        (blind-recording fix, 2026-08-26)."""
        s = make_session()
        s.answers["IP定位.name"] = "x"
        s.current_subfield = "concept"

        misroute = FakeInterviewer(
            fills=[InterviewFill(module="IP定位", subfield="core_experience", value="决斗")],
            guidance_reply="已记录。",
        )
        user_text = "先手必赢的世界"

        handle_message(s, user_text, misroute)  # stall 1
        handle_message(s, user_text, misroute)  # stall 2 -> suggestions
        assert "IP定位.concept" not in s.answers

        out3 = handle_message(s, user_text, misroute)  # stall 3 -> forced_allocate
        assert "IP定位.concept" not in s.answers  # LLM judged: no valid fill
        assert "已按原文直接记录" not in out3["reply"]
        assert "跳过" in out3["reply"] or "换" in out3["reply"]
        assert s.stall_count <= 3  # capped, not reset (field still unfilled)

    def test_stall_suggest_unavailable_asks_rephrase(self):
        """When suggest_examples returns [] (LLM offline), stall 2 asks the
        user to rephrase / 跳过 — never raw-fills."""
        s = make_session()
        s.answers["IP定位.name"] = "x"
        s.current_subfield = "concept"

        misroute = FakeInterviewer(
            fills=[InterviewFill(module="IP定位", subfield="core_experience", value="决斗")],
            guidance_reply="已记录。",
            examples=[],
        )
        user_text = "高魔科技世界"

        handle_message(s, user_text, misroute)  # stall 1
        out2 = handle_message(s, user_text, misroute)  # suggestions empty -> ask rephrase
        assert "IP定位.concept" not in s.answers
        assert "已按原文直接记录" not in out2["reply"]
        assert "跳过" in out2["reply"] or "换" in out2["reply"]
        assert s.current_subfield == "concept"  # position unchanged

    def test_number_without_pending_suggestions_passthrough(self):
        """A bare number with no pending suggestions goes to the interviewer."""
        s = make_session()
        s.answers["IP定位.name"] = "x"
        s.current_subfield = "concept"
        assert s.pending_suggestions == []

        filler = FakeInterviewer(
            fills=[InterviewFill(module="IP定位", subfield="concept", value="正常回答")],
            guidance_reply="已记录。",
        )
        out = handle_message(s, "1", filler)  # no pending -> normal interview
        assert s.answers["IP定位.concept"] == "正常回答"
        assert "已按示例记录" not in out["reply"]

    def test_question_marks_do_not_stall(self):
        """Texts ending with ？ must not increment stall counter."""
        s = make_session()
        s.answers["IP定位.name"] = "x"
        s.current_subfield = "concept"

        chatty = FakeInterviewer(
            fills=[],
            guidance_reply="请继续。",
        )

        handle_message(s, "核心概念是什么意思？", chatty)
        handle_message(s, "能举个例子吗？", chatty)

        assert "IP定位.concept" not in s.answers
        assert s.stall_count == 0

    def test_stall_resets_on_success(self):
        """A successful fill resets stall tracking; next misroute starts fresh."""
        s = make_session()
        s.answers["IP定位.name"] = "x"
        s.current_subfield = "concept"

        misroute = FakeInterviewer(
            fills=[InterviewFill(module="IP定位", subfield="core_experience", value="决斗")],
            guidance_reply="已记录。",
        )
        correct = FakeInterviewer(
            fills=[InterviewFill(module="IP定位", subfield="concept", value="因果轮回")],
            guidance_reply="已记录。",
        )

        # Turn 1: misroute -> stall_count=1
        handle_message(s, "核心是轮回", misroute)
        assert s.stall_count == 1

        # Turn 2: correct fill -> resets stall tracking
        handle_message(s, "因果轮回，剑道不息", correct)
        assert s.answers["IP定位.concept"] == "因果轮回"  # LLM value, not raw text
        assert s.stall_count == 0
        assert s.stall_subfield == ""

        # Turn 3: misroute on NEXT field (world_type) starts fresh count
        misroute2 = FakeInterviewer(
            fills=[InterviewFill(module="IP定位", subfield="core_experience", value="体验")],
            guidance_reply="已记录。",
        )
        handle_message(s, "高魔奇幻世界", misroute2)
        assert "IP定位.world_type" not in s.answers
        assert s.stall_count == 1  # fresh count, NOT 2 -> no force fill

    def test_prompt_contains_current_field_rule(self):
        """RealLLMInterviewer prompt must include the current-field-priority rule."""
        from app.domains.creation.a1.interviewer import RealLLMInterviewer

        interviewer = RealLLMInterviewer(provider=None)
        prompt = interviewer._build_prompt(
            module={"label": "IP定位"},
            subfield={"label": "核心概念", "question": "核心概念是什么？", "example": ""},
            session=make_session(),
        )
        assert "当前字段优先" in prompt


# ---- Task 4 append: divergent fallback (Metis AC-M8) ----


class TestDivergentFallback:
    """Scenario 10: InterviewResult.divergent_question is None and
    fills are non-empty → code-level template generates one divergent
    question from fill keywords × unfilled fields."""

    def test_fallback_divergent_generates_question_from_fills(self):
        """When LLM returns no divergent_question but fills exist,
        _fallback_divergent generates a template question."""
        from app.domains.creation.a1.interviewer import InterviewResult
        from app.domains.creation.a1.guide_engine import _fallback_divergent, handle_message

        s = make_session()
        fills = [
            InterviewFill(module="IP定位", subfield="name", value="灵韵海化生万物")
        ]
        # InterviewResult with fills but no divergent_question
        result = InterviewResult(
            fills=fills,
            guidance_reply="已记录。",
        )

        dq = _fallback_divergent(s, fills)
        # Should generate a question mentioning the fill keyword and an unfilled field
        assert dq is not None
        assert "灵韵海化生万物" in dq or "灵韵海化生" in dq
        # Should mention some unfilled field name
        unfilled_found = any(
            field_label in dq
            for field_label in ["核心概念", "世界类型", "核心体验", "力量体系", "文明"]
        )
        assert unfilled_found, f"No unfilled field label found in: {dq}"

    def test_fallback_divergent_none_when_no_fills(self):
        """With empty fills, _fallback_divergent returns None."""
        from app.domains.creation.a1.guide_engine import _fallback_divergent

        s = make_session()
        dq = _fallback_divergent(s, [])
        assert dq is None

    def test_fallback_divergent_none_when_all_filled(self):
        """When all fields are filled, _fallback_divergent returns None."""
        from app.domains.creation.a1.guide_engine import _fallback_divergent

        s = make_session()
        # Fill all fields
        for key in all_subfield_keys():
            s.answers[key] = "x"

        fills = [InterviewFill(module="IP定位", subfield="name", value="灵韵海")]
        dq = _fallback_divergent(s, fills)
        assert dq is None

    def test_handle_message_injects_fallback_divergent(self):
        """handle_message injects fallback divergent when LLM returns none."""
        from app.domains.creation.a1.interviewer import InterviewResult
        from app.domains.creation.a1.guide_engine import handle_message

        s = make_session()
        # FakeInterviewer always returns divergent_question=None
        # but with fills it should trigger the fallback
        out = handle_message(s, "灵韵海化生万物", name_filler())
        assert "divergent_question" in out
        # The fallback should reference the fill keyword
        if out["divergent_question"] is not None:
            assert "星陨大陆" in out["divergent_question"] or "灵韵" in out["divergent_question"]
