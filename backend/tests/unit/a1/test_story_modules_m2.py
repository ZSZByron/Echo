# -*- coding: utf-8 -*-
"""M2 故事模块族 + 故事型配方 — 契约测试（TDD RED 先行）。

覆盖面（plan modular-restructure TODO 2 / §231-232 / DN3 DN6 默认）：
1. story_modules.py 数据形态：M11 角色 6 字段 / M12 剧情 9 字段，
   复用 a1_question_tree 的 Module/SubField TypedDict（不重定义）。
2. 注册：MODULE_POOL family="story" 入池；TIER_MAP 复用既有层值（DN2）；
   问卷树门面解析故事模块（get_module/subs_for_module/all_subfield_keys）。
3. 4 故事型配方：纯故事模块（剧情+角色）——DN6 终审裁决 D19
   （产品方 2026-09-25：每分类只调用本族模块，零世界建构问卷）；
    plot 首问 = 剧情.核心抉择；romance 含情感线（M12）+ 边界声明（锚点）。
4. G5 泄露修复：interviewer prompt 目录/进度只渲染配方内字段——
   故事会话零"势力类型"类世界建构字段泄露；_parse 拒配方外 fills。
5. M0 桥接：character_sketch 素材注入角色模块 prompt 块。
6. 上传链故事门（DN6 默认）：故事型会话不走访谈外上传预填路径。
7. 设定型逐字节安全面：MODULES/默认序零改动（本文件冗余断言，
   权威回归在 test_module_registry.TestDefaultByteEquivalence）。
"""
from __future__ import annotations

import types

import pytest
from fastapi.testclient import TestClient

from app.api import a1_routes
from app.domains.creation.a1.guide_engine import A1Session, progress, sync_position
from app.domains.creation.a1.interviewer import RealLLMInterviewer
from app.domains.creation.a1.tier_map import MAX_TIER, MIN_TIER, module_tier_coverage
from app.domains.creation.seed.a1_question_tree import (
    MODULES,
    Module,
    SubField,
    all_subfield_keys,
    get_module,
    is_finalizable,
    module_ids,
    subs_for_module,
    total_subfield_count,
)
from app.domains.creation.seed.story_modules import STORY_MODULES
from app.domains.creation.shared.module_registry import (
    ANCHOR_BY_TYPE,
    MODULE_POOL,
    RECIPES,
    resolve_recipe_id,
)
from app.main import app

STORY_TYPES = ("plot", "romance", "unsure", "character_driven")
FULL_IDS = set(module_ids())


# ---------------------------------------------------------------------------
# 1. story_modules 数据形态
# ---------------------------------------------------------------------------


class TestStoryModuleShape:
    def test_story_modules_are_exactly_role_and_plot(self):
        assert [m["id"] for m in STORY_MODULES] == ["角色", "剧情"]

    def test_role_module_has_six_locked_fields(self):
        role = STORY_MODULES[0]
        assert [f["id"] for f in role["fields"]] == [
            "identity", "desire", "flaw",
            "key_relations", "arc_direction", "character_visual",
        ]

    def test_plot_module_has_nine_locked_fields(self):
        plot = STORY_MODULES[1]
        assert [f["id"] for f in plot["fields"]] == [
            "opening_event", "core_dilemma", "tension_hole", "lead_chain",
            "secret_layer", "branch_trees", "bound_characters",
            "arc_direction", "scene_hooks",
        ]

    def test_typeddict_reuse_not_redefinition(self):
        # 故事模块数据必须满足问卷树 Module TypedDict 形态（结构等价）。
        for m in STORY_MODULES:
            assert set(m.keys()) == {"id", "label", "fields"}
            for f in m["fields"]:
                assert set(f.keys()) >= {"id", "label", "question", "hint"}
        # 类型注解层面：STORY_MODULES 可赋给 list[Module]
        typed: list[Module] = STORY_MODULES
        assert typed is STORY_MODULES
        sf: SubField = STORY_MODULES[0]["fields"][0]
        assert sf["id"] == "identity"

    def test_question_copy_is_story_coach_initial_draft(self):
        # 每个字段有具体问句+提示（初稿质量线：具体、贴剧情不轰炸世界建构）。
        for m in STORY_MODULES:
            for f in m["fields"]:
                assert f["question"].strip(), f"{m['id']}.{f['id']} 缺问句"
                assert f["hint"].strip(), f"{m['id']}.{f['id']} 缺提示"
                assert f.get("example", "").strip(), (
                    f"{m['id']}.{f['id']} 缺示例"
                )

    def test_story_modules_not_merged_into_question_tree_modules(self):
        # F2 裁决（§229）：故事模块独立文件，绝不并入 MODULES。
        assert "角色" not in FULL_IDS and "剧情" not in FULL_IDS
        assert len(MODULES) == 10
        assert total_subfield_count() == 35  # 世界建构 35 字段零改动

    def test_story_module_direct_helpers(self):
        from app.domains.creation.seed.story_modules import (
            get_story_module,
            get_story_subfield,
        )

        assert get_story_module("剧情") is not None
        assert get_story_module("不存在") is None
        sf = get_story_subfield("剧情", "core_dilemma")
        assert sf is not None and sf["label"] == "核心抉择"
        assert get_story_subfield("剧情", "nope") is None
        assert get_story_subfield("不存在", "x") is None


