# -*- coding: utf-8 -*-
"""T10（批E-2）：波次二病理回归四幕 + 六通道/清单/灵感架交叉烟测。

四幕与既有覆盖的映射（全检口径——已覆盖处交叉引用，本文件补增量）：
- 幕一「老父亲」：test_list_append_loop.py::TestPathologicalFatherAppend 已锁
  （追加进清单/非三连问/非覆盖）——本文件不再重复。
- 幕二「支线结局」（2026-10-08 老伤："用支线结局说明主线成功"无处安放）：
  本文件新增——side_ending 槽存在性 + 值落库 + 无家兜底（灵感架不丢）。
- 幕三「这是分支」（P2 复合问句单槽收编）：本文件新增——
  branch_trees L2 双终点槽 success_path / failure_path 分流 + 旧字符串路径零扰动。
- 幕四「清单追加循环」：test_list_append_loop.py 已锁四出口/两档帽/归并提议
  ——本文件补一条全路径叙事（追加 ×3 → 直选打断复位）。
- 交叉烟测：本文件新增——一幕内 mirror → delivery(无家) → 直选 → 追加
  依次触发，通道状态互不复位污染（options_key 对称复位先例的全通道版）。

纪律：纯测试零生产代码；引擎级（A1Session + handle_message + stub）；
机制为批A-E 已落契约——GREEN 为预期，RED 即产品缺陷（停手报告不修码）。
"""
from __future__ import annotations

from app.domains.creation.a1.guide_engine import (
    A1Session,
    apply_l3_fill,
    handle_message,
    sync_position,
)
from app.domains.creation.a1.interviewer import (
    FakeInterviewer,
    InterviewFill,
    InterviewResult,
)
from app.domains.creation.a1.live_projection import compile_value_shape_edges
from app.domains.creation.seed.story_modules import THREE_TIER_TREE
from app.models.knowledge_graph import EdgeType


# ---------------------------------------------------------------------------
# 工具（stub 形状照 test_rack_recycle.py / test_list_append_loop.py 既有约定）
# ---------------------------------------------------------------------------


class _Stub:
    """handle_message 级 stub：可控通道旗标（批C/D stub 同形）。"""

    def __init__(
        self,
        *,
        delivery: bool = False,
        mirror: bool = False,
        fills: list[InterviewFill] | None = None,
        guidance_reply: str = "好的，继续",
    ):
        self.delivery = delivery
        self.mirror = mirror
        self.fills = fills or []
        self.guidance_reply = guidance_reply
        self.calls = 0

    def interview(self, session, text):  # noqa: ARG002
        self.calls += 1
        return InterviewResult.model_construct(
            fills=list(self.fills),
            guidance_reply=self.guidance_reply,
            delivery=self.delivery,
            mirror=self.mirror,
        )

    def suggest_examples(self, session, module_id, subfield_id):  # noqa: ARG002
        return []


def _story_session() -> A1Session:
    s = A1Session(
        session_id="t-wave2-pathology",
        user_id="u",
        recipe_id="plot",
        recipe_modules=["剧情", "角色"],
    )
    sync_position(s)
    return s


def _append(session: A1Session, value: str) -> dict:
    fake = FakeInterviewer(fills=[InterviewFill(
        module="角色", subfield="key_relations", value=value,
        relation="complement",
    )])
    return handle_message(session, value, fake)


def _l3_vs(l2_id: str, l3_id: str) -> str | None:
    for l1 in THREE_TIER_TREE:
        for l2 in l1["l2"]:
            if l2["id"] == l2_id:
                for l3 in l2["l3"]:
                    if l3["id"] == l3_id:
                        return str(l3.get("vs"))  # type: ignore[union-attr]
    return None


def _l3_child(session: A1Session, l2_id: str, l3_id: str):
    """批B 锚点寻址：answers[L2_id] 锚节点 → children 中 source==l3_id 的子节点。"""
    anchor = session.answers.get(l2_id)
    assert anchor is not None, f"锚 {l2_id} 未落库"
    node = next(
        (c for c in anchor.children if c.source == l3_id), None
    )
    assert node is not None, f"{l2_id} 下无 {l3_id} 子槽"
    return node


# ---------------------------------------------------------------------------
# 幕二：支线结局（老伤——"用支线结局说明主线成功"）
# ---------------------------------------------------------------------------


class TestActTwoSideEnding:
    def test_side_ending_slot_exists_from_to(self):
        """支线卡结局槽存在且为 ▶ 形（可承载"从铺垫到印证"结构）。"""
        assert _l3_vs("branch_card", "side_ending") == "from_to"

    def test_side_ending_value_lands(self):
        """「用支线结局说明主线成功」有结构化落点——非无处安放。"""
        s = _story_session()
        apply_l3_fill(s, "side_ending", {
            "from": "支线终幕的铺垫", "to": "主线成功被印证",
        })
        rendered = str(_l3_child(s, "branch_card", "side_ending"))
        assert "主线成功被印证" in rendered

    def test_side_ending_compiles_to_edges(self):
        """落库值随 T9 确定性编译产出（终端价值联动，不退化平文本）。"""
        s = _story_session()
        apply_l3_fill(s, "side_ending", {
            "from": "支线铺垫", "to": "主线印证",
        })
        _nodes, edges, _warnings = compile_value_shape_edges(s)
        assert any(
            e.edge_type == EdgeType.MIGRATION and "side_ending" in e.to_node_id
            for e in edges
        ), "支线结局未编译为迁移边"

    def test_unroutable_side_thought_never_lost(self):
        """LLM 判不出落点时兜底灵感架——老伤语义"永不丢失"联锁（批D 契约）。"""
        s = _story_session()
        handle_message(
            s, "我想用某条支线的结局说明主线成功", _Stub(delivery=True),
        )
        assert len(s.material_pool) == 1


