# -*- coding: utf-8 -*-
"""人物志渲染器（D22 · C——角色数据小说化渲染）— 契约测试（先于实现，TDD RED）。

D22① 权威（docs/decision-log.md）：「人物志（角色数据小说化渲染）」。
五件套模具（同 main_module.py 主模组文字版）：
  ① 冻结章节树（M11 角色字段 + 世界本体.reality_rule 语境章）
  ② 信号键绑定（角色.* 与 T7 注册一致）
  ③ LLM 导语层——**小说化语气**（本件特有：lead-in prompt 强调小说化
     渲染，逐字 D22①）；仍守「只产导语、失败降级」契约
  ④ 装配/降级/序列化——答案原文直投，LLM 永不改写用户事实
  ⑤ 溯源——C 字 issuance（stage="C"）+ ledger 披露
     ``character_codex_degraded``

语义边界（D22 明确）：C(人物志·角色数据小说化渲染) ≠ TC(角色投影模板
character_projector.py 的 Template Character)——本文件不做相位/机制投影，
character_projector.py 不受扰动。
"""
from __future__ import annotations

import pytest

from app.domains.creation.modules.output_modules import get_output_module
from app.domains.creation.seed.story_modules import M11_CHARACTER


def _fake_provider(payload: dict | None):
    """可编程假 provider：返回 payload 或抛错模拟失败。"""

    class _P:
        def chat_json(self, messages):
            if isinstance(payload, Exception):
                raise payload
            return payload

    return _P()


def _capture_provider(seen: list):
    class _P:
        def chat_json(self, messages):
            seen.extend(messages)
            return {
                "codex_fantasy": "她把秘密缝进衣角。",
                "chapters": {"身世": "守夜人的一生，从一场葬礼开始。"},
            }

    return _P()


CHARACTER_ANSWERS: dict[str, str] = {
    "角色.identity": "边城义庄的守夜人，白天入殓夜里记账",
    "角色.desire": "想要查清灭门真相，需要的是原谅自己当年逃走",
    "角色.flaw": "不信任任何人，关键证据宁可烂在手里也不求助",
    "角色.key_relations": "与叛出师门的师姐互为唯一软肋",
    "角色.arc_direction": "从用谎言保护所有人→学会让真相先落地",
    "角色.character_visual": "左耳缺角的银质耳坠，紧张时摩挲它",
    "世界本体.reality_rule": "世界由物质法则主导，魔法稀有",
}


# ---------------------------------------------------------------------------
# ① 冻结章节树（M11 字段逐字来源 + 语境章；顺序即契约）
# ---------------------------------------------------------------------------


class TestFrozenChapterTree:
    def test_chapter_headings_frozen_verbatim(self):
        from app.domains.creation.modules.character_codex import (
            CODEX_CHAPTER_HEADINGS,
        )

        assert CODEX_CHAPTER_HEADINGS == (
            "身世", "心之所欲", "暗面缺陷", "关键关系",
            "弧光方向", "视觉锚点", "世界法则",
        )

    def test_chapter_tree_covers_all_m11_fields(self):
        """M11 六字段全部入树，不增不漏（final 依 STORY_MODULES 实际子域）。"""
        from app.domains.creation.modules.character_codex import (
            _CHAPTER_SIGNALS,
        )

        bound = {k for keys in _CHAPTER_SIGNALS.values() for k in keys}
        m11_keys = {f"角色.{f['id']}" for f in M11_CHARACTER["fields"]}
        assert m11_keys <= bound
        assert "世界本体.reality_rule" in bound

    def test_signal_keys_consistent_with_t7_registration(self):
        """角色.* 键域与 T7 OUTPUT_MODULES 注册的 signal_requirements 一致。"""
        from app.domains.creation.modules.character_codex import (
            _CHAPTER_SIGNALS,
        )

        reg = get_output_module("character_codex")
        assert reg is not None
        reg_keys = set(reg["signal_requirements"])
        bound = {k for keys in _CHAPTER_SIGNALS.values() for k in keys}
        assert bound <= reg_keys | {"角色.flaw", "角色.character_visual"}


# ---------------------------------------------------------------------------
# ② 装配：答案原文直投（LLM 永不改写用户事实）
# ---------------------------------------------------------------------------


