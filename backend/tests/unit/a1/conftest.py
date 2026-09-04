"""Shared fixtures and test doubles for a1 unit tests.

Provides ``StubLLMProvider`` — a programmable LLM test double aligned with
the ``FakeProvider`` pattern used in ``test_concept_edge_extractor.py``.

Three programmable modes (combinable):

1. **Normal**     — returns a preset JSON ``response`` dict.
2. ``raise_error`` — injects an exception (simulate API failure).
3. ``sleep_seconds`` — injects an async delay (simulate timeout / latency).

Zero real API calls.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from app.ai.provider import LLMProvider


class StubLLMProvider(LLMProvider):
    """Programmable stub LLM provider for contract tests."""

    def __init__(
        self,
        response: dict[str, Any] | None = None,
        raise_error: Exception | None = None,
        sleep_seconds: float = 0.0,
    ) -> None:
        self.response = response or {}
        self.raise_error = raise_error
        self.sleep_seconds = sleep_seconds
        self.chat_json_calls = 0
        self.chat_calls = 0
        self.last_messages: list[dict[str, str]] | None = None

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        self.chat_calls += 1
        self.last_messages = messages
        if self.sleep_seconds > 0:
            await asyncio.sleep(self.sleep_seconds)
        if self.raise_error is not None:
            raise self.raise_error
        return json.dumps(self.response, ensure_ascii=False)

    async def chat_json(
        self, messages: list[dict[str, str]], **kwargs: Any
    ) -> dict[str, Any]:
        self.chat_json_calls += 1
        self.last_messages = messages
        if self.sleep_seconds > 0:
            await asyncio.sleep(self.sleep_seconds)
        if self.raise_error is not None:
            raise self.raise_error
        return self.response


@pytest.fixture(autouse=True)
def _isolated_a1_store(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Autouse: point the A1 disk store at a tmp file and reset in-memory state.

    Guarantees:
    1. Tests never read/write the real ``backend/data/a1_store.json``.
    2. No leakage between tests (dicts cleared, lazy-load flag reset).
    3. The real store file is never polluted by test data.
    """
    from app.api import a1_routes

    store_path = tmp_path / "a1_store.json"
    monkeypatch.setenv("A1_STORE_PATH", str(store_path))
    # Rebind the module-level store to the tmp path (env is only read in
    # A1Store.__init__, and a previous test may already have constructed it).
    monkeypatch.setattr(a1_routes, "_STORE", a1_routes.A1Store(store_path))
    a1_routes._loaded = False
    a1_routes._SESSIONS.clear()
    a1_routes._FILES.clear()
    yield


@pytest.fixture(autouse=True)
def _no_real_llm_provider(monkeypatch: pytest.MonkeyPatch):
    """Autouse: neutralize real LLM HTTP calls from finalize (test-order pollution).

    T8 wired finalize to call ``graphify_llm`` with the real provider built via
    ``create_provider(load_provider_config())``; on machines whose .env has an
    active provider (e.g. deepseek) tests triggering finalize without stubbing
    made real nondeterministic HTTP calls that polluted
    ``app.api.a1_routes._FILES`` and broke other tests' node-count assertions.

    We therefore stub the *provider factory* (not ``graphify_llm`` itself) with
    a raising ``StubLLMProvider``: graphify_llm internally catches any provider
    error and degrades to ``GraphifyResult(success=False)`` (pure-TREE graph),
    deterministically and with zero network.

    Override semantics (both via pytest monkeypatch, last-write-wins — test
    body runs after autouse fixture setup):
    - tests patching ``load_provider_config``/``create_provider`` in the test
      body (e.g. ``_t8_patch_provider``, ``_stub_finalize``) override this and
      keep driving the REAL ``graphify_llm`` against their own stub provider;
    - tests patching ``a1_routes.graphify_llm`` directly are unaffected.
    """
    from app.api import a1_routes

    monkeypatch.setattr(
        a1_routes,
        "load_provider_config",
        lambda: {"provider": "stub-offline"},
    )
    monkeypatch.setattr(
        a1_routes,
        "create_provider",
        lambda cfg: StubLLMProvider(
            raise_error=RuntimeError("no network in tests (autouse stub)")
        ),
    )


@pytest.fixture()
def stub_llm_provider() -> StubLLMProvider:
    """Default stub: empty response, no error, no delay."""
    return StubLLMProvider()


@pytest.fixture()
def make_stub_llm():
    """Factory fixture: make_stub_llm(response=..., raise_error=..., sleep_seconds=...)."""

    def _make(**kwargs: Any) -> StubLLMProvider:
        return StubLLMProvider(**kwargs)

    return _make
