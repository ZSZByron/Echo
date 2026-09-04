"""C7 contract: 回答驱动转正映射（e2e 闭环）。

治理文档 §6 C7：访谈器追问 + 记录 answer → 下次对话读取 answered 条目
注入 graphify prompt 作为转正证据 → 装配层产出转正边（confirmed=false，
graph.edges 可见）+ rationale 引用用户回答。端到端验证三处必须同时可见。

另覆盖单问句铁律的注入分支：提案卡片在场时待问挂起（不注入 prompt）。
"""
from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.domains.creation.a1.concept_edge_vocab import VOCAB_RELATION_NAMES
from app.domains.creation.a1.interviewer import InterviewFill, InterviewResult
from app.domains.creation.seed.a1_question_tree import MODULES
from app.main import app

QUESTION = "亡者的记忆如何传递给生者？"
ANSWER = "通过转生者的梦呓传递"
EVIDENCE_LINE = f"用户已确认：{QUESTION}→{ANSWER}"

_REL = sorted(VOCAB_RELATION_NAMES)[0]
_M0, _M1 = MODULES[0]["id"], MODULES[1]["id"]
_SF0 = MODULES[0]["fields"][0]["id"]


def _graphify_response(**extra: Any) -> dict[str, Any]:
    """Minimal valid graphify LLM output."""
    payload: dict[str, Any] = {
        "module_summaries": {},
        "entries": [],
        "edges": [],
        "constraint_fields": {},
        "open_questions": [QUESTION],
    }
    payload.update(extra)
    return payload


class _FakeInterviewer:
    """chat 通道的假访谈器：可编程 open_question_answered。"""

    def __init__(self, answered: dict | None = None) -> None:
        self.answered = answered
        self.pending: dict | None = None

    def interview(self, session: Any, text: str) -> InterviewResult:  # noqa: ARG002
        return InterviewResult(
            fills=[
                InterviewFill(module=_M0, subfield=_SF0, value="测试内容")
            ],
            guidance_reply="已记录。",
            open_question_answered=self.answered,
        )

    def forced_allocate(self, session: Any, text: str) -> InterviewResult:  # noqa: ARG002
        return InterviewResult()

    def suggest_examples(self, *a: Any, **k: Any) -> list[str]:  # noqa: ARG002
        return []

    def set_pending_open_question(self, question: dict) -> None:
        self.pending = question

    def take_open_question_answered(self) -> dict | None:
        answered = self.answered
        self.answered = None
        return answered


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def started(client):
    resp = client.post("/api/a1/session/start", json={"user_id": "u_c7", "seed_id": 1})
    assert resp.status_code == 200
    return client, resp.json()


def _inject_answers(payload):
    """Fill answers directly in the live session (bypasses chat)."""
    from app.api import a1_routes

    session = a1_routes._SESSIONS[payload["session_id"]]
    for m in MODULES:
        need = len(m["fields"]) // 2 + 1
        for f in m["fields"][:need]:
            session.answers[f"{m['id']}.{f['id']}"] = "测试内容"
    return session


def _stub_finalize(monkeypatch: pytest.MonkeyPatch, response: dict[str, Any]):
    """Override the autouse factory stub: drive real graphify_llm."""
    from tests.unit.a1.conftest import StubLLMProvider

    stub = StubLLMProvider(response=response)
    monkeypatch.setattr("app.api.a1_routes.create_provider", lambda cfg: stub)
    return stub


def _finalize(client, payload, monkeypatch, response):
    _inject_answers(payload)
    stub = _stub_finalize(monkeypatch, response)
    fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
    assert fin.status_code == 200
    return fin.json(), stub


