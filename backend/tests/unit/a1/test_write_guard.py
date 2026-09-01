"""Write guard tests — _apply_fills 三分支 + resolve_proposal + stall path.

TDD RED phase: these tests define the contract for Task 4.
All should FAIL until the guard is implemented in guide_engine.py.
"""
import hashlib

import pytest

from app.domains.creation.a1.guide_engine import (
    A1Session,
    _apply_fills,
    resolve_proposal,
    _fallback_divergent,
)
from app.domains.creation.a1.interviewer import (
    FakeInterviewer,
    InterviewFill,
    InterviewResult,
    Proposal,
)
from app.domains.creation.seed.a1_question_tree import (
    all_subfield_keys,
    get_subfield,
)


def make_session() -> A1Session:
    """Create a fresh session for each test."""
    return A1Session(session_id="s1", user_id="u1", ip_code="IP0001")


def _proposal_key(module: str, subfield: str, new: str) -> str:
    """Replicate the proposal key formula for assertions."""
    h = hashlib.md5(new.encode()).hexdigest()[:8]
    return f"{module}.{subfield}:{h}"


class TestApplyFillsEmptyPath:
    """Scenario 1: Empty field → direct write + file_diff(old='')."""

    def test_empty_field_writes_directly(self):
        s = make_session()
        fills = [InterviewFill(module="IP定位", subfield="name", value="星陨大陆")]
        file_diff, proposals = _apply_fills(s, fills)

        assert s.answers["IP定位.name"] == "星陨大陆"
        assert len(file_diff) == 1
        assert file_diff[0]["old"] == ""
        assert file_diff[0]["new"] == "星陨大陆"
        assert proposals == []

    def test_multiple_empty_fields_all_write(self):
        s = make_session()
        fills = [
            InterviewFill(module="IP定位", subfield="name", value="星陨大陆"),
            InterviewFill(module="IP定位", subfield="concept", value="因果轮回"),
        ]
        file_diff, proposals = _apply_fills(s, fills)

        assert s.answers["IP定位.name"] == "星陨大陆"
        assert s.answers["IP定位.concept"] == "因果轮回"
        assert len(file_diff) == 2
        assert all(d["old"] == "" for d in file_diff)
        assert proposals == []


class TestApplyFillsSkipPath:
    """Scenario 2: Non-empty and new == old → skip (no proposal, no write)."""

    def test_same_value_skips(self):
        s = make_session()
        s.answers["IP定位.name"] = "星陨大陆"
        fills = [InterviewFill(module="IP定位", subfield="name", value="星陨大陆")]

        file_diff, proposals = _apply_fills(s, fills)

        assert s.answers["IP定位.name"] == "星陨大陆"
        assert file_diff == []
        assert proposals == []


class TestApplyFillsInterceptPath:
    """Scenario 3 (G1 core): Non-empty and new != old → intercept,
    generate Proposal, answers keeps old value."""

    def test_conflict_generates_proposal_no_write(self):
        s = make_session()
        s.answers["IP定位.name"] = "星陨大陆"
        new_value = "星穹大陆"
        fills = [
            InterviewFill(module="IP定位", subfield="name", value=new_value,
                           conflict_note="与前设定矛盾")
        ]

        file_diff, proposals = _apply_fills(s, fills)

        # answers must NOT be updated
        assert s.answers["IP定位.name"] == "星陨大陆"
        # file_diff should be empty (nothing was written)
        assert file_diff == []
        # exactly one proposal
        assert len(proposals) == 1
        p = proposals[0]
        assert p.module == "IP定位"
        assert p.subfield == "name"
        assert p.old == "星陨大陆"
        assert p.new == new_value
        assert p.conflict_note == "与前设定矛盾"
        assert p.merge_preview == "星陨大陆；星穹大陆"

    def test_intercept_stores_in_pending_proposals(self):
        s = make_session()
        s.answers["IP定位.name"] = "星陨大陆"
        fills = [
            InterviewFill(module="IP定位", subfield="name", value="星穹大陆")
        ]

        _, proposals = _apply_fills(s, fills)

        # pending_proposals must be populated on the session
        assert len(s.pending_proposals) == 1
        key = _proposal_key("IP定位", "name", "星穹大陆")
        assert key in s.pending_proposals
        stored = s.pending_proposals[key]
        assert stored["proposal"].module == "IP定位"
        assert stored["proposal"].new == "星穹大陆"
        assert "options" in stored


