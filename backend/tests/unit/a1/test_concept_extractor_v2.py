"""TDD测试 - 两阶段抽取器 V2 (Task T-A)

阶段1: extract_concept_terms 概念词抽取
阶段2: extract_concept_relations 概念边抽取（节点确认后，关系词典制）

测试策略：全 mock LLM（零真实调用）。
覆盖：阶段1解析/去重/降级；阶段2词典校验/新词标记/上限/降级/confirmed默认False。
"""
from __future__ import annotations

from typing import Any

from app.ai.provider import LLMProvider
from app.domains.creation.a1.concept_relation_vocab import RelationRegistry
from app.domains.creation.a1.concept_edge_extractor import (
    ConceptEdgeV2,
    ConceptTerm,
    TermsResult,
    extract_concept_terms,
    extract_concept_relations,
)


class FakeProvider(LLMProvider):
    """Mock LLM provider - zero real API calls."""

    def __init__(
        self,
        response: dict[str, Any] | None = None,
        raise_error: Exception | None = None,
    ) -> None:
        self.response = response or {}
        self.raise_error = raise_error
        self.chat_json_calls = 0

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        raise NotImplementedError

    async def chat_json(
        self, messages: list[dict[str, str]], **kwargs: Any
    ) -> dict[str, Any]:
        self.chat_json_calls += 1
        if self.raise_error:
            raise self.raise_error
        return self.response


class FakeSession:
    def __init__(self, answers: dict[str, str] | None = None) -> None:
        self.session_id = "test-session"
        self.user_id = "test-user"
        self.answers = answers or {}


# =============================================================================
# 阶段1: extract_concept_terms
# =============================================================================


class TestExtractConceptTerms:
    def test_parse_terms_from_filled_fields(self):
        provider = FakeProvider(
            response={
                "terms": [
                    {"term": "死亡转生", "field_key": "世界本体.现实规则", "gloss": "死亡后转入新生"},
                    {"term": "业报", "field_key": "力量体系.cost", "gloss": "行为带来反噬"},
                ]
            }
        )
        session = FakeSession(
            answers={
                "世界本体.现实规则": "死亡即转生，灵魂进入轮回之门",
                "力量体系.cost": "过度使用力量会招致业报反弹",
            }
        )
        result = extract_concept_terms(session, provider=provider)
        assert isinstance(result, TermsResult)
        assert result.success is True
        assert len(result.terms) == 2
        assert result.terms[0].term == "死亡转生"
        assert result.terms[0].field_key == "世界本体.现实规则"
        assert result.terms[0].confirmed is False  # 默认未确认

    def test_dedupe_across_fields_keeps_first_field_key(self):
        provider = FakeProvider(
            response={
                "terms": [
                    {"term": "业报", "field_key": "力量体系.cost"},
                    {"term": "业报", "field_key": "文明与社会.core_value"},
                ]
            }
        )
        session = FakeSession(
            answers={
                "力量体系.cost": "业报守恒",
                "文明与社会.core_value": "业报至上",
            }
        )
        result = extract_concept_terms(session, provider=provider)
        terms = [t for t in result.terms if t.term == "业报"]
        assert len(terms) == 1
        assert terms[0].field_key == "力量体系.cost"  # 首次出现

    def test_empty_answers_skips_llm(self):
        provider = FakeProvider(response={"terms": []})
        session = FakeSession(answers={})
        result = extract_concept_terms(session, provider=provider)
        assert result.success is True
        assert result.terms == []
        assert provider.chat_json_calls == 0  # 空模块不调 LLM

    def test_llm_error_degrades(self):
        provider = FakeProvider(raise_error=RuntimeError("api down"))
        session = FakeSession(answers={"世界本体.现实规则": "意志主导"})
        result = extract_concept_terms(session, provider=provider)
        assert result.success is False
        assert "concept_term" in result.warning

    def test_malformed_items_skipped(self):
        provider = FakeProvider(
            response={"terms": ["not-a-dict", {"no_term": 1}, {"term": "轮回之门"}]}
        )
        session = FakeSession(answers={"世界本体.现实规则": "轮回之门开启"})
        result = extract_concept_terms(session, provider=provider)
        assert result.success is True
        assert len(result.terms) == 1
        assert result.terms[0].term == "轮回之门"


# =============================================================================
# 阶段2: extract_concept_relations
# =============================================================================


def _confirmed_terms() -> list[ConceptTerm]:
    a = ConceptTerm(term="业报", field_key="力量体系.cost", confirmed=True)
    b = ConceptTerm(term="转生", field_key="世界本体.现实规则", confirmed=True)
    c = ConceptTerm(term="轮回之门", field_key="世界本体.现实规则", confirmed=True)
    return [a, b, c]


