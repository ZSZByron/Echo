"""T3 红测：第二次收尾触发 + 产物语义注入（a1-oq-phase 施工单任务 3）。

- oq_phase 清结（末题答/跳）→ 复用 D21 三问状态机**二次**触发：
  产物语义 = 重定稿 + 文档再生成（REFINALIZE_PREFIX）；三问文案零复制。
- ChatResponse additive `oq_phase_active`；GET /file additive
  `oq_phase_active` + pending_question（前端冷启动恢复）。
- settled 解锁仅此一处（retrigger_after_oq）；>50% 门禁零触碰。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.domains.creation.a1.closing_flow import (
    QUESTIONS,
    TRIGGER_PREFIX,
    retrigger_after_oq,
)
from app.domains.creation.a1.guide_engine import A1Session, handle_message
from app.domains.creation.a1.interviewer import InterviewResult
from app.domains.creation.a1.open_questions import OpenQuestion, OpenQuestionLog
from app.domains.creation.a1.oq_phase import begin_or_reopen
from app.main import app


class _CountingStub:
    def __init__(self):
        self.calls = 0

    def interview(self, session, text):  # noqa: ARG002
        self.calls += 1
        return InterviewResult(fills=[], guidance_reply="好的，继续")

    def suggest_examples(self, session, module_id, subfield_id):  # noqa: ARG002
        return []


def _log(*statuses: str) -> OpenQuestionLog:
    return OpenQuestionLog(
        items=[
            OpenQuestion(id=f"oq-{i + 1:03d}", question=f"问题{i + 1}", status=s)
            for i, s in enumerate(statuses)
        ]
    )


def _complete_answers(s: A1Session) -> None:
    """真值填满 35 字段 + 问完态（收尾双条件——真实链路在首次收尾时已满足）。"""
    from app.domains.creation.a1.guide_engine import PHASE_COMPLETED
    from app.domains.creation.seed.a1_question_tree import all_subfield_keys

    for key in all_subfield_keys():
        s.answers[key] = f"答案-{key}"
    s.phase = PHASE_COMPLETED


def _phase_session(log: OpenQuestionLog, **kw) -> A1Session:
    s = A1Session(session_id="s_t3", user_id="u1", **kw)
    _complete_answers(s)
    assert begin_or_reopen(s, log) is True
    return s


# ---------------------------------------------------------------------------
# a. 末题答完 → 二次收尾触发（closing_step 0→1 + 重定稿话术）
# ---------------------------------------------------------------------------


def test_last_answer_triggers_second_closing():
    log = _log("pending")
    s = _phase_session(log)
    out = handle_message(s, "最后的回答", _CountingStub(), oq_log=log)
    assert s.closing_step == 1                  # D21 三问状态机复用再触发
    assert s.closing_settled is False           # settled 解锁重走
    assert "重新定稿" in out["reply"]            # 产物语义注入
    assert "想现在生成文档，还是继续访谈" in out["reply"]  # 三问 Q1 原文案复用
    assert s.oq_phase_active is False


def test_refinalize_variant_not_first_prefix():
    """变体文案：重定稿前缀在场、首次收尾前缀缺席；三问文案字节零改动。"""
    log = _log("pending")
    s = _phase_session(log)
    out = handle_message(s, "答", _CountingStub(), oq_log=log)
    assert "预设的问题都聊完了" not in out["reply"]        # 首收前缀缺席
    assert "重新定稿" in out["reply"]
    # 三问文案本体字节锁（零复制——引用同一 QUESTIONS 元组）
    assert QUESTIONS[0]["key"] == "q1"
    assert QUESTIONS[0]["text"] == "想现在生成文档，还是继续访谈、补充设定？"
    assert TRIGGER_PREFIX.startswith("预设的问题都聊完了")


def test_retrigger_idempotent_when_closing_in_progress():
    s = A1Session(session_id="s_t3b", user_id="u1", closing_step=2)
    assert retrigger_after_oq(s) is None
    assert s.closing_step == 2                  # 进行中不重置进度
    assert s.closing_settled is False


# ---------------------------------------------------------------------------
# b/c. chat + /file endpoint additive keys（TestClient）
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def started(client):
    resp = client.post(
        "/api/a1/session/start", json={"user_id": "u_test_t3", "seed_id": 1}
    )
    assert resp.status_code == 200
    return client, resp.json()


def _install_oq(payload: dict, *statuses: str) -> None:
    """把 oq_log 注入 file rec + 相位置位（绕过收尾链路，直达门态）。"""
    from app.api import a1_routes

    session = a1_routes._SESSIONS[payload["session_id"]]
    _complete_answers(session)              # 预设门禁满足（retrigger 前提）
    session.oq_phase_active = True
    session.oq_round = 1
    rec = a1_routes._FILES[payload["file_id"]]
    rec["open_questions"] = [
        OpenQuestion(id=f"oq-{i + 1:03d}", question=f"问题{i + 1}", status=st)
        .model_dump()
        for i, st in enumerate(statuses)
    ]


def test_chat_response_additive_oq_phase_active(started):
    client, payload = started
    _install_oq(payload, "pending", "pending")
    resp = client.post(
        "/api/a1/chat",
        json={"session_id": payload["session_id"], "message": "光辉是旧影子"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["oq_phase_active"] is True       # additive 新键
    assert "已记下" in body["reply"]              # 确定性作答回执（T2 门）


def test_chat_last_answer_carries_closing_signal_refinalize(started):
    client, payload = started
    _install_oq(payload, "pending")
    resp = client.post(
        "/api/a1/chat",
        json={"session_id": payload["session_id"], "message": "最后的回答"},
    )
    body = resp.json()
    assert body["oq_phase_active"] is False      # 相位闭合
    assert body["closing"]["triggered"] is True  # 二次收尾信号
    assert body["closing"]["step"] == 1
    assert "重新定稿" in body["reply"]


def test_file_endpoint_additive_phase_keys(started):
    client, payload = started
    _install_oq(payload, "pending", "answered")
    resp = client.get(f"/api/a1/file/{payload['file_id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["oq_phase_active"] is True       # 冷启动恢复键
    assert body["pending_question"] == {
        "id": "oq-001", "question": "问题1"
    }
    assert body["pending_questions_count"] == 1
