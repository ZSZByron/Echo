"""A1 two-layer question tree — 10 modules x subfields (sequential).

Authority: .sisyphus/drafts/A模块层级图-含断点.md 第4套（世界观拓扑维度）.
Answer keys use "module_id.subfield_id" (dot-separated), e.g.
"IP定位.name". Subfield ids are stable english slugs; labels are
Chinese display names.

Module order is locked (test_module_ids_match_spec):
    IP定位 / 世界本体 / 力量体系 / 地理空间 / 文明与社会 /
    历史时间线 / 视觉设计 / 玩法设计DNA / 骰子设定 / 设定边界
"""
from __future__ import annotations

import unicodedata
from typing import Sequence, TypedDict

from app.domains.creation.seed.story_modules import get_story_module


class SubField(TypedDict):
    id: str
    label: str
    question: str
    hint: str
    example: str  # 简单示例，提示用户要回答什么（前端展示+LLM prompt注入）


class _SubFieldExtras(SubField, total=False):
    # D23：多值字段可选标记（仅故事模块个别字段携带；total=False 保持
    # 既有字面量与 mypy 兼容）。
    multi: bool


class Module(TypedDict):
    id: str
    label: str
    fields: list[SubField]


MODULES: list[Module] = [
    {
        "id": "IP定位",
        "label": "IP定位",
        "fields": [
            {
                "id": "name",
                "label": "名称与概念",
                "question": "这个世界的名称是什么？",
                "hint": "起个一听就有画面的名字——星陨大陆、霓影城这种。",
                "example": "如：星陨大陆、霓影城、碎天录",
            },
            {
                "id": "concept",
                "label": "核心概念",
                "question": "用一句话说说这个世界最核心的点子。",
                "hint": "它最特别的想法是什么，又会撞出什么冲突——一句话说清。",
                "example": "如：天道崩碎后，修士以剑补天的宿命轮回",
            },
            {
                "id": "world_type",
                "label": "类型",
                "question": "这是个什么类型的世界？",
                "hint": "像给书贴标签：仙侠、奇幻、科幻、废土、武侠……混合着来也行。",
                "example": "如：东方仙侠 / 高魔奇幻 / 赛博朋克 / 废土科幻",
            },
            {
                "id": "core_experience",
                "label": "核心体验",
                "question": "在这个世界里，人们（或你的主角）最常做什么、追的是什么？"
                        "跑团玩家就想想\"你在玩什么\"。",
                "hint": "一句话：最常干的事+图什么。",
                "example": "如：以剑证道，逆天改命",
            },
        ],
    },
    {
        "id": "世界本体",
        "label": "世界本体",
        "fields": [
            {
                "id": "origin",
                "label": "来源",
                "question": "世界的起源是什么？",
                "hint": "这个世界怎么来的？谁或什么力量造的它，过去多久了？",
                "example": "如：创世神陨落，神躯化作山海",
            },
            {
                "id": "existence",
                "label": "存在物",
                "question": "这个世界里主要有哪些\"东西\"？人、种族、神怪、器物都算。",
                "hint": "把会出现的生灵、势力、奇物列出来就行，不用解释。",
                "example": "如：修士、妖魔、古神、灵器",
            },
            {
                "id": "reality_rule",
                "label": "现实规则",
                "question": "世界由意志还是物质主导？",
                "hint": "意志说了算（信得够深就能改变现实），"
                        "还是物质说了算（资源和科技决定一切）？",
                "example": "如：意志主导——信念坚定者可扭曲现实",
            },
        ],
    },
    {
        "id": "力量体系",
        "label": "力量体系",
        "fields": [
            {
                "id": "source",
                "label": "溯源维度",
                "question": "力量从哪来？",
                "hint": "谁能拥有力量、多还是少、从谁流向谁——"
                        "比如从天上流到人间，还是藏在每个人身体里。",
                "example": "如：能量源自天地灵气，流动自上而下（天→地→人）",
            },
            {
                "id": "acquire",
                "label": "获取方式",
                "question": "人怎么才能获得力量？",
                "hint": "靠学、靠天赋觉醒、靠仪式，还是靠科技？"
                        "再想想：是少数人的特权，还是人人有份？",
                "example": "如：悟道觉醒（少数）、师承学习、仪式授予",
            },
            {
                "id": "mechanism",
                "label": "机制维度",
                "question": "力量的使用遵循什么规矩？",
                "hint": "用力量要不要付出等价的东西？科技和魔法能不能共存？想想这些规矩。",
                "example": "如：等价交换——施法需消耗等量灵力，科技与法术互斥",
            },
            {
                "id": "cost",
                "label": "代价维度",
                "question": "使用力量需要付出什么代价？",
                "hint": "天下没有免费的力量——是伤身体、损寿命，还是慢慢变得不像人？",
                "example": "如：施展法术折损寿元，过度使用导致非人化",
            },
        ],
    },
    {
        "id": "地理空间",
        "label": "地理空间",
        "fields": [
            {
                "id": "terrain",
                "label": "主要地形",
                "question": "这个世界长什么样？有哪些主要地方？",
                "hint": "从大到小说——先整个世界，再说到里面的国家和地区。",
                "example": "如：主世界九州→东海州→雾隐群岛",
            },
            {
                "id": "vertical",
                "label": "垂直层级",
                "question": "这个世界在\"上下\"方向上分几层？",
                "hint": "往上有天空深空，往下有地下地心——分几层、每层住着什么。",
                "example": "如：天上浮空城/地面人间/地下幽冥三层",
            },
            {
                "id": "special_geo",
                "label": "特殊地理",
                "question": "有没有哪些特殊的地方，规则和外面不一样？",
                "hint": "比如力量失效的禁地、时间流速不同的秘境、藏着大秘密的遗迹。",
                "example": "如：法则破碎区——物理规则紊乱的禁地",
            },
        ],
    },
    {
        "id": "文明与社会",
        "label": "文明与社会",
        "fields": [
            {
                "id": "core_value",
                "label": "核心价值",
                "question": "文明的核心价值观是什么？",
                "hint": "这个世界最信奉、最看重什么？"
                        "——像\"等价交换\"\"血统至上\"这种一句话的规矩。",
                "example": "如：力量至上，弱肉强食",
            },
            {
                "id": "conflict",
                "label": "冲突来源",
                "question": "这个世界里，人和人为什么起冲突、都在争什么？",
                "hint": "常见由头：抢资源、信仰不合、种族偏见、争权利——或你自创的由头。",
                "example": "如：资源（灵石矿脉）、信仰（古神vs新道）",
            },
            {
                "id": "faction_type",
                "label": "势力类型",
                "question": "世界里有哪些主要势力？各自怎么运作？",
                "hint": "宗门、王国、议会、部落都行——说说谁说了算、怎么传位。",
                "example": "如：剑宗（师徒制）、皇朝（世袭帝制）、散修联盟",
            },
            {
                "id": "economy",
                "label": "经济",
                "question": "经济建立在什么之上？",
                "hint": "大家用什么当钱？灵石、粮食还是别的？力量本身能不能买卖？",
                "example": "如：灵石本位制，法器可交易",
            },
        ],
    },
    {
        "id": "历史时间线",
        "label": "历史时间线",
        "fields": [
            {
                "id": "time_span",
                "label": "时间跨度",
                "question": "这个世界的历史有多长、分成哪几个时代？",
                "hint": "总共多少年，再给每个时代起个名——创世纪、黄金纪、衰落纪这样。",
                "example": "如：三纪元共十万年——创世纪/黄金纪/崩碎纪",
            },
            {
                "id": "key_nodes",
                "label": "关键节点",
                "question": "历史上有哪些关键节点事件？",
                "hint": "挑几件改变世界的大事，说说发生在什么时候、波及多大地盘、牵连了谁。",
                "example": "如：300年前天道崩碎，天界崩塌、古神陨落——影响全世界的大事。",
            },
            {
                "id": "main_plot",
                "label": "主剧情",
                "question": "现在这个时代，世界上正在发生什么大事？",
                "hint": "说的是世界层面的大事（背景），不是主角个人的故事——那个后面会聊。"
                        "想想它和世界的起源有什么呼应、会怎么收场。",
                "example": "如：收集补天剑碎片对抗天道虚无",
            },
        ],
    },
    {
        "id": "视觉设计",
        "label": "视觉设计",
        "fields": [
            {
                "id": "keywords",
                "label": "视觉关键词",
                "question": "这个世界的视觉关键词有哪些？",
                "hint": "3-8 个视觉基调词，如霓虹、锈蚀、苍白。",
                "example": "如：残剑、云海、金纹、苍凉壮美",
            },
            {
                "id": "architecture",
                "label": "建筑风格",
                "question": "建筑风格是什么样的？",
                "hint": "说说房子长什么样：用什么材料、盖在哪儿、什么阶层住什么房。",
                "example": "如：依山而建的悬空剑阁，黑瓦金檐",
            },
            {
                "id": "material",
                "label": "材质偏好",
                "question": "这个世界的东西，用什么材料做？",
                "hint": "珍稀的材料、特有的动植物、传下来的手艺。",
                "example": "如：玄铁、灵木、云锦",
            },
        ],
    },
    {
        "id": "玩法设计DNA",
        "label": "玩法设计DNA",
        "fields": [
            {
                "id": "player_role",
                "label": "玩家身份",
                "question": "如果这是个游戏，玩家扮演谁？"
                        "（不跑团就换成：走进这个世界的人，是谁？）",
                "hint": "他从什么身份起步，一路会变成什么——像\"从外门弟子到执剑长老\"。",
                "example": "如：从外门弟子到执剑长老的三阶段成长",
            },
            {
                "id": "main_action",
                "label": "主要行为",
                "question": "玩家大多数时间在干什么？",
                "hint": "探索、打架、搞研究、修炼变强——哪个多哪个少？",
                "example": "如：探索秘境40% + 战斗30% + 修炼30%",
            },
            {
                "id": "growth",
                "label": "成长方式",
                "question": "角色如何成长？",
                "hint": "怎么变强——一点点积累，还是突破关口脱胎换骨？为什么而变强？",
                "example": "如：质变——每次突破境界解锁新剑意",
            },
            {
                "id": "growth_end",
                "label": "成长尽头",
                "question": "成长的终点是什么？",
                "hint": "变到头是什么样？当上人上人（地位）、摸到世界规则（法则），"
                        "还是悟明白了什么（心境）？",
                "example": "如：法则性终点——以剑合道，自成天道",
            },
        ],
    },
    {
        "id": "骰子设定",
        "label": "骰子设定",
        "fields": [
            {
                "id": "probability",
                "label": "概率分布",
                "question": "这个世界的规则，适合用哪种骰子来判定？",
                "hint": "意志主导的世界用 d20（大开大合）；"
                        "物质主导的世界用 3d6（结果更稳、少极端）。",
                "example": "如：意志主导的世界用 d20",
            },
            {
                "id": "dice_count",
                "label": "骰子数量",
                "question": "判定的时候掷几颗骰子？",
                "hint": "力量来自世界本源→固定一颗骰（如 1d20）；"
                        "力量属于每个个体→掷一把骰子（骰池）。",
                "example": "如：力量源自世界本源→固定 1d20",
            },
            {
                "id": "check_mode",
                "label": "判定方式",
                "question": "怎么判定一次尝试算不算成功？",
                "hint": "力量被少数人垄断→掷骰低于属性值算成功（Roll-under）；"
                        "人人可修→掷骰加上属性值、超过难度算成功（Roll-over）。",
                "example": "如：垄断式获取→Roll-under（属性越高越容易成功）",
            },
            {
                "id": "success_check",
                "label": "成功判定",
                "question": "不同的事，怎么算做成？",
                "hint": "打架一刀定胜负（成/败两种结果）；搞研究分阶段推进（每步有每步的收获）。",
                "example": "如：战斗→一锤定音；研究→层层推进",
            },
            {
                "id": "cost_mech",
                "label": "代价机制",
                "question": "这个世界有多残酷？失败要怎么罚？",
                "hint": "世界越残酷，失败罚得越狠——比如骰出大失败会触发反噬。",
                "example": "如：残酷世界→骰出大失败触发反噬",
            },
        ],
    },
    {
        "id": "设定边界",
        "label": "设定边界",
        "fields": [
            {
                "id": "immutable_core",
                "label": "不可变设定",
                "question": "哪些设定是你亲手定下、绝不允许 AI 改动的？",
                "hint": "你已经写下的世界规则、力量体系、主线走向——这些是底线，AI 碰不得。",
                "example": "如：世界起源、力量的来源与代价、主线走向不可动",
            },
            {
                "id": "ai_fill",
                "label": "AI补充范围",
                "question": "在底线之外，哪些地方欢迎 AI 帮你补细节？",
                "hint": "只要不动你定死的部分——场景细节、NPC 支线、视觉变体，都欢迎。",
                "example": "如：NPC支线、场景细节、视觉变体",
            },
        ],
    },
]

