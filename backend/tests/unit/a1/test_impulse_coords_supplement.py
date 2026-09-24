# -*- coding: utf-8 -*-
"""M4b impulse_coords 补充契约测试（新代码覆盖线 ≥85% 收口）。

本会话（Sisyphus-Junior 双写手）补充：未知信号 fail-loud / dashboard
只读投影 / maybe_reorder 中性轴与同族保序分支 / output 族键零轴移。
"""
from typing import Any

import pytest

from app.domains.creation.a1.guide_engine import A1Session
from app.domains.creation.a1.impulse_coords import (
    apply_signal,
    dashboard_data,
    init_impulse_coords,
    maybe_reorder,
)


def make_session(**kw: Any) -> A1Session:
    return A1Session(session_id="s1", user_id="u1", ip_code="IP0001", **kw)


def test_unknown_signal_fails_loud():
    s = make_session(creator_primary="plot")
    init_impulse_coords(s)
    with pytest.raises(ValueError, match="unknown impulse coord signal"):
        apply_signal(s, "llm_vibe")


def test_output_family_key_zero_axis_shift():
    """产出族（output）键不参与轴插值（连续值只调未访模块序）。"""
    s = make_session(creator_primary="romance")
    init_impulse_coords(s)
    before = s.impulse_coords["axis"]
    out = apply_signal(s, "fill_confirmed", key="主模组.anything")
    assert out["applied"] is True
    assert s.impulse_coords["axis"] == before  # 零轴移，仅置信度变
    assert s.impulse_coords["confidence"] > 0.3


def test_reorder_neutral_axis_keeps_order():
    """轴未漂移（== anchor）→ 重排候选 = 原序（同族保序退化）。"""
    s = make_session(creator_primary="plot")
    init_impulse_coords(s)
    order = ["剧情", "世界本体", "角色"]
    out = maybe_reorder(s, order)
    assert out == order  # 中性轴 → 不动序


def test_dashboard_data_readonly_shape():
    s = make_session(creator_primary="healing")
    init_impulse_coords(s)
    s.answers["角色.identity"] = "x"
    data = dashboard_data(s)
    for key in ("axis", "confidence", "safety_flag", "anchor",
                "anchor_source", "adjustments", "reorder_count", "audit"):
        assert key in data
    assert data["anchor_source"] == "healing"
    # 幂等：重复读不重复留痕
    n = len(data["audit"])
    assert len(dashboard_data(s)["audit"]) == n


def test_signal_outside_session_scope_still_trails():
    """超上限后仍留痕（诚实可观测：applied=False 落 audit）。"""
    s = make_session(creator_primary="romance")
    init_impulse_coords(s)
    from app.domains.creation.a1.impulse_coords import MAX_ADJUSTMENTS_PER_SESSION
    for _ in range(MAX_ADJUSTMENTS_PER_SESSION + 3):
        apply_signal(s, "fill_confirmed", key="剧情.core_dilemma")
    blocked = [e for e in s.impulse_coords["audit"] if e.get("applied") is False]
    assert blocked, "被阻尼挡下的信号也必须留痕"
