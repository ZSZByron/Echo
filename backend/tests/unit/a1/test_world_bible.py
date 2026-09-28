"""D22 世界圣经渲染器（B）——五件套模具逐字复用的契约测试。

五组：
1. 正常图谱 → 六章全有正文（答案原文直投 + LLM 导语叠加）
2. 空图谱 → 全章正文留空 + 披露（无 409、不编造）
3. 半空图谱 → 有料章正常 / 空章独立披露（逐章独立降级）
4. LLM 失败 → 骨架兜底 + ``world_bible_degraded`` 披露（永不抛出）
5. 章节树冻结（增/删/重排 → 红）
"""
from __future__ import annotations

import re

import pytest

from app.domains.creation.modules.world_bible import (
    BIBLE_CHAPTER_HEADINGS,
    compile_world_bible,
    render_markdown,
)
from app.domains.creation.shared.graph_code_issuer import GraphCodeIssuer


ANSWERS = {
    "世界本体.reality_rule": "意志主导世界：信念可以改写物理法则",
    "世界本体.core_conflict": "教会正统与觉醒者自由意志之争",
    "文明与社会.faction_type": "三大家族分治 + 地下行会",
    "历史时间线.main_plot": "百年前的坍缩事件留下裂隙，正在再次张开",
    "地理空间.terrain": "悬浮群岛与下方雾海",
    "力量体系.cost": "每次施法消耗一段记忆",
    "力量体系.acquire": "通过觉醒仪式获得",
    "设定边界.immutable_core": "裂隙不可被永久关闭；死者不可复活",
}

FULL_SIGNALS = {k: v for k, v in ANSWERS.items()}


def _compile(**kw):
    kw.setdefault("title", "星陨大陆：世界圣经")
    kw.setdefault("ip_name", "星陨大陆")
    kw.setdefault("graph_code", "IP0001-B1-v1")
    kw.setdefault("upstream_graph_code", "IP0001-W1-v1")
    kw.setdefault("provider", None)
    return compile_world_bible(FULL_SIGNALS, **kw)


class FakeProvider:
    async def chat_json(self, messages, **kw):
        return {
            "module_fantasy": "一个信念重塑物质的世界",
            "sections": {h: f"（LLM 导语：{h}）" for h in BIBLE_CHAPTER_HEADINGS},
        }


class BoomProvider:
    async def chat_json(self, messages, **kw):
        raise RuntimeError("network down")


# ---------------------------------------------------------------------------
# 组 1：正常图谱 → 六章全有正文
# ---------------------------------------------------------------------------


class TestNormalGraph:
    def test_all_six_chapters_have_body(self):
        doc, ledger = _compile()
        assert [c.heading for c in doc.chapters] == list(BIBLE_CHAPTER_HEADINGS)
        for c in doc.chapters:
            assert c.body.strip(), f"章节 {c.heading} 正文不应为空"
        assert not any("world_bible_degraded" in e["detail"] for e in ledger)

    def test_skeleton_carries_answer_verbatim(self):
        doc, _ = _compile()
        ben = next(c for c in doc.chapters if c.heading == "世界本体")
        assert "信念可以改写物理法则" in ben.body

    def test_llm_copy_overlays_intro_only_structure_identical(self):
        doc_llm, ledger = _compile(provider=FakeProvider())
        doc_fb, _ = _compile(provider=None)
        assert [c.heading for c in doc_llm.chapters] == \
            [c.heading for c in doc_fb.chapters]
        assert doc_llm.overview == "一个信念重塑物质的世界"
        assert not any("world_bible_degraded" in e["detail"] for e in ledger)

    def test_markdown_renders_with_provenance(self):
        doc, _ = _compile()
        md = render_markdown(doc)
        assert md.startswith("# 星陨大陆：世界圣经")
        assert "## 世界本体" in md
        assert "## 设定边界" in md
        assert f"溯源：{doc.graph_code} ← {doc.upstream_graph_code}" in md

    def test_b_letter_issuance_on_compile(self, tmp_path):
        issuer = GraphCodeIssuer(tmp_path / "codes.db")
        doc, _ = _compile(issuer=issuer, user_id="u1", ip=1)
        assert re.fullmatch(r"IP0001-B\d+-v\d+", doc.graph_code)

    def test_deterministic_same_input_same_skeleton(self):
        a, _ = _compile()
        b, _ = _compile()
        assert a.chapters == b.chapters


# ---------------------------------------------------------------------------
# 组 2：空图谱 → 全章留空 + 披露（无 409、不编造）
# ---------------------------------------------------------------------------


