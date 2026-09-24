"""field_sources 四出口契约测试（M4a，D12 冻结设计）。

契约（impulse spec §6 / 计划 TODO 4）：
- field_sources = answers 的平行元数据，同键空间，只看不判；
- 四来源闭集：human / llm_fill / dice_rec / upload_prefill（逐字，不扩张）；
- 四写入出口各接线一处：直答(handle_message)→human /
  _apply_fills（fills 通道，含提案 confirm）→llm_fill /
  上传预填(_prefill_session←parse_modules)→upload_prefill /
  骰子推荐(apply_dice_recommendation)→dice_rec；
- 有值（J1 真值）字段必有来源；键空间 ⊆ 配方并集；
- 存量会话无 field_sources → unknown 兜底，不抛错。

TDD RED：实现前本文件全部失败。
"""
from typing import Any

import pytest

from app.domains.creation.a1.guide_engine import (
    A1Session,
    apply_dice_recommendation,
    handle_message,
    mark_field_source,
    resolve_proposal,
    FIELD_SOURCES,
    _apply_fills,
)
from app.domains.creation.a1.interviewer import (
    InterviewFill,
    InterviewResult,
    Proposal,
)
from app.domains.creation.seed.a1_question_tree import all_subfield_keys


def make_session() -> A1Session:
    return A1Session(session_id="s1", user_id="u1", ip_code="IP0001")


class StubInterviewer:
    """Deterministic interviewer stub returning a canned result."""

    def __init__(self, result: InterviewResult) -> None:
        self._result = result

    def interview(self, session: Any, text: str) -> InterviewResult:
        return self._result

    def forced_allocate(self, session: Any, text: str) -> InterviewResult:
        return self._result

    def suggest_examples(
        self, session: Any, module_id: str, subfield_id: str
    ) -> list[str]:
        return []


class TestEnumClosed:
    """四来源枚举闭集（逐字，不允许扩张）。"""

    def test_closed_enum_verbatim(self):
        assert FIELD_SOURCES == frozenset(
            {"human", "llm_fill", "dice_rec", "upload_prefill"}
        )

    def test_mark_rejects_unknown_source(self):
        s = make_session()
        s.answers["IP定位.name"] = "星陨大陆"
        with pytest.raises(ValueError):
            mark_field_source(s, "IP定位.name", "ai_guess")


class TestLegacyFallback:
    """存量会话（无 field_sources）→ unknown 兜底，不抛错。"""

    def test_old_session_dict_loads_without_field_sources(self):
        old = {
            "session_id": "old1",
            "user_id": "u1",
            "answers": {"IP定位.name": "星陨大陆"},
        }
        s = A1Session.model_validate(old)
        assert s.field_sources == {}
        # 观察面兜底：missing key → "unknown"，不抛错、不改行为
        assert s.field_sources.get("IP定位.name", "unknown") == "unknown"

    def test_legacy_session_runs_full_message_without_error(self):
        s = A1Session.model_validate(
            {"session_id": "old2", "user_id": "u1"}
        )
        result = InterviewResult(
            fills=[InterviewFill(module="IP定位", subfield="name", value="星陨大陆")]
        )
        out = handle_message(s, "星陨大陆", StubInterviewer(result))
        assert out["file_diff"]
        # 写入后标记生效（IP定位.name = 首模块当前问题 → 直答 human）；
        # 关键契约：存量会话（无 field_sources）全程不抛错。
        assert s.field_sources.get("IP定位.name") == "human"


class TestOutletHuman:
    """出口 1：直答（当前问题字段的直接回答）→ human。"""

    def test_current_field_fill_marked_human(self):
        s = make_session()
        cur = f"{s.current_module}.{s.current_subfield}"
        sf = cur.split(".", 1)
        other = InterviewFill(module="IP定位", subfield="name", value="星陨大陆")
        result = InterviewResult(
            fills=[InterviewFill(module=sf[0], subfield=sf[1], value="意志世界"), other]
        )
        handle_message(s, "意志世界，还有星陨大陆", StubInterviewer(result))
        assert s.answers[cur] == "意志世界"
        assert s.field_sources[cur] == "human"

    def test_side_field_fill_stays_llm_fill(self):
        s = make_session()
        # 现实锚定：首模块=IP定位.name（当前问题）——侧字段须选配方内
        # 非当前键，否则按契约应标 human（直答）。
        result = InterviewResult(
            fills=[InterviewFill(module="世界本体", subfield="world_type", value="意志主导")]
        )
        handle_message(s, "聊到意志主导", StubInterviewer(result))
        assert s.field_sources.get("世界本体.world_type") == "llm_fill"

    def test_intercepted_current_field_not_marked_until_confirm(self):
        s = make_session()
        cur = f"{s.current_module}.{s.current_subfield}"
        s.answers[cur] = "旧设定"
        sf = cur.split(".", 1)
        result = InterviewResult(
            fills=[InterviewFill(module=sf[0], subfield=sf[1], value="全新设定")]
        )
        out = handle_message(s, "改成全新设定", StubInterviewer(result))
        # 被写-guard 拦截 → 尚无写入，不标 human；confirm 后走 llm_fill
        assert s.answers[cur] == "旧设定"
        assert cur not in s.field_sources
        assert s.pending_proposals


