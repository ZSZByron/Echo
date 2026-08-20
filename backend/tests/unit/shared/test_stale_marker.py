"""Tests for stale_marker module — graph registry + stale marking (TDD)."""
from __future__ import annotations

import json
import time

import pytest

from app.domains.creation.shared.stale_marker import (
    ensure_registry,
    list_user_graphs,
    mark_downstream_stale,
    record_stale_usage,
    register_graph,
)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _db(tmp_path):
    return str(tmp_path / "test.db")


def _register(db: str, user_id: str, graph_code: str, stage: str = "W",
              instance_no: int = 1, version: int = 1,
              scene_id: str | None = None, display_name: str = "",
              parent_graph_code: str | None = None) -> str:
    return register_graph(
        db, user_id, graph_code, stage, instance_no, version,
        scene_id=scene_id, display_name=display_name,
        parent_graph_code=parent_graph_code,
    )


# ── ① Register W1-v1/W1-v2/M1 → list grouped by IP, artifacts desc ──────────


def test_register_and_list_grouped_by_ip_desc_order(tmp_path):
    db = _db(tmp_path)
    ensure_registry(db)

    # Register in chronological order: W1-v1, W1-v2, M1
    g1 = _register(db, "u1", "IP0001-W1-v1", stage="W", instance_no=1, version=1)
    time.sleep(0.05)
    g2 = _register(db, "u1", "IP0001-W1-v2", stage="W", instance_no=1, version=2)
    time.sleep(0.05)
    g3 = _register(db, "u1", "IP0001-M1-v1", stage="M", instance_no=1, version=1,
                    parent_graph_code="IP0001-W1-v1")

    assert g1 != g2 != g3  # distinct UUIDs

    result = list_user_graphs(db, "u1")

    # Single IP group: IP0001
    assert "ips" in result
    assert len(result["ips"]) == 1
    ip_entry = result["ips"][0]
    assert ip_entry["ip_code"] == "IP0001"

    # Artifacts: 3 total, ordered by created_at DESC (M1 latest, then v2, then v1)
    artifacts = ip_entry["artifacts"]
    assert len(artifacts) == 3
    # M1 registered last, so it comes first in DESC order
    assert artifacts[0]["graph_code"] == "IP0001-M1-v1"
    assert artifacts[1]["graph_code"] == "IP0001-W1-v2"
    assert artifacts[2]["graph_code"] == "IP0001-W1-v1"

    # Verify fields on first artifact (M1)
    a = artifacts[0]
    assert "graph_id" in a
    assert a["stage"] == "M"
    assert a["instance_no"] == 1
    assert a["version"] == 1
    assert a["status"] == "finalized"
    assert "created_at" in a
    assert a["parent_graph_code"] == "IP0001-W1-v1"


# ── ② M1 parent=W1-v1, mark_downstream_stale → 1 marked, M1 stale ──────────


def test_mark_downstream_stale_marks_children(tmp_path):
    db = _db(tmp_path)
    ensure_registry(db)

    _register(db, "u1", "IP0001-W1-v1", stage="W", instance_no=1, version=1)
    _register(db, "u1", "IP0001-M1-v1", stage="M", instance_no=1, version=1,
              parent_graph_code="IP0001-W1-v1")

    change_set = {"reason": "W1-v1 updated", "field": "nodes"}
    count = mark_downstream_stale(db, "IP0001-W1-v1", change_set)

    assert count == 1

    # Verify M1 is now stale with change_set
    result = list_user_graphs(db, "u1")
    artifacts = result["ips"][0]["artifacts"]
    m1 = [a for a in artifacts if a["graph_code"] == "IP0001-M1-v1"][0]
    assert m1["status"] == "stale"
    assert json.loads(m1["change_set"]) == change_set


# ── ③ Repeated mark → 0 (idempotent) ────────────────────────────────────────


def test_mark_downstream_stale_idempotent(tmp_path):
    db = _db(tmp_path)
    ensure_registry(db)

    _register(db, "u1", "IP0001-W1-v1", stage="W", instance_no=1, version=1)
    _register(db, "u1", "IP0001-M1-v1", stage="M", instance_no=1, version=1,
              parent_graph_code="IP0001-W1-v1")

    change_set = {"reason": "first"}
    count1 = mark_downstream_stale(db, "IP0001-W1-v1", change_set)
    count2 = mark_downstream_stale(db, "IP0001-W1-v1", {"reason": "second"})

    assert count1 == 1
    assert count2 == 0  # already stale, no-op


# ── ④ Stale items still appear in list ──────────────────────────────────────


def test_stale_items_included_in_list(tmp_path):
    db = _db(tmp_path)
    ensure_registry(db)

    _register(db, "u1", "IP0001-W1-v1", stage="W", instance_no=1, version=1)
    _register(db, "u1", "IP0001-M1-v1", stage="M", instance_no=1, version=1,
              parent_graph_code="IP0001-W1-v1")

    mark_downstream_stale(db, "IP0001-W1-v1", {"x": 1})

    result = list_user_graphs(db, "u1")
    artifacts = result["ips"][0]["artifacts"]
    statuses = {a["status"] for a in artifacts}
    assert "stale" in statuses
    assert "finalized" in statuses
    assert len(artifacts) == 2  # nothing removed


# ── ⑤ record_stale_usage → used_stale=1 ────────────────────────────────────


def test_record_stale_usage(tmp_path):
    db = _db(tmp_path)
    ensure_registry(db)

    _register(db, "u1", "IP0001-W1-v1", stage="W", instance_no=1, version=1)
    _register(db, "u1", "IP0001-M1-v1", stage="M", instance_no=1, version=1,
              parent_graph_code="IP0001-W1-v1")
    mark_downstream_stale(db, "IP0001-W1-v1", {"x": 1})

    record_stale_usage(db, "IP0001-M1-v1")

    result = list_user_graphs(db, "u1")
    artifacts = result["ips"][0]["artifacts"]
    m1 = [a for a in artifacts if a["graph_code"] == "IP0001-M1-v1"][0]
    assert m1["used_stale"] == 1


# ── ⑥ No downstream → return 0 ──────────────────────────────────────────────


def test_mark_downstream_stale_no_children(tmp_path):
    db = _db(tmp_path)
    ensure_registry(db)

    _register(db, "u1", "IP0001-W1-v1", stage="W", instance_no=1, version=1)

    count = mark_downstream_stale(db, "IP0001-W1-v1", {"x": 1})
    assert count == 0


# ── ⑦ TestClient: GET /api/graphs?user_id=u1 → 200 with ips key ─────────────


def test_graphs_api_returns_200_with_ips_structure(tmp_path, monkeypatch):
    """Integration test: GET /api/graphs?user_id=u1 returns 200."""
    db = _db(tmp_path)
    ensure_registry(db)
    _register(db, "u1", "IP0001-W1-v1", stage="W", instance_no=1, version=1)
    _register(db, "u1", "IP0001-W1-v2", stage="W", instance_no=1, version=2)

    # Monkeypatch the DB path used by the route
    from app.api import graph_registry_routes
    monkeypatch.setattr(graph_registry_routes, "_REGISTRY_DB", db)

    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/graphs", params={"user_id": "u1"})
    assert resp.status_code == 200
    body = resp.json()
    assert "ips" in body
    assert len(body["ips"]) == 1
    assert body["ips"][0]["ip_code"] == "IP0001"
    assert len(body["ips"][0]["artifacts"]) == 2