_MODULE_ORDER: list[str] = [m["id"] for m in MODULES]
_MODULES_BY_ID: dict[str, Module] = {m["id"]: m for m in MODULES}


def _resolve_module(mid: str) -> Module | None:
    """Resolve a module id across worldview tree + story pool (M2).

    世界建构 10 模块查问卷树；M11/M12 故事模块查 story_modules（经
    get_story_module 门面）。MODULES 全集消费面（module_ids(recipe=None)/
    total_subfield_count）不受影响——故事模块只经**显式配方参数**可达。
    """
    module = _MODULES_BY_ID.get(mid)
    if module is not None:
        return module
    return get_story_module(mid)


def _recipe_order(recipe: Sequence[str] | None) -> list[str]:
    """Resolve a recipe (ordered module ids) or the full questionnaire order.

    recipe=None → full set (default recipe). Pure data plumbing — the
    registry owns recipe content; this module never imports it (the
    dependency arrow points registry → here, never back).
    """
    return list(recipe) if recipe is not None else list(_MODULE_ORDER)


def module_ids(recipe: Sequence[str] | None = None) -> list[str]:
    """Return the ordered module ids for the recipe (default = all 10)."""
    return _recipe_order(recipe)


def get_module(mid: str, recipe: Sequence[str] | None = None) -> Module | None:
    """Return the module dict for mid, or None.

    ``recipe`` is accepted for facade uniformity (M1 pool == tree modules;
    M2 story modules join the pool, not this tree).
    """
    return _resolve_module(mid)