class TestAssembly:
    def test_full_answers_direct_projection(self):
        from app.domains.creation.modules.character_codex import compile_codex

        doc, ledger = compile_codex(
            CHARACTER_ANSWERS,
            character_name="守夜人",
            graph_code="IP0001-C1-v1",
            upstream_graph_code="IP0001-M1-v1",
        )
        assert doc.codex_fantasy  # 骨架版缺省 fantasy 也非空
        bodies = {c.heading: c.body for c in doc.chapters}
        assert "角色.identity" not in "".join(bodies.values())
        assert "边城义庄的守夜人" in bodies["身世"]
        assert "左耳缺角的银质耳坠" in bodies["视觉锚点"]
        assert "世界由物质法则主导" in bodies["世界法则"]

    def test_llm_lead_in_prepended_but_facts_untouched(self):
        """LLM 导语只叠加在原文之前——用户答案原文逐字保留。"""
        from app.domains.creation.modules.character_codex import compile_codex

        doc, ledger = compile_codex(
            CHARACTER_ANSWERS,
            character_name="守夜人",
            graph_code="IP0001-C1-v1",
            upstream_graph_code="IP0001-M1-v1",
            provider=_fake_provider({
                "codex_fantasy": "一个不信任任何人的人。",
                "chapters": {"身世": "她守着义庄，也守着秘密。"},
            }),
        )
        body = doc.chapters[0].body
        assert body.startswith("她守着义庄，也守着秘密。")
        assert "边城义庄的守夜人，白天入殓夜里记账" in body
        assert ledger == []

    def test_llm_never_rewrites_quoted_facts(self):
        """引号内用户原文直投——LLM 导语只做渲染语气，不替换数据。"""
        from app.domains.creation.modules.character_codex import compile_codex

        answers = {"角色.identity": "「铁面判官」座下第一刀笔吏"}
        doc, _ = compile_codex(
            answers,
            character_name="刀笔吏",
            graph_code="IP0001-C1-v1",
            upstream_graph_code="IP0001-M1-v1",
            provider=_fake_provider({
                "codex_fantasy": "x", "chapters": {"身世": "x"},
            }),
        )
        assert "「铁面判官」座下第一刀笔吏" in doc.chapters[0].body


# ---------------------------------------------------------------------------
# ③ LLM 导语层：小说化语气 prompt 契约（D22① 逐字）+ 只产导语
# ---------------------------------------------------------------------------


class TestNovelisticPrompt:
    def test_prompt_contains_novelistic_directive(self):
        from app.domains.creation.modules import character_codex as cc

        assert "小说化" in cc._CODEX_COMPILE_PROMPT

    def test_prompt_has_no_field_directives_beyond_chapter_tree(self):
        """prompt 只允许章节树标题作为结构指令——无字段/数值/结构产出指令。"""
        from app.domains.creation.modules import character_codex as cc

        prompt = cc._CODEX_COMPILE_PROMPT.replace(
            "{headings}", "、".join(cc.CODEX_CHAPTER_HEADINGS),
        ).replace("{signals}", "x")
        for h in cc.CODEX_CHAPTER_HEADINGS:
            assert h in prompt
        # 不产结构数值（模具纪律）：不得请求 JSON 之外的数值/结构字段
        assert "不产结构数值" in prompt
        assert "输出数值" not in prompt

    def test_llm_partial_chapters_only_those_get_lead_in(self):
        """半角降级：LLM 只回了部分章 → 仅这些章叠加导语，其余纯骨架。"""
        from app.domains.creation.modules.character_codex import compile_codex

        doc, ledger = compile_codex(
            CHARACTER_ANSWERS,
            character_name="守夜人",
            graph_code="IP0001-C1-v1",
            upstream_graph_code="IP0001-M1-v1",
            provider=_fake_provider({
                "codex_fantasy": "f",
                "chapters": {"心之所欲": "她想要一个交代。"},
            }),
        )
        bodies = {c.heading: c.body for c in doc.chapters}
        assert bodies["心之所欲"].startswith("她想要一个交代。")
        assert bodies["身世"].startswith("- ")
        assert ledger == []

    def test_llm_foreign_chapter_labels_dropped(self):
        """LLM 越界章节标题被丢弃（章节树封闭）。"""
        from app.domains.creation.modules.character_codex import compile_codex

        doc, _ = compile_codex(
            CHARACTER_ANSWERS,
            character_name="守夜人",
            graph_code="IP0001-C1-v1",
            upstream_graph_code="IP0001-M1-v1",
            provider=_fake_provider({
                "codex_fantasy": "f",
                "chapters": {"骰子规则": "越界", "身世": "合法"},
            }),
        )
        bodies = {c.heading: c.body for c in doc.chapters}
        assert "越界" not in bodies.values()
        assert bodies["身世"].startswith("合法")


# ---------------------------------------------------------------------------
# ④ 降级：薄/半/空——逐章独立 + ledger 披露
# ---------------------------------------------------------------------------


