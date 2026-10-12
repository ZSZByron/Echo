"""批C红测①：六通道优先级全序矩阵（Metis CRITICAL#6 落点）。

全序契约（权威：投递式机制设计 §① 五通道 + 批C 增补两通道）：

    直选 > 重锚（「梳理一下」显式元命令）> 规则 6.5 知识（D24 锁定位）
        > 讨论镜像（虚构内发问）> 投递 > 答当前

扩展波次一 test_channel_coexistence_matrix.py（四通道共存矩阵）至
六通道两两优先组合（15 对，表驱动：给定会话状态 X + 用户输入 Y → 胜出通道 Z）。

纪律：
- 红测锁契约不锁实现：mirror/reanchor 意图键按 additive 键发现式断言
  （delivery 键先例：interviewer.py InterviewResult / 波次一 T10）。
- 锚定既有事实的行（四通道之间的既有序）允许 GREEN。
- 不要求规则 6.5/7 本体、user_confused 语义、D24 四出口变化（负向保护除外）。
"""
from __future__ import annotations

import pathlib

import pytest

import app.domains.creation.a1.inspiration_log as inspiration_log
import app.domains.creation.a1.interviewer as interviewer_mod
from app.domains.creation.a1.guide_engine import A1Session, handle_message
from app.domains.creation.a1.interviewer import (
    InterviewFill,
    InterviewResult,
    RealLLMInterviewer,
)

# ---------------------------------------------------------------------------
# 通道命名（描述性，不复用项目字母系列）
# ---------------------------------------------------------------------------

CHANNEL_DIRECT = "direct_pick"
CHANNEL_REANCHOR = "reanchor"
CHANNEL_KNOWLEDGE = "knowledge_rule65"
CHANNEL_MIRROR = "discussion_mirror"
CHANNEL_DELIVERY = "delivery"
CHANNEL_ANSWER_CURRENT = "answer_current"

REANCHOR_TRIGGER = "梳理一下"
KNOWLEDGE_SUFFIX = "（已联网查证）"

_PRE_BATCHC_RESULT_FIELDS = frozenset(
    {
        "deflect", "divergent_question", "examples", "fills",
        "guidance_reply", "innovative_category", "is_innovative",
        "knowledge_used", "open_question_answered", "proposals",
        "story_material", "worldview_invites", "delivery",
    }
)


# ---------------------------------------------------------------------------
# stub / 工具（形状照 test_channel_coexistence_matrix.py 既有约定）
# ---------------------------------------------------------------------------


class _SixChannelStub:
    """handle_message 级 stub：可控 mirror / reanchor / delivery / knowledge。

    additive 意图键经 model_construct 注入——解析侧落地前
    引擎侧按 getattr(result, key, False) 发现式消费（T7 接线点）。
    """

    def __init__(
        self,
        *,
        knowledge_used: bool = False,
        delivery: bool = False,
        mirror: bool = False,
        reanchor: bool = False,
        fills: list[InterviewFill] | None = None,
        guidance_reply: str = "好的，继续",
    ):
        self.knowledge_used = knowledge_used
        self.delivery = delivery
        self.mirror = mirror
        self.reanchor = reanchor
        self.fills = fills or []
        self.guidance_reply = guidance_reply
        self.calls = 0

    def interview(self, session, text):  # noqa: ARG002
        self.calls += 1
        return InterviewResult.model_construct(
            fills=list(self.fills),
            guidance_reply=self.guidance_reply,
            knowledge_used=self.knowledge_used,
            delivery=self.delivery,
            mirror=self.mirror,
            reanchor=self.reanchor,
        )

    def suggest_examples(self, session, module_id, subfield_id):  # noqa: ARG002
        return []


def _capture_inspiration_events(monkeypatch: pytest.MonkeyPatch) -> list:
    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        inspiration_log,
        "emit_event",
        lambda event, session, **fields: events.append((event, fields)),
    )
    return events


def _event_names(events: list) -> list[str]:
    return [name for name, _fields in events]


def _session(**kw) -> A1Session:
    base = dict(
        session_id="s_matrix",
        user_id="u1",
        current_module="IP定位",
        current_subfield="name",
    )
    base.update(kw)
    return A1Session(**base)


