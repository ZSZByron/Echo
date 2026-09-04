"""降级链测试：graphify_llm 三种失败场景（异常 / 超时 / 部分空）。

治理文档 §5：finalize 永不被 LLM 失败阻塞 —— 任何失败降级为
``GraphifyResult(success=False, warning="graphify failed: …")``，绝不 raise。
部分可接受（partial acceptance）输出则 success=True + 分域 warning 标记
（``[entries]`` / ``[edges]`` / ``[constraint_fields]``）。
"""
from __future__ import annotations

from app.domains.creation.a1.graphify import graphify_llm


class _Session:
    """Minimal session double: graphify_llm only touches session_id/answers."""

    session_id = "a1_degtest001"
    answers = {"IP定位.name": "灰烬大陆"}


# =============================================================================
# Scenario 1: provider raises → success=False, "graphify failed" domain marker
# =============================================================================


def test_degradation_provider_exception_degrades(make_stub_llm) -> None:
    stub = make_stub_llm(raise_error=RuntimeError("provider 爆炸"))

    result = graphify_llm(_Session(), stub)

    assert result.success is False
    assert result.warning.startswith("graphify failed")
    assert "provider 爆炸" in result.warning
    # degraded result is safe to feed downstream: all containers empty
    assert result.entries == []
    assert result.edges == []
    assert result.constraint_fields == {}
    assert result.module_summaries == {}
    assert result.open_questions == []


# =============================================================================
# Scenario 2: provider exceeds timeout → success=False (never hangs)
# =============================================================================


def test_degradation_timeout_degrades(make_stub_llm) -> None:
    stub = make_stub_llm(response={"module_summaries": {}}, sleep_seconds=2.0)

    result = graphify_llm(_Session(), stub, timeout=0.05)

    assert result.success is False
    assert result.warning.startswith("graphify failed")
    # timed out before any valid payload was parsed
    assert result.entries == []
    assert result.edges == []


# =============================================================================
# Scenario 3a: partially empty payload (missing fields) → D4 missing = empty,
# success stays True
# =============================================================================


def test_degradation_partial_empty_missing_fields_default_empty(
    make_stub_llm,
) -> None:
    stub = make_stub_llm(response={"module_summaries": {"IP定位": "燃烧大陆"}})

    result = graphify_llm(_Session(), stub)

    assert result.success is True
    assert result.module_summaries == {"IP定位": "燃烧大陆"}
    assert result.entries == []
    assert result.edges == []
    assert result.constraint_fields == {}
    assert result.open_questions == []
    assert result.warning == ""


# =============================================================================
# Scenario 3b: partially broken payload → partial acceptance with per-domain
# warnings ([entries] / [edges] / [constraint_fields]), never a crash
# =============================================================================


def test_degradation_partial_broken_marked_per_domain(make_stub_llm) -> None:
    stub = make_stub_llm(response={
        "module_summaries": {"IP定位": "燃烧大陆"},
        "entries": [
            {"anchor": "伪造模块.fake", "items": []},  # → [entries] domain
            {
                "anchor": "IP定位.name",
                "items": [{"title": "灰烬大陆", "content": "", "children": [
                    {"title": "越权子条目", "content": "", "children": []},
                ]}],  # → children domain warning
            },
        ],
        "edges": [
            {
                "from": "IP定位.name",
                "to": "d:IP定位.name:灰烬大陆",
                "relation": "词表外关系",
                "rationale": "",
                "confidence": "semantic",
            },  # → [edges] domain
        ],
        "constraint_fields": {"LAW.not_a_field": "越权"},  # → [constraint_fields]
        "open_questions": [],
    })

    result = graphify_llm(_Session(), stub)

    assert result.success is True  # partial acceptance, not total failure
    warning = result.warning
    assert "[entries]" in warning          # entries domain marked
    assert "[edges]" in warning            # edges domain marked
    assert "[constraint_fields]" in warning  # constraint_fields domain marked
    assert "children 深度 Phase 1 不开放" in warning  # children domain marked
    # valid fragments survived
    assert [g.anchor for g in result.entries] == ["IP定位.name"]
    assert result.entries[0].items[0].title == "灰烬大陆"
    assert any("词表外关系" in q.question for q in result.open_questions)


# =============================================================================
# Scenario 4: unparseable payload (wrong container type) → success=False
# =============================================================================


def test_degradation_unparseable_payload_degrades(make_stub_llm) -> None:
    stub = make_stub_llm(response={"entries": "应为列表，实为字符串"})

    result = graphify_llm(_Session(), stub)

    assert result.success is False
    assert result.warning.startswith("graphify failed")
    assert "entries" in result.warning
