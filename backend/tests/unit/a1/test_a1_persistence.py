"""A1 disk persistence tests (v0.5 A1) — round trip, atomicity, corruption.

The autouse ``_isolated_a1_store`` fixture in conftest points the store at a
tmp file, so these tests never touch the real ``backend/data/a1_store.json``.
Zero real LLM calls (finalize's graphify_llm is monkeypatched to degrade;
chat degrades via the autouse provider stub).
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.api import a1_routes
from app.domains.creation.a1.graphify import GraphifyResult
from app.domains.creation.a1.store import A1Store
from app.domains.creation.seed.a1_question_tree import MODULES
from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def _start(client) -> dict:
    resp = client.post(
        "/api/a1/session/start", json={"user_id": "u_persist", "seed_id": 1}
    )
    assert resp.status_code == 200
    return resp.json()


def _inject_answers(payload: dict) -> None:
    session = a1_routes._SESSIONS[payload["session_id"]]
    for m in MODULES:
        need = len(m["fields"]) // 2 + 1
        for f in m["fields"][:need]:
            session.answers[f"{m['id']}.{f['id']}"] = "测试内容"


def _finalize_degraded(client, payload: dict, monkeypatch) -> None:
    _inject_answers(payload)
    monkeypatch.setattr(
        "app.api.a1_routes.graphify_llm",
        lambda *a, **kw: GraphifyResult(
            success=False, warning="graphify degraded (test)"
        ),
    )
    fin = client.post(f"/api/a1/file/{payload['file_id']}/finalize")
    assert fin.status_code == 200


class TestPersistenceRoundTrip:
    def test_finalize_state_survives_memory_wipe(
        self, client, monkeypatch
    ):
        """Full round trip: start → finalize (degraded) → wipe memory →
        reload from disk → file record intact (graph_json/answers/etc.)."""
        payload = _start(client)
        _finalize_degraded(client, payload, monkeypatch)
        fid = payload["file_id"]
        sid = payload["session_id"]

        # store file written on the success paths
        assert a1_routes._STORE.path.exists()

        # simulate a backend restart: wipe in-memory state, reload
        a1_routes._SESSIONS.clear()
        a1_routes._FILES.clear()
        a1_routes._loaded = False
        a1_routes._load_once()

        assert fid in a1_routes._FILES
        assert sid in a1_routes._SESSIONS
        rec = a1_routes._FILES[fid]
        assert rec["status"] == "finalized"
        assert rec["graph_json"] and rec["graph_json"]["nodes"]
        assert rec["graph_code"]
        # answers survived via the session model
        assert a1_routes._SESSIONS[sid].answers
        # edge bookkeeping structures survive
        assert "confirmed_edges" in rec and "open_questions" in rec

    def test_chat_answer_survives_reload(self, client):
        """Chat fill (degraded interviewer) is persisted to disk."""
        payload = _start(client)
        sid = payload["session_id"]
        from app.domains.creation.seed.a1_question_tree import (
            first_subfield,
            get_module,
        )

        module_id = a1_routes._SESSIONS[sid].current_module
        module = get_module(module_id)
        sf = module["fields"][0]
        resp = client.post(
            "/api/a1/chat",
            json={"session_id": sid, "message": f"{sf['label']}：测试回答"},
        )
        assert resp.status_code == 200
        # whatever the interviewer produced, the store file exists
        assert a1_routes._STORE.path.exists()
        doc = json.loads(a1_routes._STORE.path.read_text(encoding="utf-8"))
        assert sid in doc["sessions"]
        assert payload["file_id"] in doc["files"]


class TestAtomicWrite:
    def test_no_tmp_file_left_after_save(self):
        store = A1Store()
        store.save({}, {})
        tmp = store.path.with_suffix(store.path.suffix + ".tmp")
        assert store.path.exists()
        assert not tmp.exists()


class TestCorruptStore:
    def test_corrupt_file_loads_empty_not_raise(self, tmp_path):
        path = tmp_path / "corrupt.json"
        path.write_text("{not valid json!!", encoding="utf-8")
        sessions, files = A1Store(path).load()
        assert sessions == {}
        assert files == {}

    def test_missing_file_loads_empty(self, tmp_path):
        sessions, files = A1Store(tmp_path / "absent.json").load()
        assert sessions == {}
        assert files == {}

    def test_corrupt_store_boot_degrades_gracefully(self, client, monkeypatch):
        """A corrupt store file must not break new sessions."""
        garbage = a1_routes._STORE.path
        garbage.parent.mkdir(parents=True, exist_ok=True)
        garbage.write_text("<<<corrupt>>>", encoding="utf-8")
        a1_routes._loaded = False
        payload = _start(client)
        assert payload["file_id"]


class TestStoreUnit:
    def test_non_json_values_saved_via_default_str(self, tmp_path):
        """default=str guards non-JSON values inside file records."""
        store = A1Store(tmp_path / "s.json")
        store.save(
            {}, {"f1": {"when": __import__("datetime").datetime(2026, 1, 1)}}
        )
        _, files = store.load()
        assert files["f1"]["when"]  # stringified, no crash