def _options_session() -> A1Session:
    s = _session()
    s.current_options = ["公司职员", "医生", "教师"]
    return s


class _FakeProvider:
    def __init__(self, responses):
        self._responses = list(responses)

    async def chat_json(self, messages):  # noqa: ARG002
        return self._responses.pop(0)


# ---------------------------------------------------------------------------
# 意图分类 additive 键锁（mirror / reanchor，delivery 先例）
# ---------------------------------------------------------------------------


def test_interviewresult_keys_additive_mirror_reanchor_only():
    fields = frozenset(interviewer_mod.InterviewResult.model_fields.keys())
    assert fields == _PRE_BATCHC_RESULT_FIELDS | {"mirror", "reanchor"}


def test_mirror_intent_parsed_from_raw():
    raw = {
        "fills": [],
        "guidance_reply": "这个问题有意思——你是在推演师姐为什么这么做吗？"
        "回到刚才：主角的职业是什么？",
        "mirror": True,
    }
    result = RealLLMInterviewer(_FakeProvider([raw])).interview(
        _session(), "师姐为什么要把剑挂在城门口？"
    )
    assert result.mirror is True


def test_real_world_fact_routes_knowledge_not_mirror():
    raw = {
        "fills": [],
        "guidance_reply": "腕带是住院病人的身份识别",
        "knowledge_request": True,
        "search_query": "精神病院 腕带 作用",
        "mirror": False,
    }
    result = RealLLMInterviewer(_FakeProvider([raw])).interview(
        _session(), "现实里精神病院的腕带代表什么？"
    )
    assert result.knowledge_request is True
    assert result.mirror is False


def test_reanchor_intent_parsed_from_raw():
    raw = {
        "fills": [],
        "guidance_reply": "好，我们梳理一下线头。",
        "reanchor": True,
    }
    result = RealLLMInterviewer(_FakeProvider([raw])).interview(
        _session(), REANCHOR_TRIGGER
    )
    assert result.reanchor is True


# ---------------------------------------------------------------------------
# 15 对两两优先组合（表驱动）
# ---------------------------------------------------------------------------


def _run_direct_beats_reanchor(monkeypatch):
    _capture_inspiration_events(monkeypatch)
    s = _options_session()
    iv = _SixChannelStub(reanchor=True)
    handle_message(s, "2，顺便梳理一下", iv)
    assert s.answers.get("IP定位.name") == "医生"  # 直选落位
    assert iv.calls == 0  # 直选在进 interview 前消费


def _run_direct_beats_knowledge(monkeypatch):
    _capture_inspiration_events(monkeypatch)
    s = _options_session(knowledge_thread_active=True, knowledge_thread_turns=1)
    handle_message(s, "1", _SixChannelStub(knowledge_used=True))
    assert s.answers.get("IP定位.name") == "公司职员"
    assert s.knowledge_thread_active is False  # D24 退出①：直选 = 回到创作


def _run_direct_beats_mirror(monkeypatch):
    _capture_inspiration_events(monkeypatch)
    s = _options_session()
    iv = _SixChannelStub(mirror=True)
    handle_message(s, "3", iv)
    assert s.answers.get("IP定位.name") == "教师"
    assert iv.calls == 0  # 直选不被镜像判定拦截


def _run_direct_beats_delivery(monkeypatch):
    _capture_inspiration_events(monkeypatch)
    s = _options_session()
    iv = _SixChannelStub(
        delivery=True,
        fills=[InterviewFill(module="IP定位", subfield="concept",
                             value="师姐的剑挂在城门口")],
    )
    handle_message(s, "2", iv)
    assert s.answers.get("IP定位.name") == "医生"
    assert iv.calls == 0  # 直选不被投递判定拦截（波次一先例）


def _run_direct_beats_answer_current(monkeypatch):
    _capture_inspiration_events(monkeypatch)
    s = _options_session()
    handle_message(s, "1", _SixChannelStub())
    assert s.answers.get("IP定位.name") == "公司职员"


