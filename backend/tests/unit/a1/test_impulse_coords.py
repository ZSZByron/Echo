"""冲动坐标观测层契约测试（M4b，impulse spec §10.1，D13）。

契约（spec §10.1 逐字）：
- 三件套：叙事-建构轴 [0,100]（锚点初值 spec L309 逐字）/ 置信度 /
  安全旗（单向棘轮，检测到即升起，坐标漂移永不降旗）；
- 四护栏：确定性更新（只吃显式信号+全留痕）/ 防振荡阻尼（滞后+每会话
  调整上限+每会话至多一次队列重排+只重排未访模块）/ 可达性不变式
  （R6 只前移不跳过）/ 安全旗棘轮；
- **E2 只看不判**：坐标落库+看板数据接口，绝不驱动路由——路由行为
  零变化回归（同输入，坐标有无 → 决策逐字节一致）。

TDD RED：实现前本文件全部失败。
"""
from typing import Any

import pytest

from app.domains.creation.a1.guide_engine import A1Session, handle_message
from app.domains.creation.a1.impulse_coords import (
    AXIS_ANCHOR_BY_TYPE,
    MAX_ADJUSTMENTS_PER_SESSION,
    REORDER_MAX_PER_SESSION,
    SIGNALS,
    apply_signal,
    dashboard_data,
    init_impulse_coords,
    maybe_reorder,
    raise_safety_flag,
)
from app.domains.creation.a1.interviewer import (
    InterviewFill,
    InterviewResult,
)
from app.domains.creation.shared.module_registry import RECIPES
from app.domains.creation.seed.a1_question_tree import all_subfield_keys


def make_session(**kw: Any) -> A1Session:
    return A1Session(session_id="s1", user_id="u1", ip_code="IP0001", **kw)


class StubInterviewer:
    def __init__(self, result: InterviewResult) -> None:
        self._result = result

    def interview(self, session: Any, text: str) -> InterviewResult:
        return self._result

    def forced_allocate(self, session: Any, text: str) -> InterviewResult:
        return self._result

    def suggest_examples(
        self, module_id: str, subfield_id: str
    ) -> list[str]:
        return []


class TestAnchorsVerbatimSpecL309:
    """锚点初值逐字锁定（spec L309，预注册纪律：写定后不随数据回调）。"""

    def test_anchor_values_verbatim(self):
        # spec L309：设定-重度≈15 / 探索≈25 / 角色驱动≈35 / 哲理≈65 /
        # 剧情≈70 / 怀旧≈75 / 爱情≈80 / 疗愈≈85；说不清≈70。
        assert AXIS_ANCHOR_BY_TYPE == {
            "setting_heavy": 15,
            "exploration": 25,
            "character_driven": 35,
            "philosophy": 65,
            "plot": 70,
            "nostalgia": 75,
            "romance": 80,
            "healing": 85,
            "unsure": 70,  # 说不清（人口先验：落故事侧但置信低）
        }

    def test_init_uses_anchor(self):
        s = make_session(creator_primary="healing")
        init_impulse_coords(s)
        assert s.impulse_coords["axis"] == 85

    def test_init_unprofiled_defaults_to_unsure_prior(self):
        s = make_session()
        init_impulse_coords(s)
        assert s.impulse_coords["axis"] == 70
        # 无选卡 → 低置信起步（spec L310：说不清 = 低置信起步）
        assert s.impulse_coords["confidence"] < 0.5

    def test_init_card_selected_high_confidence(self):
        s = make_session(creator_primary="plot", creator_profile_source="impulse_cards")
        init_impulse_coords(s)
        # 选卡 = 高置信起步（spec L310）
        assert s.impulse_coords["confidence"] >= 0.7

    def test_legacy_session_model_validate(self):
        old = {"session_id": "old1", "user_id": "u1"}
        s = A1Session.model_validate(old)
        assert s.impulse_coords == {}
        assert s.message_rounds == 0


class TestDeterministicUpdate:
    """护栏 1：确定性更新——显式信号闭集，同信号 → 同坐标 + 全留痕。"""

    def test_signal_enum_closed(self):
        assert set(SIGNALS) == {
            "pack_applied", "pack_rejected",
            "fill_confirmed", "fill_rejected",
            "skipped",
        }

    def test_same_signals_same_coords(self):
        coords_results = []
        for _ in range(2):
            s = make_session(creator_primary="romance")
            init_impulse_coords(s)
            apply_signal(s, "fill_confirmed", key="剧情.core_dilemma")
            apply_signal(s, "fill_confirmed", key="世界本体.name")
            coords_results.append(
                (s.impulse_coords["axis"], s.impulse_coords["confidence"])
            )
        assert coords_results[0] == coords_results[1]

    def test_audit_trail_full(self):
        s = make_session(creator_primary="romance")
        init_impulse_coords(s)
        apply_signal(s, "fill_confirmed", key="剧情.core_dilemma")
        audit = s.impulse_coords["audit"]
        assert len(audit) == 1
        entry = audit[0]
        for field in ("round", "signal", "key", "axis_before", "axis_after",
                      "confidence_before", "confidence_after", "applied"):
            assert field in entry

    def test_story_fill_moves_toward_narrative(self):
        s = make_session(creator_primary="romance")
        init_impulse_coords(s)
        before = s.impulse_coords["axis"]
        apply_signal(s, "fill_confirmed", key="剧情.core_dilemma")
        assert s.impulse_coords["axis"] > before  # 100=纯叙事

    def test_worldview_fill_moves_toward_worldbuilding(self):
        s = make_session(creator_primary="romance")
        init_impulse_coords(s)
        before = s.impulse_coords["axis"]
        apply_signal(s, "fill_confirmed", key="世界本体.name")
        assert s.impulse_coords["axis"] < before  # 0=纯建构

    def test_axis_clamped(self):
        s = make_session(creator_primary="setting_heavy")  # 锚点 15
        init_impulse_coords(s)
        for _ in range(MAX_ADJUSTMENTS_PER_SESSION + 1):
            apply_signal(s, "fill_confirmed", key="世界本体.name")
        assert 0 <= s.impulse_coords["axis"] <= 100


