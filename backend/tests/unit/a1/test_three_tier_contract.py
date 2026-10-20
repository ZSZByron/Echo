# -*- coding: utf-8 -*-
"""波次二 T1 契约锁红测——三级树结构大锤的验收标准（先红后绿）。

本文件是 T2 数据层落库（.sisyphus/plans/a1-wave2-structure-overhaul.md 任务 2）
的契约面，只锁"结构应满足的契约"，不锁实现细节。2026-10-12 十九项拍板闭卷。

四个契约：
1. ``test_three_tier_id_superset``  —— 旧 id 宇宙零改名零删除（label 改 id 不动）
2. ``test_recipe_entries_survive``  —— 九型配方入口全部解析到新树存活节点
3. ``test_gate_counts_recipe_only`` —— 门禁只数配方引用字段，92-L3 注册表
   扩入后 missing_sections 与 35 字段时代一致（D19 边界，Metis CRITICAL#2）
4. ``test_a1session_additive_enum`` —— A1Session additive 三枚新字段
   （material_pool / list_thread_key / list_thread_turns），默认空/零

T2 契约面（本测试对 T2 落库形态的唯一假设）：

- 三级树数据以 ``THREE_TIER_TREE`` 名字暴露在
  ``app.domains.creation.seed.story_modules`` 或
  ``app.domains.creation.seed.a1_question_tree``（二选一，统一树）。
- 形态：L1×7 顶层的 list[dict]，每个 L1 节点::

      {"id": str, "label": str, "l2": [ {"id": str, "label": str,
        "l3": [ {"id": str, ...}, ... ] }, ... ] }

  其中 15 个升格 L2 沿用现行字段 id、35 个平移 L3 沿用现行字段 id
  （⑤稿 §8.2/§8.3；旧 50 id 闭集见
  ``.sisyphus/evidence/wave2-t1-id-universe.txt``）。

红线（与本测试配套）：本文件存在期间生产代码零改动（T1 纯验证）。
"""
from __future__ import annotations

from typing import Any

from app.domains.creation.a1.guide_engine import (
    A1Session,
    core_recipe_modules,
)
from app.domains.creation.seed import a1_question_tree as qt
from app.domains.creation.seed import story_modules as sm
from app.domains.creation.seed.a1_question_tree import is_module_over_half
from app.domains.creation.shared.module_registry import MODULE_POOL, RECIPES

# ---------------------------------------------------------------------------
# 旧 id 宇宙（升级前基线；快照证据 wave2-t1-id-universe.txt，2026-10-11）
# ---------------------------------------------------------------------------

# 冻结闭集（50 字段槽位 / 49 唯一 id：arc_direction 双属角色/剧情）——
# 逐字对照 evidence 第 22 行 sorted set 抄录。T2 施工改动源文件时此集
# 不随之缩水，超集契约的保护力来自这里。
_FROZEN_OLD_IDS: frozenset[str] = frozenset({
    "acquire", "ai_fill", "arc_direction", "architecture",
    "bound_characters", "branch_trees", "character_visual", "check_mode",
    "concept", "conflict", "core_dilemma", "core_experience", "core_value",
    "cost", "cost_mech", "desire", "dice_count", "economy", "existence",
    "faction_type", "flaw", "growth", "growth_end", "identity",
    "immutable_core", "key_nodes", "key_relations", "keywords", "lead_chain",
    "main_action", "main_plot", "material", "mechanism", "name",
    "opening_event", "origin", "player_role", "probability", "reality_rule",
    "scene_hooks", "secret_layer", "source", "special_geo", "success_check",
    "tension_hole", "terrain", "time_span", "vertical", "world_type",
})

# 第二重校验用：运行时从现行源文件派生（T1 时与冻结集逐字一致）。
_RUNTIME_OLD_IDS: frozenset[str] = frozenset(
    f["id"] for m in (*qt.MODULES, *sm.STORY_MODULES) for f in m["fields"]
)

# 兼容旧引用名：契约断言一律以冻结闭集为基线。
_OLD_IDS = _FROZEN_OLD_IDS


def _load_three_tier_tree() -> list[dict[str, Any]]:
    """T2 契约面装载：统一三级树（落库位置二选一见模块 docstring）。"""
    tree = getattr(sm, "THREE_TIER_TREE", None) or getattr(
        qt, "THREE_TIER_TREE", None
    )
    assert tree is not None, (
        "T2 契约面缺失：THREE_TIER_TREE（L1×7→L2×26→L3×92 三级树数据）"
        "尚未落库——见 a1-wave2-structure-overhaul.md 任务 2"
    )
    return tree


