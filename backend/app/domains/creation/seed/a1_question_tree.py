"""A1 two-layer question tree — 10 modules x subfields (sequential).

Authority: .sisyphus/drafts/A模块层级图-含断点.md 第4套（世界观拓扑维度）.
Answer keys use "module_id.subfield_id" (dot-separated), e.g.
"IP定位.name". Subfield ids are stable english slugs; labels are
Chinese display names.

Module order is locked (test_module_ids_match_spec):
    IP定位 / 世界本体 / 力量体系 / 地理空间 / 文明与社会 /
    历史时间线 / 视觉设计 / 玩法设计DNA / 骰子设定 / AI生成边界
"""
from __future__ import annotations

from typing import TypedDict


class SubField(TypedDict):
    id: str
    label: str
    question: str
    hint: str


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
            },
            {
                "id": "concept",
                "label": "核心概念",
                "question": "这个世界观的核心概念是什么？",
                "hint": "哲学内核 + 剧情冲突，一句话概括。",
            },
            {
                "id": "world_type",
                "label": "类型",
                "question": "世界观的分类类型是什么？",
                "hint": "力量 + 物质 + 哲学三要素的组合类型。",
            },
            {
                "id": "core_experience",
                "label": "核心体验",
                "question": "玩家在世界中的核心体验是什么？",
                "hint": "主要行为 + 目标，玩家最常做什么。",
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
            },
            {
                "id": "existence",
                "label": "存在物",
                "question": "世界中主要存在哪些事物类别？",
                "hint": "力量体系 / 宇宙学 / 哲学思想 / 其他。",
            },
            {
                "id": "reality_rule",
                "label": "现实规则",
                "question": "世界由意志还是物质主导？",
                "hint": "意志主导（信念改变现实）或物质主导（资源驱动）。",
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
            },
            {
                "id": "acquire",
                "label": "获取方式",
                "question": "力量如何被获取？",
                "hint": "学习 / 觉醒 / 仪式 / 科研；获取拓扑是封闭精英还是开放众生。",
            },
            {
                "id": "mechanism",
                "label": "机制维度",
                "question": "力量交互遵循什么法则？",
                "hint": "守恒（等价交换）↔ 非守恒（唯心投射）；排他性（科技vs魔法互斥）。",
            },
            {
                "id": "cost",
                "label": "代价维度",
                "question": "使用力量需要付出什么代价？",
                "hint": "承载vs操作关系；反馈回路（变异/非人化）；物理损耗或精神腐蚀。",
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
            },
            {
                "id": "vertical",
                "label": "垂直层级",
                "question": "世界的垂直空间如何分层？",
                "hint": "深空 / 天空 / 高山 / 地面 / 地下 / 地心。",
            },
            {
                "id": "special_geo",
                "label": "特殊地理",
                "question": "有哪些塑造规则的特殊地理？",
                "hint": "shaping_rules + power_sources，法则破碎区等。",
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
            },
            {
                "id": "conflict",
                "label": "冲突来源",
                "question": "社会的主要冲突来源是什么？",
                "hint": "资源 / 信仰 / 种族 / 文化 / 权利 / 特殊冲突。",
            },
            {
                "id": "faction_type",
                "label": "势力类型",
                "question": "主要势力采用什么政治类型？",
                "hint": "政体形式：神权 / 议会 / 帝国 / 部落等。",
            },
            {
                "id": "economy",
                "label": "经济",
                "question": "经济建立在什么之上？",
                "hint": "力量物质化（力量可交易？）+ 自然资源。",
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
            },
            {
                "id": "key_nodes",
                "label": "关键节点",
                "question": "历史上有哪些关键节点事件？",
                "hint": "每个节点标注 severity（COSMIC/MAJOR/REGIONAL/MINOR）"
                        "+ 发生地 + 涉及势力 + 因果上游。",
            },
            {
                "id": "main_plot",
                "label": "主剧情",
                "question": "当前时代的主剧情线是什么？",
                "hint": "驱动维度（起源回响）+ 归宿维度（哲学闭环：循环或衰败）。",
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
            },
            {
                "id": "architecture",
                "label": "建筑风格",
                "question": "建筑风格是什么样的？",
                "hint": "由资源 + 文化风格 + 社会身份共同决定。",
            },
            {
                "id": "material",
                "label": "材质偏好",
                "question": "世界偏好的材质语言是什么？",
                "hint": "资源 + 特殊动植物 + 文化传统。",
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
            },
            {
                "id": "main_action",
                "label": "主要行为",
                "question": "玩家的主要行为是什么？",
                "hint": "探索 / 战斗 / 研究 / 提升 的配比。",
            },
            {
                "id": "growth",
                "label": "成长方式",
                "question": "角色如何成长？",
                "hint": "量变 / 质变 / 哲学 / 因果 / 探索。",
            },
            {
                "id": "growth_end",
                "label": "成长尽头",
                "question": "成长的终点是什么？",
                "hint": "社会性 / 法则性 / 哲学性终点。",
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
            },
            {
                "id": "dice_count",
                "label": "骰子数量",
                "question": "力量来源映射到什么骰子数量？",
                "hint": "本体→固定骰；客体→骰池。",
            },
            {
                "id": "check_mode",
                "label": "判定方式",
                "question": "获取方式映射到什么判定方式？",
                "hint": "封闭→Roll-under；开放→Roll-over。",
            },
            {
                "id": "success_check",
                "label": "成功判定",
                "question": "玩法行为映射到什么成功判定？",
                "hint": "战斗→二元判定；研究→多层次判定。",
            },
            {
                "id": "cost_mech",
                "label": "代价机制",
                "question": "哲学平衡映射到什么代价机制？",
                "hint": "残酷世界观→临界陷阱机制。",
            },
        ],
    },
    {
        "id": "AI生成边界",
        "label": "AI生成边界",
        "fields": [
            {
                "id": "generable",
                "label": "可生成范围",
                "question": "AI 可以生成哪些内容？",
                "hint": "A2分区 / A3场景 / NPC / 支线 / 视觉变体。",
            },
            {
                "id": "immutable",
                "label": "不可改变范围",
                "question": "哪些内容 AI 不可改变？",
                "hint": "IP定位 / 世界本体 / 力量骨架 / 地理骨架 / 主线 / 视觉 / 玩法。",
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
    """True when every subfield of mid has a key present in answers."""
    m = _MODULES_BY_ID.get(mid)
    return m is not None and all(
        f"{mid}.{f['id']}" in answers for f in m["fields"]
    )
