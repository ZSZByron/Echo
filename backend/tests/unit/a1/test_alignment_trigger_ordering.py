"""T17: 对齐触发时机 + 与收尾/轮次定序（D21⑬，问题说明书 L185 触发双档）。

四组契约：
1. 轻量命中触发矩阵：chat 每轮后确定性检测（纯代码零 LLM 检测），
   命中 → AlignmentProposer.propose（单次 chat_json）；不命中 →
   **提议 LLM 调用计数 = 0**（FakeLLM 计数器断言）。
2. 模块边界深对齐：sync_position 跨模块（模块完成边界）→ 深对齐
   提议（消费 T14 图谱摘要）；非边界轮零调用。
3. 同帧定序：先对齐后收尾——对齐提案 pending 时收尾提示延后至
   resolve；pending 清空后收尾恢复。
4. pending 并发 + D20 接缝：对齐 pending 期间新消息照常处理
   （resolve_proposal 先例：提案保留、无死锁）；受邀问题不阻塞收尾。
"""
from __future__ import annotations

from typing import Any

from app.domains.creation.a1.alignment_flow import AlignProposal
from app.domains.creation.a1.guide_engine import (
    PHASE_ASKING,
    PHASE_COMPLETED,
    ROUND_SIGNAL_ORDER,
    handle_message,
)
from app.domains.creation.a1.interviewer import FakeInterviewer, InterviewFill
from app.domains.creation.a1.closing_flow import QUESTIONS
from app.domains.creation.seed.a1_question_tree import (
    first_module,
    module_ids,
    subs_for_module,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

#: 最小图谱：一个节点（id=n1，标题=水晶王座）。标题即轻量检测实体词。
GRAPH: dict[str, Any] = {
    "nodes": {"n1": {"title": "水晶王座", "description": "王座深处的抉择"}},
    "edges": [],
}

HIT_TEXT = "我突然想到水晶王座下面封印着一条龙"
MISS_TEXT = "今天我们先聊聊别的吧"


class CountingProvider:
    """FakeLLM：计数 chat_json 调用（零 LLM 断言锚点）。"""

    def __init__(self, proposals: list[dict[str, str]] | None = None) -> None:
        self.calls = 0
        self.proposals = proposals or [
            {
                "action": "link",
                "target": "n1",
                "content": "你说的和已有记录「水晶王座」相关，建议建立关联。",
                "quote": "水晶王座下面封印着一条龙",
            }
        ]

    def chat_json(self, messages: Any) -> dict[str, Any]:
        self.calls += 1
        return {"proposals": self.proposals}


def _fake(provider: CountingProvider | None = None, **kw: Any) -> FakeInterviewer:
    fake = FakeInterviewer(**kw)
    if provider is not None:
        fake._provider = provider  # 真实 Interviewer 同名属性（T17 接线读取）
    return fake


def _pending(session: Any) -> None:
    session.pending_alignments["align-001"] = {
        "proposal": AlignProposal(
            action="dedupe", target="n1", content="已有记录，无需重录。"
        ),
        "source": "test",
    }


# ---------------------------------------------------------------------------
# 组 1：轻量命中触发矩阵（不触发 → LLM 调用计数 = 0）
# ---------------------------------------------------------------------------


class TestLightHitMatrix:
    def _session(self) -> Any:
        s = _mk(phase=PHASE_ASKING)
        return _attach_graph(s)

    def test_hit_triggers_propose_once_and_installs(self):
        s = self._session()
        provider = CountingProvider()
        out = handle_message(s, HIT_TEXT, _fake(provider))
        assert provider.calls == 1
        assert len(s.pending_alignments) == 1
        assert "对齐建议" in out["reply"]

    def test_miss_zero_llm_calls(self):
        s = self._session()
        provider = CountingProvider()
        handle_message(s, MISS_TEXT, _fake(provider))
        assert provider.calls == 0
        assert s.pending_alignments == {}

    def test_no_graph_zero_llm_calls(self):
        s = _mk(phase=PHASE_ASKING)  # 无 graph_json
        provider = CountingProvider()
        handle_message(s, HIT_TEXT, _fake(provider))
        assert provider.calls == 0

    def test_pending_blocks_nesting_zero_llm_calls(self):
        s = self._session()
        _pending(s)
        provider = CountingProvider()
        handle_message(s, HIT_TEXT, _fake(provider))
        assert provider.calls == 0  # 不做多轮对齐嵌套
        assert len(s.pending_alignments) == 1  # 原提案保留

    def test_no_provider_zero_llm_and_no_crash(self):
        s = self._session()
        fake = FakeInterviewer()  # 无 _provider 属性 → getattr 默认 None
        assert getattr(fake, "_provider", None) is None
        out = handle_message(s, HIT_TEXT, fake)
        assert s.pending_alignments == {}
        assert out["reply"]


# ---------------------------------------------------------------------------
# 组 2：模块边界深对齐（sync_position 跨模块 → 深对齐，消费 T14 摘要）
# ---------------------------------------------------------------------------


class TestModuleBoundaryDeepAlign:
    def _pre_boundary_session(self) -> Any:
        """首模块只留第一个子字段未答 → 本轮 fill 完成模块 → 跨模块。"""
        s = _mk(phase=PHASE_ASKING)
        _attach_graph(s)  # 深对齐消费 T14 摘要（无图 → propose 零调用守门）
        m = first_module()
        s.current_module = m["id"]
        s.current_subfield = subs_for_module(m["id"])[0]["id"]
        for f in subs_for_module(m["id"])[1:]:
            s.answers[f"{m['id']}.{f['id']}"] = "预填内容"
        return s

    def test_boundary_cross_triggers_deep_align_without_keyword(self):
        s = self._pre_boundary_session()
        provider = CountingProvider()
        fill = first_module()
        fake = _fake(provider, fills=[
            InterviewFill(
                module=fill["id"],
                subfield=subs_for_module(fill["id"])[0]["id"],
                value="创世的第一次裂痕",
            )
        ])
        pre = s.current_module
        handle_message(s, "创世的第一次裂痕", fake)  # 文本不含任何图谱标题
        assert provider.calls == 1  # 模块边界深对齐（无关键词也触发）
        assert s.current_module != pre  # 确实跨了模块
        assert len(s.pending_alignments) == 1

    def test_mid_module_round_zero_llm_calls(self):
        """非边界轮（chat，无跨模块、无关键词命中）→ 零 LLM。"""
        s = self._pre_boundary_session()
        provider = CountingProvider()
        fake = _fake(provider, fills=[])  # chat 分支：无 fills，指针不动
        pre = s.current_module
        handle_message(s, "随便聊聊背景", fake)
        assert s.current_module == pre  # 未跨模块（deep=False）
        assert provider.calls == 0  # 未命中 + 非边界 → 零 LLM


# ---------------------------------------------------------------------------
# 组 3：同帧定序——先对齐后收尾
# ---------------------------------------------------------------------------


class TestAlignBeforeClosing:
    def _completed(self, graph: bool = True) -> Any:
        s = _mk(phase=PHASE_COMPLETED)
        if graph:
            return _attach_graph(s)

    def test_ordering_constant_is_explicit(self):
        assert ROUND_SIGNAL_ORDER == ("alignment", "closing")

    def test_hit_at_closing_boundary_delays_closing(self):
        s = self._completed()
        provider = CountingProvider()
        out = handle_message(s, HIT_TEXT, _fake(provider))
        assert len(s.pending_alignments) == 1
        assert s.closing_step == 0  # 收尾延后：未进入 Q1
        assert "预设的问题都聊完了" not in out["reply"]
        assert "对齐建议" in out["reply"]

    def test_after_resolve_closing_resumes(self):
        s = self._completed()
        provider = CountingProvider()
        handle_message(s, HIT_TEXT, _fake(provider))
        # 全部 resolve（decline：零副作用）
        for key in list(s.pending_alignments):
            from app.domains.creation.a1.alignment_flow import resolve_alignment

            resolve_alignment(s, key, accept=False)
        assert s.pending_alignments == {}
        provider2 = CountingProvider()
        out = handle_message(s, MISS_TEXT, _fake(provider2))
        assert provider2.calls == 0
        assert s.closing_step == 1  # 收尾恢复：进入 Q1
        assert QUESTIONS[0]["text"] in out["reply"]

    def test_no_hit_closing_fires_normally(self):
        s = self._completed()
        provider = CountingProvider()
        out = handle_message(s, MISS_TEXT, _fake(provider))
        assert provider.calls == 0
        assert s.closing_step == 1
        assert QUESTIONS[0]["text"] in out["reply"]


# ---------------------------------------------------------------------------
# 组 4：pending 并发（无死锁/无双花）+ D20 接缝复测
# ---------------------------------------------------------------------------


class TestPendingConcurrencyAndD20Seam:
    def _pending_session(self) -> Any:
        s = _mk(phase=PHASE_ASKING)
        _attach_graph(s)
        _pending(s)
        return s

    def test_new_message_processed_normally_while_pending(self):
        s = self._pending_session()
        provider = CountingProvider()
        out = handle_message(s, MISS_TEXT, _fake(provider))
        assert out["reply"]  # 新消息照常处理
        assert provider.calls == 0  # 无双花（不嵌套提议）
        assert len(s.pending_alignments) == 1  # 提案保留（resolve_proposal 先例）

    def test_resolve_works_during_flow_no_deadlock(self):
        s = self._pending_session()
        from app.domains.creation.a1.alignment_flow import resolve_alignment

        r = resolve_alignment(s, "align-001", accept=True)
        assert r.get("applied") is True
        assert s.pending_alignments == {}
        # resolve 后下一轮恢复提议能力
        provider = CountingProvider()
        handle_message(s, HIT_TEXT, _fake(provider))
        assert provider.calls == 1

    def test_d20_seam_invited_does_not_block_closing(self):
        s = _mk(
            phase=PHASE_COMPLETED,
            invited_modules=["healing"],
        )
        provider = CountingProvider()
        out = handle_message(s, MISS_TEXT, _fake(provider))
        assert provider.calls == 0  # 无图零调用
        assert s.closing_step == 1  # 受邀模块不阻塞收尾（D20 接缝保持）
        assert QUESTIONS[0]["text"] in out["reply"]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _attach_graph(session: Any) -> Any:
    """挂 graph_json（pydantic 模型外属性——lookup_graph_json 的直读路径）。"""
    object.__setattr__(session, "graph_json", GRAPH)
    return session


def _mk(**kw: Any) -> Any:
    from app.domains.creation.a1.guide_engine import A1Session

    return A1Session(session_id="s-t17", user_id="u1", **kw)