def get_subfield(mid: str, sid: str) -> _SubFieldExtras | None:
    """Return the subfield dict for (mid, sid), or None."""
    m = _resolve_module(mid)
    if m is None:
        return None
    return next((f for f in m["fields"] if f["id"] == sid), None)


def first_module(recipe: Sequence[str] | None = None) -> Module:
    """Return the first module of the recipe (default: IP定位)."""
    first = _resolve_module(_recipe_order(recipe)[0])
    assert first is not None
    return first


def first_subfield(mid: str) -> SubField:
    """Return the first subfield of the given module."""
    m = _resolve_module(mid)
    assert m is not None
    return m["fields"][0]


def next_subfield(
    mid: str, sid: str | None, recipe: Sequence[str] | None = None
) -> SubField | None:
    """Return the next subfield within the same module.

    Returns the first subfield when sid is None; returns None at the
    end of the module (callers cross into the next module themselves).
    ``recipe`` accepted for facade uniformity — subfield order inside a
    module is questionnaire-tree order for every recipe.
    """
    m = _resolve_module(mid)
    if m is None:
        return None
    if sid is None:
        return m["fields"][0]
    for i, f in enumerate(m["fields"]):
        if f["id"] == sid:
            return m["fields"][i + 1] if i + 1 < len(m["fields"]) else None
    return None


