"""批C红测②：协作讨论通道（讨论镜像，拍2-18）。

用户在虚构内发问（对会话内已建立设定提 why / 推演）或自言推演时，
引擎以「镜子式」回应一轮：不复述填空、**不吸收 fills**（讨论轮后
answers 零变化）+ 桥接回当前题。

- **2 轮帽**：连续 3 轮虚构内追问 → 第 3 轮确定性桥回当前题（D24 turns 先例）。
- 出口枚举四件：帽满桥回 / 话题离开 / 直选打断 / 重锚打断。
- 埋点：mirror_triggered 事件 → data/inspiration_log.jsonl（fail-silent）。
- 镜像对话态 additive 字段镜像 knowledge_thread_*（mirror_thread_active /
  mirror_thread_turns）。

红测锁契约不锁实现；意图键 additive（delivery 键先例）。
"""
from __future__ import annotations

import json

import pytest

import app.domains.creation.a1.inspiration_log as inspiration_log
from app.domains.creation.a1.guide_engine import A1Session, handle_message
from app.domains.creation.a1.inspiration_log import emit_event
from app.domains.creation.a1.interviewer import (
    InterviewFill,
    InterviewResult,
    RealLLMInterviewer,
)


class _FakeProvider:
    def __init__(self, responses):
        self._responses = list(responses)

    async def chat_json(self, messages):  # noqa: ARG002
        return self._responses.pop(0)


class _MirrorStub:
    """handle_message 级 stub：mirror 意图旗标 + 可选 fills（须被忽略）。"""

    def __init__(self, *, mirror: bool = True, fills=None,
                 guidance_reply: str = "这个问题有意思——回到刚才：主角的职业是什么？"):
        self.mirror = mirror
        self.fills = fills or []
        self.guidance_reply = guidance_reply

    def interview(self, session, text):  # noqa: ARG002
        return InterviewResult.model_construct(
            fills=list(self.fills),
            guidance_reply=self.guidance_reply,
            mirror=self.mirror,
        )

    def suggest_examples(self, session, module_id, subfield_id):  # noqa: ARG002
        return []


def _session() -> A1Session:
    s = A1Session(
        session_id="s_mirror",
        user_id="u1",
        current_module="IP定位",
        current_subfield="name",
    )
    # 会话已建立设定（镜像锚）：虚构内 why 的问题对象
    s.answers["IP定位.concept"] = "师姐的剑挂在城门口"
    return s


@pytest.fixture
def tmp_log_path(tmp_path, monkeypatch):
    log_path = tmp_path / "inspiration_log.jsonl"
    monkeypatch.setattr(inspiration_log, "LOG_PATH", log_path)
    return log_path


# ---------------------------------------------------------------------------
# 进入判定：虚构内发问（解析侧 additive 键）
# ---------------------------------------------------------------------------


def test_in_fiction_why_parses_mirror_intent():
    raw = {
        "fills": [],
        "guidance_reply": "你是在推演师姐的动机吗？回到刚才的问题。",
        "mirror": True,
    }
    result = RealLLMInterviewer(_FakeProvider([raw])).interview(
        _session(), "师姐为什么把剑挂在城门口？"
    )
    assert result.mirror is True


def test_absent_mirror_key_defaults_false():
    raw = {
        "fills": [
            {"module": "IP定位", "subfield": "name", "value": "公司职员"}
        ],
        "guidance_reply": "已记录。",
    }
    result = RealLLMInterviewer(_FakeProvider([raw])).interview(
        _session(), "主角是公司职员"
    )
    assert result.mirror is False  # 普通答题轮：键缺省 False（delivery 先例）


# ---------------------------------------------------------------------------
# 行为：镜子式一轮——不吸收 fills + 桥接回当前题
# ---------------------------------------------------------------------------


def test_mirror_turn_does_not_absorb_fills():
    s = _session()
    snapshot = dict(s.answers)
    iv = _MirrorStub(
        fills=[InterviewFill(module="IP定位", subfield="name", value="公司职员")],
    )
    handle_message(s, "她为什么一定要把剑挂在那里？", iv)
    assert s.answers == snapshot  # 讨论轮 answers 零变化（不落任何槽）


def test_mirror_turn_bridges_back_to_current_question(monkeypatch):
    import app.domains.creation.a1.inspiration_log as insp

    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        insp, "emit_event",
        lambda event, session, **fields: events.append((event, fields)),
    )
    s = _session()
    out = handle_message(s, "她为什么一定要把剑挂在那里？", _MirrorStub())
    assert any(name == "mirror_triggered" for name, _f in events)  # 引擎侧路由
    assert s.current_module == "IP定位"  # 桥接：当前题未跳走
    assert s.current_subfield == "name"
    assert "主角" in out["reply"] or "职业" in out["reply"]  # 桥接句含当前问


def test_mirror_turn_tracks_thread_state():
    s = _session()
    handle_message(s, "她为什么把剑挂在那里？", _MirrorStub())
    assert s.mirror_thread_active is True  # additive 会话字段（knowledge 先例）
    assert s.mirror_thread_turns == 1


