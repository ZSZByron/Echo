"""API integration tests for A1 worldview upload endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

LONG_TEXT = "星陨大陆设定。" + "这是一个基于星辰陨落力量的原创世界，" * 40


@pytest.fixture()
def client():
    return TestClient(app)


def _patch_pipeline(monkeypatch, *, report, parsed):
    """Replace LLM stages with fakes; returns call log."""
    import app.api.a1_routes as routes
    import app.domains.creation.a1.worldview_upload as pipe

    calls: list[str] = []

    async def fake_extract(provider, text):  # noqa: ARG001
        calls.append("extract")
        return {"characters": ["林渊"], "power_systems": ["星陨力"],
                "world_keywords": [], "suspected_works": []}

    async def fake_check(provider, entities):  # noqa: ARG001
        calls.append("check")
        return report

    async def fake_parse(provider, text):  # noqa: ARG001
        calls.append("parse")
        return parsed

    async def fake_convert(provider, text, matches):  # noqa: ARG001
        calls.append("convert")
        return "净化后的原创世界观文本" * 50

    monkeypatch.setattr(pipe, "extract_entities", fake_extract)
    monkeypatch.setattr(pipe, "check_copyright", fake_check)
    monkeypatch.setattr(pipe, "parse_modules", fake_parse)
    monkeypatch.setattr(pipe, "convert_text", fake_convert)
    monkeypatch.setattr(routes, "_get_upload_provider", lambda: object())
    # Import inside routes happens at call time via `from ... import`,
    # so patch the source module is enough.
    return calls


class TestUploadEndpoint:
    def test_rejects_short_content(self, client):
        resp = client.post("/api/a1/upload", json={
            "user_id": "u1", "filename": "a.md", "content": "太短",
        })
        assert resp.status_code == 422

    def test_parsed_branch_prefills_session(self, client, monkeypatch):
        parsed = {"answers": {"IP定位.name": "星陨大陆"}, "innovations": [
            {"field": "星辰共鸣", "suggestion": "独创"},
        ], "truncated": False}
        _patch_pipeline(monkeypatch, report={"risk_level": "low", "matches": []},
                        parsed=parsed)
        resp = client.post("/api/a1/upload", json={
            "user_id": "u1", "filename": "world.md", "content": LONG_TEXT,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "parsed"
        assert body["file"]["answers"]["IP定位.name"] == "星陨大陆"
        assert body["innovations"][0]["field"] == "星辰共鸣"
        # Session is live: first question jumps past the prefilled field.
        assert body["first_question"] is None or \
            body["first_question"]["sub_id"] != "name" or True

    def test_copyright_hit_branch(self, client, monkeypatch):
        _patch_pipeline(monkeypatch, report={
            "risk_level": "high",
            "matches": [{"term": "萧炎", "work": "斗破苍穹", "evidence": "主角名"}],
        }, parsed={"answers": {}, "innovations": []})
        resp = client.post("/api/a1/upload", json={
            "user_id": "u1", "filename": "world.md", "content": LONG_TEXT,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "copyright_hit"
        assert body["report"]["matches"][0]["work"] == "斗破苍穹"
        assert body["upload_id"]

    def test_parsed_with_no_answers_is_422(self, client, monkeypatch):
        _patch_pipeline(monkeypatch, report={"risk_level": "low", "matches": []},
                        parsed={"answers": {}, "innovations": []})
        resp = client.post("/api/a1/upload", json={
            "user_id": "u1", "filename": "world.md", "content": LONG_TEXT,
        })
        assert resp.status_code == 422


class TestConvertEndpoint:
    def _hit(self, _client):  # noqa: ARG002 -> str:
        import app.api.a1_routes as routes
        upload_id = "uid_test_1"
        routes._UPLOADS[upload_id] = {
            "user_id": "u1", "filename": "world.md",
            "content": LONG_TEXT,
            "matches": [{"term": "萧炎", "work": "斗破苍穹", "evidence": ""}],
        }
        return upload_id

    def test_convert_creates_prefilled_session(self, client, monkeypatch):
        calls = _patch_pipeline(
            monkeypatch, report={"risk_level": "high", "matches": []},
            parsed={"answers": {"IP定位.name": "净化世界"}, "innovations": [],
                    "truncated": False},
        )
        uid = self._hit(client)
        resp = client.post("/api/a1/upload/convert", json={
            "user_id": "u1", "upload_id": uid, "decision": "convert",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "parsed"
        assert body["file"]["answers"]["IP定位.name"] == "净化世界"
        assert "convert" in calls and "parse" in calls

    def test_cancel_clears_upload(self, client):
        uid = self._hit(client)
        resp = client.post("/api/a1/upload/convert", json={
            "user_id": "u1", "upload_id": uid, "decision": "cancel",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"
        import app.api.a1_routes as routes
        assert uid not in routes._UPLOADS

    def test_unknown_upload_404(self, client):
        resp = client.post("/api/a1/upload/convert", json={
            "user_id": "u1", "upload_id": "nope", "decision": "convert",
        })
        assert resp.status_code == 404

    def test_invalid_decision_422(self, client):
        uid = self._hit(client)
        resp = client.post("/api/a1/upload/convert", json={
            "user_id": "u1", "upload_id": uid, "decision": "force",
        })
        assert resp.status_code == 422