def next_module(
    mid: str, recipe: Sequence[str] | None = None
) -> Module | None:
    """Return the module after mid in the recipe order, or None at the end."""
    order = _recipe_order(recipe)
    if mid not in order:
        return None
    i = order.index(mid)
    nxt = _resolve_module(order[i + 1]) if i + 1 < len(order) else None
    assert nxt is not None
    return nxt


def subs_for_module(mid: str) -> list[SubField]:
    """Return all subfields of the given module (empty list if unknown)."""
    m = _resolve_module(mid)
    return m["fields"] if m else []


def total_subfield_count() -> int:
    """Return the total number of subfields across all modules."""
    return sum(len(m["fields"]) for m in MODULES)


def all_subfield_keys(recipe: Sequence[str] | None = None) -> list[str]:
    """Return every answer key "module_id.subfield_id" in recipe order.

    recipe=None → the full 10-module set (default recipe).
    """
    return [
        f"{mid}.{f['id']}"
        for mid in _recipe_order(recipe)
        for f in (_resolve_module(mid) or {"fields": []})["fields"]
    ]


def is_module_done(mid: str, answers: dict[str, str]) -> bool:
    """True when every subfield of mid has a TRUTHY answer (J1)."""
    m = _resolve_module(mid)
    return m is not None and all(
        is_truthy_answer(answers.get(f"{mid}.{f['id']}")) for f in m["fields"]
    )


