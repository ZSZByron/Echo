"""Concept edge vocabulary compiled from v0.4 governance document.

This is a pure static constant module. All edges are faithfully transcribed
from docs/governance/2-A1-v0.4-世界观底层拓扑概念树.md §3.

No LLM generation. No dynamic edges. Closed vocabulary.

Edge name convention: Uses v0.4 original text verbatim (e.g., "DERIVES→骰子.概率分布").
Slot naming: v0.4 uses concept tree names (e.g., 力量.载体.权限映射),
A1 answers use questionnaire tree names (module.subfield). We align during
compilation and note differences in slot_note.

Direction semantics: from_slots = "cause/source", to_slots = "effect/target"
(topological order from v0.4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class EdgeSpec:
    """Specification for a single concept edge from v0.4 §3.

    Attributes:
        name: Edge internal name (uses v0.4 original text, e.g., "DERIVES→骰子.概率分布")
        level: Credibility level (★=rule, ◆=semantic, ◇=structure)
        from_slots: Source slot path(s) using v0.4 concept tree naming
        to_slots: Target slot path(s) using v0.4 concept tree naming
        hint: Human-readable explanation (from v0.4 §3 说明 column)
        rule: Machine-executable rule if applicable (★ edges only)
        slot_note: Alignment notes when concept tree names don't match questionnaire tree
    """

    name: str
    level: Literal["rule", "semantic", "structure"]
    from_slots: list[str]
    to_slots: list[str]
    hint: str = ""
    rule: str = ""
    slot_note: str = ""


# =============================================================================
# EDGE_VOCAB: Faithful transcription from v0.4 §3 派生边总表
# =============================================================================
# Each entry corresponds to one row in the v0.4 §3 table (lines 353-368)
# Column mapping: 级→level / 边→name / 上游→from_slots / 下游→to_slots / 说明→hint
#
# Level counts: 7 ★ (rule) + 5 ◆ (semantic) + 4 ◇ (structure) = 16 total
# =============================================================================

EDGE_VOCAB: list[EdgeSpec] = [
    # ★ Rule edges (7 total) - 纯函数，机器可执行
    EdgeSpec(
        name="DERIVES→骰子.概率分布",
        level="rule",
        from_slots=["世界本体.现实规则"],
        to_slots=["骰子.概率分布"],
        hint="意志→d20；物质→3d6",
        rule="现实规则='意志主导' → d20/d100线性分布；现实规则='物质主导' → 3d6/4dF钟形分布",
        slot_note="v0.4 slot '骰子.概率分布' → A1 answer key '骰子设定.probability_distribution' (module.subfield)",
    ),
    EdgeSpec(
        name="DERIVES→骰子.骰子数量",
        level="rule",
        from_slots=["力量.溯源.影响生灵比例"],
        to_slots=["骰子.骰子数量"],
        hint="本体→固定骰；客体→骰池",
        rule="影响生灵比例='本体·个体资质' → 固定骰数+修正值；影响生灵比例='客体·外界刺激' → 骰池资源管理",
        slot_note="v0.4 slot '力量.溯源.影响生灵比例' → A1 answer key '力量体系.source' ( bundled in source hint)",
    ),
    EdgeSpec(
        name="DERIVES→骰子.判定方式",
        level="rule",
        from_slots=["力量.载体.权限映射"],
        to_slots=["骰子.判定方式"],
        hint="封闭→under；开放→over",
        rule="权限映射='封闭精英·稀有难掌握' → Roll-under；权限映射='开放众生·普及低门槛' → Roll-over+DC",
        slot_note="v0.4 slot '力量.载体.权限映射' → A1 answer key '力量体系.acquire' ( bundled in acquire hint)",
    ),
    EdgeSpec(
        name="DERIVES→骰子.成功判定",
        level="rule",
        from_slots=["玩法.主要行为"],
        to_slots=["骰子.成功判定"],
        hint="战斗→二元；研究→多层",
        rule="主要行为含'战斗' → 二元判定(成功/失败)；主要行为含'研究/探索' → 多层次判定+Blackjack机制",
        slot_note="v0.4 slot '玩法.主要行为' → A1 answer key '玩法设计DNA.core_experience' (映射到核心体验)",
    ),
    EdgeSpec(
        name="DERIVES→骰子.代价机制",
        level="rule",
        from_slots=["力量.代价.反馈回路"],
        to_slots=["骰子.代价机制"],
        hint="残酷→临界陷阱",
        rule="反馈回路含'滥用→变异/非人化' → 临界陷阱/爆炸骰机制",
        slot_note="v0.4 slot '力量.代价.反馈回路' → A1 answer key '力量体系.cost' ( bundled in cost hint)",
    ),
    EdgeSpec(
        name="DERIVES→力量.交互拓扑",
        level="rule",
        from_slots=["世界本体.现实规则"],
        to_slots=["力量.机制.交互拓扑"],
        hint="物质→守恒；意志→非守恒",
        rule="现实规则='物质主导' → 守恒律(等价交换)；现实规则='意志主导' → 非守恒(唯心投射)",
        slot_note="v0.4 slot '力量.机制.交互拓扑' → A1 answer key '力量体系.mechanism' ( bundled in mechanism hint)",
    ),
    EdgeSpec(
        name="COMPILES→Constraint(6维)",
        level="rule",
        from_slots=["第4套各槽"],
        to_slots=["L0 约束节点"],
        hint="按 boundary-spec §2 逐模块编译表",
        rule="根据 boundary-spec §2 编译表，将第4套各槽答案编译为 6 维约束 (RED/LAW/ACT/NAR/WST/SOC)",
        slot_note="v0.4 '第4套各槽' refers to all 10 questionnaire modules in a1_question_tree.py",
    ),
    # ◆ Semantic edges (5 total) - LLM 推断+用户确认
    EdgeSpec(
        name="DERIVES→视觉.建筑/材质",
        level="semantic",
        from_slots=["文明.核心价值", "世界本体.存在物"],
        to_slots=["视觉.建筑风格", "视觉.材质偏好"],
        hint="资源+文化+身份",
        rule="LLM 根据 文明.核心价值 + 世界本体.存在物 推断视觉风格，需用户确认",
        slot_note="v0.4 slots '文明.核心价值'→'文明与社会.core_value', '视觉.建筑风格'→'视觉设计.architecture', '视觉.材质偏好'→'视觉设计.material'",
    ),
    EdgeSpec(
        name="DERIVES→文明.经济",
        level="semantic",
        from_slots=["力量.溯源.本体定义"],
        to_slots=["文明.经济"],
        hint="可交易性",
        rule="LLM 根据 力量.溯源.本体定义(意识体/物理背景/科技/等)推断经济模式(力量可交易性)，需用户确认",
        slot_note="v0.4 slots '力量.溯源.本体定义'→'力量体系.source', '文明.经济'→'文明与社会.economy'",
    ),
    EdgeSpec(
        name="DERIVES→文明.阶层",
        level="semantic",
        from_slots=["力量.载体.权限映射"],
        to_slots=["文明.阶层结构"],
        hint="封闭/开放→分化",
        rule="LLM 根据 力量.载体.权限映射 推断社会阶层分化(封闭→精英统治；开放→扁平化)，需用户确认",
        slot_note="v0.4 slots '力量.载体.权限映射'→'力量体系.acquire', '文明.阶层结构' is not in A1 tree (implicit from economy/conflict)",
    ),
    EdgeSpec(
        name="DERIVES→历史.主剧情4维",
        level="semantic",
        from_slots=["世界本体.起源.起源力量", "世界本体.存在物", "地理.主世界设计", "世界本体.存在物.哲学思想"],
        to_slots=["历史.主剧情.驱动维度", "历史.主剧情.代理维度", "历史.主剧情.舞台维度", "历史.主剧情.归宿维度"],
        hint="驱动/代理/舞台/归宿",
        rule="LLM 根据上游 4 个槽位推断主剧情 4 维度(起源回响/意志载体/空间映射/哲学闭环)，需用户确认",
        slot_note="v0.4 slots use concept tree paths, A1 answer keys: '历史.主剧情'→'历史时间线.main_plot', '地理.主世界设计'→'地理空间.terrain'",
    ),
    EdgeSpec(
        name="DERIVES→IP.类型",
        level="semantic",
        from_slots=["力量.溯源.本体定义", "世界本体.现实规则", "IP.概念"],
        to_slots=["IP.类型"],
        hint="三要素投影（可反向校验）",
        rule="LLM 根据 力量+现实规则+概念 推断 IP 类型(三要素一致性)，可反向校验，需用户确认",
        slot_note="v0.4 slots '力量.溯源.本体定义'→'力量体系.source', 'IP.概念'→'IP定位.concept', 'IP.类型'→'IP定位.world_type'",
    ),
    # ◇ Structure edges (4 total) - 答案值解析展开
    EdgeSpec(
        name="POWER_SATURATES_GEO / POWER_SOURCES_FROM_GEO / RULE_SHAPES_GEO",
        level="structure",
        from_slots=["力量.溯源.本体定义", "世界本体.现实规则", "地理.特殊地理"],
        to_slots=["Geography"],
        hint="★仅A1可建",
        rule="解析 特殊地理 答案值(TREE)，展开为 POWER_SATURATES_GEO / POWER_SOURCES_FROM_GEO / RULE_SHAPES_GEO 三种边",
        slot_note="v0.4 slots '力量.溯源.本体定义'→'力量体系.source', '地理.特殊地理'→'地理空间.special_geo'",
    ),
    EdgeSpec(
        name="GEO_CONTAINS / GEO_ABOVE / GEO_BELOW",
        level="structure",
        from_slots=["地理.主要地形", "地理.垂直层级"],
        to_slots=["Geography 层级子图"],
        hint="层级包含关系",
        rule="解析 主要地形(TREE 大陆→区域→地标) 和 垂直层级(TREE 深空/天空/.../地心)，展开为 GEO_CONTAINS / GEO_ABOVE / GEO_BELOW 边",
        slot_note="v0.4 slots '地理.主要地形'→'地理空间.terrain', '地理.垂直层级'→'地理空间.vertical'",
    ),
    EdgeSpec(
        name="EVENT_CAUSED_BY / GEO_HOSTS_EVENT",
        level="structure",
        from_slots=["历史.关键节点"],
        to_slots=["Event DAG"],
        hint="因果链与空间映射",
        rule="解析 关键节点 答案值(DAG 四元组)，展开为 EVENT_CAUSED_BY(因果链) 和 GEO_HOSTS_EVENT(空间映射) 边",
        slot_note="v0.4 slot '历史.关键节点'→'历史时间线.key_nodes'",
    ),
    EdgeSpec(
        name="FACTION_OPPOSES / ALLIED（复合映射）",
        level="structure",
        from_slots=["文明.冲突"],
        to_slots=["Faction 边"],
        hint="按 §2.L2b 映射表",
        rule="解析 冲突类型 答案值(ENUM)，按 v0.4 §2.L2b 映射表展开为 FACTION_OPPOSES / ALLIED 复合边",
        slot_note="v0.4 slots '文明.冲突'→'文明与社会.conflict', 映射表见 v0.4 §2.L2b (lines 238-245)",
    ),
]

# =============================================================================
# AXIS_SLOTS: Faithful transcription from v0.4 §2 逐层概念树
# =============================================================================
# Each entry corresponds to one AXIS slot definition in v0.4 §2
# Format: (concept_tree_slot_path, [binary_spectrum_value1, binary_spectrum_value2])
#
# Total: 8 AXIS slots (binary spectrum each has exactly 2 values)
# =============================================================================

AXIS_SLOTS: list[tuple[str, list[str]]] = [
    # L0 存在基座
    ("世界本体.起源.起源力量", ["意志型", "物质型"]),
    ("世界本体.现实规则", ["意志主导·拓扑动态可变", "物质主导·拓扑刚性稳定"]),
    # L1 动力学层
    ("力量.溯源.来源底层", ["意志", "物质"]),
    ("力量.溯源.影响生灵比例", ["本体·个体资质", "客体·外界刺激"]),
    ("力量.载体.层级拓扑", ["天赋高势能", "习得低势能"]),
    ("力量.载体.权限映射", ["封闭精英·稀有难掌握", "开放众生·普及低门槛"]),
    ("力量.机制.交互拓扑", ["守恒·等价交换", "非守恒·唯心投射"]),
    ("力量.代价.平衡拓扑", ["肉体损耗", "精神腐蚀"]),
]

# =============================================================================
# Constants for external consumption
# =============================================================================

VOCAB_RELATION_NAMES: frozenset[str] = frozenset(edge.name for edge in EDGE_VOCAB)


# =============================================================================
# Helper functions
# =============================================================================


def get_vocab_by_level(level: Literal["rule", "semantic", "structure"]) -> list[EdgeSpec]:
    """Filter edges by credibility level.

    Args:
        level: One of "rule", "semantic", "structure"

    Returns:
        List of edges matching the specified level
    """
    return [edge for edge in EDGE_VOCAB if edge.level == level]


def is_known_relation(name: str) -> bool:
    """Check if a relation name is in the closed vocabulary.

    Args:
        name: Edge name to check

    Returns:
        True if the edge exists in EDGE_VOCAB, False otherwise
    """
    return name in VOCAB_RELATION_NAMES
