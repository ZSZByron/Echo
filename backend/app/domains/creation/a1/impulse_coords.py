# -*- coding: utf-8 -*-
"""冲动坐标观测层（impulse coords）——M4b，impulse spec §10.1，D13。

三件套（spec L305-311，存于会话 ``impulse_coords``——creator_profile 扩展
的会话字段落位，creator_* / creator_confidence 先例同款 default {} 零迁移）：
- **叙事-建构轴**：连续 [0,100]，100=纯叙事，0=纯建构。锚点初值 = spec
  L309 **逐字**（预注册纪律：写定后不随数据回调，偏离 = 复核信号）；
- **置信度**：连续 [0,1]——决定调整步长（低置信 → 大阻尼）；选卡 =
  高置信起步，说不清 = 低置信起步（spec L310）；
- **安全旗**：离散布尔——单向棘轮，检测到即升起，坐标漂移永不降旗
  （spec L311）。

**E2 只看不判**（spec L322 铁律）：坐标只落库 + 供看板数据接口读取，
绝不驱动路由/配方/门禁（field_sources 先例同款；TestObserveOnlyRouting
契约锚定路由行为零变化）。

四护栏（spec L315-320，缺一不可）：
1. 确定性更新：只吃显式信号闭集，更新函数 = 确定性代码 + 全留痕；
2. 防振荡阻尼：步长 ∝ 置信度 + 每会话调整上限 + 冷却轮数 +
   每会话至多一次队列重排 + 只重排未访模块；
3. 可达性不变式：重排保持模块集合不变（R6 只前移不跳过，契约测试）；
4. 安全旗棘轮：连续值调顺序，离散旗管安全，永不参与连续插值。
"""
from __future__ import annotations

from typing import Any

from app.domains.creation.a1.interaction_log import log_event
from app.domains.creation.shared.module_registry import MODULE_POOL, RECIPES

# ---------------------------------------------------------------------------
# 锚点初值（spec L309 **逐字**，预注册：写定后不随数据回调）
# ---------------------------------------------------------------------------

#: 叙事-建构轴锚点初值（spec L309：设定-重度≈15 / 探索≈25 / 角色驱动≈35 /
#: 哲理≈65 / 剧情≈70 / 怀旧≈75 / 爱情≈80 / 疗愈≈85；「说不清」初值≈70
#: ——人口先验：故事侧 64% vs 设定侧 14%，落故事侧但置信低）。
AXIS_ANCHOR_BY_TYPE: dict[str, int] = {
    "setting_heavy": 15,
    "exploration": 25,
    "character_driven": 35,
    "philosophy": 65,
    "plot": 70,
    "nostalgia": 75,
    "romance": 80,
    "healing": 85,
    "unsure": 70,  # 「说不清」≈70（spec L309 括注）
}

#: 无 profile / 未知冲动 → 说不清先验（spec L309）。
AXIS_DEFAULT = 70

#: 置信度初值（spec L310：选卡 = 高置信起步；说不清 = 低置信起步）。
CONFIDENCE_CARD_SELECTED = 0.7
CONFIDENCE_LOW_START = 0.3

# ---------------------------------------------------------------------------
# 显式信号闭集（spec L317：坐标只吃显式信号；LLM 只能提议、用户确认才生效
# ——推断包三值判定 / fills confirm-reject / 跳过 均为用户动作面）
# ---------------------------------------------------------------------------

SIGNAL_PACK_APPLIED = "pack_applied"      # 推断包建议被用户 confirm 采纳
SIGNAL_PACK_REJECTED = "pack_rejected"    # 推断包建议被用户放弃
SIGNAL_FILL_CONFIRMED = "fill_confirmed"  # fills/提案经 confirm 落写
SIGNAL_FILL_REJECTED = "fill_rejected"    # 提案被用户放弃（drop）
SIGNAL_SKIPPED = "skipped"                # 用户跳过/偏转

SIGNALS: dict[str, dict[str, float]] = {
    # axis_base：轴基准步长（方向由涉键模块 family 决定：story→+narrative，
    # worldview→-toward worldbuilding；conf_d：置信度增量）
    "pack_applied":    {"axis_base": 0.0, "conf_d": +0.10},  # M4a ±0.1 先例
    "pack_rejected":   {"axis_base": 0.0, "conf_d": -0.10},
    "fill_confirmed":  {"axis_base": 3.0, "conf_d": +0.02},
    "fill_rejected":   {"axis_base": 0.0, "conf_d": -0.02},
    "skipped":         {"axis_base": 0.0, "conf_d": -0.05},
}

