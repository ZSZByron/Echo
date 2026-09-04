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
# C1 contract smoke: real interview answers consumed by the graphify prompt
# =============================================================================


def test_c1_real_interview_answers_feed_graphify_prompt(make_stub_llm) -> None:
    from app.domains.creation.a1.graphify import build_graphify_prompt, graphify_llm

    answers = {
        "IP定位.name": "灰烬大陆",
        "IP定位.concept": "燃烧的天空下寻找最后的绿洲；玩家是拾荒者",
        "世界本体.origin": "创世火种爆炸后世界开始燃烧",
    }
    stub = make_stub_llm(response={
        "module_summaries": {"IP定位": "燃烧大陆"},
        "entries": [{
            "anchor": "IP定位.name",
            "items": [{"title": "灰烬大陆", "content": "天空燃烧", "children": []}],
        }],
        "edges": [],
        "constraint_fields": {},
        "open_questions": [],
    })

    session = type("S", (), {"session_id": "a1_c1test0001", "answers": answers})()
    result = graphify_llm(session, stub)

    # prompt carried the verbatim answers (C1: full text, no truncation)
    system = stub.last_messages[0]["content"]
    assert system == build_graphify_prompt(answers)
    for value in answers.values():
        assert value in system
    # closed vocab + immutable block + reference rules present
    assert "关系封闭词表" in system
    assert "不可动清单" in system
    assert "节点引用规则" in system
    assert "d:{锚点}:{条目标题}" in system

    # answers were actually graphified
    assert result.success is True
    assert result.module_summaries == {"IP定位": "燃烧大陆"}
    assert stub.chat_json_calls == 1
