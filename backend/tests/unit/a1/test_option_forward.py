"""方向A一期「选项前置」契约测试（T1，施工单 + 计划 direction-a-option-forward）。

16 条契约，TDD RED 阶段：功能未实现，全部应当失败（失败原因必须是
"功能缺失"，不允许 import/语法错误导致收集失败）。

设计决策绑定（计划 D-1~D-7）：
- D-1: 直选仅限 text.strip() 恰为 "1"/"2"/"3" 且 current_options 非空；
  其余（如「把1和3揉一起」）走 LLM 理解路径。
- D-2: reroll 关键词闭集 {"换一批","再来一批","换组"}，需 current_options
  非空；连续上限 2 次；不计 stall。
- D-3: 新字段 A1Session.current_options: list[str] + reroll_streak: int。
"""
from __future__ import annotations

from typing import Any

import pytest

from app.domains.creation.a1.guide_engine import (
    PHASE_COMPLETED,
    A1Session,
    handle_message,
)
from app.domains.creation.a1.interviewer import (
    FakeInterviewer,
    InterviewFill,
    RealLLMInterviewer,
)
from app.domains.creation.seed.a1_question_tree import (
    get_module,
    get_subfield,
)

# ---------------------------------------------------------------------------
# 契约常量（与计划 T3 Step 2 逐字一致）
# ---------------------------------------------------------------------------

OPTION_INVITE_TEMPLATE = (
    "这里有几个方向，也可以直接说你的：\n{lines}\n"
    "（回复序号可直选，想换个方向就说「换一批」）"
)

#: 旧 stall==2 道歉话术（施工单明令退役）
_LEGACY_APOLOGY = "我没能准确理解你的回答"
_LEGACY_EXAMPLE_HINT = "示例方向"


def render_invite(lines: list[str]) -> str:
    rendered = "\n".join(f"{i}. {ln}" for i, ln in enumerate(lines, start=1))
    return OPTION_INVITE_TEMPLATE.format(lines=rendered)


# ---------------------------------------------------------------------------
# 测试基建
# ---------------------------------------------------------------------------


def make_session() -> A1Session:
    return A1Session(session_id="s1", user_id="u1", ip_code="IP0001")