def _tree_ids(tree: list[dict[str, Any]]) -> set[str]:
    """收集三级树全量节点 id（L2 ∪ L3——旧 id 可存活于任一层）。"""
    ids: set[str] = set()
    for l1 in tree:
        for l2 in l1.get("l2", []):
            ids.add(l2["id"])
            for l3 in l2.get("l3", []):
                ids.add(l3["id"])
    return ids


# ---------------------------------------------------------------------------
# 1. id 宇宙严格超集：旧 50 id 零改名零删除
# ---------------------------------------------------------------------------


def test_three_tier_id_superset() -> None:
    # 第二重校验（T2 源文件改名防护）：现行源文件派生 id 必须 ⊆ 冻结闭集
    # ——改名 → 新 id 不在冻结集即抓；删除 → 由既有测试/配方存活测试兜底。
    stray = sorted(_RUNTIME_OLD_IDS - _FROZEN_OLD_IDS)
    assert not stray, (
        "现行源文件出现冻结闭集之外的 id（疑似 T2 擅自改名）: %s" % stray
    )
    tree = _load_three_tier_tree()
    new_ids = _tree_ids(tree)
    missing = sorted(_OLD_IDS - new_ids)
    assert not missing, (
        "旧 id 在新树中缺失（零改名零删除契约被破坏）: %s" % missing
    )
    # 结构完备：L1×7 顶层数量（⑤稿 §8.3 合计行）
    assert len(tree) == 7, "L1 大类应为 7，实得 %d" % len(tree)


# ---------------------------------------------------------------------------
# 2. 九型配方入口全部存活（⑤稿 §8.2 配方入口语义）
# ---------------------------------------------------------------------------

# ⑤稿 §8.2 挂点下沉表（label → 沿用 id；recipe → (L2 id, L3 id)）：
# plot→剧情.核心抉择 / unsure→剧情.开场事件 / romance→角色.关键关系 /
# character_driven→角色.身份（现行 entry_subfield 的字段 id 逐字不动）。
_ENTRY_L2_BY_TYPE: dict[str, str] = {
    "plot": "core_dilemma",
    "unsure": "opening_event",
    "romance": "key_relations",
    "character_driven": "identity",
}


def test_recipe_entries_survive() -> None:
    tree = _load_three_tier_tree()
    new_ids = _tree_ids(tree)
    # L2 层 id → 该 L2 子树内 L3 id 集合（入口必须解析到存在的 L2 节点下）
    l3_by_l2: dict[str, set[str]] = {}
    for l1 in tree:
        for l2 in l1.get("l2", []):
            l3_by_l2[l2["id"]] = {l3["id"] for l3 in l2.get("l3", [])}

    for ptype in sorted(RECIPES):
        recipe = RECIPES[ptype]
        # 2a. 配方引用的模块全部仍在模块池（路由面零漂移）——九型全查
        for mid in recipe.module_ids:
            assert mid, "配方 %s 出现空模块 id" % ptype
        # 2b. 入口子字段在新树中存活
        if recipe.entry_subfield is None:
            continue
        entry_mid, entry_fid = recipe.entry_subfield
        assert entry_fid in new_ids, (
            "配方 %s 入口字段 %s 在新树中不存在" % (ptype, entry_fid)
        )
        # 2c. 故事四型入口挂⑤稿指定 L2 节点之下
        if ptype in _ENTRY_L2_BY_TYPE:
            want_l2 = _ENTRY_L2_BY_TYPE[ptype]
            assert want_l2 in l3_by_l2, (
                "配方 %s 入口 L2 %s 不在新树" % (ptype, want_l2)
            )
            assert entry_fid in l3_by_l2[want_l2] or entry_fid == want_l2, (
                "配方 %s 入口 %s 未挂到 L2 %s 下" % (ptype, entry_fid, want_l2)
            )


# ---------------------------------------------------------------------------
# 3. 门禁口径护栏：只数配方引用字段（D19 边界）
# ---------------------------------------------------------------------------


def _answers_all_of(module_ids: list[str]) -> dict[str, str]:
    """把给定模块的全部字段填上真值（现行 50 字段宇宙 = "35 字段时代"口径）。"""
    pool_fields = {m.id: [f["id"] for f in m.fields] for m in MODULE_POOL.values()}
    answers: dict[str, str] = {}
    for mid in module_ids:
        for fid in pool_fields.get(mid, []):
            answers["%s.%s" % (mid, fid)] = "真值答案"
    return answers