# 防振荡参数（spec L318：滞后 + 每会话调整上限 + 冷却轮数 + ≤1 次重排）
MAX_ADJUSTMENTS_PER_SESSION = 10   # 每会话坐标调整上限
COOLDOWN_ROUNDS = 3                # 冷却轮数（两次生效调整的最小轮距）
REORDER_MAX_PER_SESSION = 1        # 每会话至多一次队列重排

_CONF_MIN, _CONF_MAX = 0.0, 1.0
_AXIS_MIN, _AXIS_MAX = 0.0, 100.0


# ---------------------------------------------------------------------------
# 三件套落库
# ---------------------------------------------------------------------------


def init_impulse_coords(session: Any) -> dict[str, Any]:
    """按冲动档案初始化三件套（确定性；重复调用幂等——已有坐标不重置）。

    轴 = spec L309 锚点查表（无/未知 profile → 说不清先验 70）；
    置信度 = 选卡（creator_profile_source=="impulse_cards" 且非 unsure）
    → 高置信起步，否则低置信起步（spec L310）。
    """
    if session.impulse_coords:
        return session.impulse_coords
    primary = session.creator_primary or ""
    axis = AXIS_ANCHOR_BY_TYPE.get(primary, AXIS_DEFAULT)
    card_selected = (
        session.creator_profile_source == "impulse_cards"
        and primary in RECIPES
        and primary != "unsure"
    )
    session.impulse_coords = {
        "axis": float(axis),
        "confidence": CONFIDENCE_CARD_SELECTED if card_selected else CONFIDENCE_LOW_START,
        "safety_flag": False,
        "anchor": axis,
        "anchor_source": primary or "unprofiled",
        "reorder_count": 0,
        "adjustments": 0,
        "last_update_round": -(COOLDOWN_ROUNDS + 1),
        "audit": [],
    }
    log_event(session.session_id, "impulse_coords_init", axis=axis)
    return session.impulse_coords


# ---------------------------------------------------------------------------
# 确定性更新（护栏 1 + 2a 阻尼 + 4 棘轮；全留痕）
# ---------------------------------------------------------------------------


def _axis_direction(session: Any, key: str, base: float) -> float:
    """涉键模块 family → 轴方向（确定性查 MODULE_POOL，无 LLM 判定）。

    story family（剧情/角色）→ +base（向叙事端 100）；worldview → -base
    （向建构端 0）；output/未知键 → 0。
    """
    if not key or base == 0.0:
        return 0.0
    module_id = key.split(".", 1)[0]
    mdef = MODULE_POOL.get(module_id)
    if mdef is None:
        return 0.0
    if mdef.family == "story":
        return base
    if mdef.family == "worldview":
        return -base
    return 0.0


def apply_signal(session: Any, signal: str, key: str = "") -> dict[str, Any]:
    """消费一个显式信号 → 确定性坐标更新 + 全留痕（护栏 1）。

    返回 {"applied": bool, "coords": dict}。非显式信号 / 超出每会话调整
    上限 / 冷却轮内 → applied=False（坐标不动，仍留痕——诚实可观测）。
    """
    coords = init_impulse_coords(session)
    spec = SIGNALS.get(signal)
    if spec is None:
        raise ValueError(f"unknown impulse coord signal: {signal!r}")

    entry: dict[str, Any] = {
        "round": session.message_rounds,
        "signal": signal,
        "key": key,
        "axis_before": coords["axis"],
        "confidence_before": coords["confidence"],
    }

    # 护栏 2a：每会话调整上限 + 冷却轮数（防振荡；只挡连续插值，
    # 安全旗棘轮不受此限——护栏 4"离散旗管安全"）
    blocked = (
        coords["adjustments"] >= MAX_ADJUSTMENTS_PER_SESSION
        or session.message_rounds - coords["last_update_round"] < COOLDOWN_ROUNDS
    )
    if blocked:
        entry.update({
            "applied": False,
            "axis_after": coords["axis"],
            "confidence_after": coords["confidence"],
        })
        coords["audit"].append(entry)
        log_event(session.session_id, "impulse_coords_damped",
                  signal=signal, reason="cap_or_cooldown")
        return {"applied": False, "coords": coords}

    # 阻尼（spec L310：置信度决定调整步长，低置信 → 大阻尼）：
    # 有效步长 = 基准步长 × 置信度。
    raw = _axis_direction(session, key, spec["axis_base"])
    axis_delta = round(raw * coords["confidence"], 4)
    new_axis = max(_AXIS_MIN, min(_AXIS_MAX, coords["axis"] + axis_delta))
    new_conf = max(_CONF_MIN, min(
        _CONF_MAX, coords["confidence"] + spec["conf_d"]))

    entry.update({
        "applied": True,
        "axis_after": new_axis,
        "confidence_after": new_conf,
        "axis_delta": new_axis - coords["axis"],
    })
    coords["axis"] = new_axis
    coords["confidence"] = new_conf
    coords["adjustments"] += 1
    coords["last_update_round"] = session.message_rounds
    coords["audit"].append(entry)
    log_event(session.session_id, "impulse_coords_update",
              signal=signal, axis=new_axis, confidence=new_conf)
    return {"applied": True, "coords": coords}


