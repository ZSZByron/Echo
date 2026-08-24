"""TDD\u6d4b\u8bd5 - RealSemanticCompiler \u4e09\u7ea7\u5339\u914d"""
from __future__ import annotations
from typing import Any
from app.ai.provider import LLMProvider
from app.domains.creation.a1.semantic_compiler import (
    RealSemanticCompiler, deduce_dice_recommendation,
)
from app.domains.creation.shared.semantic_compiler import (
    FieldWrite, SemanticCompiler,
)


class FakeProvider(LLMProvider):
    def __init__(self, response: dict[str, Any] | None = None, raise_error: Exception | None = None) -> None:
        self.response = response or {}
        self.raise_error = raise_error
        self.chat_json_calls = 0

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        raise NotImplementedError

    async def chat_json(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        self.chat_json_calls += 1
        if self.raise_error:
            raise self.raise_error
        return self.response


SEED_LIBRARY = {
    "\u8d5b\u535a\u670b\u514b\u5e9f\u571f": [
        FieldWrite(field="LAW.world_structure", value="TOWER"),
    ],
}


class TestLevel1Seed:
    def test_l1_seed_hit_zero_llm_calls(self):
        provider = FakeProvider()
        compiler = RealSemanticCompiler(provider=provider, seed_library=SEED_LIBRARY)
        result = compiler.compile("s1", "\u8fd9\u662f\u4e00\u4e2a\u8d5b\u535a\u670b\u514b\u5e9f\u571f\u4e16\u754c")
        assert result.writes == [FieldWrite(field="LAW.world_structure", value="TOWER")]
        assert provider.chat_json_calls == 0

    def test_l1_seed_invalid_value_dropped(self):
        provider = FakeProvider()
        compiler = RealSemanticCompiler(
            provider=provider,
            seed_library={"xxx": [FieldWrite(field="LAW.world_structure", value="NOT_IN_DICT")]},
        )
        result = compiler.compile("s1", "xxx \u5b8c\u5168\u65e0\u6cd5\u89e3\u6790\u7684\u5185\u5bb9")
        assert result.writes == []
        assert result.classification_proposal is not None


class TestLevel2Rules:
    def test_l2_rule_hit_floating_islands(self):
        provider = FakeProvider()
        compiler = RealSemanticCompiler(provider=provider)
        result = compiler.compile("s1", "\u4e16\u754c\u7531\u65e0\u6570\u6d6e\u7a7a\u5c9b\u7ec4\u6210")
        assert FieldWrite(field="LAW.world_structure", value="FLOATING_ISLANDS") in result.writes
        assert provider.chat_json_calls == 0


class TestLevel3LLM:
    def test_l3_llm_hit(self):
        provider = FakeProvider(response={"writes": [{"field": "LAW.afterlife", "value": "REINCARNATION"}], "confidence": 0.9})
        compiler = RealSemanticCompiler(provider=provider)
        result = compiler.compile("s1", "\u6b7b\u8005\u4f1a\u8f6c\u4e16\u91cd\u751f")
        assert result.writes == [FieldWrite(field="LAW.afterlife", value="REINCARNATION")]

    def test_l3_invalid_json_degrades(self):
        provider = FakeProvider(response={"unexpected": "shape"})
        compiler = RealSemanticCompiler(provider=provider)
        result = compiler.compile("s1", "\u67d0\u79cd\u5947\u602a\u8bbe\u5b9a")
        assert result.writes == []
        assert result.classification_proposal is not None

    def test_l3_out_of_dict_value_dropped(self):
        provider = FakeProvider(response={"writes": [
            {"field": "LAW.world_structure", "value": "MADE_UP_VALUE"},
            {"field": "LAW.gravity", "value": "LOW"},
        ]})
        compiler = RealSemanticCompiler(provider=provider)
        result = compiler.compile("s1", "\u5947\u602a\u7684\u6df7\u5408\u8bbe\u5b9a")
        assert result.writes == [FieldWrite(field="LAW.gravity", value="LOW")]


class TestFallbackAndIdempotency:
    def test_all_fail_returns_proposal(self):
        compiler = RealSemanticCompiler()
        result = compiler.compile("s1", "\u5b8c\u5168\u65e0\u6cd5\u7406\u89e3\u7684\u5916\u661f\u6982\u5ff5")
        assert result.writes == []
        assert result.classification_proposal is not None

    def test_idempotent(self):
        compiler = RealSemanticCompiler(provider=None, seed_library=SEED_LIBRARY)
        r1 = compiler.compile("s1", "\u8d5b\u535a\u670b\u514b\u5e9f\u571f\u548c\u6d6e\u7a7a\u5c9b")
        r2 = compiler.compile("s1", "\u8d5b\u535a\u670b\u514b\u5e9f\u571f\u548c\u6d6e\u7a7a\u5c9b")
        assert r1 == r2

    def test_protocol_compatibility(self):
        assert isinstance(RealSemanticCompiler(), SemanticCompiler)


class TestDiceDeduction:
    def test_will_dominant_linear_d20(self):
        answers = {"\u4e16\u754c\u672c\u4f53::\u73b0\u5b9e\u89c4\u5219": "\u610f\u5fd7\u5360\u4e3b\u5bfc"}
        writes = deduce_dice_recommendation(answers)
        assert any(w.field == "ACT.dice_mode" and w.value == "LINEAR_D20" for w in writes)

    def test_matter_dominant_bell_curve(self):
        answers = {"\u4e16\u754c\u672c\u4f53::\u73b0\u5b9e\u89c4\u5219": "\u7269\u8d28\u5360\u4e3b\u5bfc"}
        writes = deduce_dice_recommendation(answers)
        assert any(w.field == "ACT.dice_mode" and w.value == "BELL_CURVE_3D6" for w in writes)

    def test_study_acquire_gm_calls(self):
        answers = {"\u529b\u91cf\u4f53\u7cfb::\u83b7\u53d6\u65b9\u5f0f": "\u901a\u8fc7\u5b66\u4e60\u548c\u89c9\u9192"}
        writes = deduce_dice_recommendation(answers)
        assert any(w.field == "ACT.check_direction" and w.value == "GM_CALLS" for w in writes)

    def test_research_acquire_player_calls(self):
        answers = {"\u529b\u91cf\u4f53\u7cfb::\u83b7\u53d6\u65b9\u5f0f": "\u901a\u8fc7\u79d1\u7814\u548c\u5de5\u5177"}
        writes = deduce_dice_recommendation(answers)
        assert any(w.field == "ACT.check_direction" and w.value == "PLAYER_CALLS" for w in writes)

    def test_empty_answers_no_writes(self):
        assert deduce_dice_recommendation({}) == []
