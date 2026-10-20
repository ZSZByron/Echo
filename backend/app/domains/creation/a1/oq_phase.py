"""oq_phase — 开放问题相位状态机（a1-oq-phase 施工单 T1）。

把「回答开放问题」从 LLM 碰巧分类升级为显式会话相位：

- 进入：收尾「继续访谈」且 oq_log 待问 ≥1 → 置位 + entered 埋点；
  待问 =0 → 维持原自由访谈语义（不进相位）。
- 闭合：next_pending()=None → 复位 + closed 埋点 {round, answered, skipped}
  （无 reason 枚举——Metis 防 creep）。
- 轮次：oq_round 在每次进入时 +1（首进=1、重开=2），硬上限
  ``OQ_ROUND_CAP=2``——达帽后「继续访谈」不再重开（诚实提示，
  begin_or_reopen 返回 False，调用方保留原自由访谈推进）。

A1Session 仅新增两枚 additive 字段（oq_phase_active/oq_round，bool=False/
int=0 零迁移 G3 先例）。本模块零 LLM；埋点经 inspiration_log.emit_event
（永不破坏主流程）。
"""
from __future__ import annotations

from app.domains.creation.a1.guide_engine import A1Session
from app.domains.creation.a1.inspiration_log import emit_event
from app.domains.creation.a1.open_questions import OpenQuestionLog

#: 轮次硬上限（Metis 循环防护：达限不再提供重开）。
OQ_ROUND_CAP = 2

# ---------------------------------------------------------------------------
# 确定性回执模板（T2 相位门——零 LLM；作答回执复用 reply 文本，零新键）
# ---------------------------------------------------------------------------

#: 作答回执 + 下一问。
ANSWER_NEXT_TMPL = "已记下你的回答。下一问：{question}"
#: 末题作答回执（T3 接缝：二次收尾「重定稿+文档再生成」话术在此注入）。
ANSWER_LAST_NOTE = "已记下你的回答。开放问题都答完了，可以随时在这里收尾定稿。"
#: 跳过回执 + 下一问（routes skip 分支相位激活时覆盖默认文案）。
SKIP_NEXT_TMPL = "好的，这个问题先跳过。下一问：{question}"
#: 末题跳过回执。
SKIP_LAST_NOTE = "好的，开放问题都答完了。"


def pending_count(oq_log: OpenQuestionLog) -> int:
    """当前待问条数（pending 状态）。"""
    return sum(1 for q in oq_log.items if q.status == "pending")


def continue_allowed(session: A1Session) -> bool:
    """「继续访谈」重开选项是否可用（round 达帽 → 不再提供）。"""
    return session.oq_round < OQ_ROUND_CAP


def begin_or_reopen(session: A1Session, oq_log: OpenQuestionLog) -> bool:
    """进入（首次）或重开（二次收尾再选「继续访谈」）开放问题相位。

    返回 True = 相位已激活（含幂等：已在相位中）；False = 不进入
    （待问 =0 维持自由访谈语义 / round 达帽）。进入时 oq_round += 1
    并 emit ``oq_phase_entered{round}``。
    """
    if session.oq_phase_active:
        return True  # 幂等：已在相位中
    if oq_log.next_pending() is None:
        return False  # 待问 =0 → 原自由访谈语义
    if not continue_allowed(session):
        return False  # 轮次达帽 → 不再重开
    session.oq_round += 1
    session.oq_phase_active = True
    emit_event("oq_phase_entered", session, round=session.oq_round)
    return True


def maybe_close(session: A1Session, oq_log: OpenQuestionLog) -> bool:
    """相位激活且待问清结 → 复位 + ``oq_phase_closed`` 埋点。

    载荷 {round, answered, skipped}（全日志累计计数，确定性零 LLM）。
    未激活或仍有待问 → False（不动状态）。
    """
    if not session.oq_phase_active:
        return False
    if oq_log.next_pending() is not None:
        return False
    session.oq_phase_active = False
    emit_event(
        "oq_phase_closed",
        session,
        round=session.oq_round,
        answered=sum(1 for q in oq_log.items if q.status == "answered"),
        skipped=sum(1 for q in oq_log.items if q.status == "skipped"),
    )
    return True
