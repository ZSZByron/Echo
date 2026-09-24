# -*- coding: utf-8 -*-
"""甲 M3：产出模块池清单数据（family="output"）。

镜像 M2 ``seed/story_modules.py`` 的数据落位范式：本文件是**纯数据**（不
import module_registry，防依赖回头），由 ``module_registry`` 直接 import
入池——与 STORY_MODULES 同构。

``signal_requirements`` 语义（详细设计 §2.3 L174 逐字）：
- ``required``：信号缺失 → 409 upstream_missing；
- ``hard``：前置**产物**依赖缺失 → 409（角色投影 ← 骰子投影产物，契约键
  missing_dice_template S1:247；主模组 ⑦⑧节 ← TD/TC 投影）；
- ``optional``：缺失 → 保守缺省 + ledger 披露（骰子四步法 S2:449-466）。

键 = 字段级信号（"{module}.{subfield}"，S2:131-142 ★ 投影信号标注版
信号源地图转译；骰子五链：骰子设定 / 世界本体.reality_rule /
玩法设计DNA.growth / 力量体系.cost）。产出模块不进任何 Recipe（终局
生产者非问卷模块），仅经 a1_routes 端点在 finalize 后按需触发。
"""
from __future__ import annotations

from typing import TypedDict

#: 信号依赖档位闭集（H §2.2 L174：required / optional / hard）。
SIGNAL_LEVELS = ("required", "optional", "hard")


class OutputModuleDef(TypedDict):
    """产出模块池条目（ModuleDef 数据面 + signal_requirements）。"""

    id: str
    label: str
    signal_requirements: dict[str, str]


#: 产出模块族（L2×5 + L3×3，plan §96 命名逐字锁定）。
#: 清单序 = plan §96 产出序：
#: L2（主模组文字版/骰子投影/角色投影/玩法设计完整形态/商业分析报告）
#: → L3（场景扩写/资产管线/叙事渲染）。
#: L2×2 + L3×3 = 池注册先行（Must Have §96），
#: 产出管线归后续波次（D18 台账记录）。
OUTPUT_MODULES: list[OutputModuleDef] = [
    {
        "id": "主模组文字版",
        "label": "主模组文字版",
        # finalize 八步输入信号（S1:401）：缺省走骨架披露，不 409
        "signal_requirements": {
            "历史时间线.main_plot": "optional",
            "世界本体.reality_rule": "optional",
            "文明与社会.faction_type": "optional",
            "玩法设计DNA.player_role": "optional",
            "设定边界.immutable_core": "optional",
            "骰子投影": "hard",      # ⑦骰子规则节：TD 投影存在则直投
            "角色投影": "hard",      # ⑧角色创建指南节：TC 投影存在则直投
        },
    },
    {
        "id": "骰子投影",
        "label": "骰子投影",
        # 五链信号（S2:449-457）：全 optional——四步法逐级缺省+披露，零 LLM
        "signal_requirements": {
            "骰子设定.probability": "optional",
            "骰子设定.check_mode": "optional",
            "骰子设定.success_check": "optional",
            "世界本体.reality_rule": "optional",
            "力量体系.cost": "optional",
            "玩法设计DNA.growth": "optional",
        },
    },
    {
        "id": "角色投影",
        "label": "角色投影",
        # 骰子产物依赖 = hard（S1:247：缺骰子→409 missing_dice_template）
        "signal_requirements": {
            "骰子投影": "hard",
            "世界本体.reality_rule": "optional",
            "力量体系.acquire": "optional",
            "设定边界.immutable_core": "optional",
            "角色.identity": "optional",
        },
    },
    {
        # L2 池注册先行（D18 缓期生成管线）：依赖玩法设计DNA 全字段信号；
        # 骰子投影产物 hard（玩法数值层直投，缺 → 409）
        "id": "玩法设计完整形态",
        "label": "玩法设计完整形态",
        "signal_requirements": {
            "玩法设计DNA.player_role": "optional",
            "玩法设计DNA.growth": "optional",
            "玩法设计DNA.session_flow": "optional",
            "玩法设计DNA.moment_design": "optional",
            "骰子投影": "hard",
            "世界本体.reality_rule": "optional",
        },
    },
    {
        # L2 池注册先行（D18 缓期生成管线）：商业向字段全 optional，
        # 缺失走保守缺省 + ledger 披露
        "id": "商业分析报告",
        "label": "商业分析报告",
        "signal_requirements": {
            "IP定位.positioning": "optional",
            "IP定位.audience": "optional",
            "IP定位.differentiation": "optional",
            "IP定位.tone": "optional",
            "世界本体.core_conflict": "optional",
        },
    },
    {
        # L3 池注册先行（D18 缓期生成管线）：场景扩写消费主模组文字版/
        # 定稿图谱产物——hard 依赖（缺文档 → 409）
        "id": "场景扩写",
        "label": "场景扩写",
        "signal_requirements": {
            "主模组文字版": "hard",
            "地理空间.terrain": "optional",
            "历史时间线.main_plot": "optional",
        },
    },
    {
        # L3 池注册先行（D18 缓期生成管线）：资产管线消费场景扩写产物
        "id": "资产管线",
        "label": "资产管线",
        "signal_requirements": {
            "场景扩写": "hard",
            "主模组文字版": "optional",
        },
    },
    {
        # L3 池注册先行（D18 缓期生成管线）：叙事渲染消费圆景/背景树产物
        "id": "叙事渲染",
        "label": "叙事渲染",
        "signal_requirements": {
            "圆景": "hard",
            "背景树": "hard",
            "场景扩写": "optional",
        },
    },
]

#: 产出模块 id 闭集（清单序锁定，plan §96 L2 序）。
OUTPUT_MODULE_IDS: tuple[str, ...] = tuple(m["id"] for m in OUTPUT_MODULES)

_OUTPUT_BY_ID: dict[str, OutputModuleDef] = {m["id"]: m for m in OUTPUT_MODULES}


def get_output_module(mid: str) -> OutputModuleDef | None:
    """Return the output module def for mid, or None."""
    return _OUTPUT_BY_ID.get(mid)
