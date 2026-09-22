"""M0 止血：访谈偏转死循环 hotfix 三件（甲计划任务 0）。

翻车场景重放测试数据 = `.sisyphus/evidence/jia-requirement-evidence-interview-failure.md`
真实翻车记录原文：

1. 【文明与社会·势力类型】"额！能先专注于故事吗？" → LLM 口头答应却重问同一题
   （偏转被无视 → deflect 标记 + 占位跳过推进指针）
2. 剧情细节"他见到了一个女孩，似是故人，但他坚持操守…" → 被误判为主剧情修改
   提案（替换/合并/放弃三连）→ story_material 素材槽归档
3. 降级建议"仙门/边城义庄/流民营" → story-side suggest_examples 换料
   （从用户已答剧情/角色内容延伸，禁势力/政治模板）

门禁语义：偏转占位写入后 is_module_over_half 不计数（J1 真值闸）。
连续偏转 ≥2 同一字段 → open_questions 归档。
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.domains.creation.a1 import interaction_log
from app.domains.creation.a1.guide_engine import A1Session, handle_message, progress
from app.domains.creation.a1.interviewer import (
    FakeInterviewer,
    RealLLMInterviewer,
)
from app.domains.creation.seed.a1_question_tree import (
    is_module_over_half,
    is_truthy_answer,
)

# 翻车记录原文（测试数据，逐字取自 evidence 文件）
DEFLECTION_UTTERANCE = "额！能先专注于故事吗？"
STORY_MATERIAL_TEXT = "他见到了一个女孩，似是故人，但他坚持操守…"
FACTION_KEY = "文明与社会.faction_type"


def _session(**overrides) -> A1Session:
    """plot 型会话，指针停在【文明与社会·势力类型】（翻车现场）。"""
    s = A1Session(session_id="sess-deflect", user_id="u1", creator_primary="plot")
    s.current_module = "文明与社会"
    s.current_subfield = "faction_type"
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


@pytest.fixture()
def capture_log(tmp_path, monkeypatch):
    """把 interaction log 重定向到临时文件，供留痕断言。"""
    log_path = tmp_path / "a1_interaction_log.jsonl"
    monkeypatch.setattr(interaction_log, "_LOG_PATH", log_path)
    return log_path


class _FakeProvider:
    """捕获 prompt 的假 provider（suggest_examples / interview prompt 断言用）。"""

    def __init__(self, response: dict | None = None) -> None:
        self.response = response or {"examples": ["示例A"]}
        self.captured: list[list[dict]] = []

    async def chat_json(self, messages):  # noqa: ANN001, ANN202
        self.captured.append(messages)
        return self.response


# ---------------------------------------------------------------------------
# 场景 ①：偏转 → 占位跳过推进指针（重问死循环根治）
# ---------------------------------------------------------------------------


class TestDeflectionPlaceholderAdvance:
    def test_deflect_writes_placeholder_and_advances(self, capture_log) -> None:
        session = _session()
        interviewer = FakeInterviewer(
            guidance_reply="好，我们先专注你的故事。",
            deflect=True,
        )
        out = handle_message(session, DEFLECTION_UTTERANCE, interviewer)

        # 占位答案写入（语义覆盖：J1 真值闸判非真值）
        assert session.answers[FACTION_KEY] == "（用户跳过）"
        # 指针前进：下一问不再是势力类型
        nq = out["next_question"]
        assert nq is not None
        assert nq["sub_id"] != "faction_type"
        # 共情回应来自 interviewer guidance_reply
        assert "故事" in out["reply"]
        # interaction log 留痕
        assert capture_log.exists()
        assert "deflected" in capture_log.read_text(encoding="utf-8")

    def test_deflect_placeholder_not_truthy_gate_not_counted(
        self, capture_log,  # noqa: ARG002
    ) -> None:
        """门禁语义：占位不计入 truthy → is_module_over_half 不被虚增。"""
        assert is_truthy_answer("（用户跳过）") is False

        session = _session()
        interviewer = FakeInterviewer(guidance_reply="好。", deflect=True)
        handle_message(session, DEFLECTION_UTTERANCE, interviewer)

        # 该模块本无其他已答 → 仅占位写入后门禁仍不过半（不被占位推过线）
        assert is_module_over_half("文明与社会", session.answers) is False
        p = progress(session)
        faction = next(s for s in p["sections"] if s["id"] == "文明与社会")
        assert faction["done"] is False
        assert session.phase != "completed"

    def test_deflect_two_consecutive_same_field_archives_open_question(
        self, capture_log,  # noqa: ARG002
    ) -> None:
        """连续偏转 ≥2 次同一字段 → open_questions 归档。"""
        session = _session()
        interviewer = FakeInterviewer(guidance_reply="好。", deflect=True)

        handle_message(session, DEFLECTION_UTTERANCE, interviewer)
        # 指针已被推走；模拟用户回到同一字段再次偏转（引擎侧同字段计数）
        session.current_module = "文明与社会"
        session.current_subfield = "faction_type"
        out2 = handle_message(session, "不想答这个，先跳过", interviewer)

        assert session.deflect_counts[FACTION_KEY] == 2
        assert len(session.open_question_archive) == 1
        rec = session.open_question_archive[0]
        assert rec["id"] == f"deflect-{FACTION_KEY}"
        assert rec["status"] == "skipped"
        assert rec["question"]
        # 归档只发生一次（幂等），第二次偏转不再追加
        assert out2 is not None

    def test_single_deflect_does_not_archive(self, capture_log) -> None:  # noqa: ARG002
        session = _session()
        interviewer = FakeInterviewer(guidance_reply="好。", deflect=True)
        handle_message(session, DEFLECTION_UTTERANCE, interviewer)
        assert session.deflect_counts[FACTION_KEY] == 1
        assert session.open_question_archive == []


# ---------------------------------------------------------------------------
# 场景 ②：叙事素材 → character_sketch 素材槽归档（不触发替换/合并/放弃三连）
# ---------------------------------------------------------------------------


class TestStoryMaterialArchive:
    def test_narrative_detail_goes_to_sketch_not_proposals(
        self, capture_log,  # noqa: ARG002
    ) -> None:
        session = _session()
        # 模拟 main_plot 已答（翻车现场：素材被误判为对已答主剧情的修改）
        session.answers["历史时间线.main_plot"] = "主角坚守操守的故事"
        interviewer = FakeInterviewer(
            guidance_reply="这段角色素材我记下了。",
            story_material=STORY_MATERIAL_TEXT,
        )
        out = handle_message(session, STORY_MATERIAL_TEXT, interviewer)

        # 素材进槽
        assert "似是故人" in session.character_sketch
        assert STORY_MATERIAL_TEXT in session.character_sketch
        # 不触发替换/合并/放弃三连
        assert session.pending_proposals == {}
        assert "proposals" not in out or not out.get("proposals")
        # 素材不是答案：指针不动
        assert (session.current_module, session.current_subfield) == (
            "文明与社会",
            "faction_type",
        )
        # 留痕
        assert "material_archived" in capture_log.read_text(encoding="utf-8")

    def test_material_appends_with_newline_and_clips_at_2000(
        self, capture_log,  # noqa: ARG002
    ) -> None:
        session = _session()
        session.character_sketch = "已有素材"
        long_material = "长" * 2500
        interviewer = FakeInterviewer(
            guidance_reply="记下了。", story_material=long_material
        )
        handle_message(session, "一段很长的剧情细节", interviewer)

        parts = session.character_sketch.split("\n")
        assert parts[0] == "已有素材"
        assert len(parts[1]) == 2000  # clip_answer 限额
        # J3 披露：截断记入 answer_clips
        assert any("character_sketch" in c for c in session.answer_clips)

    def test_material_with_fills_takes_fill_path(self, capture_log) -> None:  # noqa: ARG002
        """LLM 判定既有素材又有 fill 时，fill 走正常管线（素材分支只在 fills 空时兜底）。"""
        from app.domains.creation.a1.interviewer import InterviewFill

        session = _session()
        interviewer = FakeInterviewer(
            fills=[InterviewFill(
                module="文明与社会", subfield="faction_type", value="修行者联盟"
            )],
            story_material=STORY_MATERIAL_TEXT,
        )
        out = handle_message(session, STORY_MATERIAL_TEXT, interviewer)
        assert session.answers[FACTION_KEY] == "修行者联盟"
        assert out["file_diff"]


# ---------------------------------------------------------------------------
# 场景 ③：story-side 降级建议换料（不再势力/政治模板）
# ---------------------------------------------------------------------------


class TestStorySideSuggestions:
    def test_suggest_examples_prompt_story_rule_for_plot(self) -> None:
        provider = _FakeProvider()
        session = SimpleNamespace(
            seed_name="", seed_genre="", seed_description="",
            creator_primary="plot", answers={"历史时间线.main_plot": "少年与故人重逢"},
        )
        RealLLMInterviewer(provider=provider).suggest_examples(
            session, "文明与社会", "faction_type"
        )
        prompt = provider.captured[0][0]["content"]
        # 规则文本：从用户已答剧情/角色内容延伸
        assert "剧情、角色、情感线索延伸" in prompt
        assert "少年与故人重逢" in prompt  # 已答内容作为示例原料
        # 禁势力/政治模板
        assert "严禁输出势力、政治、阵营类世界建构模板" in prompt

    def test_suggest_examples_prompt_no_story_rule_for_setting_type(self) -> None:
        provider = _FakeProvider()
        session = SimpleNamespace(
            seed_name="", seed_genre="", seed_description="",
            creator_primary="", answers={},
        )
        RealLLMInterviewer(provider=provider).suggest_examples(
            session, "文明与社会", "faction_type"
        )
        prompt = provider.captured[0][0]["content"]
        # 设定型不注入故事规则（R2：差异是数据不是代码；设定型零扰动）
        assert "剧情、角色、情感线索延伸" not in prompt
        assert "严禁输出势力、政治、阵营类世界建构模板" not in prompt


# ---------------------------------------------------------------------------
# LLM 契约：deflect / story_material 解析（InterviewResult 可选字段，向前兼容豁免）
# ---------------------------------------------------------------------------


class TestInterviewContract:
    def test_parse_deflect_marker_drops_fills(self) -> None:
        provider = _FakeProvider(response={
            "fills": [{"module": "文明与社会", "subfield": "faction_type", "value": "x"}],
            "guidance_reply": "好，我们先专注故事。",
            "deflect": True,
        })
        session = SimpleNamespace(
            session_id="s", current_module="文明与社会", current_subfield="faction_type",
            answers={}, seed_name="", seed_genre="", seed_description="",
            creator_primary="plot",
        )
        result = RealLLMInterviewer(provider=provider).interview(session, DEFLECTION_UTTERANCE)
        assert result.deflect is True
        assert result.fills == []  # 偏转不生成 fills（防御性，prompt 规则之外兜底）

    def test_parse_story_material(self) -> None:
        provider = _FakeProvider(response={
            "fills": [],
            "guidance_reply": "记下了。",
            "story_material": STORY_MATERIAL_TEXT,
        })
        session = SimpleNamespace(
            session_id="s", current_module="文明与社会", current_subfield="faction_type",
            answers={}, seed_name="", seed_genre="", seed_description="",
            creator_primary="plot",
        )
        result = RealLLMInterviewer(provider=provider).interview(session, STORY_MATERIAL_TEXT)
        assert result.story_material == STORY_MATERIAL_TEXT
        assert result.deflect is False

    def test_interview_prompt_contains_deflection_and_material_rules(self) -> None:
        interviewer = RealLLMInterviewer(provider=None)
        module = {"id": "文明与社会", "label": "文明与社会", "fields": []}
        subfield = {"id": "faction_type", "label": "势力类型", "question": "?", "example": ""}
        session = SimpleNamespace(
            answers={}, seed_name="", seed_genre="", seed_description="",
            creator_primary="plot",
        )
        prompt = interviewer._build_prompt(module, subfield, session)
        # 偏转规则（全部会话——所有型都可能想先聊别的）
        assert "7.5 偏转判定" in prompt
        assert "deflect=true" in prompt
        # 叙事素材归档规则（故事型会话）
        assert "3.8 叙事素材归档" in prompt
        assert "story_material" in prompt
        # JSON 契约含新可选字段
        assert '"deflect": false' in prompt
        assert '"story_material": null' in prompt

    def test_prompt_skeleton_still_three_copies(self) -> None:
        """R2 红线：不建第二份 prompt——骨架串出现次数仍为 3。"""
        src = (
            Path(__file__).resolve().parents[3]
            / "app" / "domains" / "creation" / "a1" / "interviewer.py"
        ).read_text(encoding="utf-8")
        assert src.count("你是TRPG世界观设计的访谈引导者") == 3
