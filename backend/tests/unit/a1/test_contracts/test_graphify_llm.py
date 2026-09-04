"""T6 contract tests for graphify_llm (governance doc §4-§5, C2).

Coverage:
- stub happy path: five-field full parse + prompt snapshot assertions
- stub partial: missing list fields default to empty (D4)
- stub exception → success=False + warning contains "graphify", never raises
- stub timeout (sleep > timeout) → same degradation
- negative five classes (contract C2): fake anchor / out-of-vocab relation
  (moved to open_questions) / off-whitelist DIM.tag / Phase-1 children
  nesting / hallucinated node reference — each rejected + warning.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.domains.creation.a1.graphify import (
    GRAPHIFY_TIMEOUT,
    GraphifyResult,
    depth_id,
    graphify_llm,
)
from app.domains.creation.a1.concept_edge_vocab import VOCAB_RELATION_NAMES
from app.domains.creation.a1.tier_map import TIER_MAP
from app.domains.creation.graph.constraint_topology import STRUCTURED_FIELDS
from app.domains.creation.seed.a1_question_tree import all_subfield_keys


def _make_session(answers: dict[str, str] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        session_id="test-graphify",
        answers=answers or {},
    )


VALID_ANCHOR = sorted(all_subfield_keys())[0]
MODULE_ID = VALID_ANCHOR.split(".")[0]
TIER_RELATION = "力量源自"  # tier edge, must be in the closed vocab
VALID_DIM = sorted(STRUCTURED_FIELDS)[0]
VALID_TAG = STRUCTURED_FIELDS[VALID_DIM][0]
VALID_CONSTRAINT_KEY = f"{VALID_DIM}.{VALID_TAG}"


def _happy_response() -> dict:
    title = "斗气分裂"
    return {
        "module_summaries": {MODULE_ID: "一句话归纳"},
        "entries": [
            {
                "anchor": VALID_ANCHOR,
                "items": [{"title": title, "content": "条目内容", "children": []}],
            }
        ],
        "edges": [
            {
                "from": MODULE_ID,
                "to": depth_id(VALID_ANCHOR, title),
                "relation": TIER_RELATION,
                "rationale": "层级派生",
                "confidence": "semantic",
            }
        ],
        "constraint_fields": {VALID_CONSTRAINT_KEY: "某约束值"},
        "open_questions": ["这个世界的精神力量上限在哪里？"],
    }


# =============================================================================
# Happy path + prompt snapshot
# =============================================================================


class TestHappyPath:
    def test_five_fields_fully_parsed(self, make_stub_llm) -> None:
        raw = _happy_response()
        provider = make_stub_llm(response=raw)
        result = graphify_llm(_make_session({VALID_ANCHOR: "答案正文"}), provider)

        assert result.success is True
        assert result.warning == ""
        assert result.module_summaries == {MODULE_ID: "一句话归纳"}
        assert len(result.entries) == 1
        assert result.entries[0].anchor == VALID_ANCHOR
        assert result.entries[0].items[0].title == "斗气分裂"
        assert len(result.edges) == 1
        assert result.edges[0].relation == TIER_RELATION
        assert result.edges[0].from_ == MODULE_ID
        assert result.constraint_fields == {VALID_CONSTRAINT_KEY: "某约束值"}
        assert len(result.open_questions) == 1
        assert provider.chat_json_calls == 1

    def test_prompt_snapshot(self, make_stub_llm) -> None:
        provider = make_stub_llm(response=_happy_response())
        answers = {VALID_ANCHOR: "答案正文", "设定边界.immutable_core": "铁律：神不可被杀"}
        graphify_llm(_make_session(answers), provider)

        prompt = provider.last_messages[0]["content"]
        # closed vocabulary declaration + full vocab (26 names)
        assert "封闭词表" in prompt
        for name in VOCAB_RELATION_NAMES:
            assert name in prompt
        assert len(VOCAB_RELATION_NAMES) == 26
        # answers full text
        assert "答案正文" in prompt
        # immutable list
        assert "不可动清单" in prompt
        assert "铁律：神不可被杀" in prompt
        # tier mapping table
        assert "模块层级映射表" in prompt
        for mid in TIER_MAP:
            assert mid in prompt
        # d: node reference rule
        assert "d:{锚点}:{条目标题}" in prompt
        assert "d:" in prompt
        # C7 evidence slot present (empty for now, T17 wires it)
        assert "转正证据" in prompt

    def test_answered_evidence_injected_into_prompt(self, make_stub_llm) -> None:
        provider = make_stub_llm(response=_happy_response())
        evidence = ["精神力量上限由世界本体决定"]
        graphify_llm(_make_session({}), provider, answered_evidence=evidence)

        prompt = provider.last_messages[0]["content"]
        assert "精神力量上限由世界本体决定" in prompt


# =============================================================================
# Partial acceptance (D4)
# =============================================================================


def test_partial_empty_fields_default_empty(make_stub_llm) -> None:
    provider = make_stub_llm(response={"module_summaries": {MODULE_ID: "仅摘要"}})
    result = graphify_llm(_make_session(), provider)

    assert result.success is True
    assert result.module_summaries == {MODULE_ID: "仅摘要"}
    assert result.entries == []
    assert result.edges == []
    assert result.constraint_fields == {}
    assert result.open_questions == []


# =============================================================================
# Degradation: exception / timeout — never raises
# =============================================================================


def test_llm_exception_degrades(make_stub_llm) -> None:
    provider = make_stub_llm(raise_error=RuntimeError("api down"))
    result = graphify_llm(_make_session(), provider)

    assert result.success is False
    assert "graphify" in result.warning
    assert "api down" in result.warning
    assert result.module_summaries == {}
    assert result.entries == []
    assert result.edges == []


def test_timeout_degrades(make_stub_llm, monkeypatch) -> None:
    import app.domains.creation.a1.graphify as graphify_module

    monkeypatch.setattr(graphify_module, "GRAPHIFY_TIMEOUT", 0.05)
    provider = make_stub_llm(response=_happy_response(), sleep_seconds=0.5)
    result = graphify_llm(_make_session(), provider)  # uses monkeypatched timeout

    assert result.success is False
    assert "graphify failed" in result.warning
    assert result.edges == []


def test_timeout_via_param_injection(make_stub_llm) -> None:
    provider = make_stub_llm(response=_happy_response(), sleep_seconds=0.5)
    result = graphify_llm(_make_session(), provider, timeout=0.05)

    assert result.success is False
    assert "graphify failed" in result.warning


def test_module_default_timeout_constant() -> None:
    assert GRAPHIFY_TIMEOUT > 0


def test_non_dict_raw_degrades(make_stub_llm) -> None:
    class WeirdProvider:
        async def chat_json(self, messages, **kwargs):  # type: ignore[no-untyped-def]
            return ["not", "a", "dict"]

    result = graphify_llm(_make_session(), WeirdProvider())
    assert result.success is False
    assert "graphify failed" in result.warning


# =============================================================================
# Negative five classes (contract C2) — each rejected + warning
# =============================================================================


def test_negative_fake_anchor_dropped(make_stub_llm) -> None:
    raw = _happy_response()
    raw["entries"].append(
        {"anchor": "幻觉模块.幻觉子字段", "items": [{"title": "x", "content": ""}]}
    )
    provider = make_stub_llm(response=raw)
    result = graphify_llm(_make_session(), provider)

    assert result.success is True  # partial accept, not total failure
    anchors = [g.anchor for g in result.entries]
    assert "幻觉模块.幻觉子字段" not in anchors
    assert VALID_ANCHOR in anchors
    assert "[entries]" in result.warning
    assert "非法锚点" in result.warning


def test_negative_out_of_vocab_relation_moves_to_open_questions(make_stub_llm) -> None:
    raw = _happy_response()
    raw["edges"].append(
        {
            "from": MODULE_ID,
            "to": VALID_ANCHOR,
            "relation": "心有灵犀",  # invented, not in vocab
            "rationale": "",
            "confidence": "semantic",
        }
    )
    provider = make_stub_llm(response=raw)
    result = graphify_llm(_make_session(), provider)

    relations = [e.relation for e in result.edges]
    assert "心有灵犀" not in relations
    assert TIER_RELATION in relations  # legal edge kept
    questions = [q.question for q in result.open_questions]
    assert any("心有灵犀" in q for q in questions)
    assert "[edges]" in result.warning
    assert "词表外关系" in result.warning


def test_negative_dim_tag_off_whitelist_dropped(make_stub_llm) -> None:
    raw = _happy_response()
    raw["constraint_fields"]["FAKE.bad_tag"] = "幻觉约束"
    provider = make_stub_llm(response=raw)
    result = graphify_llm(_make_session(), provider)

    assert "FAKE.bad_tag" not in result.constraint_fields
    assert VALID_CONSTRAINT_KEY in result.constraint_fields
    assert "[constraint_fields]" in result.warning
    assert "白名单" in result.warning


def test_negative_children_nesting_warns_phase1(make_stub_llm) -> None:
    raw = _happy_response()
    raw["entries"][0]["items"][0]["children"] = [
        {"title": "越权子条目", "content": "Phase 1 不应出现"}
    ]
    provider = make_stub_llm(response=raw)
    result = graphify_llm(_make_session(), provider)

    assert result.success is True
    assert result.entries[0].items[0].children  # parsed, kept (T7/T11 consume)
    assert "children" in result.warning
    assert "Phase 1" in result.warning


def test_negative_hallucinated_node_reference_dropped(make_stub_llm) -> None:
    raw = _happy_response()
    raw["edges"].append(
        {
            "from": depth_id(VALID_ANCHOR, "不存在标题"),
            "to": MODULE_ID,
            "relation": TIER_RELATION,
            "rationale": "",
            "confidence": "semantic",
        }
    )
    provider = make_stub_llm(response=raw)
    result = graphify_llm(_make_session(), provider)

    froms = [e.from_ for e in result.edges]
    assert depth_id(VALID_ANCHOR, "不存在标题") not in froms
    assert "[edges]" in result.warning
    assert "不存在的节点" in result.warning


def test_negative_wrong_type_is_total_failure(make_stub_llm) -> None:
    # D4 boundary: wrong container type = total failure (not partial)
    provider = make_stub_llm(response={"entries": "应为列表却给了字符串"})
    result = graphify_llm(_make_session(), provider)

    assert result.success is False
    assert "graphify failed" in result.warning


def test_result_type_is_graphify_result(make_stub_llm) -> None:
    result = graphify_llm(_make_session(), make_stub_llm(response={}))
    assert isinstance(result, GraphifyResult)


# =============================================================================
# Provider-layer retry (retry once on transient failure)
# =============================================================================


class _FlakyProvider:
    """Programmable provider whose chat_json behaves per-call (retry tests)."""

    def __init__(self, behaviors: list) -> None:
        # behaviors: list of either Exception instances (raise) or dicts
        # (return), consumed one per chat_json call; the last one repeats.
        self._behaviors = list(behaviors)
        self.chat_json_calls = 0
        self.last_messages = None

    async def chat_json(self, messages, **kwargs):  # type: ignore[no-untyped-def]
        idx = min(self.chat_json_calls, len(self._behaviors) - 1)
        self.chat_json_calls += 1
        self.last_messages = messages
        behavior = self._behaviors[idx]
        if isinstance(behavior, Exception):
            raise behavior
        return behavior


def test_retry_once_on_provider_error_succeeds() -> None:
    provider = _FlakyProvider([RuntimeError("transient"), _happy_response()])
    result = graphify_llm(_make_session({VALID_ANCHOR: "答案正文"}), provider)

    assert provider.chat_json_calls == 2
    assert result.success is True
    assert result.warning == ""
    assert result.module_summaries  # five fields parsed
    assert len(result.entries) == 1
    assert len(result.edges) == 1
    assert len(result.open_questions) == 1
    assert result.constraint_fields


def test_retry_exhausted_still_degrades() -> None:
    provider = _FlakyProvider([RuntimeError("api down")])
    result = graphify_llm(_make_session(), provider)

    assert provider.chat_json_calls == 2  # retried once
    assert result.success is False
    assert "graphify failed" in result.warning
    assert "api down" in result.warning
    assert result.edges == []


def test_parse_failure_not_retried() -> None:
    provider = _FlakyProvider([["not", "a", "dict"]])  # wrong container type
    result = graphify_llm(_make_session(), provider)

    assert provider.chat_json_calls == 1  # no retry on parse/shape failure
    assert result.success is False
    assert "graphify failed" in result.warning


def test_timeout_retried_and_second_attempt_succeeds() -> None:
    import asyncio as _asyncio

    class _SlowThenFastProvider(_FlakyProvider):
        async def chat_json(self, messages, **kwargs):  # type: ignore[no-untyped-def]
            idx = min(self.chat_json_calls, len(self._behaviors) - 1)
            self.chat_json_calls += 1
            self.last_messages = messages
            behavior = self._behaviors[idx]
            if isinstance(behavior, Exception):
                raise behavior
            delay, payload = behavior
            if delay:
                await _asyncio.sleep(delay)
            return payload

    provider = _SlowThenFastProvider([(0.5, None), (0.0, _happy_response())])
    result = graphify_llm(_make_session(), provider, timeout=0.2)

    assert provider.chat_json_calls == 2
    assert result.success is True
    assert len(result.entries) == 1
