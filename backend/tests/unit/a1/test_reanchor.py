"""批C红测③：话头重锚（拍2-19）。

触发词「梳理一下」（显式元命令）→ 摊开线头清单（配方已完成模块 +
当前题 + material_pool 存量）+ 四选一分流：
    改某答案 / 跳去聊某条 / 继续当前题 / 给灵感架安家

- 依赖 material_pool（A1Session 字段已在，批A 落库）——摊开内容含 pool 条目。
- 重锚后按选择分流且 **fills 不丢**（重锚前后 session.answers 一致）。
- 重锚打断知识对话态（knowledge_thread_* 复位）与打断讨论态（mirror_* 复位）。
- 埋点：reanchor_triggered 事件 → data/inspiration_log.jsonl（fail-silent）。

红测锁契约不锁实现；意图键 additive（delivery 键先例）。
"""
from __future__ import annotations

import json

import pytest

import app.domains.creation.a1.inspiration_log as inspiration_log
from app.domains.creation.a1.guide_engine import A1Session, handle_message
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


class _ReanchorStub:
    """handle_message 级 stub：可控 reanchor 意图旗标。"""

    def __init__(self, *, reanchor: bool = False, fills=None,
                 guidance_reply: str = "好，我们把线头摊开看一看。"):
        self.reanchor = reanchor
        self.fills = fills or []
        self.guidance_reply = guidance_reply

    def interview(self, session, text):  # noqa: ARG002
        return InterviewResult.model_construct(
            fills=list(self.fills),
            guidance_reply=self.guidance_reply,
            reanchor=self.reanchor,
        )

    def suggest_examples(self, session, module_id, subfield_id):  # noqa: ARG002
        return []


def _session() -> A1Session:
    s = A1Session(
        session_id="s_reanchor",
        user_id="u1",
        current_module="IP定位",
        current_subfield="name",
    )
    s.answers["IP定位.name"] = "公司职员"
    s.answers["IP定位.concept"] = "师姐的剑挂在城门口"
    return s


# ---------------------------------------------------------------------------
# 触发：「梳理一下」进入意图分类（解析侧 additive 键）
# ---------------------------------------------------------------------------


def test_reanchor_trigger_word_parses_intent_key():
    raw = {
        "fills": [],
        "guidance_reply": "好，我们梳理一下线头。",
        "reanchor": True,
    }
    result = RealLLMInterviewer(_FakeProvider([raw])).interview(
        _session(), "梳理一下"
    )
    assert result.reanchor is True


def test_reanchor_key_defaults_false_when_absent():
    raw = {
        "fills": [
            {"module": "IP定位", "subfield": "name", "value": "医生"}
        ],
        "guidance_reply": "已记录。",
    }
    result = RealLLMInterviewer(_FakeProvider([raw])).interview(
        _session(), "改成医生"
    )
    assert result.reanchor is False  # 普通轮缺省 False（delivery 先例）


# ---------------------------------------------------------------------------
# 行为：摊开线头清单（已完成模块 + 当前题 + material_pool 存量）
# ---------------------------------------------------------------------------


def test_reanchor_spreads_lineheads_with_pool_entries(monkeypatch):
    import app.domains.creation.a1.inspiration_log as insp

    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        insp, "emit_event",
        lambda event, session, **fields: events.append((event, fields)),
    )
    s = _session()
    s.material_pool = [
        {"text": "满天都是断掉的剑", "source": "delivery_overflow"},
        {"text": "腕带上的编号是入口密钥", "source": "delivery_overflow"},
    ]
    out = handle_message(s, "梳理一下", _ReanchorStub())
    reply = out["reply"]
    assert "满天都是断掉的剑" in reply  # 摊开内容含 pool 条目
    assert "腕带上的编号是入口密钥" in reply
    assert "公司职员" in reply  # 已完成答案入清单
    assert "IP定位" in reply or "职业" in reply  # 当前题入清单


def test_reanchor_offers_four_way_choice(monkeypatch):
    import app.domains.creation.a1.inspiration_log as insp

    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        insp, "emit_event",
        lambda event, session, **fields: events.append((event, fields)),
    )
    s = _session()
    s.material_pool = [{"text": "满天都是断掉的剑", "source": "delivery_overflow"}]
    out = handle_message(s, "梳理一下", _ReanchorStub())
    reply = out["reply"]
    # 四选一：改某答案 / 跳去聊某条 / 继续当前题 / 给灵感架安家
    assert "改" in reply
    assert "继续" in reply
    assert "灵感架" in reply


