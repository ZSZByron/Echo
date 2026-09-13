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


# =============================================================================
# J4 预算护栏：store 备份轮转 + 损坏恢复（2-A1-v0.5.1 §3 J4，#10 store 蒸发）
# =============================================================================


class TestStoreBackupRotation:
    def test_save_creates_and_rotates_backups(self, tmp_path):
        """save 轮转：path→.bak1→.bak2→.bak3（保留 3 份，更旧的删除）."""
        store = A1Store(tmp_path / "a1_store.json")
        from app.domains.creation.a1.guide_engine import A1Session

        main = tmp_path / "a1_store.json"
        for i in range(6):
            store.save(
                {f"s{i}": A1Session(session_id=f"s{i}", user_id="u")},
                {f"file{i}": {"marker": i}},
            )
        assert main.exists()
        bak1 = tmp_path / "a1_store.json.bak1"
        bak2 = tmp_path / "a1_store.json.bak2"
        bak3 = tmp_path / "a1_store.json.bak3"
        bak4 = tmp_path / "a1_store.json.bak4"
        assert bak1.exists() and bak2.exists() and bak3.exists()
        assert not bak4.exists()  # 超出保留数的旧备份被清理
        # 新鲜度排序：bak1 是上一次 save 的状态（marker=4），bak3 最老（marker=2）
        assert json.loads(bak1.read_text(encoding="utf-8"))["files"]["file4"]
        assert json.loads(bak2.read_text(encoding="utf-8"))["files"]["file3"]
        assert json.loads(bak3.read_text(encoding="utf-8"))["files"]["file2"]

    def test_corrupt_main_recovers_from_newest_backup(self, tmp_path):
        """主文件损坏 → 从最新可用备份恢复（#10 单点蒸发的读取侧缓解）.

        备份链保存的是历史状态：bak1 = 上一次 save（marker=1），
        当前态（marker=2）随主文件损坏丢失——恢复到最近的好状态。
        """
        store = A1Store(tmp_path / "a1_store.json")
        from app.domains.creation.a1.guide_engine import A1Session

        store.save(
            {"s1": A1Session(session_id="s1", user_id="u")},
            {"file1": {"marker": 1}},
        )
        store.save(
            {"s2": A1Session(session_id="s2", user_id="u")},
            {"file2": {"marker": 2}},
        )
        # 模拟主文件损坏（写坏 JSON）
        (tmp_path / "a1_store.json").write_text("{corrupt!!", encoding="utf-8")

        sessions, files = store.load()
        assert "file1" in files
        assert "s1" in sessions

    def test_all_corrupt_falls_back_empty(self, tmp_path):
        """主文件与所有备份都损坏 → 空态降级（不 raise，保持既有契约）."""
        store = A1Store(tmp_path / "a1_store.json")
        from app.domains.creation.a1.guide_engine import A1Session

        store.save(
            {"s1": A1Session(session_id="s1", user_id="u")},
            {"file1": {"marker": 1}},
        )
        (tmp_path / "a1_store.json").write_text("{corrupt", encoding="utf-8")
        (tmp_path / "a1_store.json.bak1").write_text("{also corrupt", encoding="utf-8")

        sessions, files = store.load()
        assert sessions == {}
        assert files == {}

    def test_missing_main_with_backup_recovers(self, tmp_path):
        """主文件被删但备份在 → 从备份恢复（误删保护；bak1=上一次状态）."""
        store = A1Store(tmp_path / "a1_store.json")
        from app.domains.creation.a1.guide_engine import A1Session

        store.save(
            {"s1": A1Session(session_id="s1", user_id="u")},
            {"file1": {"marker": 1}},
        )
        store.save(
            {"s2": A1Session(session_id="s2", user_id="u")},
            {"file2": {"marker": 2}},
        )
        (tmp_path / "a1_store.json").unlink()

        sessions, files = store.load()
        assert "file1" in files
        assert "s1" in sessions
