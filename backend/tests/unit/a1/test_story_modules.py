"""M2 故事模块族 + 4 故事型配方 — 契约测试（先于实现，TDD RED）。

权威链：
- 计划 modular-restructure TODO 2（M11 角色 6 字段 / M12 剧情 9 字段，
  2026-09-22 重锚定定版；情感线并入 M12 场景化字段 + M10 爱情 preset）。
- 字段文案 = DECISION NEEDED 3 初稿（docs/plans/2026-09-22-jia-module-list-expansion.md §1.1）。
- 配方矩阵 = 详细设计 §3.1（8+2 重锚版）；世界建构子集 = DN6 终审裁决
  D19（产品方 2026-09-25）废除：故事配方 = 纯故事模块（剧情+角色），
  世界建构模块仅设定线使用（推翻初稿 §5.2 前移序子集方案）。
- tier 复用既有层值（DN2）：剧情→历史时间线层(3)、角色→文明与社会层(2)。
- 回归铁律：default 配方逐字节不变（m1_default_snapshot.json 用例不改仍绿）。
"""
from __future__ import annotations

import pytest

from app.domains.creation.a1.guide_engine import (
    A1Session,
    _archive_story_material,
    _fallback_divergent,
    _type_ordered_modules,
    progress,
    sync_position,
)
from app.domains.creation.a1.interviewer import _field_catalog, _progress_summary
from app.domains.creation.a1.tier_map import TIER_MAP, module_tier_coverage
from app.domains.creation.seed.a1_question_tree import (
    MODULES,
    all_subfield_keys,
    get_module,
    get_subfield,
    is_finalizable,
    module_ids,
    subs_for_module,
)
from app.domains.creation.modules.output_modules import OUTPUT_MODULE_IDS
from app.domains.creation.seed.story_modules import STORY_MODULES
from app.domains.creation.shared.module_registry import (
    ANCHOR_BY_TYPE,
    MODULE_POOL,
    RECIPES,
)
from app.domains.creation.shared.module_registry import resolve_recipe_id

STORY_TYPES = ("plot", "romance", "unsure", "character_driven")
M11_ID = "角色"
M12_ID = "剧情"

# M11 弧光方向字段 id = arc_direction（与 M12 走向基调同 id——键空间
# 模块限定不冲突；plan §231 字段名 弧光方向）。
M11_FIELDS = ("identity", "desire", "flaw", "key_relations",
              "arc_direction", "character_visual")
M12_FIELDS = ("opening_event", "core_dilemma", "tension_hole", "lead_chain",
              "secret_layer", "branch_trees", "bound_characters",
              "arc_direction", "scene_hooks")


# ---------------------------------------------------------------------------
# 故事模块数据形态（独立 story_modules.py，不进 MODULES 全集）
# ---------------------------------------------------------------------------


class TestStoryModuleData:
    def test_story_modules_ids_and_labels(self):
        # plan §230-231：M11 角色在前、M12 剧情在后（编号序即清单序）
        assert [m["id"] for m in STORY_MODULES] == [M11_ID, M12_ID]
        assert all(m["label"] == m["id"] for m in STORY_MODULES)

    def test_m11_has_six_product_locked_fields(self):
        m = next(m for m in STORY_MODULES if m["id"] == M11_ID)
        assert tuple(f["id"] for f in m["fields"]) == M11_FIELDS

    def test_m12_has_nine_fields_with_emotional_line_merged(self):
        m = next(m for m in STORY_MODULES if m["id"] == M12_ID)
        assert tuple(f["id"] for f in m["fields"]) == M12_FIELDS

    def test_field_dicts_mirror_question_tree_subfield_shape(self):
        """TypedDict 形态与问卷树 SubField 一致：id/label/question/hint/example。"""
        for m in STORY_MODULES:
            for f in m["fields"]:
                for key in ("id", "label", "question", "hint", "example"):
                    assert isinstance(f.get(key), str) and f[key], (
                        f"{m['id']}.{f.get('id')} missing {key}"
                    )

    def test_story_modules_not_in_worldview_full_set(self):
        """数据落位定死：故事模块不并入 a1_question_tree.MODULES（Momus F2）。"""
        assert M12_ID not in module_ids()
        assert M11_ID not in module_ids()
        assert all(m["id"] not in {x["id"] for x in MODULES} for m in STORY_MODULES)
        # 默认全集键空间零变化
        assert not any(
            k.startswith((f"{M12_ID}.", f"{M11_ID}.")) for k in all_subfield_keys()
        )

    def test_answer_key_space_is_story_first(self):
        assert get_subfield(M12_ID, "core_dilemma")["label"] == "核心抉择"
        assert get_subfield(M11_ID, "desire")["label"] == "欲望"


