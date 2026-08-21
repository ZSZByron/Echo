"""TDD测试 - RealSemanticCompiler 三级匹配（FakeProvider，零真实LLM调用）

覆盖：L1种子命中 / L2词典规则 / L3 LLM命中 / 非法JSON降级 /
词典外值丢弃 / 全失败提案 / 幂等性 / Protocol兼容
"""

from __future__ import annotations

from typing import Any

from app.ai.provider import LLMProvider
from app.domains.creation.a1.semantic_compiler import RealSemanticCompiler
from app.domains.creation.shared.semantic_compiler import (
    FieldWrite,
    SemanticCompiler,
)


class FakeProvider(LLMProvider):
    """假Provider：返回预设dict，统计调用次数；可注入异常"""

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

    async def chat_json(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        self.chat_json_calls += 1
        if self.raise_error:
            raise self.raise_error
        return self.response


SEED_LIBRARY = {
    "赛博朋克废土": [
        FieldWrite(field="LAW.world_structure", value="TOWER"),
    ],
}


class TestLevel1Seed:
    def test_l1_seed_hit_zero_llm_calls(self):
        """L1种子命中：零LLM调用"""
        provider = FakeProvider()
        compiler = RealSemanticCompiler(provider=provider, seed_library=SEED_LIBRARY)
        result = compiler.compile("s1", "这是一个赛博朋克废土世界")
        assert result.writes == [FieldWrite(field="LAW.world_structure", value="TOWER")]
        assert result.classification_proposal is None
        assert provider.chat_json_calls == 0

    def test_l1_seed_invalid_value_dropped(self):
        """L1种子含词典外值 → 该write被铁律丢弃 → 走L2/L3/降级"""
        provider = FakeProvider()
        compiler = RealSemanticCompiler(
            provider=provider,
            seed_library={"xxx": [FieldWrite(field="LAW.world_structure", value="NOT_IN_DICT")]},
        )
        result = compiler.compile("s1", "xxx 完全无法解析的内容")
        # 种子被丢弃，L2/L3(provider返回空)未命中 → 降级proposal
        assert result.writes == []
        assert result.classification_proposal is not None


class TestLevel2Rules:
    def test_l2_rule_hit_floating_islands(self):
        """L2词典规则：浮空岛 → LAW.world_structure=FLOATING_ISLANDS"""
        provider = FakeProvider()
        compiler = RealSemanticCompiler(provider=provider)
        result = compiler.compile("s1", "世界由无数浮空岛组成")
        assert FieldWrite(field="LAW.world_structure", value="FLOATING_ISLANDS") in result.writes
        assert provider.chat_json_calls == 0

    def test_l2_rule_english_keyword_case_insensitive(self):
        """L2英文关键词大小写不敏感"""
        compiler = RealSemanticCompiler()
        result = compiler.compile("s1", "A world of Floating Islands and high magic")
        assert FieldWrite(field="LAW.world_structure", value="FLOATING_ISLANDS") in result.writes


class TestLevel3LLM:
    def test_l3_llm_hit_when_rules_miss(self):
        """L3：规则未命中时LLM返回合法值"""
        provider = FakeProvider(
            response={"writes": [{"field": "LAW.afterlife", "value": "REINCARNATION"}], "confidence": 0.9}
        )
        compiler = RealSemanticCompiler(provider=provider)
        result = compiler.compile("s1", "死者会转世重生")
        assert result.writes == [FieldWrite(field="LAW.afterlife", value="REINCARNATION")]
        assert provider.chat_json_calls == 1

    def test_l3_llm_invalid_json_degrades_to_proposal(self):
        """LLM返回非法结构 → 降级进proposal"""
        provider = FakeProvider(response={"unexpected": "shape"})
        compiler = RealSemanticCompiler(provider=provider)
        result = compiler.compile("s1", "某种奇怪设定")
        assert result.writes == []
        assert result.classification_proposal is not None
        assert result.classification_proposal.suggestions[0].category == "其他"

    def test_l3_llm_raises_exception_degrades(self):
        """provider抛异常 → 降级，不向上传播"""
        provider = FakeProvider(raise_error=RuntimeError("api down"))
        compiler = RealSemanticCompiler(provider=provider)
        result = compiler.compile("s1", "某种奇怪设定")
        assert result.writes == []
        assert result.classification_proposal is not None

    def test_l3_out_of_dict_value_dropped(self):
        """LLM返回词典外值 → 该write被丢弃"""
        provider = FakeProvider(
            response={
                "writes": [
                    {"field": "LAW.world_structure", "value=": None},
                    {"field": "LAW.world_structure", "value": "MADE_UP_VALUE"},
                    {"field": "LAW.gravity", "value": "LOW"},
                ]
            }
        )
        compiler = RealSemanticCompiler(provider=provider)
        result = compiler.compile("s1", "奇怪的混合设定")
        assert result.writes == [FieldWrite(field="LAW.gravity", value="LOW")]


class TestFallbackAndIdempotency:
    def test_all_fail_returns_proposal_with_qita(self):
        """全失败 → proposal含'其他'"""
        compiler = RealSemanticCompiler()  # provider=None
        result = compiler.compile("s1", "完全无法理解的外星概念")
        assert result.writes == []
        assert result.classification_proposal is not None
        assert any(s.category == "其他" for s in result.classification_proposal.suggestions)

    def test_idempotent_same_input_same_result(self):
        """幂等：同输入重复compile结果不变"""
        compiler = RealSemanticCompiler(provider=None, seed_library=SEED_LIBRARY)
        r1 = compiler.compile("s1", "赛博朋克废土和浮空岛")
        r2 = compiler.compile("s1", "赛博朋克废土和浮空岛")
        assert r1 == r2

    def test_protocol_compatibility(self):
        """isinstance(RealSemanticCompiler(), SemanticCompiler) 通过"""
        assert isinstance(RealSemanticCompiler(), SemanticCompiler)
