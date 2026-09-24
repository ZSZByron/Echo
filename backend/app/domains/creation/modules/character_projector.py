# -*- coding: utf-8 -*-
"""角色投影器（M3 产出模块 · A2 资产平移）——确定性规则引擎，零 LLM。

证据：`.sisyphus/evidence/a2-plan-mining-a2-specs.md` §2.3；
规格行号 S1:339-358 / S2:340-367 / 四步判别排序法 S2:461-465。

四步判别排序法：
  1. reality_dominant 定调（核心 2 相选择）——世界本体.reality_rule
     物质主导→机制相位定调；意志主导→叙事相位定调；缺→叙事缺省+披露。
  2. main_action 相位命中——力量体系措辞（战斗/对抗→机制；交往/情感→叙事）
     选第二核心相；与第一核心相撞时取对偶相（保持核心恰 2 相）。
  3. 常量/变量分配——设定边界答案→constants（厂家常量）；力量体系.acquire
     →variables（玩家变量）；open_questions 未答项→anchors（留白锚点）。
  4. DiceTemplate 数值注入机制相位（依赖 TD；缺 → DiceRequiredError，
     路由层转 409 missing_dice_template）。

三铁律：同输入同输出；signal_sources 全字段溯源；缺料诚实披露。
封闭枚举 TemplatePhase"不允许添加或修改"。
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.domains.creation.modules.dice_projector import DiceTemplate

# ── 封闭枚举（S2:340-345 逐字——不允许添加或修改）─────────────────────


class TemplatePhase(str, Enum):
    """角色模板 4 相位。不允许添加或修改。"""
    NARRATIVE = "narrative"    # 叙事相位（锚点拓扑）
    MECHANISM = "mechanism"    # 机制相位（流程拓扑）
    RESOURCE = "resource"      # 资源相位（交换拓扑）
    DIRECTION = "direction"    # 定向相位（层级拓扑）


class PhaseContent(BaseModel):
    """相位内容：常量管底线、变量给选择、锚点留白（认知边界总纲）。"""
    phase: TemplatePhase
    priority: int              # 排序优先级 1-4
    is_core: bool              # 核心 2 相（定调结果）
    constants: list[str] = Field(default_factory=list)
    variables: list[str] = Field(default_factory=list)
    anchors: list[str] = Field(default_factory=list)


class CharacterTemplate(BaseModel):
    """TC 图谱投影产物。依赖 DiceTemplate（缺 → 409 missing_dice_template，
    由路由层转契约错误；S2:355-367 逐字适配）。"""
    graph_code: str
    upstream_graph_code: str
    dice_template_code: str
    used_stale: bool = False
    core_phases: list[str]                 # TemplatePhase.value ×2
    secondary_phases: list[str]
    phases: dict[str, PhaseContent]        # key = TemplatePhase.value
    conflict_point: str = ""               # 玩家动机 × 世界哲学
    flavor_concentration: str = ""
    signal_sources: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class DiceRequiredError(Exception):
    """缺骰子模板依赖——路由层必须转 409 missing_dice_template。"""


_MATERIAL_WORDS = ("物质", "物理", "力量", "钢铁", "实体", "身体")
_WILL_WORDS = ("意志", "信念", "精神", "心灵", "情感", "灵魂")
_ACTION_MECHANISM = ("战斗", "对抗", "竞争", "征服", "狩猎")
_ACTION_NARRATIVE = ("交往", "情感", "关系", "探索", "解谜", "成长")

_DEFAULT_ANCHOR = "留白锚点：你的角色有一个未言明的执念——自己填是谁/是什么"


def project_character_template(
    answers: dict[str, str],
    dice: DiceTemplate | None,
    *,
    graph_code: str,
    upstream_graph_code: str,
    used_stale: bool = False,
    open_questions: list[str] | None = None,
) -> CharacterTemplate:
    """四步确定性投影。缺 dice → DiceRequiredError（模块依赖声明）。"""
    if dice is None:
        raise DiceRequiredError(
            "依赖骰子模板：请先生成 dice-template（409 missing_dice_template）")

    warnings: list[str] = []
    signals: dict[str, str] = {}

    def a1(key: str) -> str:
        return (answers.get(key) or "").strip()

    reality_rule = a1("世界本体.reality_rule")
    power_source = a1("力量体系.source") or a1("力量体系.acquire")

    # ── Step1 reality_dominant 定调 ──────────────────────────────────
    material = any(w in reality_rule for w in _MATERIAL_WORDS)
    if reality_rule and material:
        first_core = TemplatePhase.MECHANISM
        core_src = "rule:reality_dominant:material"
    elif reality_rule:
        first_core = TemplatePhase.NARRATIVE
        core_src = "rule:reality_dominant:will"
    else:
        first_core = TemplatePhase.NARRATIVE
        core_src = "default"
        warnings.append("core_phase_defaults_used：世界本体未答，核心相取叙事缺省")

    # ── Step2 main_action 相位命中（核心恰 2 相，撞车取对偶）────────
    if any(w in power_source for w in _ACTION_MECHANISM):
        second_core = TemplatePhase.MECHANISM
        action_src = "rule:main_action:mechanism"
    elif any(w in power_source for w in _ACTION_NARRATIVE):
        second_core = TemplatePhase.NARRATIVE
        action_src = "rule:main_action:narrative"
    else:
        second_core = first_core
        action_src = "default"
    if second_core is first_core:
        second_core = (TemplatePhase.MECHANISM
                       if first_core is TemplatePhase.NARRATIVE
                       else TemplatePhase.NARRATIVE)
    core_phases = [first_core.value, second_core.value]
    secondary = [p.value for p in TemplatePhase
                 if p.value not in core_phases]
    signals["core_phases"] = f"{core_src};{action_src}"

    # ── Step3 常量/变量/锚点分配（S2:464）────────────────────────────
    constants: list[str] = []
    for key in sorted(answers):
        if key.startswith("设定边界.") and answers[key].strip():
            constants.append(answers[key].strip())
    if constants:
        signals["constants"] = "a1:设定边界.*"
    else:
        signals["constants"] = "default"

    variables: list[str] = []
    acquire = a1("力量体系.acquire")
    if acquire:
        variables.append(f"力量获取路径（玩家自选）：{acquire}")
        signals["variables"] = "a1:力量体系.acquire"
    else:
        signals["variables"] = "default"

    anchors = [q for q in (open_questions or []) if q]
    if anchors:
        signals["anchors"] = "a1:open_questions"
    else:
        anchors = [_DEFAULT_ANCHOR]
        signals["anchors"] = "default"
        warnings.append("anchors_default_used：无未答开放问题，锚点取通用留白")

    # ── Step4 DiceTemplate 数值注入机制相位（S2:465）────────────────
    mech_constants = list(constants) + [
        f"属性区间 {dice.stat_floor}-{dice.stat_ceiling}"
        f"（来源 {dice.graph_code}，骰核 {dice.dice_core.value}）",
    ]
    phase_bodies: dict[str, PhaseContent] = {
        TemplatePhase.MECHANISM.value: PhaseContent(
            phase=TemplatePhase.MECHANISM,
            priority=core_phases.index("mechanism") + 1
            if "mechanism" in core_phases else 3,
            is_core="mechanism" in core_phases,
            constants=mech_constants,
            variables=variables,
            anchors=anchors,
        ),
        TemplatePhase.NARRATIVE.value: PhaseContent(
            phase=TemplatePhase.NARRATIVE,
            priority=core_phases.index("narrative") + 1
            if "narrative" in core_phases else 3,
            is_core="narrative" in core_phases,
            constants=list(constants),
            variables=variables,
            anchors=anchors,
        ),
        TemplatePhase.RESOURCE.value: PhaseContent(
            phase=TemplatePhase.RESOURCE, priority=3, is_core=False,
            constants=list(constants),
            variables=variables
            or ["资源获取与消耗方式（玩家自选）"],
            anchors=anchors,
        ),
        TemplatePhase.DIRECTION.value: PhaseContent(
            phase=TemplatePhase.DIRECTION, priority=4, is_core=False,
            constants=list(constants),
            variables=["角色弧光方向（玩家自选）"],
            anchors=anchors,
        ),
    }
    signals["variables"] = signals.get("variables", "default")
    signals["dice_injection"] = f"a1:{dice.graph_code}"

    conflict_point = (a1("角色.desire") or a1("角色.identity")
                      or a1("IP定位.name"))
    flavor = a1("IP定位.tone") or a1("视觉设计.style") or ""

    # priority 归一：核心 1-2、次要 3-4（排序确定性）
    priorities = iter([1, 2, 3, 4])
    for value in core_phases + secondary:
        phase_bodies[value].priority = next(priorities)

    return CharacterTemplate(
        graph_code=graph_code,
        upstream_graph_code=upstream_graph_code,
        dice_template_code=dice.graph_code,
        used_stale=used_stale or dice.used_stale,
        core_phases=core_phases,
        secondary_phases=secondary,
        phases=phase_bodies,
        conflict_point=conflict_point,
        flavor_concentration=flavor,
        signal_sources=signals,
        warnings=warnings,
    )