def test_gate_counts_recipe_only() -> None:
    # T2 落库后本行取到 92-L3 注册表（RED 阶段断言缺失树即失败——
    # 门禁护栏测试必须在注册表扩入后的世界里成立）。
    tree = _load_three_tier_tree()
    tree_ids = _tree_ids(tree)
    assert len(tree_ids) >= len(_OLD_IDS), "新树 id 宇宙缩水"

    # 场景 A：plot 旧配方会话（recipe_modules 非空），剧情答满、角色全空、
    # 其余全树字段也答满（模拟 92-L3 注册表全量在册）。
    # 契约：missing_sections 恰为 ["角色"]——门禁只走配方（剧情+角色），
    # 注册表扩入不改变计数（多答的字段既不救场也不添乱）。
    plot_session = A1Session(
        session_id="t1-gate-plot",
        user_id="t1",
        recipe_id="plot",
        recipe_modules=["剧情", "角色"],
    )
    # 全注册表答满（模拟 92-L3 全量在册），唯独角色模块一字未答——
    # 多答字段既不救场也不添乱。
    plot_answers = _answers_all_of(
        [mid for mid in MODULE_POOL if mid != "角色"]
    )
    core = core_recipe_modules(plot_session)
    assert core == ["剧情", "角色"], (
        "门禁视角应恒等于配方模块序（D19 边界），实得 %s" % core
    )
    missing = [
        mid for mid in core
        if not is_module_over_half(mid, plot_answers)
    ]
    assert missing == ["角色"], (
        "92-L3 注册表下旧配方 missing_sections 必须与 35 字段时代一致："
        "期望 ['角色']，实得 %s" % missing
    )

    # 场景 B：default 存量会话（recipe_modules=[] → 全集 walk），35 字段
    # 全部答满 → missing_sections 为空（升级前后逐字节一致）。
    default_session = A1Session(session_id="t1-gate-default", user_id="t1")
    assert default_session.recipe_modules == []
    default_answers = _answers_all_of([m["id"] for m in qt.MODULES])
    default_missing = [
        mid for mid in core_recipe_modules(default_session)
        if not is_module_over_half(mid, default_answers)
    ]
    assert default_missing == [], (
        "存量 default 会话全答满后 missing_sections 应为空，实得 %s"
        % default_missing
    )


# ---------------------------------------------------------------------------
# 4. A1Session additive 字段枚举：恰三枚，默认空/零
# ---------------------------------------------------------------------------

# T1 基线快照（2026-10-11 实测 43 枚，证据 wave2-t1-numbers.md §4）。
_A1SESSION_OLD_FIELDS = frozenset({
    "session_id", "user_id", "ip_code", "current_module", "current_subfield",
    "answers", "phase", "seed_name", "seed_genre", "seed_description",
    "creator_primary", "creator_secondary", "creator_profile_source",
    "recipe_id", "recipe_modules", "stall_subfield", "stall_count",
    "pending_suggestions", "knowledge_thread_active", "knowledge_thread_turns",
    "pending_proposals", "merge_counts", "answer_clips", "prefill_fields",
    "field_sources", "creator_confidence", "character_sketch",
    "deflect_counts", "open_question_archive", "impulse_coords",
    "message_rounds", "invited_modules", "closing_step", "closing_settled",
    "closing_answers", "resume_later", "pending_alignments", "draft_alpha",
    "auto_merge_log", "merge_undo", "current_options", "options_key",
    "reroll_streak",
})

# 拍 2-13/2-18/2-19 数据面：灵感架 + 清单追加循环停驻状态 + 批C 增量。
# 批C（裁定 D26）：mirror_thread_active/turns 两枚——讨论镜像通道停驻态，
# 照 D24 knowledge_thread_* 先例紧邻落位（bool=False/int=0 零迁移）；
# "恰好三枚"立法本意是防 92 L3 炸平面字段，非禁通道状态机，扩至五枚。
_A1SESSION_NEW_FIELDS = frozenset({
    "material_pool", "list_thread_key", "list_thread_turns",
    "mirror_thread_active", "mirror_thread_turns",
    # a1-oq-phase 批：开放问题相位状态机（oq_phase.py，bool=False/int=0 零迁移）
    "oq_phase_active", "oq_round",
})


def test_a1session_additive_enum() -> None:
    fields = frozenset(A1Session.model_fields)
    added = fields - _A1SESSION_OLD_FIELDS
    assert added == _A1SESSION_NEW_FIELDS, (
        "A1Session 新增字段必须恰为 %s（additive 契约），实得新增 %s / "
        "缺失 %s" % (
            sorted(_A1SESSION_NEW_FIELDS),
            sorted(added - _A1SESSION_NEW_FIELDS),
            sorted(_A1SESSION_NEW_FIELDS - added),
        )
    )
    # 旧字段零删除
    removed = _A1SESSION_OLD_FIELDS - fields
    assert not removed, "A1Session 既有字段被删除: %s" % sorted(removed)
    # 默认值空/零（存量会话零迁移：G3 先例）
    fresh = A1Session(session_id="t1-additive", user_id="t1")
    assert fresh.material_pool == []
    assert fresh.list_thread_key == ""
    assert fresh.list_thread_turns == 0
    # 存量序列化往返：42 字段旧 payload（无三新字段）model_validate 直通
    legacy = A1Session.model_validate({
        "session_id": "legacy", "user_id": "legacy",
    })
    assert legacy.material_pool == []
    assert legacy.list_thread_key == ""
    assert legacy.list_thread_turns == 0


