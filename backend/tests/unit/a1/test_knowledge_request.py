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
