"""T2 红测：oq_phase 前置相位门——确定性路由（a1-oq-phase 施工单任务 2）。

- 门位：F2 提案短指令消解**之后**、六通道级联**之前**（L1905 区零触碰）。
- 相位内一切非空文本 = 确定性记为当前 oq 作答：零 LLM 调用、零 fills、
  零 proposals（16:21 病例守护——收尾态同消息不再被填充分类吸走）。
- 竞态兜底：待问已空 → maybe_close 复位 + 落回原级联。
- 16:21 病例原句守护 + 共存矩阵 additive 行（F2 > oq 门 > 级联）。
"""
from __future__ import annotations

import json

import pytest

import app.domains.creation.a1.guide_engine as guide_engine
from app.domains.creation.a1.guide_engine import A1Session, handle_message
from app.domains.creation.a1.interviewer import InterviewResult, Proposal
from app.domains.creation.a1.open_questions import OpenQuestion, OpenQuestionLog
from app.domains.creation.a1.oq_phase import begin_or_reopen


@pytest.fixture()
def event_log(tmp_path, monkeypatch):
    """把 inspiration_log.jsonl 重定向到 tmp，返回读取函数（T1 同款）。"""
    p = tmp_path / "inspiration_log.jsonl"
    monkeypatch.setattr(
        "app.domains.creation.a1.inspiration_log.LOG_PATH", p
    )

    def _events(event: str | None = None) -> list[dict]:
        if not p.exists():
            return []
        recs = [json.loads(ln) for ln in p.read_text("utf-8").splitlines()]
        if event is None:
            return recs
        return [r for r in recs if r.get("event") == event]

    return _events


#: 16:21 真机病理原句（收尾态下发 → 曾被 character_visual 填充分类吸走）。
PATHOLOGY_TEXT = "工程行业吧.光辉我不知道，我不愿意面对"


class _CountingStub:
    """handle_message 级 stub：记录 interview 调用次数（门零 LLM 断言锚）。"""

    def __init__(self, guidance_reply="好的，继续"):
        self.guidance_reply = guidance_reply
        self.calls = 0

    def interview(self, session, text):  # noqa: ARG002
        self.calls += 1
        return InterviewResult(fills=[], guidance_reply=self.guidance_reply)

    def suggest_examples(self, session, module_id, subfield_id):  # noqa: ARG002
        return []


def _session(**kw) -> A1Session:
    return A1Session(session_id="s_gate", user_id="u1", **kw)


def _log(*statuses: str) -> OpenQuestionLog:
    return OpenQuestionLog(
        items=[
            OpenQuestion(id=f"oq-{i + 1:03d}", question=f"问题{i + 1}", status=s)
            for i, s in enumerate(statuses)
        ]
    )


def _phase_session(log: OpenQuestionLog, **kw) -> A1Session:
    s = _session(**kw)
    assert begin_or_reopen(s, log) is True
    return s


# ---------------------------------------------------------------------------
# 1. 确定性作答：任意自然语言 → 当前 oq，零 LLM / 零 fills / 零 answers 写入
# ---------------------------------------------------------------------------


def test_phase_answer_is_deterministic_zero_llm():
    log = _log("pending", "pending")
    s = _phase_session(log)
    iv = _CountingStub()
    out = handle_message(s, "光辉是一团不愿面对的旧影子", iv, oq_log=log)
    assert iv.calls == 0                       # 零 LLM（不进级联）
    assert log.items[0].status == "answered"
    assert log.items[0].answer == "光辉是一团不愿面对的旧影子"
    assert log.next_pending().id == "oq-002"   # 推进到下一问
    assert s.answers == {}                     # 零 fills 落库
    assert s.oq_phase_active is True           # 仍有待问 → 相位保持
    assert "已记下" in out["reply"]
    assert "问题2" in out["reply"]              # 回执带下一问
    assert out["file_diff"] == []


# ---------------------------------------------------------------------------
# 2. 16:21 病例守护（本批最重要用例）：收尾态 + 相位 + 原句
# ---------------------------------------------------------------------------


