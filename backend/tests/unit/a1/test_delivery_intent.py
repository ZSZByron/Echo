"""T10（波次一 1.3）：规则 6 投递改写——接住-归位-回题 + 投递意图分类。

零 schema 变更红线（一期边界唯一权威：投递式机制设计 §5 施工序一期）：
- 解析侧 additive 扩展（D24 knowledge_request 键先例）——InterviewResult
  新增 delivery 布尔键；A1Session/store/持久化结构一字节不动。
- 通道优先级：直选（当前题 options）> 知识求助（6.5）> 投递判定 > 答当前。
- 休眠话术（灵感入架 / 半填补问 / 追加循环）不进代码——只存治理文档。

FakeProvider / session stub 形状照 test_knowledge_request.py 既有约定。
"""
from __future__ import annotations

import types

from app.domains.creation.a1.guide_engine import A1Session, handle_message
from app.domains.creation.a1.interviewer import (
    InterviewFill,
    InterviewResult,
    RealLLMInterviewer,
)


class _FakeProvider:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    async def chat_json(self, messages):
        self.calls.append(messages)
        return self._responses.pop(0)


def _session() -> types.SimpleNamespace:
    return types.SimpleNamespace(
        session_id="s_d",
        current_module="力量体系",
        current_subfield="acquire",
        answers={},
        creator_primary="plot",
    )


def _prompt_of(provider: _FakeProvider) -> str:
    return provider.calls[0][0]["content"]


# ---------------------------------------------------------------------------
# 解析侧：投递意图 additive 键（fills 落非当前题的树上既有槽）
# ---------------------------------------------------------------------------


def test_delivery_intent_parses_off_topic_fill():
    raw = {
        "fills": [
            {"module": "IP定位", "subfield": "concept", "value": "师姐的剑挂在城门口"}
        ],
        "guidance_reply": (
            "好画面——我记进【支线卡·结局】了（他放下这段过往）。"
            "回到刚才：这个世界的人怎么获得力量？"
            "刚才那笔记错了地方？说一声，我挪走。"
        ),
        "delivery": True,
    }
    result = RealLLMInterviewer(_FakeProvider([raw])).interview(
        _session(), "对了！主角最后把师姐的剑挂在城门口了。"
    )
    assert result.delivery is True                 # 投递意图键被解析
    assert len(result.fills) == 1                  # 归位：落树上既有槽
    assert result.fills[0].module == "IP定位"
    assert "获得力量" in result.guidance_reply      # 回题句含当前问关键词


def test_delivery_defaults_false_when_absent():
    raw = {
        "fills": [
            {"module": "力量体系", "subfield": "acquire", "value": "古神遗骸"}
        ],
        "guidance_reply": "已记录。",
    }
    result = RealLLMInterviewer(_FakeProvider([raw])).interview(_session(), "力量来自古神遗骸")
    assert result.delivery is False                # 普通答题轮：键缺省 False


def test_delivery_no_home_fills_empty_no_crash():
    # 无近槽温和处理（Edge）：LLM 置 delivery=true 但无槽可落 → 温和回题，
    # 解析不崩、不拒收、不产生 fills（灵感架通道休眠，一期不接）。
    raw = {
        "fills": [],
        "guidance_reply": "这个画面先记下了。回到刚才：这个世界的人怎么获得力量？",
        "delivery": True,
    }
    result = RealLLMInterviewer(_FakeProvider([raw])).interview(
        _session(), "我总想象一个画面：满天都是断掉的剑。"
    )
    assert result.delivery is True
    assert result.fills == []
    assert "获得力量" in result.guidance_reply      # 温和回题而非拒绝


# ---------------------------------------------------------------------------
# 通道优先级：直选 > 知识求助（6.5）> 投递判定 > 答当前
# ---------------------------------------------------------------------------


class _CountingStub:
    """handle_message 级 stub：记录 interview 是否被调用。"""

    def __init__(self):
        self.calls = 0

    def interview(self, session, text):  # noqa: ARG002
        self.calls += 1
        # 即使 LLM 想投递，直选也必须在进 interview 之前被消费。
        return InterviewResult(
            fills=[InterviewFill(module="IP定位", subfield="name", value="误填")],
            guidance_reply="投递？",
            delivery=True,
        )

    def suggest_examples(self, session, module_id, subfield_id):  # noqa: ARG002
        return []


def test_direct_pick_not_intercepted_by_delivery():
    s = A1Session(
        session_id="s1", user_id="u1",
        current_module="IP定位", current_subfield="name",
    )
    s.current_options = ["公司职员", "医生", "教师"]
    iv = _CountingStub()
    handle_message(s, "3", iv)
    assert s.answers["IP定位.name"] == "教师"       # "3" 直选正常落当前题
    assert iv.calls == 0                            # 投递判定不拦截直选