# ---------------------------------------------------------------------------
# 2. 注册：池 + tier + 门面解析
# ---------------------------------------------------------------------------


class TestStoryRegistration:
    def test_pool_contains_story_modules_with_story_family(self):
        assert set(MODULE_POOL) >= FULL_IDS | {"角色", "剧情"}
        for mid in ("角色", "剧情"):
            assert MODULE_POOL[mid].family == "story"
            assert MODULE_POOL[mid].fields is get_module(mid)["fields"]

    def test_worldview_pool_entries_untouched(self):
        for mid in FULL_IDS:
            assert MODULE_POOL[mid].family == "worldview"

    def test_tier_map_reuses_existing_tiers_dn2(self):
        assert module_tier_coverage() == []  # 池内全有 tier
        # 层值闭集 [0,6] 不破；复用映射：剧情→历史时间线同层(3)、角色→文明与社会同层(2)
        from app.domains.creation.a1.tier_map import TIER_MAP

        assert TIER_MAP["剧情"] == TIER_MAP["历史时间线"] == 3
        assert TIER_MAP["角色"] == TIER_MAP["文明与社会"] == 2
        assert MIN_TIER <= TIER_MAP["角色"] <= MAX_TIER
        assert MIN_TIER <= TIER_MAP["剧情"] <= MAX_TIER

    def test_facade_resolves_story_modules(self):
        m = get_module("剧情")
        assert m is not None and m["label"] == "剧情"
        assert len(subs_for_module("角色")) == 6
        keys = all_subfield_keys(recipe=["剧情"])
        assert keys[0] == "剧情.opening_event"
        assert len(keys) == 9

    def test_gate_works_over_story_recipe(self):
        answers = {
            f"剧情.{f['id']}": "答"
            for f in get_module("剧情")["fields"]
        }
        # 只答了 剧情 一个模块（9 字段全真值）→ 单模块配方可定稿，
        # 全集视角不可（配方外不适用语义只看配方内）。
        assert is_finalizable(answers, recipe=["剧情"]) is True
        assert is_finalizable(answers) is False


# ---------------------------------------------------------------------------
# 3. 故事型配方（DN6 初稿）
# ---------------------------------------------------------------------------