# ---------------------------------------------------------------------------
# 注册表：入池 + 4 故事型配方
# ---------------------------------------------------------------------------


class TestStoryPoolEntry:
    def test_story_modules_in_pool_with_story_family(self):
        for mid in (M12_ID, M11_ID):
            assert mid in MODULE_POOL
            assert MODULE_POOL[mid].family == "story"

    def test_pool_is_tree_plus_story(self):
        assert set(MODULE_POOL) == (
        set(module_ids()) | {M12_ID, M11_ID} | set(OUTPUT_MODULE_IDS)
    )  # M3：产出模块三件入池

    def test_story_recipes_reference_only_pool_modules(self):
        for ptype in STORY_TYPES:
            for mid in RECIPES[ptype].module_ids:
                assert mid in MODULE_POOL, f"{ptype}: {mid} not in pool"


class TestStoryRecipes:
    """配方矩阵（详细设计 §3.1，8+2 重锚版）。世界建构子集 = DN6 终审
    裁决 D19（产品方 2026-09-25）废除：故事配方 = 纯故事模块（剧情+角色），
    世界建构模块仅设定线使用。"""

    def test_all_story_recipes_are_pure_story_modules(self):
        for ptype in STORY_TYPES:
            assert RECIPES[ptype].module_ids in (
                (M12_ID, M11_ID), (M11_ID, M12_ID),
            ), ptype

    def test_plot_opens_on_story_modules(self):
        mids = RECIPES["plot"].module_ids
        assert mids[0] == M12_ID
        assert M11_ID in mids[:3]

    def test_plot_excludes_faction_bombardment_module(self):
        """验收场景②（翻车证据）：plot 全程不出现 文明与社会（势力类型）。"""
        assert "文明与社会" not in RECIPES["plot"].module_ids

    def test_unsure_excludes_faction_bombardment_module(self):
        assert "文明与社会" not in RECIPES["unsure"].module_ids

    def test_character_driven_leads_with_role_and_story_only(self):
        """D19：角色驱动 = 角色→剧情，无 文明与社会 等世界建构尾随。"""
        mids = RECIPES["character_driven"].module_ids
        assert mids[0] == M11_ID
        assert tuple(mids) == (M11_ID, M12_ID)

    def test_romance_matrix_order_and_emotional_coverage(self):
        """爱情：M11 双人关系卡打头 → M12 情感线（D19 纯故事序）。"""
        mids = RECIPES["romance"].module_ids
        assert mids[0] == M11_ID
        assert tuple(mids) == (M11_ID, M12_ID)
        # 情感线并入 M12 场景化字段（重锚定：无独立情感线模块）
        keys = set(all_subfield_keys(recipe=list(mids)))
        assert {f"{M12_ID}.opening_event", f"{M12_ID}.tension_hole"} <= keys
        assert not any(
            m["id"] == "情感线" for m in STORY_MODULES
        )

    def test_zero_worldview_modules_in_every_story_recipe(self):
        """D19 灵魂契约：世界建构族模块（含原"永远在场"的 M10 设定边界）
        全部退出故事线——边界语义由 romance 合规边界锚点承载。"""
        for ptype in STORY_TYPES:
            mids = RECIPES[ptype].module_ids
            assert not (set(mids) & set(module_ids())), ptype
        assert "合规边界" in RECIPES["romance"].anchor

    def test_story_recipes_dedupe_and_subset_of_pool(self):
        for ptype in STORY_TYPES:
            mids = RECIPES[ptype].module_ids
            assert len(mids) == len(set(mids))
            assert set(mids) <= set(MODULE_POOL)
            assert set(mids) - set(module_ids()) <= {M12_ID, M11_ID}

    def test_entry_subfield_story_first(self):
        assert RECIPES["plot"].entry_subfield == (M12_ID, "core_dilemma")
        # 说不清型 = M12 开场事件单问启动（模块清单拓展文档 §3：S0 直落
        # opening_event——"你的故事从哪一幕开始？"）
        assert RECIPES["unsure"].entry_subfield == (M12_ID, "opening_event")

    def test_anchors_verbatim_from_e1_lite(self):
        """锚点逐字锁定（一个字不许改写；romance §9 合规边界措辞保留）。"""
        for ptype in STORY_TYPES:
            assert RECIPES[ptype].anchor == ANCHOR_BY_TYPE[ptype]
        assert "合规边界" in RECIPES["romance"].anchor

    def test_resolve_recipe_id_unchanged(self):
        assert resolve_recipe_id("plot") == "plot"
        assert resolve_recipe_id("nonsense") == "default"
        assert resolve_recipe_id(None) == "default"


