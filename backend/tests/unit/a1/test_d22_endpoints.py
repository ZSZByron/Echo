"""D22 三对端点契约测试 — world-bible / character-codex / story-outline。

八步范式逐件照 doc 端点（test_doc_endpoints_m3.py 模式）：
- 409 依赖链：draft → pending_finalize（与 doc 同口径）。
- 空图谱 session 三 POST 均 200 + 降级披露（D22 全 optional，非 409/500）。
- 发号格式：IP0001-B1-v1 / IP0001-C1-v1 / IP0001-O1-v1。
- GET md/json 双序列化；stored 无 → 409 pending_finalize。
- stale 永不 409：used_stale 留痕。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import a1_routes
from app.domains.creation.a1.guide_engine import A1Session
from app.domains.creation.shared import stale_marker
from app.main import app

UPSTREAM_CODE = "IP0001-W1-v1"


def _setup_finalized_file(monkeypatch, tmp_path, user_id="u_d22",
                          file_id="f_d22", stale=False, answers=None):
    """注入 finalized 会话 + 文件记录（隔离 issuer/registry 到 tmp）。"""
    issuer_db = tmp_path / "codes.db"
    registry_db = tmp_path / "ugc.db"
    monkeypatch.setattr(a1_routes, "_ISSUER_DB", issuer_db)
    monkeypatch.setattr(a1_routes, "_registry_db", lambda: str(registry_db))
    stale_marker.ensure_registry(registry_db)

    session = A1Session(
        session_id="s_d22", user_id=user_id,
        answers=answers if answers is not None else {
            "力量体系.cost": "消耗体力",
            "世界本体.reality_rule": "物质法则主导",
            "剧情.lead_in": "少年拾剑",
        },
    )
    a1_routes._SESSIONS[session.session_id] = session
    rec = {
        "file_id": file_id,
        "session_id": session.session_id,
        "status": "finalized",
        "graph_code": UPSTREAM_CODE,
        "ip": 1,
        "graph_json": {"scene_id": "s_d22", "nodes": [], "edges": []},
        "warnings": [],
    }
    a1_routes._FILES[file_id] = rec

    if stale:
        stale_marker.register_graph(
            registry_db, user_id, "IP0001-W2-v1", "W", 2, 1,
        )
        stale_marker.mark_downstream_stale(
            registry_db, UPSTREAM_CODE, {"diff_summary": "re-finalized"},
        )
    return rec, str(registry_db)


@pytest.fixture()
def client():
    return TestClient(app)


D22_PATHS = (
    ("world-bible", "bible_code", "B"),
    ("character-codex", "codex_code", "C"),
    ("story-outline", "outline_code", "O"),
)


class TestD22EndpointContracts:
    @pytest.mark.parametrize("suffix,code_key,stage", D22_PATHS)
    def test_requires_finalized(
        self, client, monkeypatch, tmp_path, suffix, code_key, stage,
    ):
        _setup_finalized_file(monkeypatch, tmp_path)
        a1_routes._FILES["f_d22"]["status"] = "draft"
        resp = client.post(f"/api/a1/file/f_d22/{suffix}")
        assert resp.status_code == 409
        assert resp.json()["detail"] == "pending_finalize"

    @pytest.mark.parametrize("suffix,code_key,stage", D22_PATHS)
    def test_generates_with_stage_code(
        self, client, monkeypatch, tmp_path, suffix, code_key, stage,
    ):
        _setup_finalized_file(monkeypatch, tmp_path)
        resp = client.post(f"/api/a1/file/f_d22/{suffix}")
        assert resp.status_code == 200
        body = resp.json()
        assert body[code_key] == f"IP0001-{stage}1-v1"
        assert body["used_stale"] is False
        assert body["graph_id"]

    @pytest.mark.parametrize("suffix,code_key,stage", D22_PATHS)
    def test_empty_graph_session_still_200_with_degradation_disclosure(
        self, client, monkeypatch, tmp_path, suffix, code_key, stage,
    ):
        """空图谱 session：D22 三件全 optional——200 + 降级披露，非 409/500。"""
        _setup_finalized_file(monkeypatch, tmp_path, answers={})
        resp = client.post(f"/api/a1/file/f_d22/{suffix}")
        assert resp.status_code == 200
        ledger = resp.json()["ledger"]
        assert ledger  # 必有披露
        if suffix == "world-bible":
            assert any("world_bible_empty_chapters" in e["detail"]
                       for e in ledger)
        elif suffix == "character-codex":
            assert any("character_codex_degraded" in e["detail"]
                       for e in ledger)
        else:
            assert any("story_outline_degraded" in e["detail"]
                       for e in ledger)

    @pytest.mark.parametrize("suffix,code_key,stage", D22_PATHS)
    def test_get_md_and_json(
        self, client, monkeypatch, tmp_path, suffix, code_key, stage,
    ):
        _setup_finalized_file(monkeypatch, tmp_path)
        client.post(f"/api/a1/file/f_d22/{suffix}")
        md = client.get(f"/api/a1/file/f_d22/{suffix}?format=md")
        assert md.status_code == 200
        assert md.headers["content-type"].startswith("text/markdown")
        assert "# " in md.text
        assert "溯源：" in md.text
        js = client.get(f"/api/a1/file/f_d22/{suffix}?format=json")
        assert js.status_code == 200
        doc = js.json()
        assert doc["graph_code"].startswith(f"IP0001-{stage}")
        if suffix == "world-bible":
            assert len(doc["chapters"]) == 6
        elif suffix == "character-codex":
            assert len(doc["chapters"]) == 7
        else:
            assert len(doc["sections"]) == 6

    @pytest.mark.parametrize("suffix,code_key,stage", D22_PATHS)
    def test_get_before_generate_409(
        self, client, monkeypatch, tmp_path, suffix, code_key, stage,
    ):
        _setup_finalized_file(monkeypatch, tmp_path)
        resp = client.get(f"/api/a1/file/f_d22/{suffix}")
        assert resp.status_code == 409
        assert resp.json()["detail"] == "pending_finalize"

    @pytest.mark.parametrize("suffix,code_key,stage", D22_PATHS)
    def test_stale_never_409_records_usage(
        self, client, monkeypatch, tmp_path, suffix, code_key, stage,
    ):
        _setup_finalized_file(monkeypatch, tmp_path, stale=True)
        resp = client.post(f"/api/a1/file/f_d22/{suffix}")
        assert resp.status_code == 200
        assert resp.json()["used_stale"] is True
