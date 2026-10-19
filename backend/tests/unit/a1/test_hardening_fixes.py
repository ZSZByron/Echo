"""商业加固批红测（TDD RED 先行）——P0-3 F1 / P0-4 F2 / P0-5 F3。

依据：.sisyphus/plans/commercial-hardening.md + .sisyphus/evidence/freeze-diagnosis.md
- F1 真值闸拦占位填充：fill 值「无（未提供外表特征）」→ answers 零写入 +
  pending_proposals 空 + 正常值不受影响。
- F2 提案挂起的 chat 语言消解：pending_proposals 非空 + 短指令（≤6 字符）
  命中 替换/合并/放弃 → 前置短路直接 resolve_proposal（不走 LLM 通道竞争）。
- F3 已答开放问题不重问：本轮识别到 open question 回答 → session 侧挂起
  展示态同步回清（下一轮 prompt 不再注入「回到刚才的问题」）。
"""
import hashlib

from app.domains.creation.a1.guide_engine import (
    A1Session,
    _apply_fills,
    handle_message,
)
from app.domains.creation.a1.interviewer import (
    DegradingInterviewer,
    FakeInterviewer,
    InterviewFill,
)


def make_session() -> A1Session:
    return A1Session(session_id="s-hardening", user_id="u1", ip_code="IP0001")


def _proposal_key(module: str, subfield: str, new: str) -> str:
    h = hashlib.md5(new.encode()).hexdigest()[:8]
    return f"{module}.{subfield}:{h}"


def _seed_pending_proposal(s: A1Session) -> str:
    """经既有拦截通道制造一条挂起提案（answers 保留旧值）。"""
    s.answers["IP定位.name"] = "星陨大陆"
    _, proposals = _apply_fills(
        s, [InterviewFill(module="IP定位", subfield="name", value="星穹大陆")]
    )
    assert len(s.pending_proposals) == 1
    assert proposals, "前置：拦截提案应已生成"
    return _proposal_key("IP定位", "name", "星穹大陆")


# ---------------------------------------------------------------------------
# P0-3 F1：LLM 塞责式占位填充闸
# ---------------------------------------------------------------------------


class TestF1PlaceholderFillGate:
    def test_placeholder_fill_not_written_no_proposal(self):
        s = make_session()
        fills = [
            InterviewFill(
                module="角色", subfield="character_visual",
                value="无（未提供外表特征）",
            )
        ]
        file_diff, proposals = _apply_fills(s, fills)

        assert "角色.character_visual" not in s.answers
        assert file_diff == []
        assert proposals == []
        assert s.pending_proposals == {}

    def test_placeholder_conflict_does_not_propose(self):
        """占位 fill 与既有真值冲突 → 丢弃（不生成无意义提案）。"""
        s = make_session()
        s.answers["角色.character_visual"] = "银发红瞳的少女剑士"
        fills = [
            InterviewFill(
                module="角色", subfield="character_visual",
                value="无（未提供外表特征）",
            )
        ]
        file_diff, proposals = _apply_fills(s, fills)

        assert s.answers["角色.character_visual"] == "银发红瞳的少女剑士"
        assert file_diff == []
        assert proposals == []
        assert s.pending_proposals == {}

    def test_normal_fill_unaffected(self):
        s = make_session()
        fills = [
            InterviewFill(
                module="角色", subfield="character_visual",
                value="银发红瞳的少女剑士",
            )
        ]
        file_diff, proposals = _apply_fills(s, fills)

        assert s.answers["角色.character_visual"] == "银发红瞳的少女剑士"
        assert len(file_diff) == 1
        assert proposals == []

    def test_placeholder_variants_dropped(self):
        for value in ("未提供", "未提及外貌", "未说明", "无", "（无）"):
            s = make_session()
            _apply_fills(
                s,
                [InterviewFill(module="角色", subfield="character_visual", value=value)],
            )
            assert "角色.character_visual" not in s.answers, f"{value!r} 应被丢弃"


# ---------------------------------------------------------------------------
# P0-4 F2：提案挂起的 chat 短指令前置消解
# ---------------------------------------------------------------------------


class TestF2ChatProposalResolve:
    def test_chat_drop_resolves_pending_keeps_answer(self):
        s = make_session()
        key = _seed_pending_proposal(s)
        fake = FakeInterviewer(guidance_reply="不应被调用")
        out = handle_message(s, "放弃", fake)

        assert key not in s.pending_proposals
        assert s.pending_proposals == {}
        assert s.answers["IP定位.name"] == "星陨大陆"  # drop 保留原值
        assert "放弃" in out["reply"]
        assert fake.calls == 0  # 前置短路，不进 LLM

    def test_chat_replace_applies_new(self):
        s = make_session()
        key = _seed_pending_proposal(s)
        out = handle_message(s, "替换", FakeInterviewer())

        assert key not in s.pending_proposals
        assert s.answers["IP定位.name"] == "星穹大陆"
        assert "替换" in out["reply"]

    def test_chat_merge_combines_values(self):
        s = make_session()
        key = _seed_pending_proposal(s)
        out = handle_message(s, "合并", FakeInterviewer())

        assert key not in s.pending_proposals
        assert s.answers["IP定位.name"] == "星陨大陆；星穹大陆"
        assert "合并" in out["reply"]

    def test_no_pending_not_short_circuited(self):
        """pending 空 → 短指令不短路，走正常 LLM 通道。"""
        s = make_session()
        fake = FakeInterviewer(guidance_reply="好的")
        handle_message(s, "放弃", fake)

        assert fake.calls == 1
        assert s.pending_proposals == {}

    def test_long_message_not_short_circuited(self):
        """超过 6 字符的含关键词消息 → 不短路（避免误伤正常对话）。"""
        s = make_session()
        key = _seed_pending_proposal(s)
        fake = FakeInterviewer(guidance_reply="聊聊吧")
        handle_message(s, "我想放弃这条提案，再聊聊吧", fake)

        assert fake.calls == 1
        assert key in s.pending_proposals


# ---------------------------------------------------------------------------
# P0-5 F3：已答开放问题 → session 侧挂起展示态回清
# ---------------------------------------------------------------------------


class TestF3AnsweredOpenQuestionCleared:
    def test_answer_clears_session_side_pending(self):
        s = make_session()
        fake = FakeInterviewer(
            guidance_reply="记下了",
            open_question_answered={"id": "oq-001", "answer": "精灵历三年"},
        )
        fake.set_pending_open_question(
            {"id": "oq-001", "question": "这个世界的纪年是什么？"}
        )
        handle_message(s, "纪年是精灵历三年", fake)

        assert fake._pending_open_question is None

    def test_no_answer_keeps_pending(self):
        s = make_session()
        fake = FakeInterviewer(guidance_reply="好的")
        fake.set_pending_open_question(
            {"id": "oq-001", "question": "这个世界的纪年是什么？"}
        )
        handle_message(s, "随便聊聊天气", fake)

        assert fake._pending_open_question is not None

    def test_degrading_proxy_inner_cleared(self):
        """routes 用的是 DegradingInterviewer 单例——回清必须穿透代理达 inner。"""
        s = make_session()
        inner = FakeInterviewer(
            guidance_reply="记下了",
            open_question_answered={"id": "oq-001", "answer": "精灵历三年"},
        )
        proxy = DegradingInterviewer(inner)
        proxy.set_pending_open_question(
            {"id": "oq-001", "question": "这个世界的纪年是什么？"}
        )
        handle_message(s, "纪年是精灵历三年", proxy)

        assert inner._pending_open_question is None