class TestDegradation:
    def test_provider_none_degrades_with_ledger(self):
        from app.domains.creation.modules.character_codex import compile_codex

        doc, ledger = compile_codex(
            CHARACTER_ANSWERS,
            character_name="守夜人",
            graph_code="IP0001-C1-v1",
            upstream_graph_code="IP0001-M1-v1",
            provider=None,
        )
        assert ledger and "character_codex_degraded" in ledger[0]["detail"]
        assert "确定性骨架" in ledger[0]["detail"]

    def test_provider_exception_degrades_never_raises(self):
        from app.domains.creation.modules.character_codex import compile_codex

        doc, ledger = compile_codex(
            CHARACTER_ANSWERS,
            character_name="守夜人",
            graph_code="IP0001-C1-v1",
            upstream_graph_code="IP0001-M1-v1",
            provider=_fake_provider(RuntimeError("boom")),
        )
        assert ledger and "character_codex_degraded" in ledger[0]["detail"]

    def test_llm_shape_mismatch_degrades(self):
        from app.domains.creation.modules.character_codex import compile_codex

        doc, ledger = compile_codex(
            CHARACTER_ANSWERS,
            character_name="守夜人",
            graph_code="IP0001-C1-v1",
            upstream_graph_code="IP0001-M1-v1",
            provider=_fake_provider({"codex_fantasy": 123}),
        )
        assert ledger and "character_codex_degraded" in ledger[0]["detail"]

    def test_empty_answers_empty_degrade_no_exception(self):
        from app.domains.creation.modules.character_codex import compile_codex

        doc, ledger = compile_codex(
            {},
            character_name="",
            graph_code="IP0001-C1-v1",
            upstream_graph_code="IP0001-M1-v1",
            provider=None,
        )
        assert all(c.body == "" for c in doc.chapters)
        assert ledger and "character_codex_degraded" in ledger[0]["detail"]


# ---------------------------------------------------------------------------
# ⑤ 序列化 + 溯源（C 字 issuance · stage="C"）
# ---------------------------------------------------------------------------


class TestSerializationProvenance:
    def test_render_markdown_round_trip(self):
        from app.domains.creation.modules.character_codex import (
            compile_codex,
            render_markdown,
        )

        doc, _ = compile_codex(
            CHARACTER_ANSWERS,
            character_name="守夜人",
            graph_code="IP0001-C1-v1",
            upstream_graph_code="IP0001-M1-v1",
        )
        md = render_markdown(doc)
        assert md.startswith("# 守夜人")
        assert "## 身世" in md
        assert "溯源：IP0001-C1-v1 ← IP0001-M1-v1" in md

    def test_stage_c_letter_issuance(self):
        """C 字 issuance：stage="C" 出码 IP0001-C1-v1（≠ TC）。"""
        import tempfile
        from pathlib import Path

        from app.domains.creation.shared.graph_code_issuer import (
            GraphCodeIssuer,
            StageCode,
        )

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
            issuer = GraphCodeIssuer(Path(td) / "codes.db")
            code = issuer.next("u1", 1, StageCode.CODEX.value)
            assert code == "IP0001-C1-v1"
            assert StageCode.from_str("C") is StageCode.CODEX
            assert StageCode.CODEX.value == "C"
            assert StageCode.CODEX is not StageCode.SECONDARY  # C ≠ TC 语义隔离

    def test_provenance_fields_carried(self):
        from app.domains.creation.modules.character_codex import compile_codex

        doc, _ = compile_codex(
            CHARACTER_ANSWERS,
            character_name="守夜人",
            graph_code="IP0001-C1-v2",
            upstream_graph_code="IP0001-M1-v1",
            used_stale=True,
            upstream_ledger=[{"message": "up"}],
        )
        assert doc.graph_code == "IP0001-C1-v2"
        assert doc.upstream_graph_code == "IP0001-M1-v1"
        assert doc.used_stale is True
        assert doc.upstream_ledger == [{"message": "up"}]

    def test_deterministic_skeleton_without_llm(self):
        from app.domains.creation.modules.character_codex import compile_codex

        a, _ = compile_codex(
            CHARACTER_ANSWERS, character_name="守夜人",
            graph_code="IP0001-C1-v1", upstream_graph_code="IP0001-M1-v1",
        )
        b, _ = compile_codex(
            CHARACTER_ANSWERS, character_name="守夜人",
            graph_code="IP0001-C1-v1", upstream_graph_code="IP0001-M1-v1",
        )
        assert a.model_dump() == b.model_dump()
