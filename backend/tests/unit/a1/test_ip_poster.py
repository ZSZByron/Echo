"""Tests for the A1 IP poster builder."""
from app.domains.creation.a1.guide_engine import A1Session
from app.domains.creation.a1.ip_poster import build_poster


class TestIPPoster:
    def test_empty_session_yields_pending_status_and_blank_prompt(self):
        s = A1Session(session_id="s", user_id="u")
        out = build_poster(s)
        assert out["panels"] == []
        assert out["ai_image_status"] == "pending"
        assert out["ai_image_prompt"]

    def test_panels_only_for_non_empty_sections(self):
        s = A1Session(session_id="s", user_id="u")
        s.answers["世界观"] = "灵气枯竭的修真界"
        s.answers["地理"] = ""  # skipped, excluded
        out = build_poster(s)
        assert len(out["panels"]) == 1
        assert out["panels"][0]["section"] == "世界观"

    def test_prompt_stitches_section_values(self):
        s = A1Session(session_id="s", user_id="u")
        s.answers["世界观"] = "废土"
        s.answers["叙事基调"] = "荒凉"
        out = build_poster(s)
        assert "废土" in out["ai_image_prompt"]
        assert "荒凉" in out["ai_image_prompt"]

    def test_panel_uses_section_label(self):
        s = A1Session(session_id="s", user_id="u")
        s.answers["核心冲突"] = "诸神与人类之争"
        out = build_poster(s)
        assert out["panels"][0]["section"] == "核心冲突"
