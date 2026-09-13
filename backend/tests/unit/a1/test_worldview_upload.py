"""Unit tests for the A1 worldview upload pipeline (fake provider)."""
from __future__ import annotations

import pytest

from app.domains.creation.a1.worldview_upload import (
    check_copyright,
    convert_text,
    extract_entities,
    parse_modules,
    validate_text,
)
from app.domains.creation.seed.a1_question_tree import all_subfield_keys


class FakeProvider:
    """Mimics LLMProvider.chat_json (async) with scripted responses."""

    def __init__(self, responses: list[dict]):
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    async def chat_json(self, messages, **kwargs):  # noqa: ARG002
        self.calls.append((messages[0]["content"], messages[1]["content"]))
        return self._responses.pop(0)


LONG_TEXT = "星陨大陆设定。" + "这是一个基于星辰陨落力量的世界，" * 40


class TestValidateText:
    def test_ok(self):
        assert validate_text("world.md", LONG_TEXT)["ok"] is True

    def test_reject_short(self):
        out = validate_text("a.md", "太短")
        assert out["ok"] is False
        assert "太短" in out["reason"]

    def test_reject_empty_filename(self):
        assert validate_text("", LONG_TEXT)["ok"] is False

    def test_reject_binary(self):
        binary = "x" * 100 + "\x00\x01\x02" * 60
        assert validate_text("a.txt", binary)["ok"] is False


class TestExtractEntities:
    def test_normalizes_and_caps(self):
        provider = FakeProvider([{
            "characters": ["萧炎"] * 15,
            "power_systems": ["斗气"],
            "world_keywords": None,
            "suspected_works": "斗破苍穹",  # non-list must be tolerated
        }])
        out = __import__("asyncio").run(extract_entities(provider, LONG_TEXT))
        assert len(out["characters"]) == 1  # dedup by str equality
        assert out["power_systems"] == ["斗气"]
        assert out["world_keywords"] == []
        assert out["suspected_works"] == []
        assert out["truncated"] is False

    def test_j4_cap_disclosed(self):
        """J4：专名每类超 10 项截断 → capped 报告每类丢弃数（配 J3 披露）."""
        provider = FakeProvider([{
            "characters": [f"角色{i}" for i in range(13)],
            "power_systems": [f"体系{i}" for i in range(12)],
            "world_keywords": ["关键词"],
            "suspected_works": [],
        }])
        out = __import__("asyncio").run(extract_entities(provider, LONG_TEXT))
        assert len(out["characters"]) == 10
        assert len(out["power_systems"]) == 10
        assert out["capped"] == {"characters": 3, "power_systems": 2}

    def test_j4_no_cap_report_when_within_limits(self):
        provider = FakeProvider([{
            "characters": ["萧炎"],
            "power_systems": ["斗气"],
            "world_keywords": [],
            "suspected_works": [],
        }])
        out = __import__("asyncio").run(extract_entities(provider, LONG_TEXT))
        assert out["capped"] == {}


class TestCheckCopyright:
    def test_high_when_core_term_hit(self):
        provider = FakeProvider([{
            "risk_level": "low",
            "matches": [{"term": "萧炎", "work": "斗破苍穹", "evidence": "主角名"}],
        }])
        out = __import__("asyncio").run(check_copyright(provider, {
            "characters": ["萧炎"], "power_systems": [], "world_keywords": [],
            "suspected_works": [],
        }))
        assert out["risk_level"] == "high"
        assert out["matches"][0]["term"] == "萧炎"

    def test_low_when_no_hits(self):
        provider = FakeProvider([{"risk_level": "low", "matches": []}])
        out = __import__("asyncio").run(check_copyright(provider, {
            "characters": ["林渊"], "power_systems": ["星陨力"], "world_keywords": [],
            "suspected_works": [],
        }))
        assert out["risk_level"] == "low"
        assert out["matches"] == []

    def test_drops_malformed_matches(self):
        provider = FakeProvider([{
            "risk_level": "low",
            "matches": ["garbage", {"term": "", "work": "x"}, {"term": "ok", "work": "y"}],
        }])
        out = __import__("asyncio").run(check_copyright(provider, {
            "characters": [], "power_systems": [], "world_keywords": [], "suspected_works": [],
        }))
        assert [m["term"] for m in out["matches"]] == ["ok"]