class TestEmptyGraphDegradation:
    def test_empty_answers_all_chapters_empty_body(self):
        doc, ledger = compile_world_bible(
            {}, title="t", ip_name="ip",
            graph_code="IP0001-B1-v1", upstream_graph_code="IP0001-W1-v1",
        )
        assert len(doc.chapters) == 6
        for c in doc.chapters:
            assert c.body == ""
        details = "|".join(e["detail"] for e in ledger)
        assert "world_bible_empty_chapters" in details

    def test_no_fabrication_markdown_still_renders(self):
        doc, _ = compile_world_bible(
            {}, title="t", ip_name="ip",
            graph_code="IP0001-B1-v1", upstream_graph_code="IP0001-W1-v1",
        )
        md = render_markdown(doc)
        assert "## 世界本体" in md  # 结构照出
        assert "信念" not in md     # 不编造

    def test_no_409_no_exception(self):
        compile_world_bible(
            {}, title="t", ip_name="ip",
            graph_code="IP0001-B1-v1", upstream_graph_code="IP0001-W1-v1",
            provider=BoomProvider(),
        )  # 不抛即为过


# ---------------------------------------------------------------------------
# 组 3：半空图谱 → 逐章独立降级
# ---------------------------------------------------------------------------


class TestHalfEmptyIndependentDegradation:
    def test_filled_chapters_normal_empty_disclosed(self):
        partial = {k: v for k, v in FULL_SIGNALS.items()
                   if k.startswith(("世界本体.", "地理空间."))}
        doc, ledger = compile_world_bible(
            partial, title="t", ip_name="ip",
            graph_code="IP0001-B1-v1", upstream_graph_code="IP0001-W1-v1",
        )
        by_heading = {c.heading: c for c in doc.chapters}
        assert "意志主导世界" in by_heading["世界本体"].body
        assert "悬浮群岛" in by_heading["地理空间"].body
        assert by_heading["力量体系"].body == ""
        assert by_heading["设定边界"].body == ""
        details = "|".join(e["detail"] for e in ledger)
        assert "world_bible_empty_chapters" in details
        assert "力量体系" in details
        assert "文明与社会" in details
        assert "世界本体" not in doc.empty_chapters

    def test_empty_chapter_list_on_document(self):
        partial = {k: v for k, v in FULL_SIGNALS.items()
                   if k.startswith("世界本体.")}
        doc, _ = compile_world_bible(
            partial, title="t", ip_name="ip",
            graph_code="IP0001-B1-v1", upstream_graph_code="IP0001-W1-v1",
        )
        assert "世界本体" not in doc.empty_chapters
        assert set(doc.empty_chapters) == {
            "文明与社会", "历史时间线", "地理空间", "力量体系", "设定边界",
        }


# ---------------------------------------------------------------------------
# 组 4：LLM 失败 → 骨架兜底 + world_bible_degraded
# ---------------------------------------------------------------------------


class TestLLMFailureFallback:
    def test_provider_boom_skeleton_fallback(self):
        doc, ledger = _compile(provider=BoomProvider())
        assert [c.heading for c in doc.chapters] == list(BIBLE_CHAPTER_HEADINGS)
        assert "信念可以改写物理法则" in doc.chapters[0].body
        assert any("world_bible_degraded" in e["detail"] for e in ledger)

    def test_provider_none_is_not_degraded(self):
        _, ledger = _compile(provider=None)
        assert not any("world_bible_degraded" in e["detail"] for e in ledger)

    def test_bad_shape_payload_degrades(self):
        class BadShape:
            async def chat_json(self, messages, **kw):
                return {"unexpected": "shape"}

        _, ledger = _compile(provider=BadShape())
        assert any("world_bible_degraded" in e["detail"] for e in ledger)


# ---------------------------------------------------------------------------
# 组 5：章节树冻结（顺序即契约）
# ---------------------------------------------------------------------------


class TestChapterTreeFrozen:
    def test_six_chapter_tree_frozen(self):
        assert BIBLE_CHAPTER_HEADINGS == (
            "世界本体", "文明与社会", "历史时间线", "地理空间", "力量体系",
            "设定边界",
        )

    def test_compile_output_order_frozen(self):
        doc, _ = _compile()
        assert [c.heading for c in doc.chapters] == [
            "世界本体", "文明与社会", "历史时间线", "地理空间", "力量体系",
            "设定边界",
        ]

    def test_signal_binding_covers_registered_keys(self):
        from app.domains.creation.modules import world_bible as wb
        bound = {k for keys in wb._CHAPTER_SIGNALS.values() for k in keys}
        registered = {
            "世界本体.reality_rule", "世界本体.core_conflict",
            "文明与社会.faction_type", "历史时间线.main_plot",
            "地理空间.terrain", "力量体系.cost", "力量体系.acquire",
            "设定边界.immutable_core",
        }
        assert registered <= bound

    @pytest.mark.parametrize("mutation", ["add", "remove", "reorder"])
    def test_mutation_breaks_freeze_contract(self, mutation):
        tree = list(BIBLE_CHAPTER_HEADINGS)
        if mutation == "add":
            tree.append("多余章")
        elif mutation == "remove":
            tree.pop()
        else:
            tree[0], tree[1] = tree[1], tree[0]
        assert tree != list(BIBLE_CHAPTER_HEADINGS)