# ---------------------------------------------------------------------------
# 分流且 fills 不丢
# ---------------------------------------------------------------------------


def test_reanchor_preserves_answers_then_continue_choice_lands(monkeypatch):
    import app.domains.creation.a1.inspiration_log as insp

    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        insp, "emit_event",
        lambda event, session, **fields: events.append((event, fields)),
    )
    s = _session()
    s.material_pool = [{"text": "满天都是断掉的剑", "source": "delivery_overflow"}]
    snapshot = dict(s.answers)

    # 重锚轮：answers 一致（fills 不丢）
    handle_message(s, "梳理一下", _ReanchorStub())
    assert s.answers == snapshot

    # 选择「继续当前题」：直选照常消费、既有答案原位
    s.current_options = ["公司职员", "医生", "教师"]
    handle_message(s, "2", _ReanchorStub())
    assert s.answers.get("IP定位.name") == "医生"
    assert s.answers.get("IP定位.concept") == snapshot["IP定位.concept"]


# ---------------------------------------------------------------------------
# 打断复位：知识对话态 / 讨论态
# ---------------------------------------------------------------------------


def test_reanchor_resets_knowledge_thread(monkeypatch):
    import app.domains.creation.a1.inspiration_log as insp

    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        insp, "emit_event",
        lambda event, session, **fields: events.append((event, fields)),
    )
    s = _session()
    s.knowledge_thread_active = True
    s.knowledge_thread_turns = 2
    handle_message(s, "梳理一下", _ReanchorStub())
    assert s.knowledge_thread_active is False
    assert s.knowledge_thread_turns == 0


def test_reanchor_resets_mirror_thread(monkeypatch):
    """讨论态中两轮镜像后说「梳理一下」→ mirror 线程复位（驱动式置位，
    不直接 setattr additive 未落库字段）。"""
    import app.domains.creation.a1.inspiration_log as insp

    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        insp, "emit_event",
        lambda event, session, **fields: events.append((event, fields)),
    )
    s = _session()

    class _MirrorStub:
        def interview(self, session, text):  # noqa: ARG002
            return InterviewResult.model_construct(
                fills=[],
                guidance_reply="回到刚才的问题。",
                mirror=True,
            )

        def suggest_examples(self, session, module_id, subfield_id):  # noqa: ARG002
            return []

    handle_message(s, "她为什么把剑挂在那里？", _MirrorStub())
    handle_message(s, "城门口的人为什么会允许？", _MirrorStub())
    handle_message(s, "梳理一下", _ReanchorStub())
    assert s.mirror_thread_turns == 0
    assert s.mirror_thread_active is False


# ---------------------------------------------------------------------------
# 埋点：reanchor_triggered 事件 jsonl（fail-silent）
# ---------------------------------------------------------------------------


def test_reanchor_triggered_event_written_to_jsonl(tmp_path, monkeypatch):
    log_path = tmp_path / "inspiration_log.jsonl"
    monkeypatch.setattr(inspiration_log, "LOG_PATH", log_path)
    s = _session()
    handle_message(s, "梳理一下", _ReanchorStub())
    if not log_path.exists():
        raise AssertionError("reanchor_triggered 事件未落 jsonl（引擎未触发埋点）")
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    records = [json.loads(ln) for ln in lines]
    assert any(r["event"] == "reanchor_triggered" for r in records)


def test_reanchor_telemetry_failure_is_silent(tmp_path, monkeypatch):
    blocker = tmp_path / "blocker"
    blocker.write_text("not a dir", encoding="utf-8")  # 锚测缺陷修正：
    # 照 test_inspiration_log.py 先例把 blocker 造成文件（否则 mkdir
    # parents=True 建目录成功，故障永不发生）。
    bad_path = blocker / "sub" / "inspiration_log.jsonl"
    monkeypatch.setattr(inspiration_log, "LOG_PATH", bad_path)
    s = _session()
    out = handle_message(s, "梳理一下", _ReanchorStub())
    assert "reply" in out  # 写失败不抛
    assert not bad_path.exists()
