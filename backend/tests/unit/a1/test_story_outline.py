"""D22 Task13：故事大纲渲染器（O）契约测试——剧情信号叙事化渲染。

五组矩阵（同 T11/T12 契约面）+ 叙事化导语 prompt 快照。
"""
from __future__ import annotations

import re

import pytest

from app.domains.creation.modules.output_modules import get_output_module
from app.domains.creation.modules.story_outline import (
    SECTION_SIGNALS,
    STORY_SECTIONS,
    compile_copy,
    compile_outline,
    issue_outline_code,
    render_markdown,
)
from app.domains.creation.shared.graph_code_issuer import GraphCodeIssuer

ANSWERS = {
    "剧情.opening_event": "雨夜，钟塔第13次敲响",
    "剧情.core_dilemma": "拯救挚友还是守住封印",
    "剧情.branch_trees": "东线商会线；西线教会线",
    "剧情.lead_chain": "钟匠→守夜人→主教",
    "剧情.secret_layer": "钟塔地下埋着初代钟匠的遗体",
    "剧情.tension_hole": "每敲一次钟，有人遗忘一个名字",
}


class FakeProvider:
    """最小 LLM 桩：chat_json 返回预设形状。"""

    def __init__(self, payload: object) -> None:
        self._payload = payload
        self.calls: list[list[dict]] = []

    def chat_json(self, messages):
        self.calls.append(messages)
        return self._payload


# ── 第一组：五件套模具结构（冻结章节树 + 信号键绑定）───────────────────


class TestMoldStructure:
    def test_sections_frozen_six(self):
        assert STORY_SECTIONS == (
            "opening_event", "core_dilemma", "branch_trees",
            "lead_chain", "secret_layer", "tension_hole",
        )

    def test_signal_binding_matches_t7_registration(self):
        """剧情.* 键绑定须与 T7 注册 signal_requirements 完全一致。"""
        registered = set(
            get_output_module("story_outline")["signal_requirements"]
        )
        bound = {k for keys in SECTION_SIGNALS.values() for k in keys}
        assert bound == registered
        for sec, keys in SECTION_SIGNALS.items():
            assert keys == (f"剧情.{sec}",)


# ── 第二组：确定性装配（骨架直投 + 溯源）───────────────────────────────


class TestAssembly:
    def test_skeleton_direct_inject_and_provenance(self):
        doc, ledger = compile_outline(
            ANSWERS,
            title="故事大纲",
            ip_name="钟塔IP",
            graph_code="IP0001-O1-v1",
            upstream_graph_code="IP0001-W1-v2",
            provider=FakeProvider({"lead_in": "序", "sections": {}}),
        )
        assert ledger == []
        assert doc.degraded is False
        body = doc.sections[0].body
        assert "雨夜，钟塔第13次敲响" in body
        assert doc.graph_code == "IP0001-O1-v1"
        assert doc.upstream_graph_code == "IP0001-W1-v2"

    def test_missing_signal_section_left_blank(self):
        doc, _ = compile_outline(
            {"剧情.opening_event": "只有开端"},
            title="t", ip_name="i",
            graph_code="IP0001-O1-v1", upstream_graph_code="IP0001-W1-v1",
        )
        assert "只有开端" in doc.sections[0].body
        assert doc.sections[1].body == ""


# ── 第三组：LLM 叙事化导语层（copy-only 契约）──────────────────────────


class TestLLMCopy:
    def test_narrative_prompt_snapshot(self):
        """prompt 快照：叙事化语气指令 + 六节全名 + 剧情.* 信号。"""
        provider = FakeProvider(None)
        compile_copy(provider, ANSWERS)
        content = provider.calls[0][0]["content"]
        assert "叙事化" in content
        assert "只产文案" in content
        for sec in STORY_SECTIONS:
            assert f"剧情.{sec}" in content

    def test_copy_overlay_lead_in(self):
        payload = {
            "lead_in": "钟声响起时，故事开始了。",
            "sections": {"opening_event": "雨夜序幕"},
        }
        doc, ledger = compile_outline(
            ANSWERS, title="故事大纲", ip_name="钟塔IP",
            graph_code="IP0001-O1-v1", upstream_graph_code="IP0001-W1-v1",
            provider=FakeProvider(payload),
        )
        assert ledger == []
        assert doc.degraded is False
        assert doc.lead_in == "钟声响起时，故事开始了。"
        assert doc.sections[0].body.startswith("雨夜序幕")
        assert "雨夜，钟塔第13次敲响" in doc.sections[0].body  # 原文保留

    def test_llm_failure_returns_none_and_degrades(self):
        doc, ledger = compile_outline(
            ANSWERS, title="t", ip_name="i",
            graph_code="IP0001-O1-v1", upstream_graph_code="IP0001-W1-v1",
            provider=None,
        )
        assert doc.degraded is True
        assert any("story_outline_degraded" in e["detail"] for e in ledger)

    @pytest.mark.parametrize("payload", [
        None, "nope", {}, {"lead_in": ""},
        {"lead_in": "", "sections": {"opening_event": "y"}},
    ])
    def test_bad_shape_returns_none(self, payload):
        assert compile_copy(FakeProvider(payload), ANSWERS) is None


# ── 第四组：空图谱降级（薄/半降级与姊妹件一致）─────────────────────────


class TestEmptyDegrade:
    def test_empty_answers_zero_exceptions(self):
        doc, ledger = compile_outline(
            {}, title="空", ip_name="i",
            graph_code="IP0001-O1-v1", upstream_graph_code="IP0001-W1-v1",
        )
        assert len(doc.sections) == 6
        assert all(sec.body == "" for sec in doc.sections)
        assert any("story_outline_degraded" in e["detail"] for e in ledger)


# ── 第五组：序列化 + O 字母溯源 ────────────────────────────────────────


class TestSerializationAndIssuance:
    def test_render_markdown_provenance_o_letter(self):
        doc, _ = compile_outline(
            ANSWERS, title="故事大纲", ip_name="钟塔IP",
            graph_code="IP0001-O1-v1", upstream_graph_code="IP0001-W1-v1",
        )
        md = render_markdown(doc)
        assert "# 故事大纲" in md
        assert "溯源：IP0001-O1-v1 ← IP0001-W1-v1" in md

    def test_issue_outline_code_stage_o(self, tmp_path):
        issuer = GraphCodeIssuer(tmp_path / "codes.db")
        code = issue_outline_code(issuer, "u1", 1)
        assert re.fullmatch(r"IP\d{4}-O\d+-v\d+", code)