def _run_reanchor_beats_knowledge(monkeypatch):
    events = _capture_inspiration_events(monkeypatch)
    s = _session(knowledge_thread_active=True, knowledge_thread_turns=2)
    handle_message(s, REANCHOR_TRIGGER, _SixChannelStub(knowledge_used=True))
    assert CHANNEL_REANCHOR in _event_names(events)  # 重锚胜出
    assert s.knowledge_thread_active is False  # 重锚打断知识对话态
    assert s.knowledge_thread_turns == 0


def _run_reanchor_beats_mirror(monkeypatch):
    events = _capture_inspiration_events(monkeypatch)
    s = _session(mirror_thread_turns=1)
    handle_message(s, REANCHOR_TRIGGER, _SixChannelStub(mirror=True))
    assert CHANNEL_REANCHOR in _event_names(events)
    assert CHANNEL_MIRROR not in _event_names(events)
    assert s.mirror_thread_turns == 0  # 重锚打断讨论态（mirror 复位）


def _run_reanchor_beats_delivery(monkeypatch):
    events = _capture_inspiration_events(monkeypatch)
    s = _session()
    handle_message(
        s,
        REANCHOR_TRIGGER,
        _SixChannelStub(
            delivery=True,
            fills=[InterviewFill(module="IP定位", subfield="concept",
                                 value="师姐的剑挂在城门口")],
        ),
    )
    assert CHANNEL_REANCHOR in _event_names(events)  # 非"答当前"/非投递
    assert s.answers == {}  # 重锚轮不落槽


def _run_reanchor_beats_answer_current(monkeypatch):
    events = _capture_inspiration_events(monkeypatch)
    s = _session()
    handle_message(
        s,
        REANCHOR_TRIGGER,
        _SixChannelStub(
            fills=[InterviewFill(module="IP定位", subfield="name",
                                 value="公司职员")],
        ),
    )
    assert CHANNEL_REANCHOR in _event_names(events)  # pending fill 也被重锚接住
    assert s.answers.get("IP定位.name") != "公司职员"  # 不作答当前


def _run_knowledge_beats_mirror(monkeypatch):
    _capture_inspiration_events(monkeypatch)
    s = _session(knowledge_thread_active=True, knowledge_thread_turns=1)
    iv = _SixChannelStub(knowledge_used=True, mirror=True)
    out = handle_message(s, "腕带代表的到底是什么意思？", iv)
    assert out["reply"].endswith(KNOWLEDGE_SUFFIX)  # 6.5 知识胜出
    assert s.knowledge_thread_active is True


def _run_knowledge_beats_delivery(monkeypatch):
    _capture_inspiration_events(monkeypatch)
    s = _session(knowledge_thread_active=True, knowledge_thread_turns=1)
    iv = _SixChannelStub(
        delivery=True,
        knowledge_used=True,
        fills=[InterviewFill(module="IP定位", subfield="concept",
                             value="师姐的剑挂在城门口")],
    )
    handle_message(s, "对了！结局是剑挂城门口", iv)
    assert s.answers == {}  # 知识态冻结闸照丢（投递不是豁免牌）


def _run_knowledge_beats_answer_current(monkeypatch):
    _capture_inspiration_events(monkeypatch)
    s = _session(knowledge_thread_active=True, knowledge_thread_turns=1)
    handle_message(
        s,
        "主角职业就写公司职员",
        _SixChannelStub(
            fills=[InterviewFill(module="IP定位", subfield="name",
                                 value="公司职员")],
        ),
    )
    assert s.answers == {}  # 知识态内答题冻结（矩阵①先例）


def _run_mirror_beats_delivery(monkeypatch):
    events = _capture_inspiration_events(monkeypatch)
    s = _session()
    s.answers["IP定位.concept"] = "师姐的剑挂在城门口"  # 会话已建立设定 = 镜像锚
    snapshot = dict(s.answers)
    iv = _SixChannelStub(
        mirror=True,
        delivery=True,
        fills=[InterviewFill(module="IP定位", subfield="concept",
                             value="师姐的剑挂在城门口")],
    )
    handle_message(s, "她为什么一定要把剑挂在那里？", iv)
    assert CHANNEL_MIRROR in _event_names(events)  # 虚构内 why → 镜像通道
    assert s.answers == snapshot  # 不吸收 fills（讨论轮 answers 零变化）


