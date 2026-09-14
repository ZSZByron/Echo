"""J3 披露协议 · 路由级测试：warning ledger 汇集（2-A1-v0.5.1 §3 J3）.

覆盖 finalize 四通道合并（assemble/finalize/dead_edges/graphify）+
upload 条目保留 + get_file 暴露 + 标题截断披露 + upload truncated 落库。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import a1_routes
from app.main import app
from app.domains.creation.seed.a1_question_tree import all_subfield_keys
from tests.xt.conftest import full_answers, inject_answers
from tests.xt.helpers import ANCHOR, VALID_REL, FakeProvider, canned_graphify


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def started(client: TestClient):
    resp = client.post(
        "/api/a1/session/start", json={"user_id": "u_j3_ledger", "seed_id": 1}
    )
    assert resp.status_code == 200
    return client, resp.json()


def _finalize(client: TestClient, payload: dict) -> object:
    return client.post(f"/api/a1/file/{payload['file_id']}/finalize")


def _ledger(payload: dict) -> list[dict]:
    rec = a1_routes._FILES[payload["file_id"]]
    return rec.get("warnings", [])


def _has(ledger: list[dict], source: str, needle: str) -> bool:
    return any(
        e["source"] == source and needle in e["detail"] for e in ledger
    )


class TestFinalizeLedgerAssembly:
    """finalize 把四处警告合并为 file_rec["warnings"]（结构化 ledger）。"""

    def test_graphify_validation_warning_lands_in_ledger(self, started, monkeypatch):
        """级联 C 修复主案：success=True 时幻觉端点丢边警告不再蒸发."""
        client, payload = started
        inject_answers(payload["session_id"], full_answers())
        resp_ok = canned_graphify(
            entries=[{
                "anchor": ANCHOR,
                "items": [{"title": "斗气分裂", "content": "条目内容"}],
            }],
            edges=[{
                "from": "不存在的模块",
                "to": f"d:{ANCHOR}:斗气分裂",
                "relation": VALID_REL,
                "rationale": "幻觉",
                "confidence": "semantic",
            }],
        )
        fake = FakeProvider(resp_ok)
        monkeypatch.setattr(a1_routes, "create_provider", lambda *_a, **_k: fake)

        resp = _finalize(client, payload)
        assert resp.status_code == 200

        led = _ledger(payload)
        assert _has(led, "graphify", "引用了不存在的节点")
        entry = next(e for e in led if e["source"] == "graphify")
        assert entry["level"] == "warn"
        assert entry["count"] == 1

    def test_assemble_dedupe_lands_in_ledger(self, started, monkeypatch):
        client, payload = started
        inject_answers(payload["session_id"], full_answers())
        fake = FakeProvider(canned_graphify(
            entries=[{
                "anchor": ANCHOR,
                "items": [
                    {"title": "同题条目", "content": "甲"},
                    {"title": "同题条目", "content": "乙"},
                ],
            }],
        ))
        monkeypatch.setattr(a1_routes, "create_provider", lambda *_a, **_k: fake)

        assert _finalize(client, payload).status_code == 200
        led = _ledger(payload)
        assert _has(led, "assemble", "重复条目去重")

    def test_title_truncation_disclosed_in_assemble(self, started, monkeypatch):
        """级联 C：32 字标题静默截断 → assemble 警告披露（J3-4）."""
        client, payload = started
        inject_answers(payload["session_id"], full_answers())
        long_title = "星" * 40
        fake = FakeProvider(canned_graphify(
            entries=[{
                "anchor": ANCHOR,
                "items": [{"title": long_title, "content": "长标题条目"}],
            }],
        ))
        monkeypatch.setattr(a1_routes, "create_provider", lambda *_a, **_k: fake)

        assert _finalize(client, payload).status_code == 200
        led = _ledger(payload)
        assert _has(led, "assemble", "标题超32字已截断")
        # 节点 id 确实被截到 32 字（既有行为不变，只是新增披露）
        rec = a1_routes._FILES[payload["file_id"]]
        assert f"d:{ANCHOR}:" + "星" * 32 in rec["graph_json"]["nodes"]

    def test_dead_edges_aggregated_in_ledger(self, started, monkeypatch):
        client, payload = started
        inject_answers(payload["session_id"], full_answers())
        fake = FakeProvider(canned_graphify())
        monkeypatch.setattr(a1_routes, "create_provider", lambda *_a, **_k: fake)

        assert _finalize(client, payload).status_code == 200
        rec = a1_routes._FILES[payload["file_id"]]
        rec["confirmed_edges"]["term:幽灵A/term:幽灵B/衍生"] = {
            "from_node_id": "term:幽灵A",
            "to_node_id": "term:幽灵B",
            "relation": "衍生",
            "confidence": "semantic",
            "confirmed": True,
        }
        assert _finalize(client, payload).status_code == 200

        led = _ledger(payload)
        # 展示层 reason 已中文化（endpoint_missing → 端点缺失）
        assert _has(led, "dead_edges", "端点缺失")
        dead_entry = next(e for e in led if e["source"] == "dead_edges")
        assert dead_entry["count"] == 1
        assert dead_entry["level"] == "warn"

    def test_degrade_warning_lands_with_finalize_source(self, started):
        """autouse 默认 provider 工厂 raise → graphify 确定性降级（不打补丁）."""
        client, payload = started
        inject_answers(payload["session_id"], full_answers())

        resp = _finalize(client, payload)
        assert resp.status_code == 200
        led = _ledger(payload)
        assert _has(led, "finalize", "graphify failed")
        # 降级路径不应重复计入 graphify source（degrade 警告只走 finalize 通道）
        assert not _has(led, "graphify", "graphify failed")

    def test_upload_entries_preserved_through_finalize(self, started, monkeypatch):
        """upload 来源条目跨 finalize 存活（ledger 重建只动 finalize 时通道）."""
        client, payload = started
        inject_answers(payload["session_id"], full_answers())
        rec = a1_routes._FILES[payload["file_id"]]
        rec["warnings"] = [{
            "source": "upload", "detail": "原文超20000字已截断后解析",
            "count": 1, "level": "warn",
        }]
        fake = FakeProvider(canned_graphify())
        monkeypatch.setattr(a1_routes, "create_provider", lambda *_a, **_k: fake)

        assert _finalize(client, payload).status_code == 200
        led = _ledger(payload)
        assert _has(led, "upload", "原文超20000字已截断后解析")

    def test_clean_finalize_ledger_empty(self, started, monkeypatch):
        client, payload = started
        inject_answers(payload["session_id"], full_answers())
        fake = FakeProvider(canned_graphify(
            entries=[{
                "anchor": ANCHOR,
                "items": [{"title": "斗气分裂", "content": "条目内容"}],
            }],
            edges=[{
                "from": "力量体系",
                "to": f"d:{ANCHOR}:斗气分裂",
                "relation": VALID_REL,
                "rationale": "层级派生",
                "confidence": "semantic",
            }],
        ))
        monkeypatch.setattr(a1_routes, "create_provider", lambda *_a, **_k: fake)

        assert _finalize(client, payload).status_code == 200
        assert _ledger(payload) == []

    def test_answer_clips_land_in_ledger(self, started, monkeypatch):
        """J4：fills 写入层截断记录（session.answer_clips）→ finalize 进 ledger."""
        from app.domains.creation.a1.guide_engine import _apply_fills
        from app.domains.creation.a1.interviewer import InterviewFill

        client, payload = started
        session = a1_routes._SESSIONS[payload["session_id"]]
        _apply_fills(session, [
            InterviewFill(module="IP定位", subfield="name", value="灵" * 2500),
            InterviewFill(module="IP定位", subfield="concept", value="因果轮回"),
        ])
        assert len(session.answers["IP定位.name"]) == 2000
        assert len(session.answer_clips) == 1

        # 直注其余字段过门禁（J1 真值闸要求真值）
        inject_answers(payload["session_id"], full_answers())
        session.answers["IP定位.name"] = "灵" * 2000  # 保留截断后的值
        fake = FakeProvider(canned_graphify())
        monkeypatch.setattr(a1_routes, "create_provider", lambda *_a, **_k: fake)

        assert _finalize(client, payload).status_code == 200
        led = _ledger(payload)
        answers_entries = [e for e in led if e["source"] == "answers"]
        assert len(answers_entries) == 1
        assert "IP定位.name" in answers_entries[0]["detail"]
        assert "截断" in answers_entries[0]["detail"]
        assert answers_entries[0]["level"] == "warn"


class TestGetFileExposesLedger:
    def test_get_file_warnings_field(self, started):
        """get_file 响应常驻 warnings 字段（draft 态为空列表）."""
        client, payload = started
        resp = client.get(f"/api/a1/file/{payload['file_id']}")
        assert resp.status_code == 200
        assert resp.json()["warnings"] == []


class TestUploadTruncationLedger:
    def test_truncated_upload_persists_ledger_entry(self, client, monkeypatch):
        """>20000 字上传 → parse_modules truncated → rec["warnings"] upload 条目."""
        from app.domains.creation.seed.a1_question_tree import (
            all_subfield_keys as _keys,
        )
        key = _keys()[0]
        content = "星陨大陆总纲。" + "灵石矿脉塑造九州秩序。" * 1900  # >20000 字
        assert len(content) > 20000

        def _route(messages: list[dict[str, str]]) -> dict:
            system = messages[0]["content"]
            if "版权风险分析助手" in system:
                return {
                    "characters": [], "power_systems": [],
                    "world_keywords": [], "suspected_works": [],
                }
            if "IP版权合规审核员" in system:
                return {"risk_level": "low", "matches": []}
            if "世界观结构化专家" in system:
                return {"answers": {key: "星陨大陆"}, "innovations": []}
            raise AssertionError(f"unexpected prompt: {system[:40]}")

        fake = FakeProvider(_route)
        monkeypatch.setattr(a1_routes, "_get_upload_provider", lambda: fake)

        resp = client.post(
            "/api/a1/upload",
            json={"user_id": "u_j3_up", "filename": "world.md", "content": content},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["truncated"] is True

        rec = a1_routes._FILES[body["file_id"]]
        led = rec.get("warnings", [])
        assert any(
            e["source"] == "upload" and "截断" in e["detail"] for e in led
        )

    def test_short_upload_no_ledger_entry(self, client, monkeypatch):
        key = all_subfield_keys()[0]
        content = "星陨大陆设定。" + "灵石矿脉塑造九州秩序。" * 40  # <20000

        def _route(messages: list[dict[str, str]]) -> dict:
            system = messages[0]["content"]
            if "版权风险分析助手" in system:
                return {
                    "characters": [], "power_systems": [],
                    "world_keywords": [], "suspected_works": [],
                }
            if "IP版权合规审核员" in system:
                return {"risk_level": "low", "matches": []}
            if "世界观结构化专家" in system:
                return {"answers": {key: "星陨大陆"}, "innovations": []}
            raise AssertionError(f"unexpected prompt: {system[:40]}")

        fake = FakeProvider(_route)
        monkeypatch.setattr(a1_routes, "_get_upload_provider", lambda: fake)

        resp = client.post(
            "/api/a1/upload",
            json={"user_id": "u_j3_up2", "filename": "world.md", "content": content},
        )
        assert resp.status_code == 200
        assert resp.json()["truncated"] is False
        rec = a1_routes._FILES[resp.json()["file_id"]]
        assert rec.get("warnings", []) == []