class TestResolveProposalThreeChoices:
    """Scenario 4: resolve_proposal(key, choice) — replace / merge / drop."""

    def _setup_conflict(self) -> tuple[A1Session, str]:
        s = make_session()
        s.answers["IP定位.name"] = "星陨大陆"
        fills = [
            InterviewFill(module="IP定位", subfield="name", value="星穹大陆")
        ]
        _apply_fills(s, fills)
        key = _proposal_key("IP定位", "name", "星穹大陆")
        return s, key

    def test_replace_writes_new_value(self):
        s, key = self._setup_conflict()
        result = resolve_proposal(s, key, "replace")

        assert s.answers["IP定位.name"] == "星穹大陆"
        assert key not in s.pending_proposals
        assert result["applied"] is True
        assert result["choice"] == "replace"

    def test_merge_appends_with_fullwidth_semicolon(self):
        s, key = self._setup_conflict()
        result = resolve_proposal(s, key, "merge")

        assert s.answers["IP定位.name"] == "星陨大陆；星穹大陆"
        assert key not in s.pending_proposals
        assert result["applied"] is True
        assert result["choice"] == "merge"

    def test_drop_keeps_old_value(self):
        s, key = self._setup_conflict()
        result = resolve_proposal(s, key, "drop")

        assert s.answers["IP定位.name"] == "星陨大陆"
        assert key not in s.pending_proposals
        assert result["applied"] is False
        assert result["choice"] == "drop"


class TestMergeCap:
    """Scenario 5 (Metis E4): After 3 consecutive merges on the same field,
    the 4th intercepted proposal's merge option is unavailable."""

    def test_merge_cap_removes_merge_option(self):
        s = make_session()
        s.answers["IP定位.name"] = "星陨大陆"

        # Perform 3 merges
        for i, val in enumerate(["星穹大陆", "苍穹大陆", "天穹大陆"], 1):
            fills = [InterviewFill(module="IP定位", subfield="name", value=val)]
            _apply_fills(s, fills)
            key = _proposal_key("IP定位", "name", val)
            resolve_proposal(s, key, "merge")

        # After 3 merges, the field value should be all merged
        assert "星陨大陆；星穹大陆；苍穹大陆；天穹大陆" == s.answers["IP定位.name"]

        # 4th conflict
        fills = [InterviewFill(module="IP定位", subfield="name", value="新大陆")]
        _, proposals = _apply_fills(s, fills)
        key = _proposal_key("IP定位", "name", "新大陆")

        assert len(s.pending_proposals) == 1
        assert "options" in s.pending_proposals[key]
        options = s.pending_proposals[key]["options"]
        # merge should NOT be in options (cap reached)
        assert "merge" not in options
        assert "replace" in options
        assert "drop" in options


class TestStallPathCoverage:
    """Scenario 6 (Metis AC-M4): stall_count=3 forced_allocate fills
    hitting an already-filled field → proposal, not silent overwrite."""

    def test_stall_forced_allocate_hits_filled_field_generates_proposal(self):
        s = make_session()
        # Fill name field
        s.answers["IP定位.name"] = "星陨大陆"
        s.current_module = "IP定位"
        s.current_subfield = "concept"

        # Stall 3 times on concept
        misroute = FakeInterviewer(
            fills=[InterviewFill(module="IP定位", subfield="core_experience", value="决斗")],
            guidance_reply="已记录。",
        )
        # forced_allocate returns a fill that hits the ALREADY-FILLED name field
        from app.domains.creation.a1.interviewer import InterviewResult as IR
        misroute._forced_allocate_result = IR(
            fills=[InterviewFill(module="IP定位", subfield="name", value="星穹大陆",
                                  conflict_note="与原设定不同")],
            guidance_reply="我判断这条输入属于【世界名称】。",
        )

        user_text = "先手必赢的世界"
        from app.domains.creation.a1.guide_engine import handle_message

        handle_message(s, user_text, misroute)  # stall 1
        handle_message(s, user_text, misroute)  # stall 2
        out3 = handle_message(s, user_text, misroute)  # stall 3 -> forced_allocate

        # The name field should NOT be silently overwritten
        assert s.answers["IP定位.name"] == "星陨大陆"
        # A proposal should have been generated
        assert len(s.pending_proposals) == 1
        assert "proposals" in out3
        assert len(out3["proposals"]) == 1