def _run_mirror_beats_answer_current(monkeypatch):
    events = _capture_inspiration_events(monkeypatch)
    s = _session()
    s.answers["力量体系.acquire"] = "古神遗骸"  # 会话已建立设定
    snapshot = dict(s.answers)
    iv = _SixChannelStub(
        mirror=True,
        fills=[InterviewFill(module="IP定位", subfield="name",
                             value="公司职员")],
    )
    handle_message(s, "古神遗骸为什么会给人力量？我在推演一下", iv)
    assert CHANNEL_MIRROR in _event_names(events)
    assert s.answers == snapshot  # 镜像轮不落当前题


def _run_delivery_beats_answer_current(monkeypatch):
    _capture_inspiration_events(monkeypatch)
    s = _session()
    iv = _SixChannelStub(
        delivery=True,
        fills=[InterviewFill(module="IP定位", subfield="concept",
                             value="师姐的剑挂在城门口")],
    )
    handle_message(s, "对了！结局画面是剑挂城门口", iv)
    assert s.answers.get("IP定位.concept") == "师姐的剑挂在城门口"  # 归位非当前题
    assert "IP定位.name" not in s.answers  # 当前题未被杂音占用


_MATRIX_ROWS = [
    (f"{CHANNEL_DIRECT}_beats_{CHANNEL_REANCHOR}", _run_direct_beats_reanchor),
    (f"{CHANNEL_DIRECT}_beats_{CHANNEL_KNOWLEDGE}", _run_direct_beats_knowledge),
    (f"{CHANNEL_DIRECT}_beats_{CHANNEL_MIRROR}", _run_direct_beats_mirror),
    (f"{CHANNEL_DIRECT}_beats_{CHANNEL_DELIVERY}", _run_direct_beats_delivery),
    (f"{CHANNEL_DIRECT}_beats_{CHANNEL_ANSWER_CURRENT}",
     _run_direct_beats_answer_current),
    (f"{CHANNEL_REANCHOR}_beats_{CHANNEL_KNOWLEDGE}",
     _run_reanchor_beats_knowledge),
    (f"{CHANNEL_REANCHOR}_beats_{CHANNEL_MIRROR}",
     _run_reanchor_beats_mirror),
    (f"{CHANNEL_REANCHOR}_beats_{CHANNEL_DELIVERY}",
     _run_reanchor_beats_delivery),
    (f"{CHANNEL_REANCHOR}_beats_{CHANNEL_ANSWER_CURRENT}",
     _run_reanchor_beats_answer_current),
    (f"{CHANNEL_KNOWLEDGE}_beats_{CHANNEL_MIRROR}",
     _run_knowledge_beats_mirror),
    (f"{CHANNEL_KNOWLEDGE}_beats_{CHANNEL_DELIVERY}",
     _run_knowledge_beats_delivery),
    (f"{CHANNEL_KNOWLEDGE}_beats_{CHANNEL_ANSWER_CURRENT}",
     _run_knowledge_beats_answer_current),
    (f"{CHANNEL_MIRROR}_beats_{CHANNEL_DELIVERY}",
     _run_mirror_beats_delivery),
    (f"{CHANNEL_MIRROR}_beats_{CHANNEL_ANSWER_CURRENT}",
     _run_mirror_beats_answer_current),
    (f"{CHANNEL_DELIVERY}_beats_{CHANNEL_ANSWER_CURRENT}",
     _run_delivery_beats_answer_current),
]

_MATRIX_NAMES = [name for name, _fn in _MATRIX_ROWS]
_MATRIX_FNS = dict(_MATRIX_ROWS)


@pytest.mark.parametrize("scenario", _MATRIX_NAMES)
def test_channel_priority_pairwise(scenario, monkeypatch):
    """六通道两两优先：给定状态 X + 输入 Y → 胜出通道 Z。"""
    _MATRIX_FNS[scenario](monkeypatch)


# ---------------------------------------------------------------------------
# 关键互踩场景（矩阵行之外的专用断言）
# ---------------------------------------------------------------------------


