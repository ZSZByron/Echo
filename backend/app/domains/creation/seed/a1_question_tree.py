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
from typing import TypedDict


class SubField(TypedDict):
    id: str
    label: str
    question: str
    hint: str
    example: str  # 简单示例，提示用户要回答什么（前端展示+LLM prompt注入）


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
                "hint": "命名是识别标识，一句话点出核心意象。",
                "example": "如：星陨大陆、霓影城、碎天录",
            },
            {
                "id": "concept",
                "label": "核心概念",
                "question": "这个世界观的核心概念是什么？",
                "hint": "哲学内核 + 剧情冲突，一句话概括。",
                "example": "如：天道崩碎后，修士以剑补天的宿命轮回",
            },
            {
                "id": "world_type",
                "label": "类型",
                "question": "世界观的分类类型是什么？",
                "hint": "力量 + 物质 + 哲学三要素的组合类型。",
                "example": "如：东方仙侠 / 高魔奇幻 / 赛博朋克 / 废土科幻",
            },
            {
                "id": "core_experience",
                "label": "核心体验",
                "question": "玩家在世界中的核心体验是什么？",
                "hint": "主要行为 + 目标，玩家最常做什么。",
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
                "hint": "起源力量 / 起源时间线。",
                "example": "如：创世神陨落，神躯化作山海",
            },
            {
                "id": "existence",
                "label": "存在物",
                "question": "世界中主要存在哪些事物类别？",
                "hint": "力量体系 / 宇宙学 / 哲学思想 / 其他。",
                "example": "如：修士、妖魔、古神、灵器",
            },
            {
                "id": "reality_rule",
                "label": "现实规则",
                "question": "世界由意志还是物质主导？",
                "hint": "意志主导（信念改变现实）或物质主导（资源驱动）。",
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
                "question": "力量的来源与能量流动方式是什么？",
                "hint": "能量来源（有限↔无限）+ 本体定义 + 流动拓扑（自上而下/内聚）。",
                "example": "如：能量源自天地灵气，流动自上而下（天→地→人）",
            },
            {
                "id": "acquire",
                "label": "获取方式",
                "question": "力量如何被获取？",
                "hint": "学习 / 觉醒 / 仪式 / 科研；获取拓扑是封闭精英还是开放众生。",
                "example": "如：悟道觉醒（少数）、师承学习、仪式授予",
            },
            {
                "id": "mechanism",
                "label": "机制维度",
                "question": "力量交互遵循什么法则？",
                "hint": "守恒（等价交换）↔ 非守恒（唯心投射）；排他性（科技vs魔法互斥）。",
                "example": "如：等价交换——施法需消耗等量灵力，科技与法术互斥",
            },
            {
                "id": "cost",
                "label": "代价维度",
                "question": "使用力量需要付出什么代价？",
                "hint": "承载vs操作关系；反馈回路（变异/非人化）；物理损耗或精神腐蚀。",
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
                "question": "世界的主要地形结构是什么？",
                "hint": "主世界 → 地区 → 区域的层级划分。",
                "example": "如：主世界九州→东海州→雾隐群岛",
            },
            {
                "id": "vertical",
                "label": "垂直层级",
                "question": "世界的垂直空间如何分层？",
                "hint": "深空 / 天空 / 高山 / 地面 / 地下 / 地心。",
                "example": "如：天上浮空城/地面人间/地下幽冥三层",
            },
            {
                "id": "special_geo",
                "label": "特殊地理",
                "question": "有哪些塑造规则的特殊地理？",
                "hint": "shaping_rules + power_sources，法则破碎区等。",
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
                "hint": "主导意识形态，如等价交换、血统至上。",
                "example": "如：力量至上，弱肉强食",
            },
            {
                "id": "conflict",
                "label": "冲突来源",
                "question": "社会的主要冲突来源是什么？",
                "hint": "资源 / 信仰 / 种族 / 文化 / 权利 / 特殊冲突。",
                "example": "如：资源（灵石矿脉）、信仰（古神vs新道）",
            },
            {
                "id": "faction_type",
                "label": "势力类型",
                "question": "主要势力采用什么政治类型？",
                "hint": "政体形式：神权 / 议会 / 帝国 / 部落等。",
                "example": "如：剑宗（师徒制）、皇朝（世袭帝制）、散修联盟",
            },
            {
                "id": "economy",
                "label": "经济",
                "question": "经济建立在什么之上？",
                "hint": "力量物质化（力量可交易？）+ 自然资源。",
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
                "question": "历史的时间跨度和纪元如何划分？",
                "hint": "总长度 + era 划分（如创世纪/黄金纪/衰落纪）。",
                "example": "如：三纪元共十万年——创世纪/黄金纪/崩碎纪",
            },
            {
                "id": "key_nodes",
                "label": "关键节点",
                "question": "历史上有哪些关键节点事件？",
                "hint": "每个节点标注 severity（COSMIC/MAJOR/REGIONAL/MINOR）"
                        "+ 发生地 + 涉及势力 + 因果上游。",
                "example": "如：300年前天道崩碎（MAJOR，天界，涉及古神）",
            },
            {
                "id": "main_plot",
                "label": "主剧情",
                "question": "当前时代的主剧情线是什么？",
                "hint": "驱动维度（起源回响）+ 归宿维度（哲学闭环：循环或衰败）。",
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
                "hint": "由资源 + 文化风格 + 社会身份共同决定。",
                "example": "如：依山而建的悬空剑阁，黑瓦金檐",
            },
            {
                "id": "material",
                "label": "材质偏好",
                "question": "世界偏好的材质语言是什么？",
                "hint": "资源 + 特殊动植物 + 文化传统。",
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
                "question": "玩家在世界中扮演什么身份？",
                "hint": "社会 → 维度 → 超越 三阶段演进。",
                "example": "如：从外门弟子到执剑长老的三阶段成长",
            },
            {
                "id": "main_action",
                "label": "主要行为",
                "question": "玩家的主要行为是什么？",
                "hint": "探索 / 战斗 / 研究 / 提升 的配比。",
                "example": "如：探索秘境40% + 战斗30% + 修炼30%",
            },
            {
                "id": "growth",
                "label": "成长方式",
                "question": "角色如何成长？",
                "hint": "量变 / 质变 / 哲学 / 因果 / 探索。",
                "example": "如：质变——每次突破境界解锁新剑意",
            },
            {
                "id": "growth_end",
                "label": "成长尽头",
                "question": "成长的终点是什么？",
                "hint": "社会性 / 法则性 / 哲学性终点。",
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
                "question": "现实规则映射到什么概率分布？",
                "hint": "意志主导→线性d20；物质主导→钟形3d6。",
                "example": "如：意志主导→线性d20",
            },
            {
                "id": "dice_count",
                "label": "骰子数量",
                "question": "力量来源映射到什么骰子数量？",
                "hint": "本体→固定骰；客体→骰池。",
                "example": "如：力量源自本体→固定1d20",
            },
            {
                "id": "check_mode",
                "label": "判定方式",
                "question": "获取方式映射到什么判定方式？",
                "hint": "封闭→Roll-under；开放→Roll-over。",
                "example": "如：封闭获取→Roll-under（属性值越高越易成功）",
            },
            {
                "id": "success_check",
                "label": "成功判定",
                "question": "玩法行为映射到什么成功判定？",
                "hint": "战斗→二元判定；研究→多层次判定。",
                "example": "如：战斗→二元判定；研究→多层次判定",
            },
            {
                "id": "cost_mech",
                "label": "代价机制",
                "question": "哲学平衡映射到什么代价机制？",
                "hint": "残酷世界观→临界陷阱机制。",
                "example": "如：残酷世界→临界失败触发反噬",
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
                "question": "哪些世界观设定是你亲手定下的锚点，绝不允许被改动？",
                "hint": "圈定不可动的核心：你已写下的世界规则、力量体系、主线和关键设定。",
                "example": "如：世界起源、力量的来源与代价、主线走向不可动",
            },
            {
                "id": "ai_fill",
                "label": "AI补充范围",
                "question": "锚点之外，哪些部分欢迎 AI 帮你补充细节？",
                "hint": "不触碰锚点的衍生内容：场景细节、NPC支线、视觉变体等。",
                "example": "如：NPC支线、场景细节、视觉变体",
            },
        ],
    },
]