class TestIdempotentResolve:
    """Scenario 7 (Metis E3): resolve_proposal is idempotent per key —
    repeating the same key returns latest state, no double-write."""

    def test_double_resolve_is_idempotent(self):
        s = make_session()
        s.answers["IP定位.name"] = "星陨大陆"
        fills = [InterviewFill(module="IP定位", subfield="name", value="星穹大陆")]
        _apply_fills(s, fills)
        key = _proposal_key("IP定位", "name", "星穹大陆")

        r1 = resolve_proposal(s, key, "replace")
        r2 = resolve_proposal(s, key, "replace")

        assert s.answers["IP定位.name"] == "星穹大陆"
        assert r1["applied"] is True
        # Second call: key no longer in pending → not_found (idempotent, no double-write)
        assert r2["applied"] is False
        assert r2.get("error") == "not_found"


class TestReplyRewrite:
    """Scenario 8: When intercepted, reply is rewritten to a confirmation
    question citing the old value keyword + three options, in worldview language."""

    def test_intercept_reply_contains_options_and_old_value(self):
        s = make_session()
        s.answers["IP定位.name"] = "星陨大陆"
        fills = [
            InterviewFill(module="IP定位", subfield="name", value="星穹大陆",
                           conflict_note="与前设定矛盾")
        ]
        from app.domains.creation.a1.guide_engine import handle_message

        out = handle_message(s, "改成星穹大陆", FakeInterviewer(fills=fills))

        # reply should contain old value reference
        assert "星陨大陆" in out["reply"]
        # reply should mention three options
        assert "替换" in out["reply"] or "replace" in out["reply"].lower()
        assert "合并" in out["reply"] or "merge" in out["reply"].lower()
        assert "放弃" in out["reply"] or "drop" in out["reply"].lower()
        # proposals should be in output
        assert "proposals" in out


class TestSingleQuestionIronLaw:
    """Scenario 9: pending_proposals non-empty → next_question is suspended."""

    def test_pending_proposals_suspends_next_question(self):
        s = make_session()
        s.answers["IP定位.name"] = "星陨大陆"
        fills = [
            InterviewFill(module="IP定位", subfield="name", value="星穹大陆")
        ]
        from app.domains.creation.a1.guide_engine import handle_message

        out = handle_message(s, "改成星穹大陆", FakeInterviewer(fills=fills))

        # When proposals are pending, next_question should be None
        assert out["next_question"] is None


class TestConflictNotePassthrough:
    """Scenario 9b: InterviewFill.conflict_note is passed through to
    the Proposal's conflict_note field."""

    def test_conflict_note_transmitted(self):
        s = make_session()
        s.answers["IP定位.name"] = "星陨大陆"
        fills = [
            InterviewFill(
                module="IP定位", subfield="name", value="星穹大陆",
                conflict_note="灵韵海是核心地理，与地壳阴面矛盾"
            )
        ]

        _, proposals = _apply_fills(s, fills)

        assert len(proposals) == 1
        assert proposals[0].conflict_note == "灵韵海是核心地理，与地壳阴面矛盾"
        # Also check it's stored in pending_proposals
        key = _proposal_key("IP定位", "name", "星穹大陆")
        assert s.pending_proposals[key]["proposal"].conflict_note == (
            "灵韵海是核心地理，与地壳阴面矛盾"
        )
