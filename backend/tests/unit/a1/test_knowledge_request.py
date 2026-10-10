"""D24 T2: knowledge_request 触发 → 搜索注入 → 二次生成。

FakeProvider / session stub 形状照 test_interviewer_extensions.py 既有约定
（RealLLMInterviewer + SimpleNamespace session，getattr 宽松访问）。
"""
from __future__ import annotations

import types

from app.domains.creation.a1.interviewer import RealLLMInterviewer


class _FakeProvider:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    async def chat_json(self, messages):
        self.calls.append(messages)
        return self._responses.pop(0)


def _session() -> types.SimpleNamespace:
    return types.SimpleNamespace(
        session_id="s_k",
        current_module="世界本体",
        current_subfield="origin",
        answers={},
        creator_primary="plot",
    )


def test_knowledge_request_triggers_search_second_pass(monkeypatch):
    first = {"fills": [], "guidance_reply": "", "knowledge_request": True,
             "search_query": "精神病院 腕带 作用", "user_confused": False}
    second = {"fills": [], "guidance_reply": "腕带是身份识别…（选项略）",
              "knowledge_request": False, "search_query": None}
    prov = _FakeProvider([first, second])
    iv = RealLLMInterviewer(prov)
    monkeypatch.setattr("app.ai.web_search.search_sync",
                        lambda q: "- 腕带：住院病人身份识别")
    result = iv.interview(_session(), "精神病院里腕带代表什么？")
    assert len(prov.calls) == 2                      # 二段式发生
    assert "知识提问" in prov.calls[1][0]["content"]  # 注入头在场
    assert "- 腕带" in prov.calls[1][0]["content"]    # 参考资料在场
    assert result.guidance_reply.startswith("腕带")   # 二次结果生效


def test_no_flag_single_call_no_search(monkeypatch):
    first = {"fills": [], "guidance_reply": "ok", "knowledge_request": False}
    prov = _FakeProvider([first])
    monkeypatch.setattr("app.ai.web_search.search_sync", lambda q: "")
    RealLLMInterviewer(prov).interview(_session(), "你好")
    assert len(prov.calls) == 1                      # 存量行为零扰动


def test_knowledge_search_failure_degrades(monkeypatch):
    first = {"fills": [], "guidance_reply": "首版回复",
             "knowledge_request": True, "search_query": "x"}
    prov = _FakeProvider([first])
    monkeypatch.setattr("app.ai.web_search.search_sync", lambda q: "")
    result = RealLLMInterviewer(prov).interview(_session(), "查个东西")
    assert len(prov.calls) == 1                      # 降级：无二次
    assert result.guidance_reply == "首版回复"        # 首轮结果保留


# ---------------------------------------------------------------------------
# D24 T3: 知识对话态状态机（engine 级）——冻结 / 复位 / 尾注 / store 兼容。
# 构造与调用模式照 test_guide_engine.py（A1Session + handle_message）。
# ---------------------------------------------------------------------------
import app.domains.creation.a1.guide_engine as guide_engine
from app.domains.creation.a1.guide_engine import A1Session, handle_message
from app.domains.creation.a1.interviewer import InterviewFill, InterviewResult


class _EngineStub:
    """handle_message 级 stub：可控 knowledge_used / fills。"""

    def __init__(self, *, knowledge_used=False, fills=None,
                 guidance_reply="好的，继续"):
        self.knowledge_used = knowledge_used
        self.fills = fills or []
        self.guidance_reply = guidance_reply

    def interview(self, session, text):  # noqa: ARG002
        return InterviewResult(
            fills=list(self.fills),
            guidance_reply=self.guidance_reply,
            knowledge_used=self.knowledge_used,
        )

    def suggest_examples(self, session, module_id, subfield_id):  # noqa: ARG002
        return []


