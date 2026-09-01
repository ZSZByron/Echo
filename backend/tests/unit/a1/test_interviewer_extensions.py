"""TDD RED phase — Task 1 model extensions + prompt rules.

Tests will FAIL until implementation is added to interviewer.py.
"""
from __future__ import annotations

import types

import pytest

from app.domains.creation.a1.interviewer import (
    FakeInterviewer,
    InterviewFill,
    InterviewResult,
    Proposal,
    RealLLMInterviewer,
)


class TestInterviewFillConflictNote:
    """InterviewFill gets conflict_note field (default None)."""

    def test_default_conflict_note_is_none(self) -> None:
        f = InterviewFill(module="IP定位", subfield="name", value="星陨大陆")
        assert f.conflict_note is None

    def test_conflict_note_can_be_set(self) -> None:
        f = InterviewFill(
            module="地理空间",
            subfield="special_geo",
            value="第三层地壳的阴面",
            conflict_note="与已有设定重叠",
        )
        assert f.conflict_note == "与已有设定重叠"

    def test_old_construction_still_works(self) -> None:
        f = InterviewFill(module="IP定位", subfield="name", value="星陨大陆")
        assert f.module == "IP定位"
        assert f.subfield == "name"
        assert f.value == "星陨大陆"


class TestInterviewResultProposals:
    """InterviewResult gets proposals field (default [])."""

    def test_default_proposals_is_empty_list(self) -> None:
        r = InterviewResult(fills=[], guidance_reply="ok")
        assert r.proposals == []

    def test_proposals_can_be_set(self) -> None:
        p = Proposal(
            module="地理空间",
            subfield="special_geo",
            old="灵韵海化生万物",
            new="第三层地壳的阴面",
        )
        r = InterviewResult(fills=[], guidance_reply="ok", proposals=[p])
        assert len(r.proposals) == 1
        assert r.proposals[0].module == "地理空间"

    def test_old_construction_still_works(self) -> None:
        f = InterviewFill(module="IP定位", subfield="name", value="星陨大陆")
        r = InterviewResult(fills=[f], guidance_reply="ok")
        assert r.proposals == []


class TestProposalModel:
    """Proposal model with merge_preview default."""

    def test_basic_construction(self) -> None:
        p = Proposal(module="a", subfield="b", old="x", new="y")
        assert p.module == "a"
        assert p.subfield == "b"
        assert p.old == "x"
        assert p.new == "y"

    def test_merge_preview_default_fullwidth_semicolon(self) -> None:
        p = Proposal(module="a", subfield="b", old="x", new="y")
        assert p.merge_preview == "x；y"

    def test_merge_preview_with_real_values(self) -> None:
        p = Proposal(
            module="地理空间",
            subfield="special_geo",
            old="灵韵海化生万物",
            new="第三层地壳的阴面",
        )
        assert p.merge_preview == "灵韵海化生万物；第三层地壳的阴面"

    def test_conflict_note_default_none(self) -> None:
        p = Proposal(module="a", subfield="b", old="x", new="y")
        assert p.conflict_note is None

    def test_conflict_note_can_be_set(self) -> None:
        p = Proposal(module="a", subfield="b", old="x", new="y", conflict_note="重叠")
        assert p.conflict_note == "重叠"

    def test_merge_preview_can_be_overridden(self) -> None:
        p = Proposal(module="a", subfield="b", old="x", new="y", merge_preview="custom")
        assert p.merge_preview == "custom"