class TestParseModules:
    def test_drops_invalid_keys_and_keeps_valid(self):
        valid_key = all_subfield_keys()[0]
        provider = FakeProvider([{
            "answers": {valid_key: "星陨大陆", "不存在的模块.字段": "x"},
            "innovations": [{"field": "星辰共鸣", "suggestion": "独创力量来源"}],
        }])
        out = __import__("asyncio").run(parse_modules(provider, LONG_TEXT))
        assert set(out["answers"]) == {valid_key}
        assert out["innovations"][0]["field"] == "星辰共鸣"

    def test_full_alignment_with_question_tree(self):
        every = dict.fromkeys(all_subfield_keys(), "答案")
        provider = FakeProvider([{"answers": every, "innovations": []}])
        out = __import__("asyncio").run(parse_modules(provider, LONG_TEXT))
        assert set(out["answers"]) == set(all_subfield_keys())

    def test_prompt_injects_schema(self):
        provider = FakeProvider([{"answers": {}, "innovations": []}])
        __import__("asyncio").run(parse_modules(provider, LONG_TEXT))
        system = provider.calls[0][0]
        assert "IP定位.name" in system
        assert "设定边界" in system

    def test_innovations_capped_at_5(self):
        provider = FakeProvider([{
            "answers": {},
            "innovations": [{"field": f"创新{i}", "suggestion": "内容"} for i in range(9)],
        }])
        out = __import__("asyncio").run(parse_modules(provider, LONG_TEXT))
        assert len(out["innovations"]) == 5

    def test_j1_placeholder_values_not_written(self):
        """J1 答案真值闸：LLM 违反铁律回填占位值时，出口统一丢弃.

        级联 A 入口：占位值曾以 truthy 身份进入 answers → 过门禁 →
        被 graphify 全文嵌入 → 空壳图谱定稿。
        """
        k_first, k_second = all_subfield_keys()[0], all_subfield_keys()[1]
        provider = FakeProvider([{
            "answers": {
                k_first: "未提及",
                k_second: "（暂无）",  # 包裹+全角变体也要拦
                all_subfield_keys()[2]: "N/A",
                all_subfield_keys()[3]: "  ",  # 纯空白（旧逻辑已拦，回归保护）
                all_subfield_keys()[4]: "未知种族的迁徙史",  # 占位词子串=真答案，必须保留
            },
            "innovations": [],
        }])
        out = __import__("asyncio").run(parse_modules(provider, LONG_TEXT))
        assert set(out["answers"]) == {all_subfield_keys()[4]}
        assert out["answers"][all_subfield_keys()[4]] == "未知种族的迁徙史"

    def test_j4_long_answers_clipped_and_reported(self):
        """J4 预算护栏：>2000 字答案截断写入 + clipped_answers 报告（配 J3 披露）."""
        key = all_subfield_keys()[0]
        provider = FakeProvider([{
            "answers": {
                key: "灵" * 2500,
                all_subfield_keys()[1]: "短答案",
            },
            "innovations": [],
        }])
        out = __import__("asyncio").run(parse_modules(provider, LONG_TEXT))
        assert len(out["answers"][key]) == 2000
        assert out["answers"][all_subfield_keys()[1]] == "短答案"
        assert out["clipped_answers"] == [key]


class TestConvertText:
    def test_passes_matches_and_returns_text(self):
        matches = [{"term": "萧炎", "work": "斗破苍穹", "evidence": ""}]
        provider = FakeProvider([{"converted": "净化后的全文……"}])
        out = __import__("asyncio").run(convert_text(provider, LONG_TEXT, matches))
        assert out == "净化后的全文……"
        user = provider.calls[0][1]
        assert "萧炎" in user and "斗破苍穹" in user

    def test_empty_result_raises(self):
        provider = FakeProvider([{"converted": ""}])
        with pytest.raises(ValueError):
            __import__("asyncio").run(convert_text(provider, LONG_TEXT, []))

    def test_j4_long_input_truncated_in_prompt(self):
        """J4 预算护栏：convert 输入 ≤20000——超长原文截断后进 prompt + 留痕标记."""
        from app.domains.creation.a1.worldview_upload import MAX_CONTENT_CHARS

        huge = "星陨大陆设定。" + "灵石矿脉塑造九州秩序。" * 2500  # >20000
        assert len(huge) > MAX_CONTENT_CHARS
        provider = FakeProvider([{"converted": "净化后的全文……"}])
        __import__("asyncio").run(convert_text(provider, huge, []))

        user = provider.calls[0][1]
        assert "已截断" in user
        # 原文段被截到预算内（命中列表头部 + 标记行 + 截断的原文 ≤ 合理上界）
        assert len(user) < MAX_CONTENT_CHARS + 200

    def test_j4_short_input_no_marker(self):
        provider = FakeProvider([{"converted": "净化后的全文……"}])
        __import__("asyncio").run(convert_text(provider, LONG_TEXT, []))
        assert "已截断" not in provider.calls[0][1]
