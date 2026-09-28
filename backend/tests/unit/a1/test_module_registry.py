"""M1 模块注册表底座 — 契约测试（先于实现，TDD RED）。

覆盖面：
1. RECIPES 注册表：default + 冲动型全覆盖，Recipe 六字段形态锁定。
2. E1-Lite 三数据字典迁入 + 原位置 re-export 兼容。
3. 门禁子集语义（DN1 默认）：配方外模块 = 不适用，missing 只列配方内。
4. graphify 锚点校验配方并集参数化（call-chain plumbing）。
5. legacy 会话零迁移 → default 配方（G3）。
6. start_session 按 creator_primary 落定配方。
7. 设定型逐字节回归铁律（default 配方 vs m1_default_snapshot.json 基线）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import a1_routes
from app.domains.creation.a1.guide_engine import (
    A1Session,
    TYPE_ENTRY_SUBFIELD,
    TYPE_MODULE_PRIORITY,
    _type_ordered_modules,
    sync_position,
)
from app.domains.creation.a1.graphify import (
    AnchorEntries,
    GraphifyResult,
    apply_graphify_validation,
    validate_anchors,
)
from app.domains.creation.a1.tier_map import module_tier_coverage
from app.domains.creation.a1.worldview_upload import _schema_catalog
from app.domains.creation.shared.module_registry import (
    MODULE_POOL,
    RECIPES,
    Recipe,
)
from app.domains.creation.seed.a1_question_tree import (
    all_subfield_keys,
    get_module,
    is_finalizable,
    module_ids,
)
from app.main import app

SNAPSHOT_PATH = Path(__file__).parent / "baseline" / "m1_default_snapshot.json"

STORY_TYPES = frozenset({"plot", "romance", "unsure", "character_driven"})
IMPULSE_TYPES = frozenset({
    "setting_heavy", "character_driven", "plot", "philosophy",
    "exploration", "romance", "nostalgia", "healing", "unsure",
})


def _snapshot() -> dict:
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


class TestRegistryShape:
    """注册表形态：default + 冲动型全覆盖，Recipe 字段逐字锁定。"""

    def test_recipes_cover_default_and_all_impulse_types(self):
        assert "default" in RECIPES
        assert IMPULSE_TYPES <= set(RECIPES), (
            f"missing impulse recipes: {sorted(IMPULSE_TYPES - set(RECIPES))}"
        )

    def test_recipe_has_six_locked_fields(self):
        r = RECIPES["default"]
        for field in ("id", "impulse_type", "module_ids", "entry_subfield",
                      "anchor", "ai_fill_policy"):
            assert hasattr(r, field), f"Recipe missing field: {field}"
        assert isinstance(r, Recipe)

    def test_default_recipe_is_full_set_in_tree_order(self):
        assert list(RECIPES["default"].module_ids) == module_ids()

    def test_story_recipes_are_ordered_subsets_of_pool(self):
        """M2 → D19：故事四型 = 纯故事模块（剧情+角色，池内有序子集），
        世界建构模块仅设定线使用（DN6 终审裁决 2026-09-25）。"""
        pool = set(MODULE_POOL)
        for ptype in STORY_TYPES:
            r = RECIPES[ptype]
            mids = list(r.module_ids)
            assert set(mids) <= pool, f"{ptype} recipe must be a pool subset"
            assert len(mids) == len(set(mids)), f"{ptype} recipe must dedupe"
            assert "剧情" in mids and "角色" in mids, ptype
            # D19 灵魂契约：故事配方零世界建构模块
            assert not (set(mids) & set(module_ids())), ptype

    def test_recipe_entry_and_anchor(self):
        """M2：故事型入口 = 剧情.核心抉择（plot 验收 §239）/ 开场事件
        （unsure 单问启动，模块清单拓展文档 §3）。"""
        assert RECIPES["plot"].entry_subfield == ("剧情", "core_dilemma")
        assert RECIPES["unsure"].entry_subfield == ("剧情", "opening_event")
        assert RECIPES["default"].entry_subfield is None
        assert RECIPES["plot"].anchor == TYPE_ANCHOR_PLOT
        assert RECIPES["healing"].anchor != ""  # nostalgia/healing 锚点保留
        assert RECIPES["nostalgia"].anchor != ""

    def test_module_pool_covers_tree_story_output_and_tiers(self):
        """M3：池 = 问卷树 10 模块 + 剧情/角色 + 产出三件（family=output）。"""
        from app.domains.creation.modules.output_modules import (
            OUTPUT_MODULE_IDS,
        )

        assert set(MODULE_POOL) == (
            set(module_ids()) | {"剧情", "角色"} | set(OUTPUT_MODULE_IDS)
        )
        assert module_tier_coverage() == []

    def test_e1_lite_dicts_reexported_from_registry(self):
        from app.domains.creation.a1 import interviewer
        from app.domains.creation.shared import module_registry as reg

        # 数据迁入注册表，原位置 re-export 兼容（同一对象）
        assert interviewer.ANCHOR_BY_TYPE is reg.ANCHOR_BY_TYPE
        assert TYPE_MODULE_PRIORITY is reg.TYPE_MODULE_PRIORITY
        assert TYPE_ENTRY_SUBFIELD is reg.TYPE_ENTRY_SUBFIELD


TYPE_ANCHOR_PLOT = '节奏导向："这个设定会制造什么事件？"'


class TestGateSubsetSemantics:
    """DN1 默认：配方外模块 = 不适用；门禁/missing 只看配方内。"""

    def test_is_finalizable_accepts_recipe_param(self):
        story = ["历史时间线", "文明与社会", "世界本体"]
        answers = {}
        # 三个配方内模块全部过半，配方外（IP定位 等）全空
        for mid in story:
            m = get_module(mid)
            for f in m["fields"]:
                answers[f"{mid}.{f['id']}"] = "x"
        assert is_finalizable(answers, recipe=story) is True
        assert is_finalizable(answers) is False  # 全集视角仍不可定稿

    def test_session_recipe_modules_drive_ordering(self):
        s = A1Session(session_id="s", user_id="u",
                      recipe_id="plot",
                      recipe_modules=list(RECIPES["plot"].module_ids))
        assert _type_ordered_modules(s) == list(RECIPES["plot"].module_ids)
        sync_position(s)
        # 首问 = 配方首模块入口字段（M2 entry swap: 剧情.核心抉择 前置）
        assert s.current_module == "剧情"
        assert s.current_subfield == "core_dilemma"

    def test_story_recipe_full_walk_reaches_completed(self):
        story = ["历史时间线", "文明与社会", "世界本体"]
        s = A1Session(session_id="s", user_id="u",
                      recipe_id="plot", recipe_modules=list(story))
        visited = []
        for _ in range(40):
            sync_position(s)
            if s.phase == "completed":
                break
            key = f"{s.current_module}.{s.current_subfield}"
            visited.append(key)
            s.answers[key] = "答"
        assert s.phase == "completed"
        assert sorted(visited) == sorted(
            k for k in all_subfield_keys() if k.split(".", 1)[0] in story
        )

    def test_finalize_gate_recipe_scoped(self):
        """finalize 门禁遍历配方集——配方外模块不进 missing_sections。"""
        story = ["历史时间线", "文明与社会", "世界本体"]
        s = A1Session(session_id="s", user_id="u",
                      recipe_id="plot", recipe_modules=list(story))
        mids = s.recipe_modules or module_ids()
        missing = [m for m in mids if not _over_half(m, s.answers)]
        assert missing == story  # 全空时 missing 只含配方内模块
        for mid in story:
            for f in get_module(mid)["fields"]:
                s.answers[f"{mid}.{f['id']}"] = "x"
        missing2 = [m for m in mids if not _over_half(m, s.answers)]
        assert missing2 == []


def _over_half(mid: str, answers: dict) -> bool:
    from app.domains.creation.seed.a1_question_tree import is_module_over_half
    return is_module_over_half(mid, answers)


class TestGraphifyRecipeUnion:
    """锚点合法性 = 配方并集（经调用链签名传入；默认仍全集）。"""

    @staticmethod
    def _result_with(anchor: str) -> GraphifyResult:
        return GraphifyResult(
            module_summaries={},
            entries=[AnchorEntries(
                anchor=anchor,
                items=[{"title": "条目", "summary": "内容"}],
            )],
            edges=[],
            constraint_fields={},
            open_questions=[],
        )

    def test_default_still_full_set(self):
        warnings = validate_anchors(self._result_with("IP定位.name"))
        assert warnings == []

    def test_recipe_union_accepts_recipe_anchor_and_drops_outsiders(self):
        legal = {"IP定位.name"}  # 模拟 plot 配方并集（缩小后的合法集）
        assert validate_anchors(
            self._result_with("设定边界.immutable_core"), legal_anchors=legal
        ) != []  # 配方外锚点被判非法
        assert validate_anchors(
            self._result_with("IP定位.name"), legal_anchors=legal
        ) == []

    def test_apply_validation_plumbs_legal_anchors(self):
        legal = {"IP定位.name"}
        result = apply_graphify_validation(
            self._result_with("设定边界.immutable_core"), legal_anchors=legal
        )
        assert result.entries == []  # 配方外锚点整组丢弃
        assert any("非法锚点" in w for w in result.warnings)


class TestLegacySessionCompat:
    """G3：存量会话（无配方字段）零迁移 → default 配方，行为零变化。"""

    def test_model_defaults(self):
        s = A1Session.model_validate({"session_id": "s", "user_id": "u"})
        assert s.recipe_id == "default"
        assert s.recipe_modules == []

    def test_legacy_order_is_tree_order(self):
        s = A1Session(session_id="s", user_id="u", creator_primary="philosophy")
        # 无 recipe_modules（存量形态）→ creator_primary 路径保序兼容
        # （philosophy 非故事型 = 全集置换，与 E1-Lite 行为一致）
        assert _type_ordered_modules(s) == list(RECIPES["philosophy"].module_ids)
        assert sorted(_type_ordered_modules(s)) == sorted(module_ids())

    def test_store_roundtrip_keeps_recipe_fields(self):
        s = A1Session(session_id="s", user_id="u",
                      recipe_id="plot", recipe_modules=["历史时间线"])
        restored = A1Session.model_validate(s.model_dump())
        assert restored.recipe_id == "plot"
        assert restored.recipe_modules == ["历史时间线"]


class TestStartSessionRecipeResolution:
    """start_session 按 creator_primary 落定配方。"""

    @pytest.fixture()
    def client(self) -> TestClient:
        return TestClient(app)

    def _start(self, client: TestClient, impulse: str | None) -> A1Session:
        body: dict = {"user_id": "u_recipe", "custom_idea": "测试世界"}
        if impulse is not None:
            body["impulse_primary"] = impulse
        resp = client.post("/api/a1/session/start", json=body)
        assert resp.status_code == 200
        return a1_routes._SESSIONS[resp.json()["session_id"]]

    def test_plot_session_gets_story_recipe(self, client):
        s = self._start(client, "plot")
        assert s.recipe_id == "plot"
        assert s.recipe_modules == list(RECIPES["plot"].module_ids)
        assert set(s.recipe_modules) <= set(MODULE_POOL)
        assert "剧情" in s.recipe_modules and "角色" in s.recipe_modules

    def test_unknown_impulse_falls_back_to_default(self, client):
        s = self._start(client, "definitely_not_a_type")
        assert s.recipe_id == "default"
        assert s.recipe_modules == []

    def test_no_impulse_gets_default(self, client):
        s = self._start(client, None)
        assert s.recipe_id == "default"
        assert s.recipe_modules == []


class TestDefaultByteEquivalence:
    """回归铁律：default 配方全链路 vs 基线快照逐字节一致。"""

    def test_module_ids_and_keys(self):
        snap = _snapshot()
        assert module_ids() == snap["module_ids"]
        assert all_subfield_keys() == snap["all_subfield_keys"]

    def test_build_sections_structure_unchanged(self):
        from app.api.a1_routes import _build_sections
        snap = _snapshot()
        s = A1Session(session_id="s", user_id="u",
                      answers={"IP定位.name": "星陨大陆",
                               "历史时间线.main_plot": "剑补天"})
        assert [sec["id"] for sec in _build_sections(s)] == snap["build_sections_ids"]

    def test_schema_catalog_text_unchanged(self):
        snap = _snapshot()
        assert _schema_catalog() == snap["schema_catalog"]

    def test_default_walk_order_unchanged(self):
        snap = _snapshot()
        s = A1Session(session_id="s", user_id="u")
        walk = []
        for _ in range(60):
            sync_position(s)
            if s.phase == "completed":
                break
            key = f"{s.current_module}.{s.current_subfield}"
            walk.append(key)
            s.answers[key] = "答"
        assert walk == snap["default_walk_order"]

    def test_graphify_prompt_deterministic_surface_unchanged(self):
        import hashlib
        from app.domains.creation.a1.graphify import build_graphify_prompt
        snap = _snapshot()
        answers = {"IP定位.name": "星陨大陆", "历史时间线.main_plot": "剑补天"}
        digest = hashlib.sha256(
            build_graphify_prompt(answers).encode("utf-8")
        ).hexdigest()
        assert digest == snap["graphify_prompt_sha256"]

    def test_gate_results_unchanged(self):
        snap = _snapshot()
        from app.domains.creation.seed.a1_question_tree import is_module_over_half
        missing = [m for m in module_ids() if not is_module_over_half(m, {})]
        assert missing == snap["gate_missing_all_empty"]
        assert is_finalizable({}) == snap["is_finalizable_empty"]
