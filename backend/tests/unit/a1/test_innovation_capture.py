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
        suggestions=[Suggestion(field="\u91cf\u5b50\u7075\u6c14", category="\u5176\u4ed6")]
    )


class TestInnovationCapture:
    def test_other_choice_stores_only_inconsistent_content(self):
        s = A1Session(session_id="s", user_id="u")
        out = confirm_proposal(s, Confirmation(proposal=pending(), choice=CHOICE_OTHER))
        assert out["persisted"] is True
        first_key = list(s.answers.keys())[0]
        assert s.answers[first_key].startswith("[\u5176\u4ed6]")
        assert "\u91cf\u5b50\u7075\u6c14" in s.answers[first_key]

    def test_discard_persists_nothing(self):
        s = A1Session(session_id="s", user_id="u")
        out = confirm_proposal(s, Confirmation(proposal=pending(), choice=CHOICE_DISCARD))
        assert out["persisted"] is False
        assert s.answers == {}

    def test_suggested_category_stored(self):
        s = A1Session(session_id="s", user_id="u")
        out = confirm_proposal(s, Confirmation(proposal=pending(), choice="\u529b\u91cf\u4f53\u7cfb\u7c7b"))
        assert out["persisted"] is True
        first_key = list(s.answers.keys())[0]
        assert s.answers[first_key] == "\u529b\u91cf\u4f53\u7cfb\u7c7b"

    def test_file_diff_has_module_and_section(self):
        s = A1Session(session_id="s", user_id="u")
        out = confirm_proposal(s, Confirmation(proposal=pending(), choice="\u67d0\u7c7b\u522b"))
        assert out["file_diff"]
        diff = out["file_diff"][0]
        assert "module" in diff
        assert "section" in diff
