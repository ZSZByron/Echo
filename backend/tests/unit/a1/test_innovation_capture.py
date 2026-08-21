"""Tests for A1 innovation capture (proposal confirmation flow)."""
from app.domains.creation.a1.guide_engine import A1Session
from app.domains.creation.a1.innovation_capture import (
    CHOICE_DISCARD,
    CHOICE_OTHER,
    Confirmation,
    confirm_proposal,
)
from app.domains.creation.shared.semantic_compiler import (
    ClassificationProposal,
    Suggestion,
)


def pending() -> ClassificationProposal:
    return ClassificationProposal(
        suggestions=[Suggestion(field="量子灵气", category="其他")]
    )


class TestInnovationCapture:
    def test_other_choice_stores_only_inconsistent_content(self):
        s = A1Session(session_id="s", user_id="u")
        out = confirm_proposal(s, Confirmation(proposal=pending(), choice=CHOICE_OTHER))
        assert out["persisted"] is True
        assert s.answers["世界观"].startswith("[其他]")
        assert "量子灵气" in s.answers["世界观"]
        assert s.current_section == "地理"  # advanced

    def test_discard_persists_nothing(self):
        s = A1Session(session_id="s", user_id="u")
        out = confirm_proposal(s, Confirmation(proposal=pending(), choice=CHOICE_DISCARD))
        assert out["persisted"] is False
        assert s.answers == {}
        assert s.current_section == "世界观"  # unchanged

    def test_suggested_category_stored(self):
        s = A1Session(session_id="s", user_id="u")
        out = confirm_proposal(s, Confirmation(proposal=pending(), choice="力量体系类"))
        assert out["persisted"] is True
        assert s.answers["世界观"] == "力量体系类"

    def test_file_diff_returned_on_persist(self):
        s = A1Session(session_id="s", user_id="u")
        out = confirm_proposal(s, Confirmation(proposal=pending(), choice="某类别"))
        assert out["file_diff"] and out["file_diff"][0]["section"] == "世界观"
