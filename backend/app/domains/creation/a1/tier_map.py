"""A1 v0.5 content-tier mapping (C5 contract data plane).

Authority: docs/governance/2-A1-v0.5-内容图谱化统一模型与契约.md §3.
Tier values are within [0, 6] — the seven-layer tier RANGE stays closed
(甲计划 DN2 默认：模块池新模块复用既有 tier 值映射，不新增层；翻案记录
归 D14）。Coverage 契约自 M1 起为池语义：pool 内模块必有 tier。
"""
from __future__ import annotations

from app.domains.creation.seed.a1_question_tree import module_ids

# tier 0-6 七层：存在基座 / 动力学 / 显现 / 时间 / 表达 / 命题 / 治理
TIER_MAP: dict[str, int] = {
    "世界本体": 0,
    "力量体系": 1,
    "地理空间": 2,
    "文明与社会": 2,
    "历史时间线": 3,
    "视觉设计": 4,
    "玩法设计DNA": 4,
    "骰子设定": 4,
    "IP定位": 5,
    "设定边界": 6,
    # M2 故事模块（DN2 默认：复用既有层值，不新增层——翻案记录归 D14）：
    # 剧情→历史时间线层（v6 §2.7 防线 2 逐字）；角色→文明与社会层。
    "剧情": 3,
    "角色": 2,
    # M3 产出模块（DN2 默认：复用既有层值——池覆盖契约要求池内模块必有
    # tier；产出模块不进图谱层级渲染，仅满足池闭集）：
    # 主模组文字版→治理/边界层（聚合交付物）；骰子投影→玩法层（同骰子设定）；
    # 角色投影→文明与社会层（同角色）。
    "主模组文字版": 6,
    "骰子投影": 4,
    "角色投影": 2,
    # §96 池注册补齐（D18 缓期生成管线）：L2×2 沿用上游层级
    # （玩法设计完整形态→玩法层 / 商业分析报告→商业层）；
    # L3×3 派生产出沿用消费源层级（场景→地理 / 资产→玩法视觉 /
    # 叙事→时代），不新增层级语义。
    "玩法设计完整形态": 4,
    "商业分析报告": 5,
    "场景扩写": 2,
    "资产管线": 4,
    "叙事渲染": 3,
}

MIN_TIER = 0
MAX_TIER = 6


def module_tier_coverage() -> list[str]:
    """Pool-semantics coverage check: every MODULE_POOL module must have a tier.

    Returns missing ids (empty when full coverage). 池开放、tier 值闭集：
    新入池模块必须复用 [0,6] 既有层值（DN2），不得新增第 8 层。
    """
    from app.domains.creation.shared.module_registry import MODULE_POOL

    return sorted(mid for mid in MODULE_POOL if mid not in TIER_MAP)