class TestBuildPromptNewRules:
    """_build_prompt must contain three new rule anchors."""

    def _make_session(self, **overrides) -> types.SimpleNamespace:
        defaults = dict(current_module="世界本体", current_subfield="origin", answers={})
        defaults.update(overrides)
        return types.SimpleNamespace(**defaults)

    def test_prompt_contains_conflict_check_rule(self) -> None:
        interviewer = RealLLMInterviewer(provider=None)
        session = self._make_session()
        module = {"id": "世界本体", "label": "世界本体", "fields": []}
        subfield = {"id": "origin", "label": "世界起源", "question": "?", "example": ""}
        prompt = interviewer._build_prompt(module, subfield, session)
        assert "冲突预检" in prompt

    def test_prompt_contains_red_line_rule(self) -> None:
        interviewer = RealLLMInterviewer(provider=None)
        session = self._make_session()
        module = {"id": "世界本体", "label": "世界本体", "fields": []}
        subfield = {"id": "origin", "label": "世界起源", "question": "?", "example": ""}
        prompt = interviewer._build_prompt(module, subfield, session)
        assert "不可动清单" in prompt

    def test_prompt_contains_term_translation_rule(self) -> None:
        interviewer = RealLLMInterviewer(provider=None)
        session = self._make_session()
        module = {"id": "世界本体", "label": "世界本体", "fields": []}
        subfield = {"id": "origin", "label": "世界起源", "question": "?", "example": ""}
        prompt = interviewer._build_prompt(module, subfield, session)
        assert "术语转译" in prompt

    def test_red_line_with_immutable_value_in_answers(self) -> None:
        interviewer = RealLLMInterviewer(provider=None)
        session = self._make_session(answers={"设定边界.immutable_core": "世界起源不可修改"})
        module = {"id": "世界本体", "label": "世界本体", "fields": []}
        subfield = {"id": "origin", "label": "世界起源", "question": "?", "example": ""}
        prompt = interviewer._build_prompt(module, subfield, session)
        assert "世界起源不可修改" in prompt

    def test_red_line_without_immutable_value_empty_placeholder(self) -> None:
        interviewer = RealLLMInterviewer(provider=None)
        session = self._make_session(answers={})
        module = {"id": "世界本体", "label": "世界本体", "fields": []}
        subfield = {"id": "origin", "label": "世界起源", "question": "?", "example": ""}
        prompt = interviewer._build_prompt(module, subfield, session)
        assert "不可动清单" in prompt

    def test_existing_rules_untouched(self) -> None:
        interviewer = RealLLMInterviewer(provider=None)
        session = self._make_session()
        module = {"id": "世界本体", "label": "世界本体", "fields": []}
        subfield = {"id": "origin", "label": "世界起源", "question": "?", "example": ""}
        prompt = interviewer._build_prompt(module, subfield, session)
        assert "理解用户输入" in prompt
        assert "判断分配" in prompt
        assert "只能填入" in prompt
        assert "创新判定" in prompt
        assert "提问、闲聊" in prompt
        assert "用户困惑判定" in prompt
        assert "guidance_reply（中文" in prompt
        assert "发散引导" in prompt

    def test_new_rules_between_3_and_4(self) -> None:
        """New rules must be between rule 3 and rule 4 in the prompt."""
        interviewer = RealLLMInterviewer(provider=None)
        session = self._make_session()
        module = {"id": "世界本体", "label": "世界本体", "fields": []}
        subfield = {"id": "origin", "label": "世界起源", "question": "?", "example": ""}
        prompt = interviewer._build_prompt(module, subfield, session)
        idx_3 = prompt.index("判断分配")
        idx_4 = prompt.index("只能填入")
        idx_conflict = prompt.index("冲突预检")
        idx_redline = prompt.index("不可动清单")
        idx_term = prompt.index("术语转译")
        assert idx_3 < idx_conflict < idx_redline < idx_term < idx_4


class TestFakeInterviewerBackwardCompat:
    """FakeInterviewer must work without any new params."""

    def test_no_args_construction(self) -> None:
        fake = FakeInterviewer()
        session = types.SimpleNamespace(session_id="s1")
        result = fake.interview(session, "测试")
        assert result.fills == []
        assert result.guidance_reply == "已记录。"

    def test_with_fills_construction(self) -> None:
        fills = [InterviewFill(module="IP定位", subfield="name", value="星陨大陆")]
        fake = FakeInterviewer(fills=fills, guidance_reply="ok")
        session = types.SimpleNamespace(session_id="s1")
        result = fake.interview(session, "测试")
        assert len(result.fills) == 1
        assert result.fills[0].value == "星陨大陆"

    def test_proposals_optional_param(self) -> None:
        p = Proposal(module="a", subfield="b", old="x", new="y")
        fake = FakeInterviewer(fills=[], guidance_reply="ok", proposals=[p])
        session = types.SimpleNamespace(session_id="s1")
        result = fake.interview(session, "测试")
        assert len(result.proposals) == 1


class TestParseConflictNote:
    """_parse should pass through conflict_note from LLM."""

    def test_parse_conflict_note_from_llm(self) -> None:
        """When LLM returns conflict_note, it should be preserved."""
        # This test will need RealLLMInterviewer._parse accessible.
        # We test it indirectly: the field exists on InterviewFill and
        # _parse should forward it. Full integration test of _parse
        # requires mocking the subfield keys, but the model-level
        # guarantee is tested above.
        # This is a placeholder for the _parse integration.
        pass  # Will be verified via GREEN phase

    def test_fill_serialization_roundtrip(self) -> None:
        """InterviewFill with conflict_note serializes/deserializes correctly."""
        f = InterviewFill(
            module="地理空间", subfield="special_geo", value="新值",
            conflict_note="与旧设定冲突",
        )
        d = f.model_dump()
        assert d["conflict_note"] == "与旧设定冲突"
        f2 = InterviewFill.model_validate(d)
        assert f2.conflict_note == "与旧设定冲突"

    def test_proposal_serialization_roundtrip(self) -> None:
        """Proposal roundtrips through model_dump/validate."""
        p = Proposal(module="a", subfield="b", old="x", new="y")
        d = p.model_dump()
        assert d["merge_preview"] == "x；y"
        p2 = Proposal.model_validate(d)
        assert p2.merge_preview == "x；y"
