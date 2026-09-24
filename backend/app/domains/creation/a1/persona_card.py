# -*- coding: utf-8 -*-
"""人格卡（persona card）+ 入口单选 sunset 接口——M4c，plan §276-284。

**人格卡**：命名 + 视觉 + 一句话解读的确定性投影（零 LLM）。数据源 =
creator_profile（creator_primary / creator_profile_source）+ impulse_coords
三件套（M4b 的 session.impulse_coords）。同输入 → 同卡面。

- 命名 = **未决③ DECISION NEEDED 占位** "ECHO 创作人格"——终名归产品
  裁决，本常量仅为占位（G 批次在 D14/spec 记录未决状态）；
- **只看不判**（E2 铁律同款）：卡只展示观测，绝不回流路由/配方/门禁。

**入口单选 sunset 接口**（plan §281）：行为信号（坐标置信度）成熟后选卡
权重递减——**本期只留接口不启用**：环境变量 ``A1_ENTRY_SUNSET_ENABLED``
默认关闭，关闭时恒返回基础权重（行为零变化）；启用逻辑 = 后续工作。
"""
from __future__ import annotations

import os
from typing import Any

from app.domains.creation.a1.impulse_coords import init_impulse_coords

# ---------------------------------------------------------------------------
# 命名（未决③ DECISION NEEDED 占位——终名归产品裁决，不得擅定）
# ---------------------------------------------------------------------------

#: 占位命名（未决③）：默认卡名，G 批次在 D14/spec 记录未决状态。
PERSONA_NAME_PLACEHOLDER = "ECHO 创作人格"

# ---------------------------------------------------------------------------
# sunset 接口参数（仅启用后生效；默认关闭 = 参数不参与任何行为）
# ---------------------------------------------------------------------------

#: sunset 总开关环境变量（默认 "0" = 关闭，行为零变化）。
ENTRY_SUNSET_ENV = "A1_ENTRY_SUNSET_ENABLED"

#: 行为信号成熟阈值（坐标置信度 ≥ 此值才触发衰减；坐标置信度闭集 [0,1]）。
SUNSET_CONFIDENCE_THRESHOLD = 0.8

#: 成熟信号下的选卡权重乘数（递减语义：乘后 < 基础权重）。
SUNSET_DECAY_FACTOR = 0.5


# ---------------------------------------------------------------------------
# 人格卡（确定性投影，零 LLM）
# ---------------------------------------------------------------------------


def _band(axis: float) -> str:
    """叙事-建构轴 → 三段带（确定性阈值切分）。"""
    if axis >= 60.0:
        return "narrative"
    if axis <= 40.0:
        return "worldbuilding"
    return "blend"


def render_persona_card(session: Any) -> dict[str, Any]:
    """人格卡只读投影（命名+视觉+一句话解读；只看不判）。

    确定性：全部字段来自 creator_profile + impulse_coords 查表/阈值/
    模板插值，无 LLM 调用。重复调用幂等（坐标惰性初始化只发生一次）。
    """
    coords = init_impulse_coords(session)
    axis = float(coords["axis"])
    confidence = float(coords["confidence"])
    band = _band(axis)
    band_label = {"narrative": "叙事", "worldbuilding": "建构", "blend": "叙事与建构之间"}[band]
    reading = (
        f"观察样本偏向{band_label}"
        f"（轴 {axis:.0f}/100，锚点 {coords.get('anchor', axis):.0f}），"
        f"当前信号置信 {confidence:.0%}。"
    )
    if coords["safety_flag"]:
        reading += "（安全旗已升起——仅披露，不改变解读口径）"

    return {
        # 未决③ 占位命名：终名归产品裁决
        "name": PERSONA_NAME_PLACEHOLDER,
        "visual": {
            "band": band,
            "axis_position": round(axis, 2),
            # 视觉强调度随置信度（确定性映射 [0,1] → [0,1]）
            "accent": round(confidence, 2),
            "safety_flag": bool(coords["safety_flag"]),
        },
        "one_line_reading": reading,
        "sources": {
            # 数据源披露（creator_profile + 坐标三件套）
            "creator_primary": session.creator_primary or "",
            "creator_profile_source": session.creator_profile_source or "",
            "axis": axis,
            "confidence": confidence,
            "safety_flag": bool(coords["safety_flag"]),
        },
    }


# ---------------------------------------------------------------------------
# 入口单选 sunset 接口（默认关闭，行为零变化——本期只留接口）
# ---------------------------------------------------------------------------


def sunset_enabled() -> bool:
    """sunset 总开关（默认 False）。独立函数便于测试与后续接线。"""
    return os.environ.get(ENTRY_SUNSET_ENV, "0") == "1"


def entry_card_weight(session: Any, base_weight: float = 1.0) -> float:
    """入口选卡权重（sunset 语义：行为信号成熟 → 权重递减）。

    **默认关闭**：``A1_ENTRY_SUNSET_ENABLED != "1"`` 时恒返回
    ``base_weight``（行为零变化，plan §281 本期只留接口不启用）。
    启用后：坐标置信度 ≥ 阈值 → ``base_weight * SUNSET_DECAY_FACTOR``，
    否则原样返回。确定性纯函数，无副作用。
    """
    if not sunset_enabled():
        return base_weight
    coords = init_impulse_coords(session)
    # 1e-9 容差：置信度累计为浮点（0.7+0.1=0.7999…），阈值比较按语义等价收敛
    if float(coords["confidence"]) >= SUNSET_CONFIDENCE_THRESHOLD - 1e-9:
        return base_weight * SUNSET_DECAY_FACTOR
    return base_weight