class ExamplesFake(FakeInterviewer):
    """FakeInterviewer + examples 透传。

    InterviewResult.examples 字段（T2 Step 1）落地前，setattr 抛
    ValueError —— 本测试文件期待的「功能缺失红」。落地后无论
    FakeInterviewer 基建是否接线，本注入都确定性生效。
    """

    def __init__(self, *args: Any, inject: Any = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._inject = inject

    def interview(self, session: Any, text: str) -> Any:
        result = super().interview(session, text)
        setattr(result, "examples", self._inject)
        return result


def _spy_events(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """替换 inspiration_log.emit_event 为内存记录器。

    T5 落地前 inspiration_log 模块不存在 → ModuleNotFoundError（红）。
    """
    from app.domains.creation.a1 import inspiration_log

    calls: list[dict[str, Any]] = []

    def _recorder(event: str, session: Any, **fields: Any) -> None:
        calls.append(
            {"event": event, "session_id": session.session_id, **fields}
        )

    monkeypatch.setattr(inspiration_log, "emit_event", _recorder)
    return calls


def _assert_no_options(reply: str, session: A1Session) -> None:
    """白名单断言：reply 无邀请话术、无编号选项行、current_options 为空。"""
    assert "这里有几个方向" not in reply
    assert "回复序号可直选" not in reply
    assert getattr(session, "current_options", []) == []


# ---------------------------------------------------------------------------
# 契约 1-3：examples 三态（正常 / 缺失 / 畸形）
# ---------------------------------------------------------------------------


class TestExamplesAttachment:
    def test_examples_default_attached(self):
        """契约1：examples 正常 → reply 含邀请话术 + 三行「1. a」格式选项。"""
        s = make_session()
        fake = ExamplesFake(
            fills=[InterviewFill(module="IP定位", subfield="name", value="星陨大陆")],
            guidance_reply="好名字！已记录。",
            inject=["a", "b", "c"],
        )
        out = handle_message(s, "名字叫星陨大陆", fake)
        assert getattr(guide_engine_module(), "OPTION_INVITE_TEMPLATE") == (
            OPTION_INVITE_TEMPLATE
        )
        assert render_invite(["a", "b", "c"]) in out["reply"]
        assert "1. a" in out["reply"]
        assert "2. b" in out["reply"]
        assert "3. c" in out["reply"]
        # 话术追加在 guidance 之后，不替换
        assert out["reply"].startswith("好名字！已记录。")

    def test_examples_missing_degrades(self):
        """契约2：examples=[] → reply 与旧行为逐字节一致（降级零痕迹）。"""
        s = make_session()
        fake = FakeInterviewer(
            fills=[InterviewFill(module="IP定位", subfield="name", value="星陨大陆")],
            guidance_reply="好名字！已记录。",
        )
        out = handle_message(s, "名字叫星陨大陆", fake)
        assert out["reply"] == "好名字！已记录。"
        # D-3：current_options 字段必须存在（缺失时 getattr 兜底 []，
        # 这里刻意直接访问——字段未落地即红）
        assert s.current_options == []

    def test_examples_malformed_degrades(self):
        """契约3：examples 非 list（畸形 JSON 路径）→ 同样静默降级。"""
        s = make_session()
        fake = ExamplesFake(
            fills=[InterviewFill(module="IP定位", subfield="name", value="星陨大陆")],
            guidance_reply="好名字！已记录。",
            inject="这不是一个列表",
        )
        out = handle_message(s, "名字叫星陨大陆", fake)
        assert out["reply"] == "好名字！已记录。"
        assert getattr(s, "current_options", []) == []


def guide_engine_module():
    import app.domains.creation.a1.guide_engine as ge

    return ge


# ---------------------------------------------------------------------------
# 契约 4-7：白名单——以下轮次绝不渲染选项
# ---------------------------------------------------------------------------


class TestOptionWhitelist:
    def test_no_options_on_deflect_turn(self):
        """契约4：deflect 轮 → 无选项。"""
        s = make_session()
        fake = ExamplesFake(deflect=True, guidance_reply="想先聊聊故事主线？", inject=["a", "b", "c"])
        out = handle_message(s, "先不答这个", fake)
        _assert_no_options(out["reply"], s)

    def test_no_options_on_story_material_turn(self):
        """契约5：story_material 轮 → 无选项。"""
        s = make_session()
        fake = ExamplesFake(
            story_material="一个雨夜独行的剑客角色片段",
            guidance_reply="素材已收好。",
            inject=["a", "b", "c"],
        )
        out = handle_message(s, "有个角色总在雨夜独行", fake)
        _assert_no_options(out["reply"], s)

    def test_no_options_when_no_current_subfield(self):
        """契约6：completed 阶段 → 无选项。"""
        s = make_session()
        s.phase = PHASE_COMPLETED
        fake = ExamplesFake(guidance_reply="还可以继续打磨。", inject=["a", "b", "c"])
        out = handle_message(s, "再说一句", fake)
        _assert_no_options(out["reply"], s)

    def test_no_options_on_proposal_pending_turn(self):
        """契约7：write-guard 拦截成提案挂起轮 → 无选项。"""
        s = make_session()
        s.answers["IP定位.name"] = "星陨大陆"
        fake = ExamplesFake(
            fills=[
                InterviewFill(
                    module="IP定位",
                    subfield="name",
                    value="陨星之陆",
                    conflict_note="与当前设定冲突",
                )
            ],
            guidance_reply="已记录。",
            inject=["a", "b", "c"],
        )
        out = handle_message(s, "改成陨星之陆吧", fake)
        assert out.get("proposals"), "前置条件：本轮应产生 write-guard 提案"
        _assert_no_options(out["reply"], s)


# ---------------------------------------------------------------------------
# 契约 8-10：序号直选 / reroll 通道
# ---------------------------------------------------------------------------


class TestPickAndReroll:
    def test_pick_option_fills(self, monkeypatch: pytest.MonkeyPatch):
        """契约8：直选 "1" → 直填 x + stall 清零 + option_pick 埋点。"""
        events = _spy_events(monkeypatch)
        s = make_session()
        setattr(s, "current_options", ["x", "y", "z"])
        s.stall_subfield = "IP定位.name"
        s.stall_count = 2
        out = handle_message(s, "1", FakeInterviewer())
        assert s.answers["IP定位.name"] == "x"
        assert s.stall_count == 0
        assert getattr(s, "current_options") == []
        picks = [e for e in events if e["event"] == "option_pick"]
        assert len(picks) == 1
        assert picks[0]["session_id"] == "s1"
        assert picks[0]["module"] == "IP定位"
        assert picks[0]["subfield"] == "name"
        assert picks[0]["option_index"] == 0

    def test_reroll_keyword_regenerates(self, monkeypatch: pytest.MonkeyPatch):
        """契约9：「换一批」→ suggest_examples 重生成 + stall 不变 + option_reroll。"""
        events = _spy_events(monkeypatch)
        s = make_session()
        setattr(s, "current_options", ["x", "y", "z"])
        s.stall_subfield = "IP定位.name"
        s.stall_count = 1
        fake = ExamplesFake(inject=["n1", "n2", "n3"])
        out = handle_message(s, "换一批", fake)
        assert fake.suggest_calls == 1, "reroll 必须调 suggest_examples 独立生成"
        assert getattr(s, "current_options") == ["n1", "n2", "n3"]
        assert s.stall_count == 1, "reroll 一律不计 stall"
        assert getattr(s, "reroll_streak") == 1
        assert "1. n1" in out["reply"]
        rerolls = [e for e in events if e["event"] == "option_reroll"]
        assert len(rerolls) == 1
        assert rerolls[0]["session_id"] == "s1"
        assert rerolls[0]["module"] == "IP定位"
        assert rerolls[0]["subfield"] == "name"
        assert rerolls[0]["streak"] == 1

    def test_reroll_cap_two(self, monkeypatch: pytest.MonkeyPatch):
        """契约10：连续第三次「换一批」→ 不再生成，提示自由输入/直选。"""
        _spy_events(monkeypatch)
        s = make_session()
        setattr(s, "current_options", ["x", "y", "z"])
        fake = ExamplesFake(inject=[f"n{i}", f"m{i}", f"o{i}"])
        handle_message(s, "换一批", fake)
        handle_message(s, "换一批", fake)
        assert fake.suggest_calls == 2
        out3 = handle_message(s, "换一批", fake)
        assert fake.suggest_calls == 2, "第三次换一批不得再触发生成调用"
        assert "直接选" in out3["reply"]
        assert "自己的话" in out3["reply"]


# ---------------------------------------------------------------------------
# 契约 11-14：跳过续接 / 道歉退役 / 引用理解 / 推进刷新
# ---------------------------------------------------------------------------


class TestFlowContracts:
    def test_skip_then_next_question_has_options(self):
        """契约11：跳过后下一问 reply 带新字段选项（无死路）。"""
        s = make_session()
        fake = ExamplesFake(guidance_reply="好。", inject=["o1", "o2", "o3"])
        handle_message(s, "跳过", fake)
        assert s.current_subfield == "concept"  # 指针已推进
        out = handle_message(s, "我再想想", fake)
        assert render_invite(["o1", "o2", "o3"]) in out["reply"]
        assert getattr(s, "current_options") == ["o1", "o2", "o3"]

    def test_apology_path_removed(self):
        """契约12：stall==2 → 道歉话术退役；stall 计数照常累计。"""
        s = make_session()
        fake = FakeInterviewer(guidance_reply="收到。")
        handle_message(s, "嗯嗯随便说说", fake)
        handle_message(s, "换个说法再说说", fake)
        assert s.stall_count == 2, "stall 计数逻辑保留"
        s2 = make_session()
        fake2 = ExamplesFake(guidance_reply="收到。", inject=["a", "b", "c"])
        out1 = handle_message(s2, "嗯嗯随便说说", fake2)
        assert _LEGACY_APOLOGY not in out1["reply"]
        assert s2.stall_count == 1
        out2 = handle_message(s2, "换个说法再说说", fake2)
        assert _LEGACY_APOLOGY not in out2["reply"]
        assert _LEGACY_EXAMPLE_HINT not in out2["reply"]
        assert s2.stall_count == 2

    def test_merge_reference_goes_understanding(self):
        """契约13：「把1和3揉一起」→ 走 LLM 理解（fills），不被直选劫持。"""
        s = make_session()
        setattr(s, "current_options", ["x", "y", "z"])
        fake = FakeInterviewer(
            fills=[
                InterviewFill(
                    module="IP定位", subfield="name", value="x与z揉合的新方向"
                )
            ],
            guidance_reply="揉合方向已记录。",
        )
        out = handle_message(s, "把1和3揉一起", fake)
        assert fake.calls == 1, "非精确序号必须进入 interview 理解路径"
        assert s.answers["IP定位.name"] == "x与z揉合的新方向"
        assert out["reply"] == "揉合方向已记录。"

    def test_options_refreshed_on_advance(self):
        """契约14：字段推进后 current_options 为新字段选项（非残留）。"""
        s = make_session()
        fake = ExamplesFake(
            fills=[InterviewFill(module="IP定位", subfield="name", value="星陨大陆")],
            guidance_reply="好。",
            inject=["第一问选项1", "第一问选项2", "第一问选项3"],
        )
        handle_message(s, "名字叫星陨大陆", fake)
        assert s.current_subfield == "concept"
        assert getattr(s, "current_options") == [
            "第一问选项1",
            "第一问选项2",
            "第一问选项3",
        ]
        fake._inject = ["第二问选项1", "第二问选项2", "第二问选项3"]
        fake.fills = [InterviewFill(module="IP定位", subfield="concept", value="因果轮回")]
        handle_message(s, "核心体验是因果轮回", fake)
        assert getattr(s, "current_options") == [
            "第二问选项1",
            "第二问选项2",
            "第二问选项3",
        ], "推进后必须刷新为新字段的选项"


# ---------------------------------------------------------------------------
# 契约 15：prompt 防火墙条款（规则块 8.6）+ 8.5 原文未动
# ---------------------------------------------------------------------------


class TestPromptFirewall:
    def test_prompt_firewall_clause(self):
        """契约15：interview system prompt 含防火墙条款 + 引用理解条款；
        8.5 规则块原文未动。"""
        it = RealLLMInterviewer(None)
        module = get_module("IP定位")
        subfield = get_subfield("IP定位", "name")
        assert module is not None and subfield is not None
        prompt = it._build_prompt(module, subfield, make_session())

        # 防火墙条款（8.6 第 3 段）
        assert "示例必须是陈述句" in prompt
        assert "严禁出现任何新的疑问句" in prompt
        assert "唯一疑问句" in prompt

        # 引用理解条款（8.6 第 2 段）
        assert "选2吧" in prompt
        assert "把1和3揉一起" in prompt
        assert "第1点对" in prompt
        assert "不要当作纯数字" in prompt

        # 8.5 原文未动（关键句逐字存在）
        it.set_pending_open_question({"id": "q1", "question": "测试问题？"})
        block = "\n".join(it._pending_question_block())
        assert "8.5 待问开放问题" in block
        assert "严禁追加任何其他疑问句——单问句铁律" in block


# ---------------------------------------------------------------------------
# 契约 16：埋点事件（JSON-lines 具体 key-value）
# ---------------------------------------------------------------------------


class TestTelemetryEvents:
    def test_telemetry_events_emitted(self, monkeypatch: pytest.MonkeyPatch):
        """契约16：pick / skip / stall 三事件各落具体 key-value。"""
        events = _spy_events(monkeypatch)

        # --- pick ---
        s = make_session()
        setattr(s, "current_options", ["x", "y", "z"])
        handle_message(s, "2", FakeInterviewer())
        pick = next(e for e in events if e["event"] == "option_pick")
        assert pick["session_id"] == "s1"
        assert pick["module"] == "IP定位"
        assert pick["subfield"] == "name"
        assert pick["option_index"] == 1

        # --- skip ---
        events.clear()
        s2 = make_session()
        handle_message(s2, "跳过", FakeInterviewer())
        skip = next(e for e in events if e["event"] == "skip")
        assert skip["session_id"] == "s1"
        assert skip["module"] == "IP定位"
        assert skip["subfield"] == "name"

        # --- stall ---
        events.clear()
        s3 = make_session()
        handle_message(s3, "嗯嗯随便说说", FakeInterviewer(guidance_reply="好。"))
        stall = next(e for e in events if e["event"] == "stall")
        assert stall["session_id"] == "s1"
        assert stall["module"] == "IP定位"
        assert stall["subfield"] == "name"
        assert stall["stall_count"] == 1