def test_knowledge_request_outranks_delivery():
    first = {"fills": [], "guidance_reply": "", "knowledge_request": True,
             "search_query": "腕带 作用", "user_confused": False,
             "delivery": True}
    second = {"fills": [], "guidance_reply": "腕带是身份识别…",
              "knowledge_request": False, "delivery": False}
    prov = _FakeProvider([first, second])
    iv = RealLLMInterviewer(prov)
    import app.ai.web_search as ws

    original = ws.search_sync
    try:
        ws.search_sync = lambda _q: "- 腕带：住院病人身份识别"
        result = iv.interview(_session(), "腕带代表什么？顺便主角结局是把剑挂城门口")
    finally:
        ws.search_sync = original
    assert len(prov.calls) == 2                     # 6.5 命中：二段式发生
    assert result.knowledge_used is True


# ---------------------------------------------------------------------------
# 零 schema 变更锁：A1Session 字段集与 T9 后完全一致
# ---------------------------------------------------------------------------

_T9_SESSION_FIELDS = frozenset(
    {
        "answer_clips", "answers", "auto_merge_log", "character_sketch",
        "closing_answers", "closing_settled", "closing_step",
        "creator_confidence", "creator_primary", "creator_profile_source",
        "creator_secondary", "current_module", "current_options",
        "current_subfield", "deflect_counts", "draft_alpha", "field_sources",
        "impulse_coords", "invited_modules", "ip_code",
        "knowledge_thread_active", "knowledge_thread_turns", "merge_counts",
        "merge_undo", "message_rounds", "open_question_archive",
        "options_key", "pending_alignments", "pending_proposals",
        "pending_suggestions", "phase", "prefill_fields", "recipe_id",
        "recipe_modules", "reroll_streak", "resume_later", "seed_description",
        "seed_genre", "seed_name", "session_id", "stall_count",
        "stall_subfield", "user_id",
    }
)


def test_a1session_schema_unchanged_since_t9():
    assert frozenset(A1Session.model_fields.keys()) == _T9_SESSION_FIELDS


def test_no_dormant_state_structures():
    # 一期红线：不预留 material_pool/半填任何数据结构（连影子都不留）。
    assert "material_pool" not in A1Session.model_fields


# ---------------------------------------------------------------------------
# prompt 侧：规则 6 改写 + 8.6 疑因(b) 核正 + 6.5/7 零 diff 锁 + 休眠隔离
# ---------------------------------------------------------------------------


def _build_prompt() -> str:
    prov = _FakeProvider([{"fills": [], "guidance_reply": "ok"}])
    RealLLMInterviewer(prov).interview(_session(), "你好")
    return _prompt_of(prov)


def test_rule6_contains_catch_home_return():
    prompt = _build_prompt()
    # 接住-归位-回题 三步话术（⑨稿 §3 句式表，模板变量化）
    assert "接住" in prompt
    assert "归位" in prompt
    assert "回题" in prompt
    assert "【槽位名】" in prompt                    # 落位确认模板变量
    assert "【当前问题】" in prompt
    assert "我挪走" in prompt                        # 撤销护栏（D23 披露沿用）
    # 绝不指责跑题：负向断言
    assert "跑题" not in prompt


def test_rule86_examples_bound_to_current_question():
    prompt = _build_prompt()
    # T3 疑因(b) 核正：示例序号只对当前题 options 有效
    assert "只对当前题" in prompt or "只服务于【当前问题】" in prompt


def test_rule65_and_rule7_byte_identical():
    prompt = _build_prompt()
    lines = prompt.split("\n")

    def _line(prefix: str) -> str:
        hits = [ln for ln in lines if ln.startswith(prefix)]
        assert len(hits) == 1, f"expected exactly one {prefix!r} line"
        return hits[0]

    # 冻结 T9 后的 6.5/7 原文（diff 零行红线的测试侧锁——prompt 中各为
    # 一条隐式拼接单行）
    assert _line("6.5 知识求助判定") == (
        "6.5 知识求助判定（优先于规则 6 的提问分支）：如果用户向你提出"
        "领域事实性/知识性问题——期待你提供资料来帮他写故事，而不是在"
        "回答当前问题（如「精神病院里腕带代表什么」「当前最受欢迎的"
        "现代小说女性主角职业是什么」）：置 knowledge_request=true，"
        "并给出一个用于联网检索的中文 search_query（概括用户想知道的"
        "知识点）。此时 fills 必须留空、user_confused=false——严禁把"
        "用户的提问内容当作任何字段的答案记录。"
    )
    assert _line("7. 用户困惑判定") == (
        "7. 用户困惑判定：如果用户表示不理解当前问题/概念/术语，或明确说"
        "「不知道」「没想法」「不懂」，置 user_confused=true 并给出一个用于联网"
        "检索的中文 search_query（针对用户不理解的概念）。此时 fills 留空，"
        "不要追问用户，等系统提供参考资料后再引导。"
    )


def test_dormant_phrases_absent_from_code():
    # 休眠话术隔离：灵感入架 / 半填补问 / 追加循环 4 式不进 prompt。
    prompt = _build_prompt()
    for phrase in ("灵感架", "半填", "追加循环", "安家，还是先留着"):
        assert phrase not in prompt
