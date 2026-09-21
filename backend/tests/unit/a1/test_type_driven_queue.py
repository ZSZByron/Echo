# -*- coding: utf-8 -*-
"""E1-Lite T2 — type-driven forward-only queue reordering (R6 conservative).

sync_position traversal order is permuted by creator_primary: priority
modules move forward, nothing is skipped. Pure permutation guarantees
all 35 field keys remain reachable and phase can still reach COMPLETED.
"""

import pytest

from app.domains.creation.a1.guide_engine import (
    A1Session,
    TYPE_ENTRY_SUBFIELD,
    TYPE_MODULE_PRIORITY,
    sync_position,
)
from app.domains.creation.seed.a1_question_tree import (
    MODULES,
    all_subfield_keys,
    get_subfield,
    module_ids,
)


def make_session(creator_primary: str = "") -> A1Session:
    return A1Session(
        session_id="s1",
        user_id="u1",
        ip_code="IP0001",
        creator_primary=creator_primary,
    )


def fill_all(session: A1Session) -> None:
    for key in all_subfield_keys():
        session.answers[key] = "x"


class TestTypeDrivenHappyPath:
    """plot 新会话首问 = 历史时间线.main_plot（故事问题，非 time_span）。"""

    def test_plot_new_session_first_question_is_story(self):
        s = make_session("plot")
        sync_position(s)
        assert s.current_module == "历史时间线"
        assert s.current_subfield == "main_plot"
        sf = get_subfield(s.current_module, s.current_subfield)
        assert sf is not None
        # First question must be the story question (main_plot), NOT the
        # time_span question ("当前时间段里世界正在发生什么？" belongs to
        # time_span — the entry swap exists precisely to avoid it).
        assert sf["id"] == "main_plot"
        time_span = get_subfield("历史时间线", "time_span")
        assert time_span is not None
        assert sf["question"] != time_span["question"]


class TestTypeMatrix:
    """逐型矩阵：每型新会话 current_module = 该型前置模块首元素。"""

    @pytest.mark.parametrize(
        "ptype,expected_module",
        [
            ("plot", "历史时间线"),
            ("unsure", "历史时间线"),
            ("philosophy", "世界本体"),
            ("romance", "IP定位"),
            ("character_driven", "文明与社会"),
            ("setting_heavy", "视觉设计"),
            ("exploration", "玩法设计DNA"),
        ],
    )
    def test_first_module_matches_priority_head(self, ptype, expected_module):
        assert TYPE_MODULE_PRIORITY[ptype][0] == expected_module
        s = make_session(ptype)
        sync_position(s)
        assert s.current_module == expected_module


class TestR6Reachability:
    """R6 保守模式：只前移不跳过——重排是置换，全部字段仍可答、可达 COMPLETED。"""

    def test_reorder_is_pure_permutation(self):
        for ptype in TYPE_MODULE_PRIORITY:
            s = make_session(ptype)
            ordered = _ordered(s)
            assert sorted(ordered) == sorted(module_ids())
            assert len(ordered) == len(module_ids())

    def test_plot_full_walk_reaches_completed_with_all_35_keys(self):
        s = make_session("plot")
        remaining = list(all_subfield_keys())
        assert len(remaining) == 35
        # End-to-end walk: answer whatever sync_position points at, in
        # order, until COMPLETED. Forward-only means every key gets asked.
        guard = 0
        while s.phase != "completed":
            guard += 1
            assert guard <= 40, "sync_position must terminate"
            sync_position(s)
            if s.phase == "completed":
                break
            key = f"{s.current_module}.{s.current_subfield}"
            assert key in remaining, f"field asked twice or never: {key}"
            remaining.remove(key)
            s.answers[key] = "答"
        assert s.phase == "completed"
        assert remaining == []
        assert sorted(s.answers.keys()) == sorted(all_subfield_keys())


def _ordered(session: A1Session) -> list[str]:
    from app.domains.creation.a1.guide_engine import _type_ordered_modules

    return _type_ordered_modules(session)


class TestGatePreserved:
    """门禁保持：门禁未达模块即使在类型序后段，仍优先命中。"""

    def test_gate_failing_late_module_wins_over_type_head(self):
        s = make_session("plot")
        # 历史时间线 (type head, 3 fields) fully answered → over gate.
        for f in ["time_span", "key_nodes", "main_plot"]:
            s.answers[f"历史时间线.{f}"] = "x"
        sync_position(s)
        # Gate section scans in TYPE order; first gate-failing module hit
        # is 文明与社会 (0/4), which plot-order puts before IP定位 — i.e.
        # the gate section decides by type order, not questionnaire order.
        assert s.current_module == "文明与社会"
        assert s.current_subfield == "core_value"

    def test_gate_rescues_late_module_in_type_order(self):
        s = make_session("plot")
        # Everything answered except 视觉设计 — which sits LATE in plot
        # order — yet the gate section must still service it first.
        for m in MODULES:
            if m["id"] == "视觉设计":
                continue
            for f in m["fields"]:
                s.answers[f"{m['id']}.{f['id']}"] = "x"
        sync_position(s)
        assert s.current_module == "视觉设计"
        assert s.current_subfield == "keywords"


class TestDefaultOrderRegression:
    """无 profile / healing → 原序行为完全一致。"""

    def test_no_profile_keeps_original_order(self):
        s = make_session("")
        sync_position(s)
        assert s.current_module == "IP定位"
        assert s.current_subfield == "name"
        assert _ordered(s) == module_ids()

    def test_healing_keeps_original_order(self):
        s = make_session("healing")
        sync_position(s)
        assert s.current_module == "IP定位"
        assert _ordered(s) == module_ids()

    def test_nostalgia_keeps_original_order(self):
        s = make_session("nostalgia")
        sync_position(s)
        assert _ordered(s) == module_ids()

    def test_no_profile_full_walk_covers_all_keys_once(self):
        s = make_session("")
        visited = []
        for _ in range(40):
            sync_position(s)
            if s.phase == "completed":
                break
            visited.append(f"{s.current_module}.{s.current_subfield}")
            s.answers[visited[-1]] = "答"
        assert s.phase == "completed"
        # Gate-aware order deviates from tree order mid-walk (pre-existing
        # behaviour), but every key must be asked exactly once, in full.
        assert sorted(visited) == sorted(all_subfield_keys())
        assert len(visited) == len(set(visited)) == 35


class TestCrossTurnIdempotence:
    """跨 chat 轮次 sync_position 幂等：作答后指针按类型序前进不回跳。"""

    def test_plot_pointer_moves_forward_never_back(self):
        s = make_session("plot")
        visited = []
        for _ in range(40):
            sync_position(s)
            if s.phase == "completed":
                break
            key = f"{s.current_module}.{s.current_subfield}"
            visited.append(key)
            s.answers[key] = "答"
        assert s.phase == "completed"
        # Every field asked exactly once (no repeats / no backward jumps)
        assert len(visited) == len(set(visited)) == 35
        # Idempotence: calling sync_position again changes nothing
        s.answers.pop(visited[-1])
        sync_position(s)
        assert f"{s.current_module}.{s.current_subfield}" == visited[-1]
        sync_position(s)
        assert f"{s.current_module}.{s.current_subfield}" == visited[-1]

    def test_entry_subfield_swap_only_for_listed_types(self):
        # Entry swap is defined only for plot/unsure on 历史时间线
        assert set(TYPE_ENTRY_SUBFIELD.keys()) == {"plot", "unsure"}
        for ptype, (mid, sid) in TYPE_ENTRY_SUBFIELD.items():
            assert mid == "历史时间线"
            assert sid == "main_plot"