# ---------------------------------------------------------------------------
# 幕三：这是分支（P2 双终点槽分流）
# ---------------------------------------------------------------------------


class TestActThreeBranchDual:
    def test_dual_endpoint_slots_exist(self):
        """branch_trees L2 = 双终点两槽，各 ▶ 形（复合问句不再挤单槽）。"""
        assert _l3_vs("branch_trees", "success_path") == "from_to"
        assert _l3_vs("branch_trees", "failure_path") == "from_to"

    def test_endpoints_split_into_distinct_slots(self):
        """「成功了…失败了他…」分流入两槽——不合并、不覆盖。"""
        s = _story_session()
        apply_l3_fill(s, "success_path", {
            "from": "孤身上路", "to": "成了新掌门", "trigger": "掌门信物现世",
        })
        apply_l3_fill(s, "failure_path", {
            "from": "孤身上路", "to": "客死他乡", "trigger": "追兵夜袭",
        })
        succ = _l3_child(s, "branch_trees", "success_path")
        fail = _l3_child(s, "branch_trees", "failure_path")
        assert succ is not fail, "双终点被并槽"
        assert "新掌门" in str(succ)
        assert "客死他乡" in str(fail)
        assert "新掌门" not in str(fail), "成功终点泄漏进失败槽"

    def test_dual_endpoints_compile_two_migration_edges(self):
        s = _story_session()
        apply_l3_fill(s, "success_path", {"from": "a", "to": "胜", "trigger": "t1"})
        apply_l3_fill(s, "failure_path", {"from": "a", "to": "败", "trigger": "t2"})
        _nodes, edges, _warnings = compile_value_shape_edges(s)
        tos = {
            e.to_node_id for e in edges if e.edge_type == EdgeType.MIGRATION
        }
        assert any("success_path:to" in t for t in tos), "成功终点未产迁移边"
        assert any("failure_path:to" in t for t in tos), "失败终点未产迁移边"

    def test_legacy_branch_trees_string_zero_disturbance(self):
        """旧会话 branch_trees 纯字符串（● 路径）零新边——P2 收编不砸旧数据。"""
        s = _story_session()
        s.answers["剧情.branch_trees"] = "成功端网但家散了；失败亡命江湖"
        _nodes, edges, _warnings = compile_value_shape_edges(s)
        assert not [
            e for e in edges
            if e.edge_type in (EdgeType.MIGRATION, EdgeType.LINKAGE)
        ], "旧字符串答案被误产新边（存量兼容破坏）"


# ---------------------------------------------------------------------------
# 幕四：清单追加循环全路径叙事（增量——分项已由 test_list_append_loop 锁）
# ---------------------------------------------------------------------------


class TestActFourFullLoopNarrative:
    def test_three_appends_then_direct_answer_interrupt(self):
        """追加 ×3 停驻 → 直选打断：清单保留 3 条 + 停驻复位（全路径一幕）。"""
        s = _story_session()
        for snippet in (
            "老父亲——他这辈子最亏欠的人",
            "叛出师门的师姐——互为唯一软肋",
            "线人的女儿——他偷偷照顾的孩子",
        ):
            _append(s, snippet)
        assert s.list_thread_key == "key_relations"
        node = s.answers.get("角色.key_relations")
        rendered = str(node)
        assert rendered.count("——") >= 3, f"三张卡丢失：{rendered!r}"
        # 直选打断：当前题挂选项，用户回数字 → 停驻复位、清单保留。
        s.current_options = ["缉毒警", "卧底", "逃犯"]
        s.options_key = ""
        handle_message(s, "1", _Stub())
        assert (s.list_thread_key, s.list_thread_turns) == ("", 0), (
            "直选打断未复位清单停驻"
        )
        assert str(s.answers.get("角色.key_relations")).count("——") >= 3, (
            "打断后清单条目丢失"
        )


# ---------------------------------------------------------------------------
# 交叉烟测：mirror → delivery(无家) → 直选 → 追加 一幕内混合触发
# ---------------------------------------------------------------------------


class TestCrossChannelSmoke:
    def test_mixed_sequence_no_state_pollution(self):
        s = _story_session()

        # ① 讨论镜像一轮：不落槽、进讨论态。
        out1 = handle_message(
            s, "她为什么一定要把剑挂在城门口？", _Stub(mirror=True),
        )
        assert s.answers == {}, "镜像轮误落槽"
        assert s.mirror_thread_active, "镜像态未置位"
        assert out1["next_question"] is not None, "镜像轮丢失当前题"

        # ② 投递无家：上灵感架（永不拒收）；镜像态话题离开复位。
        handle_message(
            s, "我总想象一个画面：满天都是断掉的剑。", _Stub(delivery=True),
        )
        assert len(s.material_pool) == 1, "无家素材未入灵感架"
        assert not s.mirror_thread_active, "投递轮未复位镜像态（话题离开出口）"

        # ③ 直选：当前题挂选项，数字直选消费。
        s.current_options = ["雨夜码头", "婚堂", "钟表铺"]
        s.options_key = ""
        handle_message(s, "2", _Stub())
        assert not s.current_options, "直选后选项未消费复位"
        assert len(s.material_pool) == 1, "直选轮污染灵感架"

        # ④ 清单追加：停驻置位；前三步状态不被误复位。
        _append(s, "老父亲——他这辈子最亏欠的人")
        assert s.list_thread_key == "key_relations", "追加未停驻"
        assert len(s.material_pool) == 1, "追加轮污染灵感架"
        assert not s.mirror_thread_active, "追加轮误置镜像态"
        assert str(s.answers.get("角色.key_relations")), "追加未落清单"
