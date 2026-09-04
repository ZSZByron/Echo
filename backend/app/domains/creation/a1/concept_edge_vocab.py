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
# Level counts: §3 总表 7 ★ (rule) + 5 ◆ (semantic) + 4 ◇ (structure) = 16
#             + §2 槽位注册表 tier 间派生边 1 ★ (rule) + 9 ◆ (semantic) = 10
# 总计: 26 edges (8 rule + 14 semantic + 4 structure)
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
    # =========================================================================
    # Tier 间派生边（增量编译自 v0.4 §2 槽位注册表「上游依据→下游派生」列）
    # =========================================================================
    # §3 总表未覆盖的 §2 上下游链接，按 tier 映射（v0.5 §3）跨模块补入：
    #   tier0 世界本体 / tier1 力量体系 / tier2 地理空间+文明与社会 /
    #   tier3 历史时间线 / tier4 视觉+玩法 / tier5 IP定位 / tier6 设定边界
    # 命名采用设计计划 §5.1 形状范本的中文短边名（机器可读常量，仍封闭）
    # =========================================================================
    # ◆ Tier-spanning semantic edges (9 total)
    EdgeSpec(
        name="力量源自",
        level="semantic",
        from_slots=["世界本体.起源.起源力量"],
        to_slots=["力量.溯源"],
        hint="力量源头指向起源设定",
        rule="LLM 依据 起源力量(意志型/物质型) 推断力量体系的来源底层，需用户确认",
        slot_note="v0.4 §2 L0: 起源力量 下游 力量.溯源(流动拓扑)；tier0→tier1；A1 keys '世界本体.origin'→'力量体系.source'",
    ),
    EdgeSpec(
        name="中心位于",
        level="semantic",
        from_slots=["地理.主世界设计.架构维度"],
        to_slots=["世界本体.起源.起源力量"],
        hint="世界结构的中心=起源物",
        rule="LLM 依据 架构维度(浮岛/同心球/世界树) 推断世界中心与起源物的空间对应，需用户确认",
        slot_note="设计计划 §5.1 范本边；tier2→tier0；'地理空间.terrain'→'世界本体.origin'",
    ),
    EdgeSpec(
        name="争夺焦点",
        level="semantic",
        from_slots=["文明.冲突"],
        to_slots=["地理.特殊地理"],
        hint="冲突围绕的地理目标",
        rule="LLM 依据 冲突类型 推断各方争夺的地理焦点(特殊地理/高势能区)，需用户确认",
        slot_note="设计计划 §5.1 范本边；tier2→tier2 跨模块；'文明与社会.conflict'→'地理空间.special_geo'",
    ),
    EdgeSpec(
        name="纪元塑史",
        level="semantic",
        from_slots=["地理.主世界设计.纪元维度"],
        to_slots=["历史.事件图"],
        hint="事件图拓扑形态与纪元设定一致（进步→链/循环→环/虚无→熵增链）",
        rule="LLM 依据 纪元维度(创世阶段/循环机制) 推断事件图拓扑形态，v0.4 §2 标注为[校验]，需用户确认",
        slot_note="v0.4 §2 L3: 历史事件图 上游 主世界.纪元维度；tier2→tier3；'地理空间.terrain'→'历史时间线.key_nodes'",
    ),
    EdgeSpec(
        name="时间起于",
        level="semantic",
        from_slots=["世界本体.起源.起源时间线"],
        to_slots=["历史.长度"],
        hint="历史时间轴起点=起源时间线",
        rule="LLM 依据 起源时间线 推断历史长度与 era 划分起点，需用户确认",
        slot_note="v0.4 §2 L0: 起源时间线 下游 历史.time_span；tier0→tier3；'世界本体.origin'→'历史时间线.length'",
    ),
    EdgeSpec(
        name="存在塑力",
        level="semantic",
        from_slots=["世界本体.存在物"],
        to_slots=["力量.载体.层级拓扑"],
        hint="存在物差异→力量分布（龙→天赋拓扑；人类→习得拓扑）",
        rule="LLM 依据 存在物分类 推断力量层级分化形态，需用户确认",
        slot_note="v0.4 §2 L0: 存在物 下游 力量.层级拓扑；tier0→tier1；'世界本体.existence'→'力量体系.acquire'",
    ),
    EdgeSpec(
        name="视觉投影",
        level="semantic",
        from_slots=["IP.概念", "地理.主世界设计", "文明.核心价值"],
        to_slots=["视觉.关键词"],
        hint="风格DNA=概念+地理+文明的投影",
        rule="LLM 依据 IP.概念 + 地理 + 文明.核心价值 推断视觉风格关键词，需用户确认",
        slot_note="v0.4 §2 L4: 视觉.关键词 上游 IP.概念+地理+文明；tier5/2→tier4；'视觉.关键词'→'视觉设计.style'",
    ),
    EdgeSpec(
        name="身份锚定",
        level="semantic",
        from_slots=["文明.势力类型"],
        to_slots=["玩法.玩家身份"],
        hint="社会→维度→超越三阶段分别锚定 L2/L1宇宙学/L0哲学",
        rule="LLM 依据 势力类型 推断玩家身份的社会位置与超越路径，需用户确认",
        slot_note="v0.4 §2 L4: 玩法.玩家身份 上游 文明.势力；tier2→tier4；'文明与社会.faction'→'玩法设计DNA.player_role'",
    ),
    EdgeSpec(
        name="成长映射",
        level="semantic",
        from_slots=["力量.机制.交互拓扑", "IP.概念", "历史.主剧情.归宿维度"],
        to_slots=["玩法.成长方式", "玩法.成长尽头"],
        hint="量变/质变→成长路径；归宿→成长尽头（社会性/法则性/哲学性）",
        rule="LLM 依据 力量.机制 + IP.概念 + 历史.归宿 推断成长方式与成长尽头拓扑，需用户确认",
        slot_note="v0.4 §2 L4: 成长方式/成长尽头 上游链；tier1/5/3→tier4；'玩法设计DNA.growth'",
    ),
    # ★ Tier-spanning rule edge (1 total) - 确定性编译
    EdgeSpec(
        name="CONSTRAINT_LIMITS（边界锚定）",
        level="rule",
        from_slots=["边界.不可变集"],
        to_slots=["IP定位", "世界本体", "力量体系", "地理空间", "历史时间线", "视觉设计", "玩法设计DNA"],
        hint="锚定不可变集声明的全部节点（v0.4 §2 L6）",
        rule="解析 边界.不可变集 锁定清单，对清单内每个模块节点建 CONSTRAINT_LIMITS 锚定边（确定性编译）",
        slot_note="v0.4 §2 L6: 边界.不可变集 CONSTRAINT_LIMITS 边；tier6→tier0-4；A1 key '设定边界.immutable_core'",
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