def module_done_ratio(mid: str, answers: dict[str, str]) -> float:
    """Fraction (0..1) of mid's subfields with a TRUTHY answer (J1).

    Placeholder values (占位词典) and empty strings do not count toward
    the numerator — they are semantically absent. Unknown modules return
    0.0 (never finalizable by accident).
    """
    m = _resolve_module(mid)
    if m is None or not m["fields"]:
        return 0.0
    done = sum(
        1 for f in m["fields"] if is_truthy_answer(answers.get(f"{mid}.{f['id']}"))
    )
    return done / len(m["fields"])


FINALIZE_MODULE_THRESHOLD = 0.5


def is_module_over_half(mid: str, answers: dict[str, str]) -> bool:
    """Finalize gate: strictly more than 50% of subfields TRUTHY answered."""
    return module_done_ratio(mid, answers) > FINALIZE_MODULE_THRESHOLD


def is_finalizable(
    answers: dict[str, str], recipe: Sequence[str] | None = None
) -> bool:
    """True when EVERY module in the recipe exceeds the 50% finalize threshold.

    门禁子集语义（DN1 默认）：配方外模块 = 不适用，不参与判定。
    recipe=None → 全集（default 配方，行为与 M1 之前逐字节一致）。
    """
    return all(
        is_module_over_half(mid, answers) for mid in _recipe_order(recipe)
    )


# ---------------------------------------------------------------------------
# J1 答案真值闸（answer truth gate）— 2-A1-v0.5.1 §3 J1
#
# 治级联 A「真值链」：parse_modules / interviewer fills 曾把"未提及"类
# 占位值当 truthy 写入 answers，门禁只查 key 存在即放行，graphify 再把
# 占位值全文嵌入 → 空壳图谱合法定稿。
#
# 修复方式：一个 canonical 谓词 + 各写入出口统一调用（parse_modules /
# _apply_fills）+ 门禁计数真值感知（本文件 module_done_ratio）。
# 已接受的权衡（治理文档钦定）：
#   - 词典法漏新变体 → 由 J3 披露协议兜底可见；
#   - 不用 LLM 判真值（会再引入方差）；
#   - "无"不入词典（可能是合法否定答案，如"是否有神"→"无"）。
# ---------------------------------------------------------------------------