SEVERITY_VALUES: list[str] = ["COSMIC", "MAJOR", "REGIONAL", "MINOR"]

_MODULE_ORDER: list[str] = [m["id"] for m in MODULES]
_MODULES_BY_ID: dict[str, Module] = {m["id"]: m for m in MODULES}


def module_ids() -> list[str]:
    """Return the ordered ids of all 10 modules."""
    return list(_MODULE_ORDER)


def get_module(mid: str) -> Module | None:
    """Return the module dict for mid, or None."""
    return _MODULES_BY_ID.get(mid)


def get_subfield(mid: str, sid: str) -> SubField | None:
    """Return the subfield dict for (mid, sid), or None."""
    m = _MODULES_BY_ID.get(mid)
    if m is None:
        return None
    return next((f for f in m["fields"] if f["id"] == sid), None)


def first_module() -> Module:
    """Return the first module (IP定位)."""
    return MODULES[0]


def first_subfield(mid: str) -> SubField:
    """Return the first subfield of the given module."""
    m = _MODULES_BY_ID[mid]
    return m["fields"][0]


def next_subfield(mid: str, sid: str | None) -> SubField | None:
    """Return the next subfield within the same module.

    Returns the first subfield when sid is None; returns None at the
    end of the module (callers cross into the next module themselves).
    """
    m = _MODULES_BY_ID.get(mid)
    if m is None:
        return None
    if sid is None:
        return m["fields"][0]
    for i, f in enumerate(m["fields"]):
        if f["id"] == sid:
            return m["fields"][i + 1] if i + 1 < len(m["fields"]) else None
    return None


