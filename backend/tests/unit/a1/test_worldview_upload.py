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
