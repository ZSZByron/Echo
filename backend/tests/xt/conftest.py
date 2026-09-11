"""Shared fixtures for the extreme-testing (xt) suite.

Store-file isolation is session-scoped in tests/conftest.py (A1_STORE_PATH);
this conftest adds per-test in-memory dict cleanup. Shared fakes/builders
live in tests/xt/helpers.py (single source, importable from test modules).
"""
from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api import a1_routes
from app.domains.creation.seed.a1_question_tree import all_subfield_keys
from app.main import app


@pytest.fixture(autouse=True)
def _clean_a1_memory():
    """Isolate a1_routes in-memory dicts per test (store file isolation is
    already session-scoped). Also drop zombie visual-bg thread registry."""
    a1_routes._SESSIONS.clear()
    a1_routes._FILES.clear()
    a1_routes._visual_bg_tasks.clear()
    yield
    a1_routes._SESSIONS.clear()
    a1_routes._FILES.clear()
    a1_routes._visual_bg_tasks.clear()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def started(client: TestClient):
    resp = client.post(
        "/api/a1/session/start", json={"user_id": "u_xt_auto", "seed_id": 1}
    )
    assert resp.status_code == 200
    return client, resp.json()


def inject_answers(session_id: str, answers: dict[str, str]) -> None:
    """Write answers straight into the live session (deterministic setup,
    bypasses the interview LLM)."""
    session = a1_routes._SESSIONS[session_id]
    session.answers = dict(answers)


def full_answers(value_fn: Any = None) -> dict[str, str]:
    """Every subfield answered with a non-empty value."""
    if value_fn is None:
        value_fn = lambda k: f"答案-{k}"  # noqa: E731
    return {k: value_fn(k) for k in all_subfield_keys()}


@pytest.fixture()
def no_visual_bg(monkeypatch: pytest.MonkeyPatch):
    """Kill the background visual-bg pipeline (it would hit a real provider
    via create_provider inside its own thread)."""

    async def _noop(_file_id: str) -> None:
        return None

    monkeypatch.setattr(a1_routes, "_pregenerate_visual_bg", _noop)
