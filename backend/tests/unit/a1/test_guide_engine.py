"""Tests for the A1 guide engine (sequential state machine + compiler)."""
from app.domains.creation.a1.guide_engine import (
    A1Session,
    PHASE_ASKING,
    PHASE_COMPLETED,
    handle_message,
    progress,
)
from app.domains.creation.shared.semantic_compiler import (
    ClassificationProposal,
    CompileResult,
    FieldWrite,
    Suggestion,
)


class FakeCompiler:
    """Deterministic compiler: hits -> writes, misses -> proposal."""

    def __init__(self, hit: bool = True):
        self.hit = hit
        self.calls = 0

    def compile(self, session_id: str, text: str) -> CompileResult:
        self.calls += 1
        if self.hit:
            return CompileResult(writes=[FieldWrite(field="world_structure", value="FLOATING_ISLANDS")])
        return CompileResult(
            classification_proposal=ClassificationProposal(
                suggestions=[Suggestion(field=text[:8], category="其他")]
            )
        )


def make_session() -> A1Session:
    return A1Session(session_id="s1", user_id="u1", ip_code="IP0001")


class TestGuideEngine:
    def test_regular_write_persists_and_advances(self):
        s = make_session()
        out = handle_message(s, "浮空岛世界", FakeCompiler(hit=True))
        assert s.answers["世界观"] == "world_structure=FLOATING_ISLANDS"
        assert out["file_diff"]
        assert s.current_section == "地理"
        assert s.phase == PHASE_ASKING

    def test_innovative_statement_pends_proposal(self):
        s = make_session()
        out = handle_message(s, "一种全新的设定xyz", FakeCompiler(hit=False))
        assert "classification_proposal" in out
        assert s.current_section == "世界观"  # did not advance
        assert s.answers == {}

    def test_skip_advances_without_value(self):
        s = make_session()
        out = handle_message(s, "跳过", FakeCompiler(hit=False))
        assert s.current_section == "地理"
        assert s.answers["世界观"] == ""
        assert out["progress"]["done"] == 1

    def test_progress_counts_completed_sections(self):
        s = make_session()
        handle_message(s, "浮空岛世界", FakeCompiler(hit=True))
        p = progress(s)
        assert p["total"] == 10 and p["done"] == 1

    def test_all_sections_completed_enters_completed_phase(self):
        s = make_session()
        for _ in range(10):
            handle_message(s, "正常设定", FakeCompiler(hit=True))
        assert s.phase == PHASE_COMPLETED
        out = handle_message(s, "再说一句", FakeCompiler(hit=True))
        assert out["next_question"] is None
        assert "已完成" in out["reply"]