def test_freeze_drops_fills_in_knowledge_thread(monkeypatch):
    events = []
    monkeypatch.setattr(
        guide_engine, "log_event",
        lambda sid, ev, **kw: events.append((ev, kw)),
    )
    s = A1Session(session_id="s1", user_id="u1",
                  knowledge_thread_active=True, knowledge_thread_turns=1)
    iv = _EngineStub(
        fills=[
            InterviewFill(module="IP定位", subfield="name", value="公司职员"),
            InterviewFill(module="IP定位", subfield="concept", value="职场故事"),
        ],
        guidance_reply="补充说明",
    )
    out = handle_message(s, "公司职员请具体", iv)
    assert s.answers == {}                            # fills 全部丢弃
    assert out["file_diff"] == []
    assert events and events[0][0] == "knowledge_freeze"
    assert events[0][1]["dropped"] == 2
    assert events[0][1]["turns"] == 1
    # 冻结轮保持知识态（anti-stuck：turns 前进在 _update 内）
    assert s.knowledge_thread_active is True


def test_exit_on_number_pick():
    s = A1Session(session_id="s1", user_id="u1",
                  knowledge_thread_active=True, knowledge_thread_turns=2)
    s.current_options = ["公司职员", "医生", "教师"]
    handle_message(s, "1", _EngineStub())
    assert s.answers["IP定位.name"] == "公司职员"       # 直选正常处理
    assert s.knowledge_thread_active is False          # 退出①
    assert s.knowledge_thread_turns == 0


def test_exit_on_skip():
    s = A1Session(session_id="s1", user_id="u1",
                  knowledge_thread_active=True, knowledge_thread_turns=2)
    out = handle_message(s, "跳过", _EngineStub())
    assert s.answers["IP定位.name"] == ""               # 常规跳过
    assert s.current_subfield == "concept"
    assert s.knowledge_thread_active is False          # 退出②
    assert s.knowledge_thread_turns == 0


def test_forced_exit_after_turns_over_3():
    s = A1Session(session_id="s1", user_id="u1",
                  knowledge_thread_active=True, knowledge_thread_turns=4)
    iv = _EngineStub(
        fills=[InterviewFill(module="IP定位", subfield="name", value="星陨")],
        guidance_reply="继续说",
    )
    handle_message(s, "主角叫星陨", iv)   # 冻结轮：turns 5 → 强制退出③
    assert s.knowledge_thread_active is False
    assert s.knowledge_thread_turns == 0
    assert s.answers == {}                             # 本轮 fills 仍冻结


def test_exit_when_topic_leaves():
    s = A1Session(session_id="s1", user_id="u1",
                  knowledge_thread_active=True, knowledge_thread_turns=2)
    handle_message(s, "好了不聊这个了", _EngineStub(knowledge_used=False))
    assert s.knowledge_thread_active is False          # 退出④
    assert s.knowledge_thread_turns == 0


def test_disclosure_footnote_appended():
    s = A1Session(session_id="s1", user_id="u1")
    out = handle_message(
        s, "精神病院里腕带代表什么",
        _EngineStub(knowledge_used=True, guidance_reply="腕带是身份识别"),
    )
    assert out["reply"].endswith("（已联网查证）")
    # user_confused 通道（knowledge_used=False）不加尾注
    s2 = A1Session(session_id="s2", user_id="u1")
    out2 = handle_message(
        s2, "你在说什么听不懂", _EngineStub(knowledge_used=False,
                                            guidance_reply="我的意思是…")
    )
    assert "（已联网查证）" not in out2["reply"]


def test_store_roundtrip_new_fields(tmp_path):
    from app.domains.creation.a1.store import A1Store

    store = A1Store(path=tmp_path / "store.json")
    s = A1Session(session_id="s1", user_id="u1",
                  knowledge_thread_active=True, knowledge_thread_turns=2)
    store.save({"s1": s}, {})
    loaded, _ = store.load()
    assert loaded["s1"].knowledge_thread_active is True
    assert loaded["s1"].knowledge_thread_turns == 2
    # 旧数据缺新键 → 默认 False/0
    old = A1Session.model_validate({"session_id": "s2", "user_id": "u1"})
    assert old.knowledge_thread_active is False
    assert old.knowledge_thread_turns == 0
