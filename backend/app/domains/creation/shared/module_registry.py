# -*- coding: utf-8 -*-
"""甲：模块池 + 冲动配方（产品方 2026-09-22 裁决）。

M1 底座（plan modular-restructure TODO 1）：
- ``MODULE_POOL``：模块池（M1 = 原 10 世界建构模块引用；故事模块归 M2
  ``story_modules.py``、产出模块归 M3 ``modules/``，经此入池）。
- ``Recipe``：冲动类型 → 模块配方（id/impulse_type/module_ids 有序子集/
  entry_subfield/anchor/ai_fill_policy 六字段逐字锁定）。
- ``RECIPES``：default + 冲动型全覆盖；**默认配方 = 原 10 模块全集** →
  无 creator_primary / 未知值 / 存量会话行为零变化（G3 兼容）。

E1-Lite 三数据字典数据迁入（原位置留 re-export 兼容 import）：
- ``TYPE_MODULE_PRIORITY``（原 guide_engine.py）→ 非故事型配方 module_ids
  序（head + 其余按问卷树序 = 纯置换，行为等价）；故事四型（plot/romance/
  unsure/character_driven）= 前移序本身即子集序（spec §5.2，DN6 初稿）。
- ``TYPE_ENTRY_SUBFIELD``（原 guide_engine.py）→ ``Recipe.entry_subfield``。
- ``ANCHOR_BY_TYPE``（原 interviewer.py）→ ``Recipe.anchor``。

门禁语义（DN1 默认）：配方外模块 = 不适用——finalize 门禁与
missing_sections 只遍历配方内模块。LLM 不进控制流：配方选择是查表。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domains.creation.a1.tier_map import TIER_MAP
from app.domains.creation.seed.a1_question_tree import MODULES
from app.domains.creation.seed.story_modules import STORY_MODULES

# ---------------------------------------------------------------------------
# E1-Lite 三数据字典（数据源迁入；guide_engine / interviewer 原位置 re-export）
# ---------------------------------------------------------------------------

# E1-Lite T2 — type-driven queue (spec §5.2, R6 conservative mode).
# Module ids are the Chinese ids from the questionnaire tree; priority
# lists only *move modules forward* — never skip them.
TYPE_MODULE_PRIORITY: dict[str, list[str]] = {
    "plot":             ["历史时间线", "文明与社会", "世界本体"],
    "unsure":           ["历史时间线", "文明与社会", "世界本体"],
    "philosophy":       ["世界本体", "文明与社会", "力量体系", "历史时间线"],
    "romance":          ["IP定位", "历史时间线", "视觉设计"],
    "character_driven": ["文明与社会", "历史时间线", "世界本体", "力量体系"],
    "setting_heavy":    ["视觉设计"],
    "exploration":      ["玩法设计DNA", "骰子设定", "力量体系", "世界本体"],
    # nostalgia / healing 不入表 → 原序（§5.2 两行未定义前移序）
}
# 入口子字段前置（模块内置换，仅 plot/unsure——否则首问是 time_span 非故事问题）
TYPE_ENTRY_SUBFIELD: dict[str, tuple[str, str]] = {
    "plot":   ("历史时间线", "main_plot"),
    "unsure": ("历史时间线", "main_plot"),
}

# E1-Lite T3: 语气锚点（spec §5.2 "语气锚点"列逐字，一个字不许改写；
# 引号形态 = spec 原文直引号 U+0022）。注入 _seed_block 模板变量
# （R2：差异是数据不是代码——单一 prompt 骨架）。
ANCHOR_BY_TYPE: dict[str, str] = {
    "plot": '节奏导向："这个设定会制造什么事件？"',
    "unsure": '中性引导"先聊聊你世界里发生的事"',
    "philosophy": '追问"如果这条规则被违反会怎样"',
    "romance": '情感张力导向；A1 极轻量化；合规边界（§9）',
    "character_driven": '一切围绕"这如何影响 TA 的命运"',
    "setting_heavy": '机制自洽："这里的力量为什么成立？"',
    "exploration": '能力边界展示："AI 可以替你试三种方案"',
    "nostalgia": '"我在保护原作的味道"——风格保真',
    "healing": '陪伴低压力："不想答的都可以跳过，我会替你补上"',
}

# M0 止血：故事型主冲动集合（叙事素材归档判定用；interviewer/guide_engine 复用）。
STORY_PRIMARY_TYPES = frozenset({"plot", "romance", "unsure", "character_driven"})

#: 冲动型白名单（与 a1_routes.IMPULSE_TYPE_IDS 同源九型，不允许增删改写）。
IMPULSE_TYPE_IDS: frozenset[str] = frozenset({
    "setting_heavy", "character_driven", "plot", "philosophy",
    "exploration", "romance", "nostalgia", "healing", "unsure",
})


# ---------------------------------------------------------------------------
# 模块池
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModuleDef:
    """One pool module. M1: worldview family referencing question-tree data.

    family: "worldview"（M1）/"story"（M2 story_modules.py 入池）/
    "output"（M3 modules/ 入池）。tier 复用既有 tier 映射（DN2 默认）。
    """

    id: str
    label: str
    family: str
    fields: list[dict[str, Any]]  # 引用 a1_question_tree SubField 数据（零拷贝语义）
    tier: int


#: 模块池：原 10 世界建构模块引用（M1）+ M11 角色 / M12 剧情故事模块（M2，
#: family="story"，2026-09-22 重锚定定版——情感线并入 M12 + M10 爱情 preset，
#: 无独立情感线模块）；产出模块归 M3 经此入池。
_MODULE_POOL: dict[str, ModuleDef] = {
    m["id"]: ModuleDef(
        id=m["id"],
        label=m["label"],
        family="worldview",
        fields=m["fields"],
        tier=TIER_MAP[m["id"]],
    )
    for m in MODULES
}
_MODULE_POOL.update({
    m["id"]: ModuleDef(
        id=m["id"],
        label=m["label"],
        family="story",
        fields=m["fields"],
        tier=TIER_MAP[m["id"]],
    )
    for m in STORY_MODULES
})

MODULE_POOL: dict[str, ModuleDef] = _MODULE_POOL


# ---------------------------------------------------------------------------
# 配方表
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Recipe:
    """冲动类型 → 模块配方（六字段逐字锁定，plan §96）。

    module_ids: 有序子集（default = 原 10 模块全集）。
    entry_subfield: (module_id, subfield_id) 入口前置；None = 无入口置换。
    anchor: 语气锚点（spec §5.2 列原文）；"" = 无锚点。
    ai_fill_policy: M1 统一 "default"（字段级粒度归 M4b，未决①收口）。
    """

    id: str
    impulse_type: str
    module_ids: tuple[str, ...]
    entry_subfield: tuple[str, str] | None
    anchor: str
    ai_fill_policy: str = "default"


_DEFAULT_ORDER: tuple[str, ...] = tuple(m["id"] for m in MODULES)


def _full_permutation(head: list[str]) -> tuple[str, ...]:
    """E1-Lite 纯置换语义：head 前移，其余保持问卷树序（每模块恰一次）。"""
    return tuple(head) + tuple(mid for mid in _DEFAULT_ORDER if mid not in head)


# M2 故事型配方矩阵（详细设计 §3.1，8+2 重锚版；计划 Must Have §102：
# 故事四型 = M12 剧情 + M11 角色 + 有限世界建构子集）。
# 世界建构子集的裁剪与序 = **DECISION NEEDED 6 初稿待终审**：
# - 世界建构部分 = §5.2 前移序的**保序子集**（子集序即前移序，DN6）；
# - plot/unsure 剔除 文明与社会——翻车证据验收场景②（势力类型轰炸）
#   的根治项，终审可回填；
# - unsure 入口 = M12 开场事件单问启动（模块清单拓展文档 §3 S0 直落
#   opening_event）；plot 入口 = 核心抉择（验收 §239 首问）；
# - romance 入口 = 角色.关键关系（双人关系卡打头，§3.1 矩阵）；
# - 设定边界（M10）按全局规则 1"永远在场"常驻各型收尾。
_STORY_RECIPES: dict[str, Recipe] = {
    "plot": Recipe(
        id="plot",
        impulse_type="plot",
        module_ids=(
            "剧情", "角色", "历史时间线", "世界本体", "设定边界",
        ),
        entry_subfield=("剧情", "core_dilemma"),
        anchor=ANCHOR_BY_TYPE["plot"],
    ),
    "unsure": Recipe(
        id="unsure",
        impulse_type="unsure",
        module_ids=(
            "剧情", "角色", "历史时间线", "世界本体", "设定边界",
        ),
        entry_subfield=("剧情", "opening_event"),
        anchor=ANCHOR_BY_TYPE["unsure"],
    ),
    "romance": Recipe(
        id="romance",
        impulse_type="romance",
        module_ids=(
            "角色", "IP定位", "剧情", "历史时间线", "视觉设计", "设定边界",
        ),
        entry_subfield=("角色", "key_relations"),
        anchor=ANCHOR_BY_TYPE["romance"],  # §9 合规边界措辞逐字保留
    ),
    "character_driven": Recipe(
        id="character_driven",
        impulse_type="character_driven",
        module_ids=(
            "角色", "文明与社会", "剧情", "历史时间线",
            "世界本体", "力量体系", "设定边界",
        ),
        entry_subfield=("角色", "identity"),
        anchor=ANCHOR_BY_TYPE["character_driven"],
    ),
}


def _build_recipes() -> dict[str, Recipe]:
    recipes: dict[str, Recipe] = {
        "default": Recipe(
            id="default",
            impulse_type="",
            module_ids=_DEFAULT_ORDER,
            entry_subfield=None,
            anchor="",
        )
    }
    for ptype, head in TYPE_MODULE_PRIORITY.items():
        if ptype in _STORY_RECIPES:
            # 故事四型（M2）：矩阵配方取代 M1 临时前移子集（DN6 初稿）。
            recipes[ptype] = _STORY_RECIPES[ptype]
            continue
        # 非故事型：全集置换（与 E1-Lite 行为逐字节等价）。
        recipes[ptype] = Recipe(
            id=ptype,
            impulse_type=ptype,
            module_ids=_full_permutation(head),
            entry_subfield=TYPE_ENTRY_SUBFIELD.get(ptype),
            anchor=ANCHOR_BY_TYPE.get(ptype, ""),
        )
    # nostalgia / healing 不在优先级表 → 原序全集（§5.2 两行未定义前移序）。
    for ptype in ("nostalgia", "healing"):
        recipes[ptype] = Recipe(
            id=ptype,
            impulse_type=ptype,
            module_ids=_DEFAULT_ORDER,
            entry_subfield=None,
            anchor=ANCHOR_BY_TYPE.get(ptype, ""),
        )
    return recipes


#: 配方表：default + 九冲动型（含 nostalgia/healing 原序全集与 exploration）。
RECIPES: dict[str, Recipe] = _build_recipes()


def resolve_recipe_id(creator_primary: str | None) -> str:
    """Deterministic recipe lookup: unknown/empty → "default" (G3)."""
    cp = creator_primary or ""
    return cp if cp in RECIPES else "default"