class TestStoryRecipes:
    def test_story_recipes_are_pure_story_modules(self):
        """DN6 终审裁决（D19，产品方 2026-09-25）：故事配方 = 纯故事模块
        （剧情+角色），世界建构模块仅设定线使用。"""
        expected = {
            "plot": ("剧情", "角色"),
            "unsure": ("剧情", "角色"),
            "romance": ("角色", "剧情"),
            "character_driven": ("角色", "剧情"),
        }
        for ptype in STORY_TYPES:
            mids = RECIPES[ptype].module_ids
            assert set(mids) == {"剧情", "角色"}, ptype
            assert tuple(mids) == expected[ptype], ptype

    def test_story_recipes_contain_zero_worldview_modules(self):
        """D19 灵魂契约：每个故事型配方的 module_ids 与世界建构族交集为空
        ——故事用户零世界建构问卷（"每个分类只调用本族模块"）。"""
        worldview_ids = set(module_ids())
        for ptype in STORY_TYPES:
            overlap = set(RECIPES[ptype].module_ids) & worldview_ids
            assert not overlap, f"{ptype} 混入世界建构模块: {overlap}"

    def test_plot_recipe_contains_core_dilemma_and_entry(self):
        r = RECIPES["plot"]
        assert "剧情" in r.module_ids
        assert r.entry_subfield == ("剧情", "core_dilemma")

    def test_plot_first_question_is_core_dilemma(self):
        s = A1Session(
            session_id="s", user_id="u", recipe_id="plot",
            recipe_modules=list(RECIPES["plot"].module_ids),
        )
        sync_position(s)
        assert (s.current_module, s.current_subfield) == ("剧情", "core_dilemma")
        sf = get_module("剧情")
        q = next(f for f in sf["fields"] if f["id"] == "core_dilemma")
        assert q["question"].strip()

    def test_romance_recipe_has_love_line_and_boundary_semantics(self):
        r = RECIPES["romance"]
        # 情感线并入 M12 场景化字段：romance 必含 剧情（D19：仅本族两模块）
        assert "剧情" in r.module_ids
        assert "角色" in r.module_ids
        # 边界声明不再靠 M10 模块（D19 世界建构退出故事线），
        # 由 §9 合规边界锚点措辞承载
        assert "合规边界" in r.anchor

    def test_unsure_recipe_opens_with_single_question_startup(self):
        r = RECIPES["unsure"]
        assert "剧情" in r.module_ids
        assert r.entry_subfield == ("剧情", "opening_event")

    def test_character_driven_recipe_leads_with_role(self):
        r = RECIPES["character_driven"]
        assert r.module_ids[0] == "角色"
        assert "剧情" in r.module_ids

    def test_story_anchors_unchanged_from_e1_lite(self):
        for ptype in STORY_TYPES:
            assert RECIPES[ptype].anchor == ANCHOR_BY_TYPE[ptype]

    def test_default_recipe_untouched(self):
        assert RECIPES["default"].module_ids == tuple(module_ids())
        assert RECIPES["default"].entry_subfield is None
        assert RECIPES["default"].anchor == ""
        # 非故事型配方不受影响
        assert RECIPES["philosophy"].module_ids[0] == "世界本体"
        assert set(RECIPES["philosophy"].module_ids) == FULL_IDS

    def test_resolve_recipe_id_story_types(self):
        for ptype in STORY_TYPES:
            assert resolve_recipe_id(ptype) == ptype
        assert resolve_recipe_id("nope") == "default"
        assert resolve_recipe_id("") == "default"


# ---------------------------------------------------------------------------
# 4. G5 泄露修复
# ---------------------------------------------------------------------------