# ---------------------------------------------------------------------------
# tier（DN2：复用既有层值）
# ---------------------------------------------------------------------------


class TestStoryTiers:
    def test_story_modules_reuse_existing_tier_values(self):
        assert TIER_MAP[M12_ID] == TIER_MAP["历史时间线"]  # 3
        assert TIER_MAP[M11_ID] == TIER_MAP["文明与社会"]  # 2

    def test_pool_coverage_still_empty(self):
        assert module_tier_coverage() == []


# ---------------------------------------------------------------------------
# 问卷树门面：故事模块经配方参数可解析（MODULES 全集消费面零扰动）
# ---------------------------------------------------------------------------


class TestFacadeResolvesStoryModules:
    def test_get_module_story(self):
        m = get_module(M12_ID)
        assert m is not None and m["label"] == M12_ID

    def test_subs_for_module_story(self):
        assert len(subs_for_module(M11_ID)) == 6

    def test_all_subfield_keys_recipe_union(self):
        keys = all_subfield_keys(recipe=list(RECIPES["plot"].module_ids))
        assert f"{M12_ID}.opening_event" in keys
        assert f"{M11_ID}.identity" in keys
        assert "文明与社会.势力类型" not in keys

    def test_story_recipe_full_walk_reaches_completed(self):
        s = A1Session(session_id="s", user_id="u", recipe_id="plot",
                      recipe_modules=list(RECIPES["plot"].module_ids))
        visited = []
        for _ in range(80):
            sync_position(s)
            if s.phase == "completed":
                break
            key = f"{s.current_module}.{s.current_subfield}"
            visited.append(key)
            s.answers[key] = "答"
        assert s.phase == "completed"
        expected = set(all_subfield_keys(recipe=s.recipe_modules))
        assert set(visited) == expected

    def test_plot_first_question_is_core_dilemma(self):
        """首问 = 剧情.核心抉择（S0 故事直落，非历史纪元）。"""
        s = A1Session(session_id="s", user_id="u", recipe_id="plot",
                      recipe_modules=list(RECIPES["plot"].module_ids))
        sync_position(s)
        assert (s.current_module, s.current_subfield) == (M12_ID, "core_dilemma")

    def test_plot_walk_never_hits_faction_bombardment(self):
        """验收场景：plot 全走访无任何 文明与社会 字段（势力类型轰炸根治）。"""
        s = A1Session(session_id="s", user_id="u", recipe_id="plot",
                      recipe_modules=list(RECIPES["plot"].module_ids))
        visited = []
        for _ in range(80):
            sync_position(s)
            if s.phase == "completed":
                break
            visited.append(f"{s.current_module}.{s.current_subfield}")
            s.answers[s.current_module + "." + s.current_subfield] = "答"
        assert all(not k.startswith("文明与社会.") for k in visited)

    def test_gate_subset_semantics_story(self):
        """配方内全达标即可 finalize（配方外不适用，DN1）。"""
        answers = {k: "答" for k in all_subfield_keys(
            recipe=list(RECIPES["plot"].module_ids))}
        assert is_finalizable(answers,
                              recipe=list(RECIPES["plot"].module_ids)) is True
        assert is_finalizable(answers) is False  # 全集视角仍不可定稿


# ---------------------------------------------------------------------------
# G5 泄露修复：interviewer prompt 目录/进度按配方渲染
# ---------------------------------------------------------------------------