def test_pending_fill_then_reanchor_wins_not_answer_current(monkeypatch):
    """pending fill 时说「梳理一下」→ 重锚胜出（非答当前）。"""
    events = _capture_inspiration_events(monkeypatch)
    s = _session()
    # 幕①：正常答题建立进度
    handle_message(
        s, "主角是公司职员",
        _SixChannelStub(
            fills=[InterviewFill(module="IP定位", subfield="name",
                                 value="公司职员")],
        ),
    )
    assert "IP定位.name" in s.answers
    # 幕②：说「梳理一下」——pending 状态被摊开，不作答
    handle_message(s, REANCHOR_TRIGGER, _SixChannelStub())
    assert CHANNEL_REANCHOR in _event_names(events)


def test_reanchor_interrupts_knowledge_thread_and_resets(monkeypatch):
    """知识对话态中说「梳理一下」→ 重锚打断知识态并复位。"""
    events = _capture_inspiration_events(monkeypatch)
    s = _session()
    handle_message(
        s, "腕带代表什么意思？",
        _SixChannelStub(knowledge_used=True,
                        guidance_reply="腕带是住院病人的身份识别"),
    )
    assert s.knowledge_thread_active is True
    handle_message(s, REANCHOR_TRIGGER, _SixChannelStub())
    assert CHANNEL_REANCHOR in _event_names(events)
    assert s.knowledge_thread_active is False
    assert s.knowledge_thread_turns == 0


# ---------------------------------------------------------------------------
# 字节锁负向保护（既有测试引用）
# ---------------------------------------------------------------------------


def test_rule65_rule7_byte_identical_guard_still_referenced():
    """规则 6.5/7 本体字节锁既有测试必须存活（红测不得要求其变）。"""
    from tests.unit.a1.test_delivery_intent import (  # noqa: F401
        test_rule65_and_rule7_byte_identical,
    )


# ---------------------------------------------------------------------------
# 附：话术包红测
# ⑨稿 = docs/plans/2026-10-10-新结构引导话术设计.md（§1 动态问句模板 26、
# §2 L3 追问 57、Q16 支线卡、「记下了」过度承诺行修复清单）
# ---------------------------------------------------------------------------

_TALKPACK_DOC = (
    str(pathlib.Path(__file__).resolve().parents[4]
        / "docs/plans/2026-10-10-新结构引导话术设计.md")
)
_DYNAMIC_TEMPLATE_ATTRS = (
    "DYNAMIC_INVITE_TEMPLATES",
    "DYNAMIC_TEMPLATES",
    "INVITE_TEMPLATES",
    "TALK_TEMPLATES",
)
# ▶ 四情形 + ⇄ 两情形（⑨稿 §1.1；描述性命名）
_SITUATION_ARROW_FULL = "arrow_full_question"
_SITUATION_ARROW_FROM_MISSING = "arrow_from_missing"
_SITUATION_ARROW_TO_MISSING = "arrow_to_missing"
_SITUATION_ARROW_TRIGGER_MISSING = "arrow_trigger_missing"
_SITUATION_DIM_FULL = "dim_full_question"
_SITUATION_DIM_DIRECTION_MISSING = "dim_direction_missing"


def _load_dynamic_templates():
    """候选名发现式装载（AttributeError/AssertionError 红，非 ImportError）。"""
    from app.domains.creation.seed import story_modules as sm

    missing = []
    for name in _DYNAMIC_TEMPLATE_ATTRS:
        if hasattr(sm, name):
            return getattr(sm, name), name
        missing.append(name)
    raise AssertionError(
        f"26 动态问句模板数据未落库：story_modules 缺少候选常量 {missing}"
    )


def test_dynamic_question_templates_exist_26_total():
    templates, _name = _load_dynamic_templates()
    assert isinstance(templates, list)
    assert len(templates) == 26  # ▶20 + ⇄5 + 支线主问1（⑥稿 §0 咬合）


def test_dynamic_templates_cover_all_six_situations_with_slot_vars():
    templates, _name = _load_dynamic_templates()
    situations = set()
    for item in templates:
        assert isinstance(item, dict), f"模板条目须为结构化 dict：{item!r}"
        text = item.get("template") or item.get("text") or ""
        assert isinstance(text, str) and text.strip(), f"模板缺话术：{item!r}"
        assert "{" in text, f"模板须含槽位变量（{text!r}）"
        situ = item.get("situation") or item.get("case")
        assert situ, f"模板缺情形标注：{item!r}"
        situations.add(situ)
    assert {
        _SITUATION_ARROW_FULL,
        _SITUATION_ARROW_FROM_MISSING,
        _SITUATION_ARROW_TO_MISSING,
        _SITUATION_ARROW_TRIGGER_MISSING,
        _SITUATION_DIM_FULL,
        _SITUATION_DIM_DIRECTION_MISSING,
    } <= situations