class TestG5PromptNoLeak:
    """故事会话 prompt 零配方外字段（翻车场景：势力类型轰炸）。"""

    def _plot_recipe(self) -> list[str]:
        return list(RECIPES["plot"].module_ids)

    def test_field_catalog_recipe_scoped(self):
        from app.domains.creation.a1.interviewer import _field_catalog

        catalog = _field_catalog(self._plot_recipe())
        assert "剧情.core_dilemma" in catalog
        assert "角色.identity" in catalog  # plot 配方含角色模块
        # 配方外世界建构字段零泄露
        assert "文明与社会.faction_type" not in catalog
        assert "势力类型" not in catalog
        assert "IP定位" not in catalog

    def test_field_catalog_default_unchanged(self):
        from app.domains.creation.a1.interviewer import _field_catalog

        default_catalog = _field_catalog()
        assert "IP定位.name" in default_catalog
        assert "势力类型" in default_catalog  # 全集目录仍含（default 会话合法）
        assert "剧情.core_dilemma" not in default_catalog

    def test_progress_summary_recipe_scoped(self):
        from app.domains.creation.a1.interviewer import _progress_summary

        summary = _progress_summary({}, recipe=self._plot_recipe())
        assert "剧情: 0/9" in summary
        # D19：世界建构模块彻底退出故事线（进度摘要零世界建构）
        assert "历史时间线" not in summary
        assert "世界本体" not in summary and "设定边界" not in summary
        assert "IP定位" not in summary and "势力类型" not in summary

    def test_story_session_prompt_has_zero_out_of_recipe_fields(self):
        iv = RealLLMInterviewer(provider=None)
        session = types.SimpleNamespace(
            session_id="s1",
            current_module="剧情",
            current_subfield="core_dilemma",
            answers={},
            seed_name="", seed_genre="", seed_description="",
            creator_primary="plot",
            recipe_modules=self._plot_recipe(),
            recipe_id="plot",
            character_sketch="",
        )
        module = get_module("剧情")
        subfield = next(
            f for f in module["fields"] if f["id"] == "core_dilemma"
        )
        prompt = iv._build_prompt(module, subfield, session)
        # 首问 = 故事问题
        assert "核心抉择" in prompt or "core_dilemma" in prompt
        # 配方外世界建构模块零泄露（逐模块目录行；D19 后 plot 配方仅
        # 剧情/角色——全部世界建构字段不得出现）
        for leak in (
            "IP定位.name", "文明与社会.faction_type", "势力类型",
            "骰子设定.probability", "玩法设计DNA.player_role",
            "地理空间.terrain", "历史时间线.time_span",
            "世界本体.reality_rule", "设定边界.immutable_core",
        ):
            assert leak not in prompt, f"配方外字段泄露：{leak}"
        # 进度摘要同样只渲染配方内
        assert "剧情: 0/9" in prompt

    def test_default_session_prompt_byte_identical_catalog(self):
        iv = RealLLMInterviewer(provider=None)
        session = types.SimpleNamespace(
            session_id="s1",
            current_module="IP定位",
            current_subfield="name",
            answers={},
            seed_name="", seed_genre="", seed_description="",
            creator_primary="",
            recipe_modules=[],   # default：空 = 全集
            recipe_id="default",
            character_sketch="",
        )
        module = get_module("IP定位")
        subfield = module["fields"][0]
        prompt = iv._build_prompt(module, subfield, session)
        assert "势力类型" in prompt  # 全集目录保留
        assert "IP定位.name: 名称与概念" in prompt

    def test_parse_drops_out_of_recipe_fills(self):
        iv = RealLLMInterviewer(provider=None)
        recipe = self._plot_recipe()
        valid = set(all_subfield_keys(recipe=recipe))
        raw = {
            "fills": [
                {"module": "剧情", "subfield": "core_dilemma", "value": "救师父还是守城"},
                {"module": "文明与社会", "subfield": "faction_type", "value": "神权"},
                {"module": "剧情", "subfield": "not_a_field", "value": "x"},
            ],
            "guidance_reply": "已记录。",
        }
        result = iv._parse(raw, "t", valid_keys=valid)
        assert [(f.module, f.subfield) for f in result.fills] == [
            ("剧情", "core_dilemma")
        ]

    def test_parse_default_still_full_set(self):
        iv = RealLLMInterviewer(provider=None)
        raw = {
            "fills": [
                {"module": "文明与社会", "subfield": "faction_type", "value": "神权"},
            ],
            "guidance_reply": "已记录。",
        }
        result = iv._parse(raw, "t")
        assert len(result.fills) == 1  # default 全集视角合法


# ---------------------------------------------------------------------------
# 5. 会话进度配方化（前端进度条数据面）
# ---------------------------------------------------------------------------