class TestDamping:
    """护栏 2a：阻尼——置信度决定调整步长（低置信 → 大阻尼）。"""

    def test_low_confidence_smaller_step(self):
        highs, lows = [], []
        for label, conf in (("high", 0.9), ("low", 0.2)):
            s = make_session(creator_primary="romance")
            init_impulse_coords(s)
            s.impulse_coords["confidence"] = conf
            before = s.impulse_coords["axis"]
            apply_signal(s, "fill_confirmed", key="剧情.core_dilemma")
            delta = s.impulse_coords["axis"] - before
            (highs if label == "high" else lows).append(delta)
        assert max(lows) <= min(highs)  # 低置信步长 ≤ 高置信步长

    def test_adjustment_cap_per_session(self):
        s = make_session(creator_primary="romance")
        init_impulse_coords(s)
        for _ in range(MAX_ADJUSTMENTS_PER_SESSION):
            apply_signal(s, "fill_confirmed", key="剧情.core_dilemma")
        snapshot = dict(s.impulse_coords)
        out = apply_signal(s, "fill_confirmed", key="剧情.core_dilemma")
        assert out["applied"] is False
        assert s.impulse_coords["axis"] == snapshot["axis"]
        assert s.impulse_coords["confidence"] == snapshot["confidence"]


class TestSafetyFlagRatchet:
    """护栏 4：安全旗单向棘轮——升起永不降。"""

    def test_raise_sets_true(self):
        s = make_session(creator_primary="healing")
        init_impulse_coords(s)
        raise_safety_flag(s, reason="crisis_signal")
        assert s.impulse_coords["safety_flag"] is True

    def test_never_lowered_by_updates(self):
        s = make_session(creator_primary="healing")
        init_impulse_coords(s)
        raise_safety_flag(s, reason="crisis_signal")
        for _ in range(3):
            apply_signal(s, "skipped")
        assert s.impulse_coords["safety_flag"] is True

    def test_ratchet_idempotent_and_audited(self):
        s = make_session(creator_primary="romance")
        init_impulse_coords(s)
        assert raise_safety_flag(s, "a") is True
        assert raise_safety_flag(s, "b") is True  # 已升 → 幂等 True
        raises = [e for e in s.impulse_coords["audit"] if e["signal"] == "safety_raise"]
        assert len(raises) == 1  # 首次升旗留痕，重复不刷屏


class TestAntiOscillationReorder:
    """护栏 2b：每会话至多一次队列重排 + 只重排未访模块（spec L318）。"""

    def test_at_most_one_reorder_per_session(self):
        s = make_session(creator_primary="romance")
        init_impulse_coords(s)
        order1 = maybe_reorder(s, list(RECIPES["romance"].module_ids))
        assert order1 is not None  # 首次允许（未访模块存在时）
        order2 = maybe_reorder(s, order1)
        assert order2 == order1  # 第二次 = 无重排（≤1 次/会话）
        assert s.impulse_coords["reorder_count"] <= REORDER_MAX_PER_SESSION

    def test_reorder_keeps_module_set_and_visited(self):
        s = make_session(creator_primary="romance")
        init_impulse_coords(s)
        order = list(RECIPES["romance"].module_ids)
        visited = order[0]
        s.answers[f"{visited}.identity"] = "主角是一柄会说话的剑"
        new_order = maybe_reorder(s, order)
        if new_order is not None:
            assert sorted(new_order) == sorted(order)  # 集合不变
            # 已访模块位置不动（已答内容永不动）
            assert new_order.index(visited) == order.index(visited)

    def test_reorder_reachability_invariant(self):
        """可达性不变式：重排后配方键集不变 → 已答键恒可达（R6 只前移不跳过）。"""
        s = make_session(creator_primary="romance")
        init_impulse_coords(s)
        order = list(RECIPES["romance"].module_ids)
        for i, mid in enumerate(order[:3]):
            subs = [f["id"] for f in __import__(
                "app.domains.creation.seed.a1_question_tree",
                fromlist=["subs_for_module"]).subs_for_module(mid)]
            s.answers[f"{mid}.{subs[0]}"] = f"答案{i}"
        new_order = maybe_reorder(s, order)
        if new_order is not None:
            before = set(all_subfield_keys(recipe=order))
            after = set(all_subfield_keys(recipe=new_order))
            assert after == before  # 门禁数学可达性：键集不变