# 归一化后精确匹配的占位词典（不允许随意扩充：误收会吞真实答案）。
_PLACEHOLDER_ANSWERS: frozenset[str] = frozenset({
    # 中文占位
    "未提及", "未明确", "未知", "缺少依据", "未说明", "未指定",
    "未确定", "未定义", "未给出", "未提供", "未回答", "未涉及",
    "未透露", "未详述", "不明确", "不适用", "不详", "暂无", "暂缺",
    "无依据", "无相关内容", "无资料", "无内容", "空缺",
    "待定", "待补", "待补充", "待确认", "待填写",
    "文中未提及", "原文未提及", "用户未提及", "资料未提及", "未上传",
    # 英文/ASCII 占位（casefold 后匹配）
    "n/a", "n.a", "na", "none", "null", "nil", "unknown",
    "not mentioned", "not specified", "unspecified", "not applicable",
    "not determined", "not provided", "not available",
    "no data", "no evidence", "tbd", "tba", "todo", "missing", "empty",
    # 纯符号占位
    "-", "—", "——", "———", "--", "---",
    # M0 止血：访谈偏转占位（guide_engine.DEFLECT_PLACEHOLDER"（用户跳过）"
    # 归一化后命中——J1 真值闸 → 门禁/进度不计数）
    "用户跳过",
})

# 归一化时从首尾剥离的字符：空白、包裹符号、标点。
_TRUTH_NORM_STRIP = (
    " \t\r\n\"'“”‘’「」『』()（）[]【】{}〈〉《》·*_-—.,，、。．;；:：!！?？…"
)


def _truth_norm(value: str) -> str:
    """Deterministic normalization for placeholder exact-match.

    NFKC（全角→半角，Ｎ／Ａ→N/A）→ strip → casefold → 剥离首尾空白/
    包裹符号/标点。纯函数、零 LLM、不折叠内部空白（保持确定性）。
    """
    return (
        unicodedata.normalize("NFKC", value)
        .strip()
        .casefold()
        .strip(_TRUTH_NORM_STRIP)
    )


def is_truthy_answer(value: str | None) -> bool:
    """J1 canonical predicate: does this answer carry real user semantics?

    False（不写入 answers / 不计入门禁分子）:
      - None / 空串 / 纯空白
      - 归一化后精确命中占位词典（未提及/未知/缺少依据/N/A 等变体，
        含全角、包裹符号、首尾标点等漂移形式）

    True: 其余一切（含"无"、含占位词作子串的长句，如"未知种族的迁徙历史"）。
    """
    if not value:
        return False
    normalized = _truth_norm(str(value))
    return bool(normalized) and normalized not in _PLACEHOLDER_ANSWERS


# ---------------------------------------------------------------------------
# J4 预算护栏（answer budget）— 2-A1-v0.5.1 §3 J4
#
# 治级联 D「无护栏链」半边：answer value 无上限 → 35×5000 答案炸弹全文
# 嵌入 graphify prompt。护栏=写入出口截断（_apply_fills / parse_modules）
# + graphify prompt 层二次防线（直注/存量数据）——截断必配 J3 披露。
# ---------------------------------------------------------------------------

ANSWER_MAX_CHARS = 2000


def clip_answer(value: str, limit: int = ANSWER_MAX_CHARS) -> tuple[str, bool]:
    """J4 budget gate: cap one answer at ``limit`` chars.

    Returns ``(clipped_value, was_clipped)``. 纯函数；截断必须由调用方
    披露（session.answer_clips / clipped_answers → warning ledger）。
    """
    if len(value) <= limit:
        return value, False
    return value[:limit], True