def next_module(mid: str) -> Module | None:
    """Return the module after mid in order, or None at the end."""
    if mid not in _MODULE_ORDER:
        return None
    i = _MODULE_ORDER.index(mid)
    return MODULES[i + 1] if i + 1 < len(MODULES) else None


def subs_for_module(mid: str) -> list[SubField]:
    """Return all subfields of the given module (empty list if unknown)."""
    m = _MODULES_BY_ID.get(mid)
    return m["fields"] if m else []


def total_subfield_count() -> int:
    """Return the total number of subfields across all modules."""
    return sum(len(m["fields"]) for m in MODULES)


def all_subfield_keys() -> list[str]:
    """Return every answer key "module_id.subfield_id" in order."""
    return [f"{m['id']}.{f['id']}" for m in MODULES for f in m["fields"]]


def is_module_done(mid: str, answers: dict[str, str]) -> bool:
    """True when every subfield of mid has a TRUTHY answer (J1)."""
    m = _MODULES_BY_ID.get(mid)
    return m is not None and all(
        is_truthy_answer(answers.get(f"{mid}.{f['id']}")) for f in m["fields"]
    )


def module_done_ratio(mid: str, answers: dict[str, str]) -> float:
    """Fraction (0..1) of mid's subfields with a TRUTHY answer (J1).

    Placeholder values (占位词典) and empty strings do not count toward
    the numerator — they are semantically absent. Unknown modules return
    0.0 (never finalizable by accident).
    """
    m = _MODULES_BY_ID.get(mid)
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


def is_finalizable(answers: dict[str, str]) -> bool:
    """True when EVERY module exceeds the 50% finalize threshold."""
    return all(is_module_over_half(mid, answers) for mid in module_ids())


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
