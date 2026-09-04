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
