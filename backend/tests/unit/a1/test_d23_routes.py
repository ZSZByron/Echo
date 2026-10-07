"""D23 routes-layer tests: confirm intent classification, merge undo,
auto_merges passthrough (a1_routes wiring on top of the frozen engine)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def started(client):
    resp = client.post("/api/a1/session/start", json={"user_id": "u_test_d23", "seed_id": 1})
    assert resp.status_code == 200
    return client, resp.json()


class _FixedIntentInterviewer:
    """Minimal stand-in for DegradingInterviewer: classify returns a fixed
    intent; open-question hooks are inert."""

    def __init__(self, intent: str | Exception):
        self._intent = intent

    def classify_confirm_intent(self, old_value: str, new_value: str, user_reply: str) -> str:
        if isinstance(self._intent, Exception):
            raise self._intent
        return self._intent

    def set_pending_open_question(self, question: dict) -> None:
        pass

    def take_open_question_answered(self) -> dict | None:
        return None


def _seed_proposal(session, old="原有内容", new="新增内容"):
    from app.domains.creation.a1.guide_engine import Proposal

    proposal_key = "IP定位.name:d23test"
    session.answers["IP定位.name"] = old
    session.pending_proposals[proposal_key] = {
        "proposal": Proposal(
            module="IP定位",
            subfield="name",
            old=old,
            new=new,
            conflict_note=None,
        ),
        "options": ["replace", "merge", "drop"],
    }
    return proposal_key


class TestConfirmIntentClassification:
    def test_confirm_keyword_miss_classified_as_merge(self, started, monkeypatch):
        """Keyword miss (non-keyword free text) → interviewer classify →
        merge → proposal resolved as merge (NOT needs_clarification)."""
        from app.api import a1_routes

        monkeypatch.setattr(
            a1_routes,
            "_get_interviewer",
            lambda: _FixedIntentInterviewer("merge"),
        )
        client, payload = started
        session = a1_routes._SESSIONS[payload["session_id"]]
        proposal_key = _seed_proposal(session, old="原有内容", new="新增内容")

        resp = client.post("/api/a1/chat/confirm", json={
            "session_id": payload["session_id"],
            "kind": "fill",
            "proposal": {"key": proposal_key},
            "choice": "这两个是一个东西",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("needs_clarification") is not True
        assert session.answers.get("IP定位.name") == "原有内容；新增内容"

    def test_confirm_classifier_unavailable_falls_back_to_template(self, started, monkeypatch):
        """classify → 'other' (or raise) → needs_clarification template,
        byte-identical to the pre-D23 fallback text."""
        from app.api import a1_routes

        monkeypatch.setattr(
            a1_routes,
            "_get_interviewer",
            lambda: _FixedIntentInterviewer("other"),
        )
        client, payload = started
        session = a1_routes._SESSIONS[payload["session_id"]]
        proposal_key = _seed_proposal(session, old="原始值", new="冲突值")

        resp = client.post("/api/a1/chat/confirm", json={
            "session_id": payload["session_id"],
            "kind": "fill",
            "proposal": {"key": proposal_key},
            "choice": "嗯",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("needs_clarification") is True
        assert any(w in body["reply"] for w in ["替换", "合并", "放弃"])
        assert body["reply"] == (
            f"你之前定过【name】是『原始值』。"
            f"这次的『冲突值』——是要**替换**它，"
            f"还是两者**合并**（同一条里都保留），"
            f"还是先**放弃**这条修改？"
        )
        # zero side effect
        assert session.answers.get("IP定位.name") == "原始值"

    def test_confirm_classifier_exception_falls_back_to_template(self, started, monkeypatch):
        from app.api import a1_routes

        monkeypatch.setattr(
            a1_routes,
            "_get_interviewer",
            lambda: _FixedIntentInterviewer(RuntimeError("llm down")),
        )
        client, payload = started
        session = a1_routes._SESSIONS[payload["session_id"]]
        proposal_key = _seed_proposal(session)

        resp = client.post("/api/a1/chat/confirm", json={
            "session_id": payload["session_id"],
            "kind": "fill",
            "proposal": {"key": proposal_key},
            "choice": "嗯",
        })
        assert resp.status_code == 200
        assert resp.json().get("needs_clarification") is True
        assert session.answers.get("IP定位.name") == "原有内容"


class TestMergeUndoEndpoint:
    def test_merge_undo_endpoint_roundtrip(self, started):
        """Trigger an auto-merge on the session, undo via HTTP → restored
        True + answers restored; repeat → restored False (idempotent 200)."""
        from app.api import a1_routes
        from app.domains.creation.a1.guide_engine import _apply_fills
        from app.domains.creation.a1.interviewer import InterviewFill

        client, payload = started
        session_id = payload["session_id"]
        session = a1_routes._SESSIONS[session_id]
        key = "角色.desire"
        old_text = "最想躺平，但家里条件不好，整天当牛马"
        merged_text = "平凡的度过一生——最想躺平，但家里条件不好，整天当牛马"
        session.answers[key] = old_text
        file_diff, proposals = _apply_fills(session, [InterviewFill(
            module="角色", subfield="desire", value="平凡的度过一生",
            relation="equivalent", merged_value=merged_text,
        )])
        assert proposals == []
        assert len(session.auto_merge_log) == 1
        token = session.auto_merge_log[0]["token"]

        resp = client.post("/api/a1/merge/undo", json={
            "session_id": session_id, "token": token,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["restored"] is True
        assert body["field_key"] == key
        assert session.answers[key] == old_text

        # Idempotent replay: token already consumed → 200 restored=False
        resp2 = client.post("/api/a1/merge/undo", json={
            "session_id": session_id, "token": token,
        })
        assert resp2.status_code == 200
        assert resp2.json()["restored"] is False

    def test_merge_undo_unknown_session_404(self, client):
        resp = client.post("/api/a1/merge/undo", json={
            "session_id": "no_such_session", "token": "abc",
        })
        assert resp.status_code == 404


class TestChatAutoMergesPassthrough:
    def test_chat_response_carries_auto_merges(self, started, monkeypatch):
        """handle_message output dict (which carries "auto_merges" when
        merges happened) is returned as-is by the /api/a1/chat route."""
        from app.api import a1_routes

        def fake_handle_message(session, message, interviewer):
            return {
                "reply": "已合并。",
                "file_diff": [],
                "proposals": [],
                "phase": session.phase,
                "auto_merges": [{"merged": "平凡的度过一生——最想躺平", "field_key": "角色.desire"}],
            }

        monkeypatch.setattr(a1_routes, "handle_message", fake_handle_message)
        monkeypatch.setattr(
            a1_routes,
            "_get_interviewer",
            lambda: _FixedIntentInterviewer("other"),
        )
        client, payload = started
        resp = client.post("/api/a1/chat", json={
            "session_id": payload["session_id"], "message": "平凡的度过一生",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "auto_merges" in body
        assert body["auto_merges"][0]["merged"]


class TestAnswersTreeView:
    def test_get_file_answers_plain_strings_and_tree(self, started):
        """answers 值渲染为纯串；answers_tree 暴露完整节点结构。"""
        from app.api import a1_routes
        from app.domains.creation.a1.guide_engine import AnswerNode

        client, payload = started
        session = a1_routes._SESSIONS[payload["session_id"]]
        session.answers["角色.desire"] = AnswerNode(
            text="最想躺平",
            children=[AnswerNode(text="第二条", source="llm_fill")],
        )
        session.answers["IP定位.name"] = "纯串答案"

        resp = client.get(f"/api/a1/file/{payload['file_id']}")
        assert resp.status_code == 200
        body = resp.json()
        # answers: plain strings only
        assert body["answers"]["角色.desire"] == "最想躺平；第二条"
        assert body["answers"]["IP定位.name"] == "纯串答案"
        # answers_tree: full node structure
        tree = body["answers_tree"]
        assert tree["角色.desire"] == {
            "text": "最想躺平",
            "children": [{"text": "第二条", "children": [], "source": "llm_fill"}],
            "source": "",
        }
        assert tree["IP定位.name"] == {"text": "纯串答案", "children": [], "source": ""}
