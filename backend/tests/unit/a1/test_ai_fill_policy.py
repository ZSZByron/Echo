"""ai_fill 字段级粒度契约测试（M4b，未决①收口，plan TODO 5 §269）。

契约：
- Recipe.ai_fill_policy 字段级声明：ai_fill_exclude = 留给用户的字段键
  元组（LLM fills 不得触碰）；default 配方 = 空 → 行为逐字节不变；
- 过滤点 = fills 应用点（_apply_fills），确定性代码，无 LLM；
- 直答豁免：当前问题字段（用户口述直答）永不过滤——"留给用户"语义。
"""
from typing import Any

from app.domains.creation.a1.guide_engine import A1Session, _apply_fills
from app.domains.creation.a1.interviewer import InterviewFill
from app.domains.creation.shared.module_registry import RECIPES


def make_session(**kw: Any) -> A1Session:
    return A1Session(session_id="s1", user_id="u1", ip_code="IP0001", **kw)


class TestPolicyData:
    def test_default_recipe_no_exclusion(self):
        assert RECIPES["default"].ai_fill_exclude == ()

    def test_romance_reserves_faction_type_for_user(self):
        # plan §269 例：romance 型 faction_type 留给用户。
        assert "文明与社会.faction_type" in RECIPES["romance"].ai_fill_exclude


class TestFilteringAtApplyPoint:
    def test_excluded_fill_not_written(self):
        s = make_session(creator_primary="romance")
        diffs, intercepted = _apply_fills(
            s,
            [InterviewFill(module="文明与社会", subfield="faction_type",
                           value="神权帝国")],
        )
        assert diffs == []
        assert intercepted == []
        assert "文明与社会.faction_type" not in s.answers
        assert "文明与社会.faction_type" not in s.field_sources

    def test_non_excluded_fill_unaffected(self):
        s = make_session(creator_primary="romance")
        diffs, _ = _apply_fills(
            s,
            [InterviewFill(module="角色", subfield="identity", value="执剑人")],
        )
        assert s.answers["角色.identity"] == "执剑人"
        assert diffs

    def test_default_recipe_zero_behavior_change(self):
        s = make_session()  # 无 profile → default 全集，无排除
        diffs, _ = _apply_fills(
            s,
            [InterviewFill(module="文明与社会", subfield="faction_type",
                           value="神权帝国")],
        )
        assert s.answers["文明与社会.faction_type"] == "神权帝国"

    def test_direct_answer_exemption(self):
        """直答豁免：排除键恰为当前问题 → 用户口述直答，不过滤。"""
        s = make_session(creator_primary="romance")
        s.current_module = "文明与社会"
        s.current_subfield = "faction_type"
        diffs, _ = _apply_fills(
            s,
            [InterviewFill(module="文明与社会", subfield="faction_type",
                           value="部落议会")],
        )
        assert s.answers["文明与社会.faction_type"] == "部落议会"
        assert s.field_sources["文明与社会.faction_type"] == "human"

    def test_excluded_fill_cannot_smuggle_via_proposal(self):
        """排除键非空时连拦截提案都不产生（LLM 不得借 write-guard 触达）。"""
        s = make_session(creator_primary="romance")
        s.answers["文明与社会.faction_type"] = "旧值"
        diffs, intercepted = _apply_fills(
            s,
            [InterviewFill(module="文明与社会", subfield="faction_type",
                           value="新值")],
        )
        assert diffs == []
        assert intercepted == []
        assert s.answers["文明与社会.faction_type"] == "旧值"
        assert s.pending_proposals == {}