def _iter_l3_nodes():
    from app.domains.creation.seed.story_modules import THREE_TIER_TREE

    for l1 in THREE_TIER_TREE:
        for l2 in l1["l2"]:
            for l3 in l2["l3"]:
                yield l3


_FOLLOWUP_KEYS = (
    "followup", "followups", "l3_followup", "prompt", "prompts", "追问",
)


def test_57_l3_followup_talkscripts_present_in_tree():
    count = 0
    for l3 in _iter_l3_nodes():
        texts = []
        for key in _FOLLOWUP_KEYS:
            value = l3.get(key)
            if isinstance(value, str) and value.strip():
                texts.append(value)
            elif isinstance(value, list):
                texts.extend(t for t in value if isinstance(t, str) and t.strip())
        if texts:
            count += 1
            for t in texts:
                assert len(t) <= 60, f"追问须短（⑨稿 §2 规范）：{t!r}"
                assert t.rstrip().endswith("？"), f"追问须口语问句形态：{t!r}"
    assert count == 57  # 57 条 L3 追问话术（⑨稿 §2）


def test_q16_branch_card_usage_shape_locked():
    """Q16 话术形态锁（批A 已落数据，此处锁使用面）。"""
    from app.domains.creation.seed.story_modules import (
        Q16_BRANCH_CARD,
        STORYLINE_ORDER,
    )

    assert Q16_BRANCH_CARD["id"] == "branch_card"
    assert "可以跳过" in Q16_BRANCH_CARD["question"]  # 问句形态可跳过
    assert Q16_BRANCH_CARD["hint"] and Q16_BRANCH_CARD["example"]
    assert len(STORYLINE_ORDER) == 16
    assert STORYLINE_ORDER[-1] == "branch_card"  # 支线卡第 16 位


def test_overpromise_line_fix_scope_only_enumerated_row():
    """「记下了：」过度承诺行修复——仅⑨稿枚举行（补 from 模板行）。

    问句不可落槽时的引擎侧话术必须诚实（如「这个我先放在灵感架上」），
    不得出现「记下了：」固定过线承诺行。
    """
    doc_lines = pathlib.Path(_TALKPACK_DOC).read_text(encoding="utf-8").splitlines()
    hits = [ln for ln in doc_lines if "记下了" in ln]
    assert len(hits) == 1, f"⑨稿「记下了」应恰一处（枚举行）：{len(hits)}"
    assert "补 from" in hits[0]


def test_engine_copy_overpromise_free_and_existing_keys_untouched():
    """负向保护：引擎既有文案零触碰——「已按示例记录」存活（L1398 语义）、
    a1 引擎模块不得引入「记下了：」固定承诺行。"""
    import pathlib

    a1_dir = (pathlib.Path(__file__).resolve().parents[3]
              / "app/domains/creation/a1")
    offenders: list[str] = []
    for py in a1_dir.glob("*.py"):
        src = py.read_text(encoding="utf-8")
        if "记下了：" in src:
            offenders.append(str(py))
    assert offenders == []
    guide_src = (a1_dir / "guide_engine.py").read_text(encoding="utf-8")
    assert "已按示例记录" in guide_src  # 既有文案键集不变


def test_delivery_no_home_reply_stays_honest(monkeypatch):
    """问句不可落槽 → 诚实话术，不出现「记下了」过线承诺。"""
    _capture_inspiration_events(monkeypatch)
    s = _session()
    out = handle_message(
        s,
        "我总想象一个画面：满天都是断掉的剑。",
        _SixChannelStub(
            delivery=True,
            fills=[],  # 无槽可落
            guidance_reply="这个我先放在灵感架上。回到刚才：主角的职业是什么？",
        ),
    )
    assert "记下了" not in out["reply"]
    assert "主角的职业" in out["reply"]  # 温和回题（波次一先例语义）