class TestExtractConceptRelations:
    def test_known_relation_confidence_from_vocab(self):
        provider = FakeProvider(
            response={
                "edges": [
                    {
                        "from_term": "业报",
                        "to_term": "转生",
                        "relation": "引发",
                        "rationale": "业报触发转生机制",
                    },
                    {
                        "from_term": "轮回之门",
                        "to_term": "转生",
                        "relation": "共现",
                        "rationale": "同一设定中共现",
                    },
                ]
            }
        )
        result = extract_concept_relations(
            _confirmed_terms(), FakeSession({}), RelationRegistry(), provider=provider
        )
        assert result.success is True
        assert len(result.edges) == 2
        e0 = result.edges[0]
        assert e0.relation == "引发"
        assert e0.confidence == "semantic"  # ◆
        assert e0.is_new_relation is False
        assert e0.confirmed is False  # 默认 False
        e1 = result.edges[1]
        assert e1.confidence == "structure"  # ◇ 共现

    def test_new_relation_flagged_semantic(self):
        provider = FakeProvider(
            response={
                "edges": [
                    {
                        "from_term": "业报",
                        "to_term": "转生",
                        "relation": "反噬",
                        "rationale": "业报反噬转生质量",
                    }
                ]
            }
        )
        result = extract_concept_relations(
            _confirmed_terms(), FakeSession({}), RelationRegistry(), provider=provider
        )
        assert result.success is True
        assert len(result.edges) == 1
        e = result.edges[0]
        assert e.is_new_relation is True  # 提议新词待确认
        assert e.confidence == "semantic"
        assert e.confirmed is False

    def test_edges_to_unconfirmed_terms_skipped(self):
        provider = FakeProvider(
            response={
                "edges": [
                    {"from_term": "业报", "to_term": "幽灵概念", "relation": "引发"},
                    {"from_term": "幽灵概念", "to_term": "转生", "relation": "引发"},
                    {"from_term": "业报", "to_term": "转生", "relation": "引发"},
                ]
            }
        )
        result = extract_concept_relations(
            _confirmed_terms(), FakeSession({}), RelationRegistry(), provider=provider
        )
        assert len(result.edges) == 1
        assert result.edges[0].from_term == "业报"
        assert result.edges[0].to_term == "转生"

    def test_edge_cap_terms_times_1_5(self):
        """边数 ≤ 概念词数×1.5（3词 → 4条上限）."""
        edges = [
            {
                "from_term": "业报",
                "to_term": "转生",
                "relation": "引发",
                "rationale": f"edge{i}",
            }
            for i in range(6)
        ]
        provider = FakeProvider(response={"edges": edges})
        result = extract_concept_relations(
            _confirmed_terms(), FakeSession({}), RelationRegistry(), provider=provider
        )
        assert result.success is True
        assert len(result.edges) == 4  # int(3 * 1.5)

    def test_no_terms_skips_llm(self):
        provider = FakeProvider(response={"edges": []})
        result = extract_concept_relations(
            [], FakeSession({}), RelationRegistry(), provider=provider
        )
        assert result.success is True
        assert result.edges == []
        assert provider.chat_json_calls == 0

    def test_llm_error_degrades(self):
        provider = FakeProvider(raise_error=RuntimeError("boom"))
        result = extract_concept_relations(
            _confirmed_terms(), FakeSession({}), RelationRegistry(), provider=provider
        )
        assert result.success is False
        assert "concept_edge" in result.warning

    def test_new_relation_visible_after_registry_add(self):
        """用户确认新词入典后，同关系再抽取时 is_new_relation=False."""
        provider = FakeProvider(
            response={
                "edges": [
                    {"from_term": "业报", "to_term": "转生", "relation": "反噬"}
                ]
            }
        )
        registry = RelationRegistry()
        registry.add("反噬")
        result = extract_concept_relations(
            _confirmed_terms(), FakeSession({}), registry, provider=provider
        )
        assert result.edges[0].is_new_relation is False

    def test_unconfirmed_term_object_excluded(self):
        """ConceptTerm.confirmed=False 的词不参与连边."""
        terms = _confirmed_terms()
        terms.append(ConceptTerm(term="黑曜石", field_key="视觉设计.material", confirmed=False))
        provider = FakeProvider(
            response={
                "edges": [
                    {"from_term": "黑曜石", "to_term": "转生", "relation": "引发"},
                ]
            }
        )
        result = extract_concept_relations(
            terms, FakeSession({}), RelationRegistry(), provider=provider
        )
        assert result.edges == []
