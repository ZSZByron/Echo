# -*- coding: utf-8 -*-
"""M3 端点契约测试 — 文档输出（doc，D15）+ TD/TC 依赖 409 链。

- 409 依赖链：draft → pending_finalize；缺骰子 → missing_dice_template
  （契约族照搬，S1:241-253）。
- stale 永不 409：上游重定稿后 doc/TD/TC 照常产出，used_stale 留痕。
- ledger 透传：module_compile 降级披露并入 file warnings（J3 五源纪律）。
- 零 LLM key 免费线：provider 注入失败 → 确定性骨架照常产出。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import a1_routes
from app.domains.creation.a1.guide_engine import A1Session
from app.domains.creation.a1.warning_ledger import entry as ledger_entry
from app.domains.creation.shared import stale_marker
from app.domains.creation.shared.module_registry import MODULE_POOL
from app.main import app

UPSTREAM_CODE = "IP0001-W1-v1"


def _setup_finalized_file(monkeypatch, tmp_path, user_id="u_m3",
                          file_id="f_m3", stale=False):
    """注入一个 finalized 会话 + 文件记录（隔离 issuer/registry 到 tmp）。"""
    issuer_db = tmp_path / "codes.db"
    registry_db = tmp_path / "ugc.db"
    monkeypatch.setattr(a1_routes, "_ISSUER_DB", issuer_db)
    monkeypatch.setattr(a1_routes, "_registry_db", lambda: str(registry_db))
    stale_marker.ensure_registry(registry_db)

    session = A1Session(
        session_id="s_m3", user_id=user_id,
        answers={
            "骰子设定.probability": "百分比骰",
            "骰子设定.check_mode": "对抗检定",
            "骰子设定.success_check": "达到难度值即成功",
            "力量体系.cost": "消耗体力",
            "世界本体.reality_rule": "物质法则主导",
            "历史时间线.main_plot": "剑补天",
            "设定边界.immutable_core": "神王不可被杀死",
        },
    )
    a1_routes._SESSIONS[session.session_id] = session
    rec = {
        "file_id": file_id,
        "session_id": session.session_id,
        "status": "finalized",
        "graph_code": UPSTREAM_CODE,
        "ip": 1,
        "graph_json": {"scene_id": "s_m3", "nodes": [], "edges": []},
        "warnings": [ledger_entry("upload", "[upload] 测试截断")],
    }
    a1_routes._FILES[file_id] = rec

    if stale:
        # 上游重定稿：W1-v1 被标记 stale（不阻断——铁律 2）
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


class TestDocEndpoints:
    def test_doc_generate_requires_finalized(self, client, monkeypatch, tmp_path):
        _setup_finalized_file(monkeypatch, tmp_path)
        a1_routes._FILES["f_m3"]["status"] = "draft"
        resp = client.post("/api/a1/file/f_m3/doc")
        assert resp.status_code == 409
        assert resp.json()["detail"] == "pending_finalize"

    def test_doc_generate_zero_llm_free_line(self, client, monkeypatch, tmp_path):
        """provider None（无 key）→ 骨架照常产出（免费线可跑通）。"""
        _setup_finalized_file(monkeypatch, tmp_path)
        monkeypatch.setattr(
            a1_routes, "create_provider",
            lambda cfg: (_ for _ in ()).throw(RuntimeError("no key")),
        )
        resp = client.post("/api/a1/file/f_m3/doc")
        assert resp.status_code == 200
        body = resp.json()
        assert body["doc_code"].startswith("IP0001-M")
        assert body["used_stale"] is False
        # ledger 透传：upload 旧条目保留 + 降级披露追加
        details = [e["detail"] for e in body["ledger"]]
        assert any("测试截断" in d for d in details)
        assert any("module_compile_degraded" in d for d in details)

    def test_doc_get_md_and_json(self, client, monkeypatch, tmp_path):
        _setup_finalized_file(monkeypatch, tmp_path)
        client.post("/api/a1/file/f_m3/doc")
        md = client.get("/api/a1/file/f_m3/doc?format=md")
        assert md.status_code == 200
        assert md.headers["content-type"].startswith("text/markdown")
        assert "# " in md.text
        js = client.get("/api/a1/file/f_m3/doc?format=json")
        assert js.status_code == 200
        assert len(js.json()["sections"]) == 9

    def test_doc_get_before_generate_409(self, client, monkeypatch, tmp_path):
        _setup_finalized_file(monkeypatch, tmp_path)
        resp = client.get("/api/a1/file/f_m3/doc")
        assert resp.status_code == 409

    def test_stale_upstream_never_409_and_records_usage(
        self, client, monkeypatch, tmp_path,
    ):
        rec, registry_db = _setup_finalized_file(
            monkeypatch, tmp_path, stale=True,
        )
        resp = client.post("/api/a1/file/f_m3/doc")
        assert resp.status_code == 200  # stale 不阻断
        assert resp.json()["used_stale"] is True


class TestDiceCharacterEndpoints:
    def test_dice_requires_finalized(self, client, monkeypatch, tmp_path):
        _setup_finalized_file(monkeypatch, tmp_path)
        a1_routes._FILES["f_m3"]["status"] = "draft"
        resp = client.post("/api/a1/file/f_m3/dice-template")
        assert resp.status_code == 409
        assert resp.json()["detail"] == "pending_finalize"

    def test_dice_projection_issues_td_code(self, client, monkeypatch, tmp_path):
        _setup_finalized_file(monkeypatch, tmp_path)
        resp = client.post("/api/a1/file/f_m3/dice-template")
        assert resp.status_code == 200
        body = resp.json()
        assert body["template"]["graph_code"].startswith("IP0001-TD")
        assert body["template"]["signal_sources"]

    def test_dice_tolerates_string_node_ids_in_graph(
        self, client, monkeypatch, tmp_path,
    ):
        """F3 回归：定稿图 nodes 混入纯字符串节点 id 时 dice-template
        不得 500（_cst_constraints 消费端容错，dict 与 str 并存）。"""
        rec, _ = _setup_finalized_file(monkeypatch, tmp_path)
        rec["graph_json"]["nodes"] = [
            {"id": "n1", "serial_number": "2-1", "level": 2,
             "description": "普通节点"},
            "cst_LAW.immutable",
            {"id": "cst_ACT.cost", "serial_number": "9-1", "level": 2,
             "description": "消耗体力"},
        ]
        resp = client.post("/api/a1/file/f_m3/dice-template")
        assert resp.status_code == 200
        # 字符串节点无 description，仅 dict 形态的 cst 节点贡献约束文本
        assert "消耗体力" in str(resp.json()["template"])

    def test_character_without_dice_409_contract(
        self, client, monkeypatch, tmp_path,
    ):
        _setup_finalized_file(monkeypatch, tmp_path)
        resp = client.post("/api/a1/file/f_m3/character-template")
        assert resp.status_code == 409
        assert resp.json()["detail"] == "missing_dice_template"

    def test_character_after_dice_issues_tc_code(
        self, client, monkeypatch, tmp_path,
    ):
        _setup_finalized_file(monkeypatch, tmp_path)
        client.post("/api/a1/file/f_m3/dice-template")
        resp = client.post("/api/a1/file/f_m3/character-template")
        assert resp.status_code == 200
        assert resp.json()["template"]["graph_code"].startswith("IP0001-TC")
        assert resp.json()["template"]["dice_template_code"].startswith(
            "IP0001-TD",
        )

    def test_character_stale_never_409(self, client, monkeypatch, tmp_path):
        _setup_finalized_file(monkeypatch, tmp_path, stale=True)
        client.post("/api/a1/file/f_m3/dice-template")
        resp = client.post("/api/a1/file/f_m3/character-template")
        assert resp.status_code == 200
        assert resp.json()["template"]["used_stale"] is True


class TestOutputModulesNotInInterviewFlow:
    """产出模块是终局生产者：不出现在任何问卷面。"""

    def test_not_in_sections_for_any_session(self):
        from app.api.a1_routes import _build_sections
        s = A1Session(session_id="s", user_id="u")
        ids = [sec["id"] for sec in _build_sections(s)]
        assert not set(ids) & {"主模组文字版", "骰子投影", "角色投影"}

    def test_pool_still_has_all_worldview_modules(self):
        from app.domains.creation.seed.a1_question_tree import module_ids
        assert set(module_ids()) <= set(MODULE_POOL)
