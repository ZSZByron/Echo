# -*- coding: utf-8 -*-
"""骰子投影器（M3 产出模块 · A2 资产平移）——确定性规则引擎，零 LLM。

证据：`.sisyphus/evidence/a2-plan-mining-a2-specs.md` §2.2/§6.3；
规格行号 S1:292-334 / S2:293-337 / 四步法 S2:449-466。

四步法（S2:449-457 逐字适配）：
  Step1 骰子核心：骰子设定 4 字段已填 → 直投；缺 → reality_rule 判定
        （物质主导→d20_modifier；意志→dice_pool/percentage 按 probability
        措辞）；全缺 → d20_modifier 缺省 + ledger 披露 dice_defaults_used。
  Step2 等级系统：累积型/跃迁型词法计数（零 LLM）→ 70% 阈值判定
        （承袭 2-A2 §6.3.2 比例法）；无信号 → tier 缺省 + 披露。
  Step3 难度系统：等级系统联动（slot→counter_value 五档 DC 表；
        tier→contextual 五梯度；hybrid→双轨）。
  Step4 边界钳制：cst_* 约束文本存在 → 钳 stat_floor/ceiling；
        稀疏 → 保守缺省 + 披露。

三铁律：同输入同输出（确定性断言测试）；signal_sources 全字段溯源；
诚实可观测（降级/缺料全部 warnings 披露）。封闭枚举"不允许添加或修改"。
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ── 封闭枚举三件（S2:293-305 逐字——不允许添加或修改）──────────────────


class DiceCoreType(str, Enum):
    """骰子核心类型。不允许添加或修改。"""
    D20_MODIFIER = "d20_modifier"   # 数值骰（物质主导）
    DICE_POOL = "dice_pool"         # 骰池计数（意志主导）
    PERCENTAGE = "percentage"       # 百分比对冲（意志主导）


class GrowthSystem(str, Enum):
    """等级系统。不允许添加或修改。"""
    SLOT = "slot"
    TIER = "tier"
    HYBRID = "hybrid"


class DifficultySystem(str, Enum):
    """难度系统。不允许添加或修改。"""
    COUNTER_VALUE = "counter_value"
    CONTEXTUAL = "contextual"
    HYBRID = "hybrid"


DEFAULT_STAT_FLOOR = 10
DEFAULT_STAT_CEILING = 20


class DifficultyTier(BaseModel):
    """五档对照表行（GM 直查，S2:307-311）。"""
    label: str            # 日常/简单/标准/困难/极限
    modifier: int         # 挑战系数（对抗数值用）
    gradient: int         # 情境梯度 1-5（情境阻力用）
    description: str      # GM 参考说明


class DiceTemplate(BaseModel):
    """TD 图谱投影产物。全部字段由确定性规则从 A1 答案推导，零 LLM
    （S2:313-337 逐字适配；world_ref → upstream_graph_code）。"""

    graph_code: str                        # IPxxxx-TD{n}-v{n}（发号器产出）
    upstream_graph_code: str               # 消费的 A1 W 图谱码
    used_stale: bool = False               # 消费 stale 上游留痕（铁律）
    # 骰子五链
    dice_core: DiceCoreType
    dice_source: str                       # 骰子来源描述
    check_mode: str = ""                   # 判定方式（直投 骰子设定.check_mode）
    success_check: str = ""                # 成功判定（直投 success_check）
    cost_mechanism: str = ""               # 代价机制（源：力量体系.cost）
    # 等级系统
    growth_system: GrowthSystem
    level_cap: int | None = None
    tier_labels: list[str] = Field(
        default_factory=lambda: ["凡人", "精英", "英雄", "传奇", "神话"])
    modifier_range: tuple[int, int] = (-2, 5)
    # 难度系统
    difficulty_system: DifficultySystem
    difficulty_table: list[DifficultyTier]
    # 数值边界（cst_* 约束钳制；稀疏时保守缺省+披露）
    stat_floor: int = DEFAULT_STAT_FLOOR
    stat_ceiling: int = DEFAULT_STAT_CEILING
    # 溯源与披露
    signal_sources: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


# ── 词法信号表（确定性；迭代序固定 → 同输入同输出）─────────────────────

_MATERIAL_WORDS = ("物质", "物理", "力量", "钢铁", "实体", "身体")
_WILL_WORDS = ("意志", "信念", "精神", "心灵", "情感", "灵魂")
_PCT_WORDS = ("百分比", "百分数", "%", "百分骰")
_POOL_WORDS = ("骰池", "池判定", "成功数")
_SLOT_WORDS = ("槽位", "技能槽", "配置位", "解锁槽")
_CUMULATIVE_WORDS = ("经验", "积累", "累积", "成长", "训练", "磨炼", "熟练")
_DISCRETE_WORDS = ("天赋", "血统", "觉醒", "传承", "顿悟", "血脉",
                   "跃迁", "突破", "质变")

#: 五档对照表（modifier 单调、落在默认钳制区间 (-2,5)；gradient 1-5）。
_FIVE_TIERS: tuple[tuple[str, int, int, str], ...] = (
    ("日常", -2, 1, "常规事务，多数角色可直接完成"),
    ("简单", -1, 2, "略需技巧，失败代价轻微"),
    ("标准", 0, 3, "常规冒险挑战，成败各半的基准线"),
    ("困难", 2, 4, "需要专门能力或团队协作"),
    ("极限", 5, 5, "传奇级挑战，失败代价惨重"),
)


def _difficulty_table(system: DifficultySystem) -> list[DifficultyTier]:
    """Step3 联动表：同一五档骨架按系统换语义（确定性）。"""
    rows = []
    for label, modifier, gradient, base in _FIVE_TIERS:
        if system is DifficultySystem.COUNTER_VALUE:
            desc = f"DC 对抗：基准值{modifier:+d}（{base}）"
        elif system is DifficultySystem.CONTEXTUAL:
            desc = f"情境梯度 {gradient}/5（{base}）"
        else:
            desc = f"双轨：DC {modifier:+d} / 梯度 {gradient}/5（{base}）"
        rows.append(DifficultyTier(
            label=label, modifier=modifier, gradient=gradient, description=desc))
    return rows


def _wording_signal(text: str, words: tuple[str, ...]) -> bool:
    return any(w in text for w in words)


def _clamp_from_constraints(
    constraints: list[str] | None, warnings: list[str],
) -> tuple[int, int, int | None]:
    """Step4 边界钳制：从 cst_* 约束文本提取数值；稀疏 → 缺省+披露。"""
    floor, ceiling, level_cap = DEFAULT_STAT_FLOOR, DEFAULT_STAT_CEILING, None
    if constraints:
        for c in constraints:
            m = re.search(r"不低于\s*(\d+)", c)
            if m:
                floor = int(m.group(1))
            m = re.search(r"(?:不超过|上限为?|至多)\s*(\d+)", c)
            if m:
                ceiling = int(m.group(1))
            m = re.search(r"等级?上限\s*(\d+)", c)
            if m:
                level_cap = int(m.group(1))
        if floor != DEFAULT_STAT_FLOOR or ceiling != DEFAULT_STAT_CEILING:
            return floor, ceiling, level_cap
    warnings.append("stat_bounds_default_used：约束稀疏，属性边界取保守缺省")
    return floor, ceiling, level_cap


def project_dice_template(
    answers: dict[str, str],
    *,
    graph_code: str,
    upstream_graph_code: str,
    used_stale: bool = False,
    constraints: list[str] | None = None,
) -> DiceTemplate:
    """四步确定性投影（同输入同输出）。answers 键 = "{module}.{subfield}"。"""
    warnings: list[str] = []
    signals: dict[str, str] = {}

    def a1(key: str) -> str:
        return (answers.get(key) or "").strip()

    # ── Step1 骰子核心 ────────────────────────────────────────────────
    probability = a1("骰子设定.probability")
    check_mode = a1("骰子设定.check_mode")
    success_check = a1("骰子设定.success_check")
    dice_count = a1("骰子设定.dice_count")
    reality_rule = a1("世界本体.reality_rule")
    direct_filled = any((probability, dice_count, check_mode, success_check))

    if _wording_signal(probability, _PCT_WORDS):
        core, core_src = DiceCoreType.PERCENTAGE, "a1:骰子设定.probability"
    elif _wording_signal(probability, _POOL_WORDS):
        core, core_src = DiceCoreType.DICE_POOL, "a1:骰子设定.probability"
    elif direct_filled:
        core, core_src = DiceCoreType.D20_MODIFIER, "a1:骰子设定.probability"
    elif reality_rule:
        # reality_rule 判定（S2:452）：物质主导→d20；意志→骰池/百分比
        if _wording_signal(reality_rule, _MATERIAL_WORDS):
            core, core_src = DiceCoreType.D20_MODIFIER, "rule:reality_dominant"
        else:
            core, core_src = DiceCoreType.DICE_POOL, "rule:reality_dominant"
    else:
        core, core_src = DiceCoreType.D20_MODIFIER, "default"
        warnings.append(
            "dice_defaults_used：骰子设定与世界本体均未答，骰核取 d20_modifier 缺省")

    # ── Step2 等级系统（词法计数，零 LLM）────────────────────────────
    # S2:454 映射：定量/累积偏好→slot（台阶渐进）；定性/跃迁偏好→tier
    # （跳跃质变）——SLOT/TIER 枚举注释逐字（GrowthSystem docstring）。
    growth_texts = [v for k, v in sorted(answers.items()) if v]
    cum = sum(_wording_signal(t, _CUMULATIVE_WORDS) for t in growth_texts)
    disc = sum(_wording_signal(t, _DISCRETE_WORDS) for t in growth_texts)
    slot_hit = any(_wording_signal(t, _SLOT_WORDS) for t in growth_texts)
    total = cum + disc
    dna_growth = a1("玩法设计DNA.growth")
    if dna_growth:
        # 玩法设计DNA.growth 直投信号（S2:454）：定量→slot / 定性→tier /
        # 双现→hybrid——先于词法兜底（signal_requirements optional 档）。
        quantitative = _wording_signal(dna_growth, ("定量", "数值"))
        qualitative = _wording_signal(dna_growth, ("定性", "位阶", "质变"))
        if quantitative and qualitative:
            growth, growth_src = GrowthSystem.HYBRID, "a1:玩法设计DNA.growth"
        elif quantitative:
            growth, growth_src = GrowthSystem.SLOT, "a1:玩法设计DNA.growth"
        else:
            growth, growth_src = GrowthSystem.TIER, "a1:玩法设计DNA.growth"
    elif slot_hit and total:
        growth, growth_src = GrowthSystem.HYBRID, "rule:lexical_slot_ratio"
    elif slot_hit:
        growth, growth_src = GrowthSystem.SLOT, "rule:lexical_slot"
    elif total and (cum / total) >= 0.7:
        growth, growth_src = GrowthSystem.SLOT, "rule:lexical_ratio_0.7"
    elif total:
        growth, growth_src = GrowthSystem.TIER, "rule:lexical_ratio_0.7"
    else:
        growth, growth_src = GrowthSystem.TIER, "default"
        warnings.append(
            "growth_defaults_used：无等级信号，等级系统取 tier 缺省（位阶制）")

    # ── Step3 难度系统联动（S2:456）──────────────────────────────────
    difficulty = {
        GrowthSystem.SLOT: DifficultySystem.COUNTER_VALUE,
        GrowthSystem.TIER: DifficultySystem.CONTEXTUAL,
        GrowthSystem.HYBRID: DifficultySystem.HYBRID,
    }[growth]
    signals["difficulty_system"] = f"rule:linkage:{growth.value}"

    # ── Step4 边界钳制 ───────────────────────────────────────────────
    floor, ceiling, level_cap = _clamp_from_constraints(constraints, warnings)

    # ── 五链 signal_sources 全字段溯源（S1:331-333 三形态）──────────
    signals.update({
        "dice_core": core_src,
        "dice_source": (f"a1:骰子设定.probability" if probability
                        else ("rule:reality_dominant" if reality_rule
                              else "default")),
        "check_mode": "a1:骰子设定.check_mode" if check_mode else "default",
        "success_check": "a1:骰子设定.success_check" if success_check else "default",
        "cost_mechanism": "a1:力量体系.cost" if a1("力量体系.cost") else "default",
        "growth_system": growth_src,
    })

    return DiceTemplate(
        graph_code=graph_code,
        upstream_graph_code=upstream_graph_code,
        used_stale=used_stale,
        dice_core=core,
        dice_source=dice_count or probability or reality_rule or "缺省骰核",
        check_mode=check_mode,
        success_check=success_check,
        cost_mechanism=a1("力量体系.cost"),
        growth_system=growth,
        level_cap=level_cap,
        difficulty_system=difficulty,
        difficulty_table=_difficulty_table(difficulty),
        stat_floor=floor,
        stat_ceiling=ceiling,
        signal_sources=signals,
        warnings=warnings,
    )