class TestOutletLlmFill:
    """出口 2：_apply_fills（fills 通道，含提案 confirm）→ llm_fill。"""

    def test_empty_field_direct_write_marked(self):
        s = make_session()
        # 非当前问题字段（侧字段）走 fills 通道 → llm_fill；当前问题字段
        # 属直答出口（见 TestOutletHuman）。
        _apply_fills(s, [InterviewFill(module="世界本体", subfield="world_type", value="意志主导")])
        assert s.field_sources["世界本体.world_type"] == "llm_fill"

    def test_placeholder_fill_not_written_not_marked(self):
        s = make_session()
        _apply_fills(s, [InterviewFill(module="IP定位", subfield="name", value="待补充")])
        assert "IP定位.name" not in s.answers
        assert "IP定位.name" not in s.field_sources

    def test_proposal_confirm_replace_marked_llm_fill(self):
        s = make_session()
        s.answers["IP定位.name"] = "旧大陆"
        _apply_fills(s, [InterviewFill(module="IP定位", subfield="name", value="新星陨")])
        assert "IP定位.name" not in s.field_sources  # 拦截态不标
        key = next(iter(s.pending_proposals))
        out = resolve_proposal(s, key, "replace")
        assert out["applied"] is True
        assert s.answers["IP定位.name"] == "新星陨"
        # fills 通道 confirm（已经用户 confirm）→ llm_fill
        assert s.field_sources["IP定位.name"] == "llm_fill"


class TestOutletUploadPrefill:
    """出口 3：parse_modules 预填链（_prefill_session）→ upload_prefill。"""

    def _prefill(self):
        import app.api.a1_routes as routes

        parsed = {
            "answers": {
                "IP定位.name": "星陨大陆",
                "世界本体.world_type": "意志主导",
            },
            "clipped_answers": [],
            "innovations": [],
        }
        out = routes._prefill_session("u1", parsed)
        return routes._SESSIONS[out["session_id"]]

    def test_prefill_session_marks_all_answers(self):
        s = self._prefill()
        assert s.field_sources == {
            "IP定位.name": "upload_prefill",
            "世界本体.world_type": "upload_prefill",
        }

    def test_user_fill_overwrites_prefill_source_to_llm_fill(self):
        s = self._prefill()
        _apply_fills(
            s, [InterviewFill(module="IP定位", subfield="name", value="新大陆")]
        )
        assert s.answers["IP定位.name"] == "新大陆"
        assert s.field_sources["IP定位.name"] == "llm_fill"


class TestOutletDiceRec:
    """出口 4：骰子推荐写入（当前无 live 端点——确定性 apply 函数即接线点）。"""

    def test_apply_dice_recommendation_writes_and_marks(self):
        s = make_session()
        ok = apply_dice_recommendation(s, "骰子设定.probability", "D100")
        assert ok is True
        assert s.answers["骰子设定.probability"] == "D100"
        assert s.field_sources["骰子设定.probability"] == "dice_rec"

    def test_apply_dice_recommendation_intercepts_placeholder(self):
        s = make_session()
        ok = apply_dice_recommendation(s, "骰子设定.probability", "待定")
        assert ok is False
        assert "骰子设定.probability" not in s.answers
        assert "骰子设定.probability" not in s.field_sources


class TestContractInvariants:
    """契约：有值字段必有来源 + 键空间 ⊆ 配方并集。"""

    def test_every_truthy_answer_has_source_after_flow(self):
        s = make_session()
        _apply_fills(
            s,
            [
                InterviewFill(module="IP定位", subfield="name", value="星陨大陆"),
                InterviewFill(module="IP定位", subfield="concept", value="因果轮回"),
            ],
        )
        apply_dice_recommendation(s, "骰子设定.probability", "D100")
        for key, value in s.answers.items():
            if value.strip():
                assert key in s.field_sources, f"answered field {key} lacks source"
                assert s.field_sources[key] in FIELD_SOURCES

    def test_source_keyspace_subset_of_recipe_union(self):
        s = make_session()
        s.recipe_modules = ["IP定位", "世界本体"]  # 子集配方
        _apply_fills(s, [InterviewFill(module="IP定位", subfield="name", value="星陨大陆")])
        legal = set(all_subfield_keys(recipe=s.recipe_modules or None))
        assert set(s.field_sources) <= legal

    def test_observe_only_no_logic_branch(self):
        """只看不判：field_sources 不改变门禁/进度计算结果。"""
        from app.domains.creation.a1.guide_engine import progress

        s1 = make_session()
        s2 = make_session()
        fills = [InterviewFill(module="IP定位", subfield="name", value="星陨大陆")]
        _apply_fills(s1, fills)
        s2.answers["IP定位.name"] = "星陨大陆"  # 同答案、无来源标记
        assert progress(s1) == progress(s2)
