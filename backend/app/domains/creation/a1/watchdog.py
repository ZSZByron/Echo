# -*- coding: utf-8 -*-
"""看门狗（watchdog）——M4b，plan TODO 5 §270。

每 N 轮门禁检查：会话后半程（模块完成度过半）且配方内存在未访模块
（零真值答案）→ 产出确定性回归提示（建议回到未访模块话题）。

铁律：
- 确定性代码，无 LLM 进控制流——提示内容是模板字符串，不调用任何
  provider（LLM 只产内容不进控制流的普适化，D-A2-4）；
- N 可配（env ``A1_WATCHDOG_EVERY_N``，默认 5）；
- 只附建议（结果 dict 新增可选键 ``watchdog``），不改 reply/路由/指针
  ——additive 门模式，存量断言零扰动。
"""
from __future__ import annotations

import os
from typing import Any

from app.domains.creation.a1.interaction_log import log_event
from app.domains.creation.seed.a1_question_tree import is_truthy_answer

#: 默认检查间隔（轮）。
DEFAULT_EVERY_N = 5


def _every_n() -> int:
    try:
        return max(1, int(os.environ.get("A1_WATCHDOG_EVERY_N", DEFAULT_EVERY_N)))
    except ValueError:
        return DEFAULT_EVERY_N


def check_watchdog(session: Any) -> dict[str, Any] | None:
    """每 N 轮门禁检查（确定性；无未访模块/未到间隔/前半程 → None）。"""
    n = _every_n()
    rounds = session.message_rounds
    if rounds <= 0 or rounds % n != 0:
        return None

    recipe = session.recipe_modules or []
    unvisited: list[str] = []
    for mid in recipe:
        has_truthy = any(
            is_truthy_answer(v)
            for k, v in session.answers.items()
            if k.startswith(f"{mid}.")
        )
        if not has_truthy:
            unvisited.append(mid)
    if not unvisited:
        return None

    # 后半程判定：已完成模块数过半（进入会话后半段）。
    done = sum(1 for mid in recipe if mid not in unvisited)
    if done * 2 < len(recipe):
        return None

    suggestion = (
        "看门狗提示：「" + "」「".join(unvisited) + "」这些模块还没开始，"
        "要不要先聊聊其中一块？回复「跳过」可继续当前话题。"
    )
    log_event(
        session.session_id, "watchdog_fired",
        round=rounds, unvisited=unvisited,
    )
    return {
        "kind": "watchdog",
        "round": rounds,
        "unvisited_modules": [{"id": mid} for mid in unvisited],
        "suggestion": suggestion,
    }