class TestInterviewerRecipeScoped:
    PLOT_MIDS = list(RECIPES["plot"].module_ids)

    def test_field_catalog_scoped_to_recipe(self):
        catalog = _field_catalog(self.PLOT_MIDS)
        assert f"{M12_ID}.opening_event" in catalog
        assert "文明与社会" not in catalog
        assert "骰子设定" not in catalog

    def test_field_catalog_default_unchanged(self):
        """default（recipe=None）与全集渲染逐字节一致（回归铁律）。"""
        lines = [
            f"{m['id']}.{f['id']}: {f['label']} — {f['question']}"
            for m in MODULES for f in m["fields"]
        ]
        assert _field_catalog() == "\n".join(lines)

    def test_progress_summary_scoped_to_recipe(self):
        summary = _progress_summary({}, self.PLOT_MIDS)
        assert f"{M12_ID}: 0/9" in summary
        assert "文明与社会" not in summary
        assert "骰子设定" not in summary

    def test_progress_summary_default_unchanged(self):
        expected = "  ".join(
            f"{m['id']}: 0/{len(m['fields'])}" for m in MODULES
        )
        assert _progress_summary({}) == expected


# ---------------------------------------------------------------------------
# M0 素材槽迁移：故事会话素材入 M11 字段；存量/default 仍走 character_sketch
# ---------------------------------------------------------------------------


class _MaterialResult:
    """M0 素材归档路径的最小 result 形态（duck-typed）。"""

    def __init__(self, material: str) -> None:
        self.fills = []
        self.story_material = material
        self.guidance_reply = "记下了。"


class TestStoryMaterialRouting:
    def test_story_session_material_routes_into_m11_field(self):
        s = A1Session(session_id="s", user_id="u", recipe_id="plot",
                      recipe_modules=list(RECIPES["plot"].module_ids))
        sync_position(s)
        _archive_story_material(s, _MaterialResult("他见到了一个女孩，似是故人"))
        routed = [k for k, v in s.answers.items()
                  if k.startswith(f"{M11_ID}.") and v]
        assert routed, "story session material must land in an M11 field"
        # 指针不动（素材不是答案，M0 语义保留）
        assert (s.current_module, s.current_subfield) == (M12_ID, "core_dilemma")

    def test_default_session_material_still_goes_to_sketch(self):
        """存量/default 路径逐字节保留（M0 测试语义不迁移）。"""
        s = A1Session(session_id="s", user_id="u")
        _archive_story_material(s, _MaterialResult("一段素材"))
        assert "一段素材" in s.character_sketch
        assert not any(k.startswith(f"{M11_ID}.") for k in s.answers)


# ---------------------------------------------------------------------------
# progress()/发散兜底配方感知（前端进度条消费配方元数据）
# ---------------------------------------------------------------------------


class TestProgressRecipeAware:
    def test_progress_scoped_to_recipe(self):
        s = A1Session(session_id="s", user_id="u", recipe_id="plot",
                      recipe_modules=list(RECIPES["plot"].module_ids))
        p = progress(s)
        ids = [sec["id"] for sec in p["sections"]]
        assert ids == list(RECIPES["plot"].module_ids)
        assert p["total"] == len(ids)
        assert p["finalizable"] == is_finalizable(
            s.answers, recipe=s.recipe_modules)

    def test_progress_default_matches_full_set(self):
        s = A1Session(session_id="s", user_id="u")
        p = progress(s)
        assert [sec["id"] for sec in p["sections"]] == module_ids()
        assert p["total"] == len(MODULES)

    def test_fallback_divergent_targets_recipe_keys(self):
        s = A1Session(session_id="s", user_id="u", recipe_id="plot",
                      recipe_modules=list(RECIPES["plot"].module_ids))
        s.answers[f"{M12_ID}.opening_event"] = "妹妹在雪原失踪"
        from app.domains.creation.a1.interviewer import InterviewFill
        dq = _fallback_divergent(s, [InterviewFill(
            module=M12_ID, subfield="opening_event", value="妹妹在雪原失踪")])
        assert dq is not None
        # 兜底目标只落在配方内字段（不诱导世界建构轰炸）
        story_labels = {f["label"] for f in subs_for_module(M12_ID)}
        assert any(lbl in dq for lbl in story_labels)


class TestTypeOrderedModulesStory:
    def test_story_session_order_is_recipe(self):
        s = A1Session(session_id="s", user_id="u", recipe_id="romance",
                      recipe_modules=list(RECIPES["romance"].module_ids))
        assert _type_ordered_modules(s) == list(RECIPES["romance"].module_ids)