def raise_safety_flag(session: Any, reason: str = "") -> bool:
    """安全旗单向棘轮（spec L311：检测到即升起，坐标漂移永不降旗）。

    幂等：已升 → True 不重复留痕。返回升旗后的旗值（恒 True）。
    """
    coords = init_impulse_coords(session)
    if coords["safety_flag"]:
        return True
    coords["safety_flag"] = True
    coords["audit"].append({
        "round": session.message_rounds,
        "signal": "safety_raise",
        "key": "",
        "reason": reason[:200],
        "axis_before": coords["axis"],
        "axis_after": coords["axis"],
        "confidence_before": coords["confidence"],
        "confidence_after": coords["confidence"],
        "applied": True,
    })
    log_event(session.session_id, "impulse_coords_safety_raise", reason=reason[:120])
    return True


# ---------------------------------------------------------------------------
# 护栏 2b/3：队列重排（每会话 ≤1 次 + 只重排未访模块 + 可达性不变式）
# ---------------------------------------------------------------------------


def maybe_reorder(session: Any, recipe_modules: list[str]) -> list[str] | None:
    """观测期重排候选（E2 只看不判：返回新序候选，**不写回会话路由**）。

    - 每会话至多一次（reorder_count 棘轮）；
    - 只重排未访模块（已答字段所在模块位置永不动——spec L318）；
    - 可达性不变式：模块集合不变（键集不变 → R6 只前移不跳过保持）。
    无未访模块 / 已达上限 → 返回 None。
    """
    coords = init_impulse_coords(session)
    if coords["reorder_count"] >= REORDER_MAX_PER_SESSION:
        # 已达上限 → 幂等返回原序（≤1 次/会话；不产生新审计条目）
        return list(recipe_modules)

    def _visited(mid: str) -> bool:
        return any(
            k.startswith(f"{mid}.") for k in session.answers
        )

    visited = [mid for mid in recipe_modules if _visited(mid)]
    unvisited = [mid for mid in recipe_modules if not _visited(mid)]
    if not unvisited:
        return None
    # 确定性重排：叙事-建构轴偏向叙事端（axis > anchor）→ 未访故事模块
    # 前置；偏向建构端 → 未访世界建构模块前置。同族内保持原相对序。
    axis = coords["axis"]
    anchor = float(coords.get("anchor", AXIS_DEFAULT))
    if axis > anchor:
        prefer = ("story", "worldview")
    elif axis < anchor:
        prefer = ("worldview", "story")
    else:
        prefer = None
    if prefer is not None:
        def _rank(mid: str) -> int:
            fam = MODULE_POOL.get(mid).family if MODULE_POOL.get(mid) else ""
            return prefer.index(fam) if fam in prefer else len(prefer)
        unvisited_sorted = sorted(unvisited, key=_rank)  # Python 稳定排序
        visited_iter = iter(visited)
        new_order = [
            next(visited_iter) if _visited(mid) else unvisited_sorted.pop(0)
            for mid in recipe_modules
        ]
    else:
        new_order = list(recipe_modules)
    coords["reorder_count"] += 1
    coords["audit"].append({
        "round": session.message_rounds,
        "signal": "reorder_candidate",
        "key": "",
        "axis_before": axis,
        "axis_after": axis,
        "confidence_before": coords["confidence"],
        "confidence_after": coords["confidence"],
        "applied": True,
        "before": list(recipe_modules),
        "after": new_order,
    })
    log_event(session.session_id, "impulse_coords_reorder_candidate")
    return new_order


# ---------------------------------------------------------------------------
# 看板数据接口（E2：坐标落库 + 看板"反推类型迁移曲线"，spec L322）
# ---------------------------------------------------------------------------


def dashboard_data(session: Any) -> dict[str, Any]:
    """看板只读投影（三件套 + 审计轨迹 + 锚点来源）。不落任何判断。"""
    coords = init_impulse_coords(session)
    return {
        "axis": coords["axis"],
        "confidence": coords["confidence"],
        "safety_flag": coords["safety_flag"],
        "anchor": coords["anchor"],
        "anchor_source": coords["anchor_source"],
        "adjustments": coords["adjustments"],
        "reorder_count": coords["reorder_count"],
        "audit": list(coords["audit"]),
    }
