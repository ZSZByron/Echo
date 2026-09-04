"""C1 contract: answers (NL) → graphify prompt 消费冒烟测试。

契约（治理文档 §6 C1）：真实访谈对话可被 graphify prompt 消费（冒烟）。
实现依赖 T1 的 graphify.py —— 未就绪前以 xfail(strict) 占位。

本文件同时承载 StubLLMProvider 三模式的 smoke 测试（直接绿，不 xfail）。
"""
from __future__ import annotations

import pytest


# =============================================================================
# StubLLMProvider three-mode smoke tests (MUST stay green)
# =============================================================================


async def test_stub_normal_mode_returns_preset_response(make_stub_llm) -> None:
    stub = make_stub_llm(response={"nodes": [], "edges": []})

    result = await stub.chat_json([{"role": "user", "content": "hi"}])

    assert result == {"nodes": [], "edges": []}
    assert stub.chat_json_calls == 1


async def test_stub_raise_error_mode_injects_exception(make_stub_llm) -> None:
    stub = make_stub_llm(raise_error=RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        await stub.chat_json([{"role": "user", "content": "hi"}])


async def test_stub_sleep_mode_injects_delay(make_stub_llm) -> None:
    import time

    stub = make_stub_llm(response={"ok": True}, sleep_seconds=0.05)

    start = time.perf_counter()
    result = await stub.chat_json([{"role": "user", "content": "hi"}])
    elapsed = time.perf_counter() - start

    assert result == {"ok": True}
    assert elapsed >= 0.04


async def test_stub_chat_mode_returns_json_string(make_stub_llm) -> None:
    stub = make_stub_llm(response={"a": 1})

    raw = await stub.chat([{"role": "user", "content": "hi"}])

    assert '"a"' in raw


# =============================================================================
# C1 contract smoke (placeholder — turned green after graphify.py lands)
# =============================================================================


@pytest.mark.xfail(strict=True, reason="C1: graphify prompt 消费 answers 尚未实现（T1）")
async def test_c1_real_interview_answers_feed_graphify_prompt() -> None:
    pytest.fail("C1 contract not implemented yet")