def test_c7_answered_question_becomes_confirmed_node_e2e(
    started, monkeypatch
) -> None:
    """回答 → status=answered → 下次 finalize 转正边入图（confirmed=false）。"""
    from app.api import a1_routes

    client, payload = started
    result, _ = _finalize(client, payload, monkeypatch, _graphify_response())
    assert result["status"] == "finalized"

    rec = a1_routes._FILES[payload["file_id"]]
    oqs = rec["open_questions"]
    # C6 铁律：结构化 list[dict]，非裸 list[str]
    assert isinstance(oqs, list) and oqs and isinstance(oqs[0], dict)
    assert oqs[0]["id"] == "oq-001"
    assert oqs[0]["question"] == QUESTION
    assert oqs[0]["status"] == "pending"

    # chat 回答待问
    fake = _FakeInterviewer(answered={"id": "oq-001", "answer": ANSWER})
    monkeypatch.setattr(a1_routes, "_INTERVIEWER", fake)
    resp = client.post(
        "/api/a1/chat",
        json={"session_id": payload["session_id"], "message": ANSWER},
    )
    assert resp.status_code == 200
    assert resp.json()["pending_question"] is None
    oqs = rec["open_questions"]
    assert oqs[0]["status"] == "answered"
    assert oqs[0]["answer"] == ANSWER

    # 下次 finalize：stub 返回引用该回答的转正边
    edge = {
        "from": _M0,
        "to": _M1,
        "relation": _REL,
        "rationale": f"用户已回答：{ANSWER}",
        "confidence": "semantic",
    }
    _finalize(
        client, payload, monkeypatch,
        _graphify_response(edges=[edge], open_questions=[]),
    )
    graph_edges = rec["graph_json"]["edges"]
    promo = [
        e for e in graph_edges
        if e.get("from_node_id") == _M0 and e.get("to_node_id") == _M1
    ]
    assert promo, "转正边必须入图"
    assert promo[0].get("confirmed") is False


def test_c7_answered_evidence_injected_into_graphify_prompt(
    started, monkeypatch
) -> None:
    """answered 条目以「用户已确认：{question}→{answer}」注入 graphify prompt。"""
    from app.api import a1_routes

    client, payload = started
    _finalize(client, payload, monkeypatch, _graphify_response())
    rec = a1_routes._FILES[payload["file_id"]]
    rec["open_questions"] = [{
        "id": "oq-001", "question": QUESTION, "status": "answered",
        "answer": ANSWER, "created_at": "", "source_hint": "",
    }]

    _, stub = _finalize(
        client, payload, monkeypatch,
        _graphify_response(open_questions=[]),
    )
    system = stub.last_messages[0]["content"]
    assert "【上一轮已回答的转正证据】" in system
    assert EVIDENCE_LINE in system


def test_c7_confirmed_node_rationale_cites_user_answer(
    started, monkeypatch
) -> None:
    """转正边的 rationale 必须引用用户回答原文。"""
    from app.api import a1_routes

    client, payload = started
    _finalize(client, payload, monkeypatch, _graphify_response())
    rec = a1_routes._FILES[payload["file_id"]]
    rec["open_questions"] = [{
        "id": "oq-001", "question": QUESTION, "status": "answered",
        "answer": ANSWER, "created_at": "", "source_hint": "",
    }]

    edge = {
        "from": _M0, "to": _M1, "relation": _REL,
        "rationale": f"依据用户回答：{ANSWER}，建立该关系。",
        "confidence": "semantic",
    }
    _finalize(
        client, payload, monkeypatch,
        _graphify_response(edges=[edge], open_questions=[]),
    )
    # GraphEdge 模型无 rationale 字段：rationale 持久化在 rec["edge_rationales"]
    rationales = rec.get("edge_rationales", {})
    assert any(ANSWER in (r or "") for r in rationales.values())

def test_c7_pending_question_suspended_when_proposal_present(
    started, monkeypatch
) -> None:
    """单问句铁律：提案卡片在场 → 待问挂起（不注入 prompt、卡不出现）。"""
    from app.api import a1_routes
    from app.domains.creation.a1.interviewer import Proposal

    client, payload = started
    _finalize(client, payload, monkeypatch, _graphify_response())

    session = a1_routes._SESSIONS[payload["session_id"]]
    session.pending_proposals["k1"] = {
        "proposal": Proposal(
            module=_M0, subfield="concept", old="旧", new="新"
        ),
        "options": ["替换", "合并", "丢弃"],
    }

    fake = _FakeInterviewer()
    monkeypatch.setattr(a1_routes, "_INTERVIEWER", fake)
    resp = client.post(
        "/api/a1/chat",
        json={"session_id": payload["session_id"], "message": "随便说说"},
    )
    assert resp.status_code == 200
    body = resp.json()
    # 待问不注入 prompt（挂起），但角标计数仍可见
    assert fake.pending is None
    assert body["pending_question"] is None
    assert body["pending_questions_count"] == 1
