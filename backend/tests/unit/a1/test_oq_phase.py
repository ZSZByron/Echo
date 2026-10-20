"""T1 红测：oq_phase 状态机（进入/闭合/轮次，a1-oq-phase 施工单任务 1）。

- 进入：第一次收尾「继续访谈」且 oq_log 待问 ≥1 → oq_phase_active=True
  + oq_phase_entered 埋点；待问 =0 → 维持原自由访谈语义（不进相位）。
- 闭合：next_pending()=None → 复位 + oq_phase_closed{round,answered,skipped}。
- 轮次：重开 oq_round+1；oq_round 达帽 2 → 「继续访谈」不再重开。
- additive：A1Session 仅新增 oq_phase_active / oq_round 两键（默认零迁移）。
"""
from __future__ import annotations

import json

import pytest

from app.domains.creation.a1.closing_flow import advance_answer
from app.domains.creation.a1.guide_engine import A1Session
from app.domains.creation.a1.inspiration_log import LOG_PATH
from app.domains.creation.a1.open_questions import OpenQuestion, OpenQuestionLog
from app.domains.creation.a1.oq_phase import (
    OQ_ROUND_CAP,
    begin_or_reopen,
    maybe_close,
)

# ---------------------------------------------------------------------------
# 夹具：埋点重定向到临时文件 + 会话/日志构造
# ---------------------------------------------------------------------------


@pytest.fixture()
def event_log(tmp_path, monkeypatch):
    """把 inspiration_log.jsonl 重定向到 tmp，返回读取函数。"""
    p = tmp_path / "inspiration_log.jsonl"
    monkeypatch.setattr(
        "app.domains.creation.a1.inspiration_log.LOG_PATH", p
    )
    assert p != LOG_PATH  # 模块级常量本尊不在本模块名下，读侧仅作烟测

    def _events(event: str | None = None) -> list[dict]:
        if not p.exists():
            return []
        recs = [json.loads(ln) for ln in p.read_text("utf-8").splitlines()]
        if event is None:
            return recs
        return [r for r in recs if r.get("event") == event]

    return _events


def _session(closing_step: int = 1, **kw) -> A1Session:
    return A1Session(
        session_id="t-oq-phase", user_id="t", closing_step=closing_step, **kw
    )


def _log(*statuses: str) -> OpenQuestionLog:
    return OpenQuestionLog(
        items=[
            OpenQuestion(id=f"oq-{i + 1:03d}", question=f"问题{i + 1}", status=s)
            for i, s in enumerate(statuses)
        ]
    )


# ---------------------------------------------------------------------------
# 1. additive schema（沿用 additive 锁模式：新增键恰为两枚、默认零迁移）
# ---------------------------------------------------------------------------


def test_a1session_oq_phase_keys_additive():
    fields = frozenset(A1Session.model_fields.keys())
    assert {"oq_phase_active", "oq_round"} <= fields
    fresh = A1Session(session_id="t1", user_id="t")
    assert fresh.oq_phase_active is False
    assert fresh.oq_round == 0
    # 存量 payload（无新键）零迁移直通
    legacy = A1Session.model_validate({"session_id": "legacy", "user_id": "l"})
    assert legacy.oq_phase_active is False
    assert legacy.oq_round == 0
    # 不得复用/篡改既有 phase 字段
    assert legacy.phase == "asking"


# ---------------------------------------------------------------------------
# 2. 进入条件：有待问 → 置位 + entered 埋点
# ---------------------------------------------------------------------------


def test_enter_with_pending_questions(event_log):
    s = _session()
    log = _log("pending", "pending")
    entered = advance_answer(s, "继续访谈", oq_log=log)
    assert entered is not None
    assert s.oq_phase_active is True
    assert s.oq_round == 1
    evs = event_log("oq_phase_entered")
    assert len(evs) == 1
    assert evs[0]["session_id"] == "t-oq-phase"
    assert evs[0]["round"] == 1


def test_enter_without_pending_keeps_free_interview(event_log):
    s = _session()
    log = _log()  # 0 待问
    entered = advance_answer(s, "继续访谈", oq_log=log)
    assert entered is not None  # 原自由访谈语义保持（收尾照常推进）
    assert s.oq_phase_active is False
    assert s.oq_round == 0
    assert event_log("oq_phase_entered") == []


def test_begin_or_reopen_no_log_pending_false():
    s = _session()
    assert begin_or_reopen(s, _log()) is False
    assert s.oq_phase_active is False


# ---------------------------------------------------------------------------
# 3. 闭合：清结 → 复位 + closed 埋点载荷 {round, answered, skipped}
# ---------------------------------------------------------------------------


def test_close_reset_and_event_payload(event_log):
    s = _session()
    log = _log("pending", "pending", "skipped")
    assert begin_or_reopen(s, log) is True
    log.mark_answered("oq-001", "答一")
    log.mark_answered("oq-002", "答二")
    assert maybe_close(s, log) is True
    assert s.oq_phase_active is False
    evs = event_log("oq_phase_closed")
    assert len(evs) == 1
    assert evs[0]["round"] == 1
    assert evs[0]["answered"] == 2
    assert evs[0]["skipped"] == 1


def test_close_noop_when_not_active_or_still_pending(event_log):
    s = _session()
    log = _log("pending")
    assert maybe_close(s, log) is False  # 未激活
    assert begin_or_reopen(s, log) is True
    assert maybe_close(s, log) is False  # 仍有待问
    assert s.oq_phase_active is True
    assert event_log("oq_phase_closed") == []


# ---------------------------------------------------------------------------
# 4. 轮次：重开 +1；达帽 2 拒绝重开
# ---------------------------------------------------------------------------


def test_reopen_increments_round(event_log):
    s = _session()
    log = _log("pending")
    assert begin_or_reopen(s, log) is True          # 第一轮 round=1
    log.mark_answered("oq-001", "答")
    assert maybe_close(s, log) is True
    log.upsert(OpenQuestion(id="oq-002", question="新问"))  # 重定稿产新问
    assert begin_or_reopen(s, log) is True          # 第二次收尾重开
    assert s.oq_phase_active is True
    assert s.oq_round == 2
    evs = event_log("oq_phase_entered")
    assert len(evs) == 2 and evs[-1]["round"] == 2


def test_round_cap_rejection(event_log):
    s = _session(oq_round=OQ_ROUND_CAP)
    log = _log("pending", "pending")
    entered = advance_answer(s, "继续访谈", oq_log=log)
    assert entered is not None  # 收尾状态机照常推进（不阻塞）
    assert s.oq_phase_active is False
    assert s.oq_round == OQ_ROUND_CAP
    assert event_log("oq_phase_entered") == []
    # 诚实提示：达帽话术出现在回复中
    assert "两轮" in entered


def test_round_cap_helper():
    assert begin_or_reopen(_session(oq_round=2), _log("pending")) is False