# ---------------------------------------------------------------------------
# T2 专项断言（追加批）：树计数 / vs 全覆盖 / 清单位点 / cap 分布 / Q16。
# 四契约本体之上追加，不修改既有断言。
# ---------------------------------------------------------------------------

VS_ENUM_EXPECTED = {"point", "from_to", "dim_dir", "dual"}


def _tree_counts() -> tuple[int, int, int, dict[str, int]]:
    l1_n = l2_n = l3_n = 0
    vs_counter: dict[str, int] = {}
    for l1 in _load_three_tier_tree():
        l1_n += 1
        for l2 in l1["l2"]:
            l2_n += 1
            for l3 in l2["l3"]:
                l3_n += 1
                vs = l3.get("vs")
                assert vs in VS_ENUM_EXPECTED, (
                    "L3 %s 的 vs 值 %r 越出闭集 %s" % (l3["id"], vs, sorted(VS_ENUM_EXPECTED))
                )
                vs_counter[vs] = vs_counter.get(vs, 0) + 1
    return l1_n, l2_n, l3_n, vs_counter


def test_tree_counts_and_vs_coverage() -> None:
    l1_n, l2_n, l3_n, vs_counter = _tree_counts()
    assert l1_n == 7, "L1 应为 7，实得 %d" % l1_n
    assert l2_n == 26, "L2 应为 26，实得 %d" % l2_n
    assert l3_n == 92, "L3 应为 92，实得 %d" % l3_n
    # vs 标注全覆盖 92/92 + ⑥稿分布 ●66+▶20+⇄5+⇉1
    assert sum(vs_counter.values()) == 92, "vs 覆盖不足 92：%s" % vs_counter
    assert vs_counter == {
        "point": 66, "from_to": 20, "dim_dir": 5, "dual": 1,
    }, "vs 分布与⑥稿判定表不符：%s" % vs_counter


def test_list_spots_and_caps() -> None:
    tree = _load_three_tier_tree()
    list_l3: list[str] = []
    list_l2: list[str] = []
    for l1 in tree:
        for l2 in l1["l2"]:
            if l2.get("list"):
                list_l2.append(l2["id"])
                assert l2.get("item_template"), "清单位点 %s 缺 item_template" % l2["id"]
            for l3 in l2["l3"]:
                if l3.get("list"):
                    list_l3.append(l3["id"])
                    assert l3.get("item_template"), "清单位点 %s 缺 item_template" % l3["id"]
    # 首批 15 处 = 13 个 L3 位点 + 支线卡 L2 + 灵感架（会话级 material_pool）
    spots = len(list_l3) + len(list_l2) + 1
    assert spots == 15, "清单位点应为 15（13 L3+支线卡 L2+灵感架），实得 %d" % spots
    # cap 表：位点键与树内标注一一对应 + 灵感架；12 帽×3 + 6 帽×12
    caps = getattr(sm, "LIST_CAPS")
    tree_list_ids = set(list_l3) | set(list_l2)
    # 批B additive 演进（learnings 批A 先例）：旧字段宇宙清单位点
    # key_relations 入表（T4 红测契约 LIST_CAPS["key_relations"] 直读）。
    assert set(caps) == tree_list_ids | {"material_pool", "key_relations"}, (
        "cap 表位点与树内清单位点不齐：tree=%s caps=%s"
        % (sorted(tree_list_ids), sorted(caps))
    )
    big = sorted(k for k, v in caps.items() if v == 12)
    small = sorted(k for k, v in caps.items() if v == 6)
    assert big == ["existence", "key_nodes", "material_pool"], (
        "12 帽应为灵感架/关键节点/存在物三处，实得 %s" % big
    )
    # 批B additive 演进：key_relations 入表（6 帽档）→ 6 帽 12→13 处。
    assert len(small) == 13, "6 帽应为 13 处（12+key_relations），实得 %d：%s" % (len(small), small)


def test_q16_branch_main_question() -> None:
    q16 = getattr(sm, "Q16_BRANCH_CARD", None)
    assert q16 is not None, "Q16 支线主问未落库"
    assert "可跳过" in q16["hint"], "Q16 hint 须含'可跳过'：%s" % q16["hint"]
    order = getattr(sm, "STORYLINE_ORDER", None)
    assert order is not None, "故事线配方序列未落库"
    assert len(order) == 16, "故事线序列应为 16 问，实得 %d" % len(order)
    assert order[15] == q16["id"], (
        "Q16 应在故事线序列第 16 位，实得第 16 位=%s" % order[15]
    )