# ---------------------------------------------------------------------------
# 2 轮帽：第 3 轮虚构内追问 → 确定性桥回当前题（D24 turns 先例）
# ---------------------------------------------------------------------------


def test_three_consecutive_fiction_whys_hit_cap_bridge():
    s = _session()
    handle_message(s, "她为什么把剑挂在那里？", _MirrorStub())
    handle_message(s, "城门口的人为什么会允许这件事？", _MirrorStub())
    assert s.mirror_thread_turns == 2  # 帽内
    out3 = handle_message(s, "那她后来为什么不取下来？", _MirrorStub())
    assert s.mirror_thread_turns == 0  # 第 3 轮：帽满 → 桥回复位
    assert s.mirror_thread_active is False
    assert s.current_subfield == "name"  # 确定性桥回当前题
    assert "主角" in out3["reply"] or "职业" in out3["reply"]


# ---------------------------------------------------------------------------
# 出口枚举四件
# ---------------------------------------------------------------------------


def _drive_to_mirror_thread(s: A1Session) -> None:
    handle_message(s, "她为什么把剑挂在那里？", _MirrorStub())
    handle_message(s, "城门口的人为什么会允许？", _MirrorStub())


def test_exit_1_cap_full_bridge_back():
    s = _session()
    _drive_to_mirror_thread(s)
    handle_message(s, "她后来为什么没有后悔？", _MirrorStub())
    assert s.mirror_thread_active is False  # 出口①：帽满桥回


def test_exit_2_topic_leaves_back_to_creation():
    s = _session()
    _drive_to_mirror_thread(s)
    handle_message(
        s,
        "好了，主角职业就写公司职员",
        _MirrorStub(
            mirror=False,
            fills=[InterviewFill(module="IP定位", subfield="name",
                                 value="公司职员")],
        ),
    )
    assert s.answers.get("IP定位.name") == "公司职员"  # 答案照常落槽
    assert s.mirror_thread_active is False  # 出口②：话题离开
    assert s.mirror_thread_turns == 0


def test_exit_3_direct_pick_interrupts_mirror():
    s = _session()
    _drive_to_mirror_thread(s)
    s.current_options = ["公司职员", "医生", "教师"]
    handle_message(s, "2", _MirrorStub())
    assert s.answers.get("IP定位.name") == "医生"  # 直选照常消费
    assert s.mirror_thread_active is False  # 出口③：直选打断
    assert s.mirror_thread_turns == 0


def test_exit_4_reanchor_interrupts_mirror(monkeypatch):
    import app.domains.creation.a1.inspiration_log as insp

    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        insp, "emit_event",
        lambda event, session, **fields: events.append((event, fields)),
    )
    s = _session()
    _drive_to_mirror_thread(s)
    handle_message(s, "梳理一下", _MirrorStub(mirror=False))
    assert s.mirror_thread_active is False  # 出口④：重锚打断
    assert s.mirror_thread_turns == 0
    assert any(name == "reanchor_triggered" for name, _f in events)


# ---------------------------------------------------------------------------
# 埋点：mirror_triggered 事件 jsonl（fail-silent）
# ---------------------------------------------------------------------------


def test_mirror_triggered_event_written_to_jsonl(tmp_log_path):
    s = _session()
    handle_message(s, "她为什么把剑挂在那里？", _MirrorStub())
    if not tmp_log_path.exists():
        raise AssertionError("mirror_triggered 事件未落 jsonl（引擎未触发埋点）")
    lines = tmp_log_path.read_text(encoding="utf-8").strip().splitlines()
    records = [json.loads(ln) for ln in lines]
    mirror_events = [r for r in records if r["event"] == "mirror_triggered"]
    assert len(mirror_events) == 1
    assert mirror_events[0]["session_id"] == "s_mirror"


def test_telemetry_failure_is_silent_for_mirror(tmp_path, monkeypatch):
    blocker = tmp_path / "blocker"
    blocker.write_text("not a dir", encoding="utf-8")  # 锚测缺陷修正：照
    # test_inspiration_log.py 先例把 blocker 造成文件，mkdir 才会失败
    # （否则 parents=True 会建出目录、写入成功，"故障"永不发生）。
    bad_path = blocker / "sub" / "inspiration_log.jsonl"
    monkeypatch.setattr(inspiration_log, "LOG_PATH", bad_path)
    s = _session()
    # 写失败不抛（fail-silent：inspiration_log.emit_event 既有契约）
    out = handle_message(s, "她为什么把剑挂在那里？", _MirrorStub())
    assert "reply" in out
    assert not bad_path.exists()


def test_emit_event_helper_remains_the_append_function():
    """埋点 append 函数 = inspiration_log.emit_event（T7 复用，不许另起炉灶）。"""
    import inspect

    src = inspect.getsource(emit_event)
    assert "except Exception" in src  # fail-silent 契约在位
