"""T11（波次一 1.3 回归护栏）：知识求助 / 投递 / 直选 / 答当前 四通道共存矩阵。

不重复 T10 已有断言（test_delivery_intent.py：解析侧 additive、直选不被投递
拦截、6.5>投递优先级、A1Session 42 字段冻结）——本文件补齐**同会话交错**
场景：四通道在同一 session 内先后发生，互不污染。

Fake/stub 形状照 test_knowledge_request.py / test_delivery_intent.py 既有约定。
"""
from __future__ import annotations

import app.domains.creation.a1.guide_engine as guide_engine
from app.domains.creation.a1.guide_engine import A1Session, handle_message
from app.domains.creation.a1.interviewer import (
    InterviewFill,
    InterviewResult,
    RealLLMInterviewer,
)

# ---------------------------------------------------------------------------
# schema additive 锁：InterviewResult 键集 = 既有键 + delivery（1.3 唯一增量）
# 批C（2026-10-12）演进：+mirror/reanchor 两枚 additive 意图键（delivery 键
# 同款先例，T6 红测 test_interviewresult_keys_additive_mirror_reanchor_only
# 接棒闭集）——冻结集随意图键演进扩容，锁语义（零删改）不变。
# ---------------------------------------------------------------------------

_PRE_13_RESULT_FIELDS = frozenset(
    {
        "deflect", "divergent_question", "examples", "fills",
        "guidance_reply", "innovative_category", "is_innovative",
        "knowledge_used", "open_question_answered", "proposals",
        "story_material", "worldview_invites",
    }
)


def test_interviewresult_keys_additive_delivery_only():
    fields = frozenset(InterviewResult.model_fields.keys())
    assert fields == _PRE_13_RESULT_FIELDS | {
        "delivery", "mirror", "reanchor",
    }


# ---------------------------------------------------------------------------
# 矩阵①：知识通道 fills 冻结不被投递绕过——知识态下 LLM 置 delivery=true
# 携带 fills，冻结闸必须照丢（投递意图不是冻结豁免牌）。
# ---------------------------------------------------------------------------


class _Stub:
    """handle_message 级 stub：可控 delivery / knowledge_used / fills。"""

    def __init__(self, *, knowledge_used=False, delivery=False, fills=None,
                 guidance_reply="好的，继续"):
        self.knowledge_used = knowledge_used
        self.delivery = delivery
        self.fills = fills or []
        self.guidance_reply = guidance_reply

    def interview(self, session, text):  # noqa: ARG002
        return InterviewResult(
            fills=list(self.fills),
            guidance_reply=self.guidance_reply,
            knowledge_used=self.knowledge_used,
            delivery=self.delivery,
        )

    def suggest_examples(self, session, module_id, subfield_id):  # noqa: ARG002
        return []


def test_delivery_fills_still_frozen_in_knowledge_thread(monkeypatch):
    events = []
    monkeypatch.setattr(
        guide_engine, "log_event",
        lambda _sid, ev, **kw: events.append((ev, kw)),
    )
    s = A1Session(session_id="s_m1", user_id="u1",
                  knowledge_thread_active=True, knowledge_thread_turns=1)
    iv = _Stub(
        delivery=True,
        fills=[
            InterviewFill(module="IP定位", subfield="concept",
                          value="师姐的剑挂在城门口"),
        ],
        guidance_reply="记下了。回到刚才：这个世界的人怎么获得力量？",
    )
    out = handle_message(s, "对了！主角最后把师姐的剑挂在城门口了", iv)
    assert s.answers == {}                             # 冻结：投递 fills 照丢
    assert out["file_diff"] == []
    assert events and events[0][0] == "knowledge_freeze"
    assert events[0][1]["dropped"] == 1
    assert s.knowledge_thread_active is True           # 冻结轮保持知识态


# ---------------------------------------------------------------------------
# 矩阵②：投递后直选仍可用——投递轮把灵感落树上既有槽（IP定位.concept），
# 下一轮 "3" 直选当前题照常消费，两笔写入互不覆盖。
# ---------------------------------------------------------------------------


def test_direct_pick_works_after_delivery_turn():
    s = A1Session(session_id="s_m2", user_id="u1",
                  current_module="力量体系", current_subfield="acquire")
    # 轮①：投递——灵感落非当前题的树上槽
    iv1 = _Stub(
        delivery=True,
        fills=[InterviewFill(module="IP定位", subfield="concept",
                             value="师姐的剑挂在城门口")],
        guidance_reply="记进支线卡了。回到刚才：怎么获得力量？",
    )
    out1 = handle_message(s, "对了！结局画面是剑挂城门口", iv1)
    assert s.answers["IP定位.concept"] == "师姐的剑挂在城门口"
    assert "（已联网查证）" not in out1["reply"]        # 非知识轮无尾注
    # 轮②：直选——当前位置（fill 落位后引擎已推进）的 options 序号照常消费
    cur_key = f"{s.current_module}.{s.current_subfield}"
    s.current_options = ["古神遗骸", "科技改造", "天赋觉醒"]
    handle_message(s, "2", _Stub(delivery=True))       # 即使 stub 想投递
    assert s.answers[cur_key] == "科技改造"             # 直选落当前题
    assert s.answers["IP定位.concept"] == "师姐的剑挂在城门口"  # 投递产物在位


# ---------------------------------------------------------------------------
# 矩阵③：腕带病理两幕重放后投递正常——D24 两幕三行（知识→冻结→直选退出）
# 走完后，投递通道照常工作且不复燃知识态。
# ---------------------------------------------------------------------------


def test_wristband_replay_then_delivery_lands(monkeypatch):
    events = []
    monkeypatch.setattr(
        guide_engine, "log_event",
        lambda _sid, ev, **kw: events.append((ev, kw)),
    )
    s = A1Session(session_id="s_m3", user_id="u1")

    # 幕①：腕带知识提问 → 知识态置位
    out1 = handle_message(
        s, "在精神病院里腕带代表着什么意思？",
        _Stub(knowledge_used=True,
              guidance_reply="腕带是住院病人的身份识别"),
    )
    assert out1["reply"].endswith("（已联网查证）")
    assert s.knowledge_thread_active is True

    # 幕②：追问 → fills 冻结（病理核心）
    handle_message(
        s, "公司职员请具体！",
        _Stub(knowledge_used=False,
              fills=[InterviewFill(module="IP定位", subfield="name",
                                   value="公司职员")],
              guidance_reply="你想让主角的职业是哪一种？"),
    )
    assert s.answers == {}

    # 幕③：直选「1」→ 创作回归（退出①）
    s.current_options = ["公司职员", "医生", "教师"]
    handle_message(s, "1", _Stub())
    assert s.answers["IP定位.name"] == "公司职员"
    assert s.knowledge_thread_active is False

    # 幕④：投递轮——两幕病理走完后投递照常落槽、知识态不复燃
    iv4 = _Stub(
        delivery=True,
        fills=[InterviewFill(module="IP定位", subfield="concept",
                             value="师姐的剑挂在城门口")],
        guidance_reply="记下了。回到刚才的问题。",
    )
    handle_message(s, "想起来结局：师姐的剑挂在城门口", iv4)
    assert s.answers["IP定位.concept"] == "师姐的剑挂在城门口"
    assert s.knowledge_thread_active is False          # 投递≠知识态
    assert s.knowledge_thread_turns == 0
    freeze_events = [e for e in events if e[0] == "knowledge_freeze"]
    assert len(freeze_events) == 1                     # 仅幕②冻结一次
