"""D21⑦ 主次配方结合切换：主∪次联合边界 + 切换机制（spec §5.4 L67）。

五组契约：
1. 联合边界构建（start-API）：主+次双有效 → recipe_modules = 主配方序
   为基 + 次配方独有模块追加（重叠只计一次，归属主规则）；重叠 fixture
   （主=plot + 次=unsure → 同配方族，恰好一次）。
2. 切换后未访序调整（unit）：已访模块不重问（answers 保留，sync_position
   跳过），未访模块按新配方前移；只重排不删减（R6 forward-only）。
3. 单冲动零回归：default / 仅主冲动 → 与既有行为逐字节一致
   （m1_default_snapshot 六场景口径——空/未知/次==主/次未知/仅次）。
4. D20 受邀交互：切换不清零 invited_modules、不重置其进度；受邀模块
   切换后仍可完成并计入 done（progress()）。
5. recipe-switch 端点契约（API）：applied 返回 + 新序投影；未知 file 404、
   非 主/次 target 400、default 会话 409。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import a1_routes
from app.domains.creation.a1.guide_engine import (
    A1Session,
    _apply_worldview_invites,
    apply_recipe_switch,
    progress,
    subs_for_module,
    sync_position,
)
from app.domains.creation.shared.module_registry import RECIPES, resolve_recipe_id
from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _start(client: TestClient, **extra) -> dict:
    payload = {"user_id": "u_rs", "custom_idea": "测试世界观"}
    payload.update(extra)
    resp = client.post("/api/a1/session/start", json=payload)
    assert resp.status_code == 200
    return resp.json()


def _session(client: TestClient, data: dict) -> A1Session:
    return a1_routes._SESSIONS[data["session_id"]]


def _fill_module(session: A1Session, mid: str) -> None:
    for sf in subs_for_module(mid):
        session.answers[f"{mid}.{sf['id']}"] = f"答案_{mid}.{sf['id']}"


# ---------------------------------------------------------------------------
# 组 1：联合边界构建（start-API）
# ---------------------------------------------------------------------------


class TestJointBoundaryConstruction:
    def test_primary_plus_secondary_union(self, client: TestClient) -> None:
        """主=plot + 次=setting_heavy：主序为基，次独有模块按次序追加。"""
        data = _start(
            client, impulse_primary="plot", impulse_secondary="setting_heavy"
        )
        session = _session(client, data)
        primary = list(RECIPES["plot"].module_ids)
        secondary = list(RECIPES["setting_heavy"].module_ids)
        expected = primary + [m for m in secondary if m not in primary]
        assert session.recipe_modules == expected
        # 重叠只计一次（若有）：len == 去重后的并集
        assert len(session.recipe_modules) == len(set(session.recipe_modules))
        assert session.recipe_id == "plot"  # 归属主规则：recipe_id 不变

    def test_overlap_dedup_same_family(self, client: TestClient) -> None:
        """重叠 fixture：主=plot + 次=unsure → 同为 (剧情, 角色)，无重复。"""
        data = _start(client, impulse_primary="plot", impulse_secondary="unsure")
        session = _session(client, data)
        assert session.recipe_modules == ["剧情", "角色"]

    def test_single_impulse_primary_only(self, client: TestClient) -> None:
        """仅主冲动 → 主配方序，无追加（零回归口径）。"""
        data = _start(client, impulse_primary="philosophy")
        session = _session(client, data)
        assert session.recipe_modules == list(RECIPES["philosophy"].module_ids)

    def test_invalid_secondary_ignored(self, client: TestClient) -> None:
        """次冲动未知 → 只落主配方（存量降级语义不变）。"""
        data = _start(
            client, impulse_primary="plot", impulse_secondary="wtf_99"
        )
        session = _session(client, data)
        assert session.recipe_modules == list(RECIPES["plot"].module_ids)


# ---------------------------------------------------------------------------
# 组 2：切换后未访序调整（unit，guide_engine.apply_recipe_switch）
# ---------------------------------------------------------------------------


class TestSwitchUnvisitedReorder:
    def _plot_session_with_visited_qingjie(self) -> A1Session:
        session = A1Session(session_id="a1_rs", user_id="u")
        session.creator_primary = "plot"
        session.creator_secondary = "setting_heavy"
        session.recipe_id = "plot"
        session.recipe_modules = list(RECIPES["plot"].module_ids) + ["视觉设计"]
        _fill_module(session, "剧情")  # 已访模块：进度保留
        sync_position(session)
        return session

    def test_visited_not_reasked(self) -> None:
        session = self._plot_session_with_visited_qingjie()
        applied = apply_recipe_switch(session, "setting_heavy")
        assert applied == "setting_heavy"
        # 已访模块字段全部保留（进度不清零 → 不会被重问）
        for sf in subs_for_module("剧情"):
            assert f"剧情.{sf['id']}" in session.answers
        # 当前指针不在已访模块上
        assert session.current_module != "剧情"

    def test_unvisited_reordered_forward(self) -> None:
        session = self._plot_session_with_visited_qingjie()
        apply_recipe_switch(session, "setting_heavy")
        # 未访段按新配方前移：视觉设计（次配方 head）提前到剩余段首位
        assert session.recipe_modules[0] == "视觉设计"
        # 未访指针落在次配方 head 模块
        assert session.current_module == "视觉设计"

    def test_reorder_only_no_removal_r6(self) -> None:
        session = self._plot_session_with_visited_qingjie()
        before = set(session.recipe_modules)
        apply_recipe_switch(session, "setting_heavy")
        # R6 forward-only：只重排不删减
        assert set(session.recipe_modules) == before
        assert len(session.recipe_modules) == len(set(session.recipe_modules))

    def test_switch_back_to_primary(self) -> None:
        session = self._plot_session_with_visited_qingjie()
        apply_recipe_switch(session, "setting_heavy")
        apply_recipe_switch(session, "plot")
        assert session.recipe_modules == ["剧情", "角色", "视觉设计"]

    def test_noop_cases(self) -> None:
        session = self._plot_session_with_visited_qingjie()
        # 非主/次 target → no-op
        assert apply_recipe_switch(session, "romance") == ""
        # default 会话（recipe_modules 空）→ no-op
        bare = A1Session(session_id="a1_bare", user_id="u")
        assert apply_recipe_switch(bare, "plot") == ""


# ---------------------------------------------------------------------------
# 组 3：单冲动 / default 零回归（m1_default_snapshot 六场景口径）
# ---------------------------------------------------------------------------


class TestZeroRegressionSingleImpulse:
    SIX_CASES = [
        {},
        {"impulse_primary": "hacker_vibes", "impulse_secondary": "plot"},
        {"impulse_primary": "plot", "impulse_secondary": "plot"},
        {"impulse_primary": "plot", "impulse_secondary": "wtf_99"},
        {"impulse_primary": "plot"},
        {"impulse_secondary": "setting_heavy"},
    ]

    def test_six_cases_boundary_byte_identical(self, client: TestClient) -> None:
        """六场景：联合边界分支绝不触发（default 空 / 仅主配方序）。"""
        for extra in self.SIX_CASES:
            data = _start(client, **extra)
            session = _session(client, data)
            rid = resolve_recipe_id(session.creator_primary)
            expected: list[str] = (
                [] if rid == "default" else list(RECIPES[rid].module_ids)
            )
            assert session.recipe_modules == expected, f"case={extra}"
            assert session.recipe_id == rid

    def test_switch_matches_snapshot_registry(self, client: TestClient) -> None:
        """default 会话（无冲动档案）无边界可切 → 400（target 非主/次）。"""
        data = _start(client)  # 无冲动 → default
        resp = client.post(
            f"/api/a1/file/{data['file_id']}/recipe-switch",
            json={"target": "plot"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 组 4：D20 受邀交互
# ---------------------------------------------------------------------------


class TestInvitedInteraction:
    def _session_with_invite(self) -> A1Session:
        session = A1Session(session_id="a1_inv", user_id="u")
        session.creator_primary = "plot"
        session.creator_secondary = "setting_heavy"
        session.recipe_id = "plot"
        session.recipe_modules = list(RECIPES["plot"].module_ids)
        accepted = _apply_worldview_invites(session, ["力量体系"])
        assert accepted == ["力量体系"]
        return session

    def test_switch_preserves_invited_modules(self) -> None:
        session = self._session_with_invite()
        apply_recipe_switch(session, "setting_heavy")
        assert session.invited_modules == ["力量体系"]
        assert "力量体系" in session.recipe_modules

    def test_invited_completes_and_counts_after_switch(self) -> None:
        session = self._session_with_invite()
        apply_recipe_switch(session, "setting_heavy")
        _fill_module(session, "力量体系")
        prog = progress(session)
        invited_section = next(
            s for s in prog["sections"] if s["id"] == "力量体系"
        )
        assert invited_section["done"] is True
        assert invited_section["done_fields"] == invited_section["total_fields"]


# ---------------------------------------------------------------------------
# 组 5：recipe-switch 端点契约（API）
# ---------------------------------------------------------------------------


class TestRecipeSwitchEndpoint:
    def test_switch_applies_and_returns_order(self, client: TestClient) -> None:
        data = _start(
            client, impulse_primary="plot", impulse_secondary="setting_heavy"
        )
        resp = client.post(
            f"/api/a1/file/{data['file_id']}/recipe-switch",
            json={"target": "setting_heavy"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["applied"] == "setting_heavy"
        primary = list(RECIPES["plot"].module_ids)
        secondary = list(RECIPES["setting_heavy"].module_ids)
        joint = primary + [m for m in secondary if m not in primary]
        # 新序 = 次配方成员前移，其余保持联合边界原序（只重排）
        head = [m for m in secondary if m in joint]
        rest = [m for m in joint if m not in secondary]
        assert body["recipe_modules"] == head + rest
        assert body["first_question"]["question"]

    def test_unknown_file_404(self, client: TestClient) -> None:
        resp = client.post(
            "/api/a1/file/nonexistent/recipe-switch",
            json={"target": "plot"},
        )
        assert resp.status_code == 404

    def test_target_not_primary_or_secondary_400(
        self, client: TestClient
    ) -> None:
        data = _start(client, impulse_primary="plot")
        resp = client.post(
            f"/api/a1/file/{data['file_id']}/recipe-switch",
            json={"target": "romance"},
        )
        assert resp.status_code == 400
