"""Tests for the A1 guide engine (LLM-interviewer state machine)."""
from app.domains.creation.a1.guide_engine import (
    A1Session,
    PHASE_ASKING,
    PHASE_COMPLETED,
    handle_message,
    progress,
)
from app.domains.creation.a1.interviewer import (
    FakeInterviewer,
    InterviewFill,
)
from app.domains.creation.seed.a1_question_tree import (
    total_subfield_count,
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
        # first unanswered is now core_experience
        assert s.current_subfield == "core_experience"

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

    def test_llm_failure_degrades_to_direct_store(self):
        """A name is just a name — LLM down must never block intake."""
        s = make_session()
        from app.domains.creation.a1.interviewer import DegradingInterviewer

        out = handle_message(
            s,
            "星陨大陆",
            DegradingInterviewer(FakeInterviewer(raise_error=True)),
        )
        assert s.answers["IP定位.name"] == "星陨大陆"
        assert s.current_subfield == "concept"
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
