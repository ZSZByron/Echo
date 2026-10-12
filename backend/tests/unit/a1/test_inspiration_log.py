"""inspiration_log 单元测试（T5）：JSON-lines 落盘 + fail-silent 保证。"""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.domains.creation.a1 import inspiration_log
from app.domains.creation.a1.guide_engine import A1Session, handle_message
from app.domains.creation.a1.inspiration_log import emit_event
from app.domains.creation.a1.interviewer import FakeInterviewer


def make_session() -> A1Session:
    return A1Session(session_id="s1", user_id="u1", ip_code="IP0001")


class _StubSession:
    """最小 session 鸭子类型（只暴露 emit_event 需要的 session_id）。"""

    session_id = "s1"


@pytest.fixture()
def tmp_log_path(tmp_path: Any, monkeypatch: pytest.MonkeyPatch):
    """把 LOG_PATH 指到 tmp 目录，隔离仓库工作目录。"""
    log_path = tmp_path / "inspiration_log.jsonl"
    monkeypatch.setattr(inspiration_log, "LOG_PATH", log_path)
    return log_path


def test_emit_writes_jsonl(tmp_log_path):
    """emit_event 落一行合法 JSON：ts/session_id/event + 附加字段。"""
    emit_event("option_pick", _StubSession(), module="IP定位", subfield="name",
               option_index=0)
    lines = tmp_log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["session_id"] == "s1"
    assert record["event"] == "option_pick"
    assert record["module"] == "IP定位"
    assert record["subfield"] == "name"
    assert record["option_index"] == 0
    assert "ts" in record
    # 追加写：第二次调用产生第二行
    emit_event("skip", _StubSession())
    assert len(tmp_log_path.read_text(encoding="utf-8").splitlines()) == 2


def test_telemetry_failure_is_silent(tmp_path: Any, monkeypatch: pytest.MonkeyPatch):
    """日志路径不可写 → emit_event 静默返回 None，主流程不受影响。"""
    # 目录不存在且不可创建的路径：把 LOG_PATH 指到一个"文件"下的子路径
    blocker = tmp_path / "blocker"
    blocker.write_text("not a dir", encoding="utf-8")
    bad_path = blocker / "sub" / "inspiration_log.jsonl"
    monkeypatch.setattr(inspiration_log, "LOG_PATH", bad_path)

    # 直接调用：不抛异常
    assert emit_event("stall", _StubSession(), module="m", subfield="s",
                      stall_count=1) is None

    # 主流程完整性：emitter 失败时 handle_message pick 轮仍返回正常 dict
    s = make_session()
    setattr(s, "current_options", ["x", "y", "z"])
    out = handle_message(s, "1", FakeInterviewer())
    assert isinstance(out, dict)
    assert out["reply"] == "已按示例记录：x"
    assert s.answers["IP定位.name"] == "x"
