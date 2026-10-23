"""D22 Task13：故事大纲渲染器（O）契约测试——真写作大纲（方案 B）。

矩阵：T7 信号绑定 / 降级六节骨架（与 HEAD 行为逐字节一致）/
新 LLM 写作大纲契约（梗概·主题人物·三幕节拍·章节·伏笔·支线）+
诚实纪律 prompt 快照 + 帽值截断。
"""
from __future__ import annotations

import re

import pytest

from app.domains.creation.modules.output_modules import get_output_module
from app.domains.creation.modules.story_outline import (
    SECTION_SIGNALS,
    STORY_SECTIONS,
    compile_outline,
    compile_outline_llm,
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

FULL_OUTLINE = {
    "lead_in": "钟声响起时，故事开始了。",
    "logline": "当钟塔第13次敲响，钟匠必须找回被遗忘的名字，否则全城失忆。",
    "theme": "记忆是否比人更重要？",
    "protagonist": "钟匠想要救回挚友，需要直面封印，错误信念是他能独自承担一切。",
    "antagonist": "吞噬名字的钟塔回声。",
    "acts": [
        {"name": "第一幕·开端", "summary": "钟声与遗忘之夜。",
         "beats": ["第十三次钟响", "挚友失名"]},
        {"name": "第二幕·对抗", "summary": "追查回声源头。",
         "beats": ["地下探秘", "教会阻挠", "真相反转"]},
        {"name": "第三幕·结局", "summary": "以名为祭，重铸封印。", "beats": ["终局钟鸣"]},
    ],
    "chapters": [
        {"title": "雨夜钟鸣", "goal": "查明钟声来由", "obstacle": "守夜人封锁",
         "outcome": "得到残页", "cost": "自己忘了一个名字", "hook": "残页写着主教名"},
        {"title": "地下回声", "goal": "找到初代钟匠", "obstacle": "封印反噬",
         "outcome": "见到遗体", "cost": "挚友彻底失名", "hook": ""},
    ],
    "foreshadowing": [
        {"plant": "钟塔只有十二格刻度", "payoff": "第十三响来自地下", "weight": "高"},
    ],
    "subplots": [
        {"name": "商会暗线", "tie": "第二幕商会会长供出封印图纸"},
    ],
}


class FakeProvider:
    """最小 LLM 桩：chat_json 返回预设形状。"""

    def __init__(self, payload: object) -> None:
        self._payload = payload
        self.calls: list[list[dict]] = []

    def chat_json(self, messages):
        self.calls.append(messages)
        return self._payload


# ── 第一组：五件套模具结构（冻结章节树 + 信号键绑定，T7 契约不变）──────


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


# ── 第二组：降级路径（LLM 缺席 → 六节骨架，行为与 HEAD 一致）──────────


class TestDegradeSkeleton:
    def test_no_provider_skeleton_direct_inject_and_provenance(self):
        doc, ledger = compile_outline(
            ANSWERS,
            title="故事大纲",
            ip_name="钟塔IP",
            graph_code="IP0001-O1-v1",
            upstream_graph_code="IP0001-W1-v2",
        )
        assert doc.degraded is True
        assert any("story_outline_degraded" in e["detail"] for e in ledger)
        assert [s.heading for s in doc.sections] == list(STORY_SECTIONS)
        assert "雨夜，钟塔第13次敲响" in doc.sections[0].body
        assert doc.graph_code == "IP0001-O1-v1"
        assert doc.upstream_graph_code == "IP0001-W1-v2"
        assert doc.lead_in == (
            "钟塔IP：一段可直接开团的剧情大纲（确定性骨架版）"
        )

    def test_missing_signal_section_left_blank(self):
        doc, _ = compile_outline(
            {"剧情.opening_event": "只有开端"},
            title="t", ip_name="i",
            graph_code="IP0001-O1-v1", upstream_graph_code="IP0001-W1-v1",
        )
        assert "只有开端" in doc.sections[0].body
        assert doc.sections[1].body == ""

    def test_empty_answers_zero_exceptions(self):
        doc, ledger = compile_outline(
            {}, title="空", ip_name="i",
            graph_code="IP0001-O1-v1", upstream_graph_code="IP0001-W1-v1",
        )
        assert len(doc.sections) == 6
        assert all(sec.body == "" for sec in doc.sections)
        assert any("story_outline_degraded" in e["detail"] for e in ledger)


# ── 第三组：真写作大纲 LLM 契约（compile_outline_llm 单点）─────────────


class TestWritingOutlineAssembly:
    def test_full_outline_six_form_section_tree(self):
        doc, ledger = compile_outline(
            ANSWERS, title="故事大纲", ip_name="钟塔IP",
            graph_code="IP0001-O1-v1", upstream_graph_code="IP0001-W1-v1",
            provider=FakeProvider(FULL_OUTLINE),
        )
        assert ledger == []
        assert doc.degraded is False
        assert doc.lead_in == "钟声响起时，故事开始了。"
        headings = [s.heading for s in doc.sections]
        assert headings == [
            "一句话梗概", "主题与人物", "主线三幕节拍",
            "第一幕·开端", "第二幕·对抗", "第三幕·结局",
            "章节分解", "伏笔与回收", "支线与交点",
        ]
        # 梗概
        assert doc.sections[0].level == 2
        assert doc.sections[0].body == (
            "当钟塔第13次敲响，钟匠必须找回被遗忘的名字，否则全城失忆。"
        )
        # 主题与人物：标签式三行，全非空
        body = doc.sections[1].body
        assert "- 主题：记忆是否比人更重要？" in body
        assert "- 主角：钟匠想要救回挚友" in body
        assert "- 反抗力量：吞噬名字的钟塔回声。" in body
        # 三幕：level3 子节 + summary + beats 列表
        acts_secs = [s for s in doc.sections if s.level == 3]
        assert [s.heading for s in acts_secs] == [
            "第一幕·开端", "第二幕·对抗", "第三幕·结局",
        ]
        assert acts_secs[0].body.startswith("钟声与遗忘之夜。")
        assert "- 第十三次钟响" in acts_secs[0].body
        # 章节：列表行格式（不用表格）
        ch_body = [s for s in doc.sections if s.heading == "章节分解"][0].body
        assert ch_body.startswith("- 第1章 雨夜钟鸣：目标「查明钟声来由」")
        assert "→ 阻碍「守夜人封锁」" in ch_body
        assert "→ 结果「得到残页」" in ch_body
        assert "（代价：自己忘了一个名字；钩：残页写着主教名）" in ch_body
        assert "- 第2章 地下回声" in ch_body
        # 空钩省略「钩：」段
        line2 = [ln for ln in ch_body.splitlines()
                 if ln.startswith("- 第2章")][0]
        assert "钩：" not in line2
        # 伏笔
        assert [s for s in doc.sections if s.heading == "伏笔与回收"][0].body == (
            "- 钟塔只有十二格刻度 → 第十三响来自地下（重要度：高）"
        )
        # 支线
        assert [s for s in doc.sections if s.heading == "支线与交点"][0].body == (
            "- 商会暗线——第二幕商会会长供出封印图纸"
        )

    @pytest.mark.parametrize("mutate", [
        lambda d: d.update(logline=""),
        lambda d: d.update(logline=None),
        lambda d: d.update(lead_in="  "),
        lambda d: d.update(acts=[]),
        lambda d: d.update(acts="nope"),
        lambda d: d.update(acts=[{"summary": "无名"}]),
        lambda d: d.update(chapters="nope"),
        lambda d: d.update(foreshadowing=[42]),
        lambda d: d.update(subplots=[None]),
        lambda d: d.pop("logline"),
    ])
    def test_bad_shape_degrades_to_skeleton(self, mutate):
        payload = dict(FULL_OUTLINE)
        mutate(payload)
        doc, ledger = compile_outline(
            ANSWERS, title="t", ip_name="i",
            graph_code="IP0001-O1-v1", upstream_graph_code="IP0001-W1-v1",
            provider=FakeProvider(payload),
        )
        assert doc.degraded is True
        assert [s.heading for s in doc.sections] == list(STORY_SECTIONS)
        assert any("story_outline_degraded" in e["detail"] for e in ledger)

    @pytest.mark.parametrize("payload", [
        None, "nope", 42, {"lead_in": "x"},  # logline 缺失
    ])
    def test_llm_single_point_returns_none_on_bad_shape(self, payload):
        assert compile_outline_llm(FakeProvider(payload), ANSWERS) is None

    def test_provider_absent_returns_none(self):
        assert compile_outline_llm(None, ANSWERS) is None


# ── 第四组：帽值截断（超帽静默截断，不算失败）──────────────────────────


class TestCaps:
    def test_chapter_cap_24(self):
        payload = dict(FULL_OUTLINE)
        payload["chapters"] = [
            {"title": f"章{i}", "goal": "g", "obstacle": "o",
             "outcome": "r", "cost": "c", "hook": ""}
            for i in range(1, 26)
        ]
        doc, ledger = compile_outline(
            ANSWERS, title="t", ip_name="i",
            graph_code="IP0001-O1-v1", upstream_graph_code="IP0001-W1-v1",
            provider=FakeProvider(payload),
        )
        assert doc.degraded is False
        assert ledger == []
        ch_sec = [s for s in doc.sections if s.heading == "章节分解"][0]
        assert len(ch_sec.body.splitlines()) == 24
        assert "- 第24章" in ch_sec.body
        assert "- 第25章" not in ch_sec.body

    def test_beats_and_lists_caps(self):
        payload = dict(FULL_OUTLINE)
        payload["acts"] = [
            {"name": "第一幕·开端", "summary": "s",
             "beats": [f"节拍{i}" for i in range(9)]},
        ]
        payload["foreshadowing"] = [
            {"plant": f"伏{i}", "payoff": "收", "weight": "低"}
            for i in range(15)
        ]
        payload["subplots"] = [
            {"name": f"支线{i}", "tie": "交点"} for i in range(8)
        ]
        doc, _ = compile_outline(
            ANSWERS, title="t", ip_name="i",
            graph_code="IP0001-O1-v1", upstream_graph_code="IP0001-W1-v1",
            provider=FakeProvider(payload),
        )
        assert doc.degraded is False
        act_sec = [s for s in doc.sections if s.level == 3][0]
        beats = [ln for ln in act_sec.body.splitlines() if ln.startswith("- ")]
        assert len(beats) == 6
        fs_sec = [s for s in doc.sections if s.heading == "伏笔与回收"][0]
        assert len(fs_sec.body.splitlines()) == 12
        sp_sec = [s for s in doc.sections if s.heading == "支线与交点"][0]
        assert len(sp_sec.body.splitlines()) == 6


# ── 第五组：空可省节 + 诚实纪律 prompt 快照 ────────────────────────────


class TestOptionalSectionsAndPrompt:
    def test_empty_optional_sections_omitted(self):
        payload = dict(FULL_OUTLINE)
        payload["chapters"] = []
        payload["foreshadowing"] = []
        payload["subplots"] = []
        payload["theme"] = ""
        payload["antagonist"] = ""
        doc, _ = compile_outline(
            ANSWERS, title="t", ip_name="i",
            graph_code="IP0001-O1-v1", upstream_graph_code="IP0001-W1-v1",
            provider=FakeProvider(payload),
        )
        headings = [s.heading for s in doc.sections]
        assert "一句话梗概" in headings
        assert "主线三幕节拍" in headings
        assert "章节分解" not in headings
        assert "伏笔与回收" not in headings
        assert "支线与交点" not in headings
        # 空字段标签行省略
        body = [s for s in doc.sections if s.heading == "主题与人物"][0].body
        assert "- 主题：" not in body
        assert "- 反抗力量：" not in body
        assert "- 主角：" in body

    def test_prompt_honesty_discipline_and_key_fields(self):
        """prompt 快照：诚实纪律 + 全部素材输入 + 关键字段名。"""
        provider = FakeProvider(None)
        compile_outline_llm(provider, ANSWERS)
        content = provider.calls[0][0]["content"]
        assert "只用用户素材合成" in content
        assert "禁止编造" in content
        assert "空数组" in content
        for field in ("lead_in", "logline", "theme", "protagonist",
                      "antagonist", "acts", "chapters",
                      "foreshadowing", "subplots"):
            assert f'"{field}"' in content
        for kw in ("一句话梗概", "三幕", "伏笔", "支线", "章节"):
            assert kw in content
        # 全部答案原文进入 prompt（不限剧情.*）
        for value in ANSWERS.values():
            assert value in content


# ── 第六组：序列化 + O 字母溯源 ────────────────────────────────────────


class TestSerializationAndIssuance:
    def test_render_markdown_provenance_o_letter(self):
        doc, _ = compile_outline(
            ANSWERS, title="故事大纲", ip_name="钟塔IP",
            graph_code="IP0001-O1-v1", upstream_graph_code="IP0001-W1-v1",
        )
        md = render_markdown(doc)
        assert "# 故事大纲" in md
        assert "溯源：IP0001-O1-v1 ← IP0001-W1-v1" in md

    def test_render_markdown_writing_outline(self):
        doc, _ = compile_outline(
            ANSWERS, title="故事大纲", ip_name="钟塔IP",
            graph_code="IP0001-O1-v1", upstream_graph_code="IP0001-W1-v1",
            provider=FakeProvider(FULL_OUTLINE),
        )
        md = render_markdown(doc)
        assert "> 钟声响起时，故事开始了。" in md
        assert "## 一句话梗概" in md
        assert "### 第一幕·开端" in md

    def test_issue_outline_code_stage_o(self, tmp_path):
        issuer = GraphCodeIssuer(tmp_path / "codes.db")
        code = issue_outline_code(issuer, "u1", 1)
        assert re.fullmatch(r"IP\d{4}-O\d+-v\d+", code)