def test_pathology_16_21_guard_zero_fills_zero_proposals():
    log = _log("pending")
    s = _phase_session(log, closing_step=2)    # 收尾态同帧
    iv = _CountingStub()
    out = handle_message(s, PATHOLOGY_TEXT, iv, oq_log=log)
    assert iv.calls == 0                       # 不进 LLM 分类/填充
    assert s.pending_proposals == {}           # 零 proposals
    assert s.answers == {}                     # 零 fills（角色.character_visual 不被写）
    assert log.items[0].status == "answered"   # 作答落在当前 oq
    assert log.items[0].answer == PATHOLOGY_TEXT
    assert s.oq_phase_active is False          # 末题答完 → 相位闭合
    assert out["file_diff"] == []


# ---------------------------------------------------------------------------
# 3. 提案短指令共存：F2 最高优先，消解后回 oq 流
# ---------------------------------------------------------------------------


def test_proposal_directive_resolves_then_back_to_oq_flow():
    log = _log("pending", "pending")
    s = _phase_session(log)
    s.pending_proposals["k1"] = {
        "proposal": Proposal(
            module="IP定位", subfield="name", old="旧值", new="新值"
        ),
        "options": ["replace", "merge", "drop"],
    }
    iv = _CountingStub()
    out1 = handle_message(s, "放弃", iv, oq_log=log)
    assert s.pending_proposals == {}           # F2 消解
    assert "放弃" in out1["reply"]
    assert iv.calls == 0                       # 消解轮零 LLM
    assert log.next_pending().id == "oq-001"   # oq 未被消费
    # 下一轮：回到 oq 作答流
    out2 = handle_message(s, "光辉是旧影子", iv, oq_log=log)
    assert iv.calls == 0
    assert log.items[0].status == "answered"
    assert "已记下" in out2["reply"]


# ---------------------------------------------------------------------------
# 4. 末题答完 → 闭合（closed 埋点 + T3 话术接缝）
# ---------------------------------------------------------------------------


def test_last_answer_closes_phase_with_seam(event_log):
    log = _log("pending")
    s = _phase_session(log)
    out = handle_message(s, "最后一个答案", _CountingStub(), oq_log=log)
    assert s.oq_phase_active is False
    assert s.oq_round == 1
    evs = event_log("oq_phase_closed")
    assert len(evs) == 1
    assert evs[0]["answered"] == 1 and evs[0]["skipped"] == 0
    assert "答完" in out["reply"]               # 收尾接缝话术（T3 注入点）


# ---------------------------------------------------------------------------
# 5. 竞态兜底：相位激活但待问已空 → 复位 + 落回原级联
# ---------------------------------------------------------------------------


def test_race_guard_resets_and_falls_through_to_cascade(event_log):
    log = _log()                               # 空：无待问
    s = _session(oq_phase_active=True, oq_round=1)  # 残影激活（刷新竞态）
    iv = _CountingStub(guidance_reply="好，回到力量体系——怎么获得？")
    out = handle_message(s, "随便聊聊设定", iv, oq_log=log)
    assert iv.calls == 1                       # 落回原级联（interviewer 照常）
    assert s.oq_phase_active is False          # 竞态复位
    evs = event_log("oq_phase_closed")
    assert len(evs) == 1                       # 复位走 maybe_close（埋点不缺）
    assert out["reply"] == "好，回到力量体系——怎么获得？"


# ---------------------------------------------------------------------------
# 6. 共存矩阵 additive 行：门序 = F2 > oq 门 > 级联；既有六通道零触碰
# ---------------------------------------------------------------------------


def test_matrix_oq_gate_order_f2_above_gate_above_cascade(monkeypatch):
    """oq 相位作答轮：级联轮末定序零进入（_round_end_signals 不被触达）。"""
    calls: list[str] = []

    def spy_round_end(session, text, out, provider, *, pre_module, oq_log=None):  # noqa: ARG001 (spy: 签名对齐被拦截点)
        calls.append("round_end")
        return out

    monkeypatch.setattr(guide_engine, "_round_end_signals", spy_round_end)
    log = _log("pending")
    s = _phase_session(log)
    handle_message(s, "答案内容", _CountingStub(), oq_log=log)
    assert calls == []                         # 相位作答不进级联（含轮末）
    assert log.items[0].status == "answered"
