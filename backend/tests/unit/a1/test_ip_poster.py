"""Tests for the A1 IP poster builder."""
from app.domains.creation.a1.guide_engine import A1Session
from app.domains.creation.a1.ip_poster import build_poster


class TestIPPoster:
    def test_empty_session_yields_pending_status(self):
        s = A1Session(session_id="s", user_id="u")
        out = build_poster(s)
        assert out["panels"] == []
        assert out["ai_image_status"] == "pending"
        assert out["ai_image_prompt"]

    def test_panels_only_for_non_empty_modules(self):
        s = A1Session(session_id="s", user_id="u")
        s.answers["IP定位.name"] = "灵气枯竭的修真界"
        s.answers["IP定位.world_type"] = ""
        out = build_poster(s)
        assert len(out["panels"]) == 1
        assert out["panels"][0]["title"] == "IP定位"

    def test_prompt_stitches_module_values(self):
        s = A1Session(session_id="s", user_id="u")
        s.answers["IP定位.name"] = "废土"
        s.answers["视觉设计.keywords"] = "荒凉"
        out = build_poster(s)
        assert "废土" in out["ai_image_prompt"]
        assert "荒凉" in out["ai_image_prompt"]

    def test_panel_uses_module_label(self):
        s = A1Session(session_id="s", user_id="u")
        s.answers["AI生成边界.immutable_core"] = "不可修改IP定位"
        out = build_poster(s)
        assert out["panels"][0]["title"] == "AI生成边界"
