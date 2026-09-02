"""Prefill guard exemption tests (upload-deadlock fix).

Prefill values are LLM *guesses* made at upload time — the user never
confirmed them. The write guard protects *user-confirmed* content, so
user-spoken fills must directly overwrite prefill guesses (recorded in
file_diff), after which the field returns to normal guard protection.
"""
import pytest

from app.domains.creation.a1.guide_engine import (
    A1Session,
    _apply_fills,
)
from app.domains.creation.a1.interviewer import (
    InterviewFill,
)


class TestPrefillExemption:
    """Prefill-sourced values are guesses; user fills overwrite directly."""

    def test_prefill_conflict_writes_directly(self):
        s = A1Session(session_id="s1", user_id="u1", ip_code="IP0001")
        s.answers["IP定位.name"] = "星陨大陆"  # prefill guess
        s.prefill_fields.append("IP定位.name")
        fills = [InterviewFill(module="IP定位", subfield="name", value="星穹大陆")]

        file_diff, proposals = _apply_fills(s, fills)

        # Direct overwrite of the guess
        assert s.answers["IP定位.name"] == "星穹大陆"
        assert proposals == []
        # file_diff records old→new so user sees the overwrite
        assert len(file_diff) == 1
        assert file_diff[0]["old"] == "星陨大陆"
        assert file_diff[0]["new"] == "星穹大陆"

    def test_prefill_key_removed_after_write(self):
        s = A1Session(session_id="s1", user_id="u1", ip_code="IP0001")
        s.answers["IP定位.name"] = "星陨大陆"
        s.prefill_fields.append("IP定位.name")
        _apply_fills(s, [InterviewFill(module="IP定位", subfield="name", value="星穹大陆")])

        assert "IP定位.name" not in s.prefill_fields

        # Second conflict → back to normal guard (proposal, no write)
        file_diff, proposals = _apply_fills(
            s, [InterviewFill(module="IP定位", subfield="name", value="星辰大陆")]
        )
        assert s.answers["IP定位.name"] == "星穹大陆"
        assert len(proposals) == 1
        assert file_diff == []

    def test_user_filled_field_still_intercepted(self):
        s = A1Session(session_id="s1", user_id="u1", ip_code="IP0001")
        s.answers["IP定位.name"] = "星陨大陆"  # user confirmed (no prefill mark)
        fills = [InterviewFill(module="IP定位", subfield="name", value="星穹大陆")]

        file_diff, proposals = _apply_fills(s, fills)

        assert s.answers["IP定位.name"] == "星陨大陆"
        assert len(proposals) == 1
        assert file_diff == []


class TestBackwardCompat:
    """Old sessions serialized without prefill_fields must deserialize."""

    def test_default_empty_prefill_fields(self):
        s = A1Session(session_id="s1", user_id="u1", ip_code="IP0001")
        assert s.prefill_fields == []

    def test_conflict_without_prefill_attribute_uses_guard(self):
        # Simulates a session object built by old code paths
        s = A1Session(session_id="s1", user_id="u1", ip_code="IP0001")
        s.answers["IP定位.name"] = "星陨大陆"
        assert not hasattr(s, "nonexistent")  # sanity
        file_diff, proposals = _apply_fills(
            s, [InterviewFill(module="IP定位", subfield="name", value="星穹大陆")]
        )
        assert len(proposals) == 1
        assert file_diff == []
