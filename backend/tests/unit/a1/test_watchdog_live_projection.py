"""看门狗 + live_projection 契约测试（M4b，plan TODO 5 §270-271）。

看门狗契约：
- 每 N 轮（可配，env A1_WATCHDOG_EVERY_N，默认 5）门禁检查；
- 会话后半程（进度过半）且配方内存在未访模块 → 确定性回归提示；
- 确定性代码，无 LLM 进控制流；提示内容确定性。

live_projection 契约：
- `a1/live_projection.py`，零新 LLM（无 provider 形参、无任何 LLM 调用）；
- 半成品 answers → 背景树 L0-L2 投影（bg 根 + L2 模块节点 + TREE 边）；
- 同输入 → 同投影（确定性快照）；披露"非定稿快照"。
"""
from typing import Any

from app.domains.creation.a1.guide_engine import A1Session, handle_message
from app.domains.creation.a1.interviewer import InterviewResult
from app.domains.creation.a1.live_projection import project_live
from app.domains.creation.a1.watchdog import check_watchdog
from app.domains.creation.shared.module_registry import RECIPES


def make_session(**kw: Any) -> A1Session:
    s = A1Session(session_id="s1", user_id="u1", ip_code="IP0001", **kw)
    s.recipe_id = "romance"
    s.recipe_modules = list(RECIPES["romance"].module_ids)
    return s


def _fill_half(s: A1Session) -> None:
    """填充前半模块（romance 配方 6 模块 → 前 3 个全答）。"""
    from app.domains.creation.seed.a1_question_tree import subs_for_module
    for mid in s.recipe_modules[:3]:
        for f in subs_for_module(mid):
            s.answers[f"{mid}.{f['id']}"] = f"{mid}的答案{f['id']}"


class TestWatchdog:
    def test_no_fire_when_all_visited(self):
        s = make_session()
        _fill_half(s)
        for mid in s.recipe_modules[3:]:
            from app.domains.creation.seed.a1_question_tree import subs_for_module
            f = subs_for_module(mid)[0]
            s.answers[f"{mid}.{f['id']}"] = "x"
        s.message_rounds = 5
        assert check_watchdog(s) is None

    def test_fires_second_half_with_unvisited_module(self):
        s = make_session()
        _fill_half(s)  # 后半 3 模块全未访
        s.message_rounds = 5  # N=5 的倍数 + 进度过半
        wd = check_watchdog(s)
        assert wd is not None
        assert "watchdog" == wd["kind"]
        assert wd["unvisited_modules"], "应列出未访模块"
        # 确定性提示内容
        assert s.recipe_modules[3] in [m["id"] for m in wd["unvisited_modules"]]
        assert "要不要" in wd["suggestion"]

    def test_not_fired_before_n_multiple(self):
        s = make_session()
        _fill_half(s)
        s.message_rounds = 4
        assert check_watchdog(s) is None

    def test_not_fired_first_half(self):
        s = make_session()
        s.message_rounds = 5
        # 0 模块完成 → 前半程，不触发
        assert check_watchdog(s) is None

    def test_deterministic_prompt_content(self):
        outs = []
        for _ in range(2):
            s = make_session()
            _fill_half(s)
            s.message_rounds = 5
            outs.append(check_watchdog(s))
        assert outs[0] == outs[1]

    def test_n_configurable_via_env(self, monkeypatch):
        monkeypatch.setenv("A1_WATCHDOG_EVERY_N", "2")
        s = make_session()
        _fill_half(s)
        s.message_rounds = 2
        assert check_watchdog(s) is not None

    def test_handle_message_attaches_watchdog(self):
        s = make_session()
        _fill_half(s)
        s.message_rounds = 4  # 本次消息后 = 5 → 触发
        out = handle_message(s, "随便聊聊", StubWd())
        assert out.get("watchdog") is not None


class StubWd:
    def interview(self, session: Any, text: str) -> InterviewResult:
        return InterviewResult(guidance_reply="好的。")

    def forced_allocate(self, session: Any, text: str) -> InterviewResult:
        return InterviewResult()

    def suggest_examples(self, module_id: str, subfield_id: str) -> list[str]:
        return []


class TestLiveProjection:
    def test_zero_llm_signature(self):
        import inspect
        sig = inspect.signature(project_live)
        assert "provider" not in sig.parameters
        assert "llm" not in sig.parameters

    def test_deterministic_snapshot(self):
        snapshots = []
        for _ in range(2):
            s = make_session()
            _fill_half(s)
            snapshots.append(project_live(s))
        assert snapshots[0] == snapshots[1]

    def test_projection_structure_l0_l2(self):
        s = make_session()
        _fill_half(s)
        proj = project_live(s)
        nodes = proj["nodes"]
        # bg 根（level 1）+ 已有答案模块节点（level 2）——L0-L2 投影
        levels = {n["level"] for n in nodes}
        assert levels <= {1, 2}
        bg = [n for n in nodes if n["level"] == 1]
        assert len(bg) == 1
        l2_ids = {n["id"] for n in nodes if n["level"] == 2}
        assert set(s.recipe_modules[:3]) <= l2_ids
        # TREE 边：bg → module
        assert all(e["edge_type"] == "tree" for e in proj["edges"])
        # 披露：非定稿快照
        assert "live" in proj["note"].lower() or "快照" in proj["note"]

    def test_empty_answers_projection_still_valid(self):
        s = make_session()
        proj = project_live(s)
        assert len(proj["nodes"]) == 1  # 只有 bg 根
        assert proj["edges"] == []

    def test_recipe_scoped(self):
        s = make_session()
        _fill_half(s)
        proj = project_live(s)
        l2_ids = {n["id"] for n in proj["nodes"] if n["level"] == 2}
        assert l2_ids == set(s.recipe_modules[:3])