class TestObserveOnlyRouting:
    """E2 只看不判（铁律）：坐标有无 → 路由决策逐字节一致。"""

    def test_routing_identical_with_and_without_coords(self):
        result = InterviewResult(
            fills=[InterviewFill(module="剧情", subfield="core_dilemma", value="抉择")]
        )
        outputs = []
        for populate in (False, True):
            s = make_session(
                creator_primary="romance",
                creator_profile_source="impulse_cards",
            )
            s.recipe_id = "romance"
            s.recipe_modules = list(RECIPES["romance"].module_ids)
            if populate:
                init_impulse_coords(s)
                raise_safety_flag(s, "test")
                apply_signal(s, "fill_confirmed", key="剧情.core_dilemma")
            out = handle_message(s, "他必须烧掉王座", StubInterviewer(result))
            outputs.append({
                k: out[k] for k in ("reply", "next_question", "file_diff",
                                    "progress", "phase")
            })
        assert outputs[0] == outputs[1]

    def test_queue_order_identical_with_and_without_coords(self):
        from app.domains.creation.a1.guide_engine import _type_ordered_modules
        orders = []
        for populate in (False, True):
            s = make_session(creator_primary="romance")
            s.recipe_modules = list(RECIPES["romance"].module_ids)
            if populate:
                init_impulse_coords(s)
                apply_signal(s, "fill_confirmed", key="世界本体.name")
            orders.append(_type_ordered_modules(s))
        assert orders[0] == orders[1]


class TestCoverageCompletions:
    """分支补齐：错误面 / 方向闭集 / 看板投影。"""

    def test_unknown_signal_raises(self):
        s = make_session()
        init_impulse_coords(s)
        with pytest.raises(ValueError):
            apply_signal(s, "llm_vibe")  # 非显式信号闭集 → 拒绝

    def test_unknown_key_zero_axis_delta(self):
        s = make_session(creator_primary="romance")
        init_impulse_coords(s)
        before = s.impulse_coords["axis"]
        out = apply_signal(s, "fill_confirmed", key="不存在的模块.x")
        assert out["applied"] is True
        assert s.impulse_coords["axis"] == before  # 未知键 → 方向 0

    def test_reorder_toward_worldbuilding_prefers_worldview(self):
        s = make_session(creator_primary="setting_heavy")  # 锚点 15
        init_impulse_coords(s)
        s.impulse_coords["axis"] = 5.0  # 低于锚点 → 偏建构
        order = list(RECIPES["romance"].module_ids)
        new_order = maybe_reorder(s, order)
        assert new_order is not None
        assert sorted(new_order) == sorted(order)
        assert s.impulse_coords["reorder_count"] == 1

    def test_reorder_axis_at_anchor_noop_order(self):
        s = make_session(creator_primary="romance")
        init_impulse_coords(s)
        s.impulse_coords["axis"] = s.impulse_coords["anchor"]  # 无偏好
        order = list(RECIPES["romance"].module_ids)
        assert maybe_reorder(s, order) == order

    def test_reorder_none_when_all_visited(self):
        s = make_session(creator_primary="romance")
        init_impulse_coords(s)
        from app.domains.creation.seed.a1_question_tree import subs_for_module
        order = list(RECIPES["romance"].module_ids)
        for mid in order:
            f = subs_for_module(mid)[0]
            s.answers[f"{mid}.{f['id']}"] = "x"
        assert maybe_reorder(s, order) is None

    def test_dashboard_data_projection(self):
        s = make_session(creator_primary="romance")
        init_impulse_coords(s)
        apply_signal(s, "fill_confirmed", key="剧情.core_dilemma")
        raise_safety_flag(s, "t")
        data = dashboard_data(s)
        for k in ("axis", "confidence", "safety_flag", "anchor",
                  "anchor_source", "adjustments", "reorder_count", "audit"):
            assert k in data
        assert data["safety_flag"] is True


class TestCoverageCompletions2:
    def test_output_family_key_zero_delta(self):
        s = make_session(creator_primary="romance")
        init_impulse_coords(s)
        before = s.impulse_coords["axis"]
        apply_signal(s, "fill_confirmed", key="文档.第一节")  # output family
        assert s.impulse_coords["axis"] == before

    def test_reorder_toward_narrative_prefers_story(self):
        s = make_session(creator_primary="setting_heavy")
        init_impulse_coords(s)
        s.impulse_coords["axis"] = 90.0  # 高于锚点 → 偏叙事
        order = list(RECIPES["romance"].module_ids)
        new_order = maybe_reorder(s, order)
        assert new_order is not None
        assert sorted(new_order) == sorted(order)