class TestSessionProgressRecipeScoped:
    def test_progress_only_contains_recipe_modules(self):
        s = A1Session(
            session_id="s", user_id="u", recipe_id="plot",
            recipe_modules=list(RECIPES["plot"].module_ids),
            answers={"剧情.core_dilemma": "救师父还是守城"},
        )
        p = progress(s)
        assert [sec["id"] for sec in p["sections"]] == list(
            RECIPES["plot"].module_ids
        )
        assert p["total"] == len(RECIPES["plot"].module_ids)
        plot_sec = next(sec for sec in p["sections"] if sec["id"] == "剧情")
        assert plot_sec["done_fields"] == 1
        assert plot_sec["total_fields"] == 9

    def test_progress_default_unchanged(self):
        s = A1Session(session_id="s", user_id="u")
        p = progress(s)
        assert p["total"] == 10
        assert [sec["id"] for sec in p["sections"]] == module_ids()


# ---------------------------------------------------------------------------
# 6. M0 素材槽 → M11 角色模块桥接
# ---------------------------------------------------------------------------


class TestCharacterSketchBridge:
    def _session(self, **over) -> types.SimpleNamespace:
        base = dict(
            session_id="s1",
            current_module="角色",
            current_subfield="identity",
            answers={},
            seed_name="", seed_genre="", seed_description="",
            creator_primary="character_driven",
            recipe_modules=list(RECIPES["character_driven"].module_ids),
            recipe_id="character_driven",
            character_sketch="主角阿鸢：摆渡人，白天渡人夜里传密信",
        )
        base.update(over)
        return types.SimpleNamespace(**base)

    def test_sketch_injected_into_role_module_prompt(self):
        iv = RealLLMInterviewer(provider=None)
        module = get_module("角色")
        subfield = module["fields"][0]
        prompt = iv._build_prompt(module, subfield, self._session())
        assert "摆渡人" in prompt  # 归档素材可见
        assert "角色素材" in prompt  # 桥接规则块

    def test_no_injection_when_sketch_empty_or_other_module(self):
        iv = RealLLMInterviewer(provider=None)
        module = get_module("角色")
        subfield = module["fields"][0]
        prompt_empty = iv._build_prompt(
            module, subfield, self._session(character_sketch="")
        )
        assert "角色素材" not in prompt_empty
        plot_module = get_module("剧情")
        plot_sub = plot_module["fields"][0]
        prompt_other = iv._build_prompt(
            plot_module, plot_sub, self._session()
        )
        assert "角色素材" not in prompt_other

    def test_default_session_no_injection(self):
        iv = RealLLMInterviewer(provider=None)
        session = self._session(
            current_module="IP定位", current_subfield="name",
            creator_primary="", recipe_modules=[], recipe_id="default",
        )
        module = get_module("IP定位")
        prompt = iv._build_prompt(module, module["fields"][0], session)
        assert "角色素材" not in prompt


# ---------------------------------------------------------------------------
# 7. 上传链故事门（DN6 默认：故事型走访谈，不暴露上传预填）
# ---------------------------------------------------------------------------


class TestUploadStoryGate:
    """上传链是"新会话"入口（UploadRequest 无 session_id）——DN6 默认：
    故事型冲动不暴露上传预填路径；不传 impulse 行为逐字节不变（additive）。"""

    @pytest.fixture()
    def client(self) -> TestClient:
        return TestClient(app)

    def test_upload_rejected_for_story_impulse(self, client):
        resp = client.post(
            "/api/a1/upload",
            json={
                "user_id": "u_gate", "filename": "a.txt",
                "content": "世界观文本", "impulse_primary": "plot",
            },
        )
        assert resp.status_code == 409

    def test_upload_path_intact_without_impulse(self, client):
        resp = client.post(
            "/api/a1/upload",
            json={"user_id": "u_gate", "filename": "no_such.txt", "content": ""},
        )
        # 非故事门不拦（422 文本校验等既有行为——门只针对故事型冲动）
        assert resp.status_code != 409

    def test_start_response_exposes_recipe_id(self, client):
        resp = client.post(
            "/api/a1/session/start",
            json={"user_id": "u_gate", "custom_idea": "测试", "impulse_primary": "plot"},
        )
        assert resp.status_code == 200
        assert resp.json()["recipe_id"] == "plot"
