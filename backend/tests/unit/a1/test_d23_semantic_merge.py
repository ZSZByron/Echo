"""D23 语义分流 + 层级条目 — C10 病理回归 / C11 渲染确定性.

对应问题说明书（修订 2）四撞墙病理的引擎级回归：
1) 等价新说法被字符串差异拦截（躺平 vs 平凡的度过一生）→ equivalent 自动合并
2) 补充新信息在单字符串槽无处安放（老父亲 → key_relations 第二条）→ complement 子条目
3) 循环三连问 → 合并后落定值参与 Branch 2 同值短路
4) 兜底与护栏：
   - relation 缺失/未知 → 现行拦截行为不变（存量保护）
   - 真矛盾 → 三选一提案，不豁免（question_text 用 LLM 人话问题）
   - 自动合并不消耗 merge_counts 上限
   - 子条目上限 6（拍板 4）
   - undo 恢复旧值（幂等）
"""
import hashlib

from app.domains.creation.a1.guide_engine import (
    A1Session,
    AnswerNode,
    _apply_fills,
    answer_view,
    is_multi_value,
    resolve_proposal,
    undo_auto_merge,
)
from app.domains.creation.a1.interviewer import (
    FakeInterviewer,
    InterviewFill,
)

DESIRE = "角色.desire"
KEY_REL = "角色.key_relations"


def make_session() -> A1Session:
    return A1Session(session_id="s1", user_id="u1", ip_code="IP0065")


def _proposal_key(module: str, subfield: str, new: str) -> str:
    h = hashlib.md5(new.encode()).hexdigest()[:8]
    return f"{module}.{subfield}:{h}"


class TestEquivalentAutoMerge:

    def test_equivalent_merges_without_proposal(self):
        s = make_session()
        s.answers[DESIRE] = "最想躺平，但家里条件不好，整天当牛马"
        merged_text = "平凡的度过一生——最想躺平，但家里条件不好，整天当牛马"
        fills = [InterviewFill(
            module="角色", subfield="desire", value="平凡的度过一生",
            relation="equivalent", merged_value=merged_text,
        )]
        file_diff, proposals = _apply_fills(s, fills)

        assert proposals == []
        assert s.pending_proposals == {}
        assert answer_view(s.answers[DESIRE]) == merged_text
        assert len(file_diff) == 1
        assert len(s.auto_merge_log) == 1
        rec = s.auto_merge_log[0]
        assert rec["token"]
        assert rec["merged"] == merged_text
        assert rec["field_key"] == DESIRE

    def test_equivalent_missing_relation_falls_back_to_current_behavior(self):
        s = make_session()
        s.answers[DESIRE] = "最想躺平"
        fills = [InterviewFill(module="角色", subfield="desire",
                               value="平凡的度过一生")]
        file_diff, proposals = _apply_fills(s, fills)

        assert len(proposals) == 1
        assert answer_view(s.answers[DESIRE]) == "最想躺平"
        key = _proposal_key("角色", "desire", "平凡的度过一生")
        assert key in s.pending_proposals

    def test_auto_merge_not_consumed_by_cap(self):
        s = make_session()
        s.answers[DESIRE] = "躺平"
        for i in range(5):
            fills = [InterviewFill(
                module="角色", subfield="desire", value=f"换述{i}",
                relation="equivalent", merged_value=f"躺平＋细节{i}",
            )]
            _apply_fills(s, fills)

        assert s.merge_counts == {}
        assert s.pending_proposals == {}

    def test_undo_restores_previous_value_idempotent(self):
        s = make_session()
        s.answers[DESIRE] = "最想躺平"
        fills = [InterviewFill(
            module="角色", subfield="desire", value="平凡的度过一生",
            relation="equivalent", merged_value="融合后",
        )]
        _apply_fills(s, fills)
        token = s.auto_merge_log[0]["token"]

        result = undo_auto_merge(s, token)
        assert result["restored"] is True
        assert answer_view(s.answers[DESIRE]) == "最想躺平"
        assert s.auto_merge_log == []

        r2 = undo_auto_merge(s, token)
        assert r2["restored"] is False

    def test_equivalent_merged_value_missing_falls_back_to_concat(self):
        s = make_session()
        s.answers[DESIRE] = "躺平"
        fills = [InterviewFill(
            module="角色", subfield="desire", value="平凡的度过一生",
            relation="equivalent",
        )]
        _apply_fills(s, fills)
        assert answer_view(s.answers[DESIRE]) == "躺平；平凡的度过一生"


class TestComplementHierarchy:

    def test_complement_appends_child_on_multi_field(self):
        s = make_session()
        s.answers[KEY_REL] = "与大道系统：从对抗打脸到调教重塑"
        fills = [InterviewFill(
            module="角色", subfield="key_relations",
            value="与老父亲：他在老家务农，只有这一个亲人",
            relation="complement",
        )]
        file_diff, proposals = _apply_fills(s, fills)

        assert proposals == []
        node = s.answers[KEY_REL]
        assert isinstance(node, AnswerNode)
        assert node.text == "与大道系统：从对抗打脸到调教重塑"
        assert len(node.children) == 1
        assert node.children[0].text == "与老父亲：他在老家务农，只有这一个亲人"
        view = answer_view(node)
        assert "大道系统" in view and "老父亲" in view

    def test_complement_on_scalar_field_goes_proposal_with_llm_question(self):
        s = make_session()
        s.answers[DESIRE] = "躺平"
        fills = [InterviewFill(
            module="角色", subfield="desire", value="还想买房",
            relation="complement",
            conflict_question="之前说躺平，现在多了买房——以新的为准，还是都要，还是先放着？",
        )]
        file_diff, proposals = _apply_fills(s, fills)

        assert len(proposals) == 1
        assert proposals[0].question_text.startswith("之前说躺平")
        assert answer_view(s.answers[DESIRE]) == "躺平"

    def test_children_cap_six(self):
        s = make_session()
        s.answers[KEY_REL] = AnswerNode(
            text="主线",
            children=[AnswerNode(text=f"关系{i}") for i in range(6)],
        )
        fills = [InterviewFill(
            module="角色", subfield="key_relations", value="第七段",
            relation="complement",
        )]
        file_diff, proposals = _apply_fills(s, fills)

        assert len(proposals) == 1
        node = s.answers[KEY_REL]
        assert len(node.children) == 6

    def test_equivalent_with_merge_target_merges_into_child(self):
        s = make_session()
        s.answers[KEY_REL] = AnswerNode(text="", children=[
            AnswerNode(text="与老父亲：务农"),
            AnswerNode(text="与大道系统：对抗"),
        ])
        fills = [InterviewFill(
            module="角色", subfield="key_relations",
            value="父亲年纪大了",
            relation="equivalent",
            merge_target="与老父亲",
            merged_value="与老父亲：务农，父亲年纪大了",
        )]
        _apply_fills(s, fills)

        node = s.answers[KEY_REL]
        assert node.children[0].text == "与老父亲：务农，父亲年纪大了"
        assert node.children[1].text == "与大道系统：对抗"

    def test_legacy_str_promotes_to_node_on_complement(self):
        s = make_session()
        s.answers[KEY_REL] = "旧的一段"
        fills = [InterviewFill(
            module="角色", subfield="key_relations", value="新的一段",
            relation="complement",
        )]
        _apply_fills(s, fills)
        node = s.answers[KEY_REL]
        assert isinstance(node, AnswerNode)
        assert node.text == "旧的一段"
        assert [c.text for c in node.children] == ["新的一段"]


class TestConflictPathKeepsProposal:

    def test_conflict_relation_keeps_proposal_with_llm_question(self):
        s = make_session()
        s.answers["IP定位.name"] = "星陨大陆"
        fills = [InterviewFill(
            module="IP定位", subfield="name", value="星穹大陆",
            relation="conflict",
            conflict_question="之前是星陨大陆，现在是星穹大陆——以哪个为准？",
        )]
        file_diff, proposals = _apply_fills(s, fills)

        assert len(proposals) == 1
        assert proposals[0].question_text == (
            "之前是星陨大陆，现在是星穹大陆——以哪个为准？"
        )
        assert s.answers["IP定位.name"] == "星陨大陆"

    def test_unknown_relation_falls_back(self):
        s = make_session()
        s.answers["IP定位.name"] = "星陨大陆"
        fills = [InterviewFill(
            module="IP定位", subfield="name", value="星穹大陆",
            relation="banana",
        )]
        file_diff, proposals = _apply_fills(s, fills)

        assert len(proposals) == 1
        assert proposals[0].question_text == ""

    def test_resolve_merge_on_multi_field_appends_child(self):
        s = make_session()
        s.answers[KEY_REL] = "与大道系统：对抗"
        fills = [InterviewFill(
            module="角色", subfield="key_relations", value="与师姐：互为软肋",
            relation="conflict", conflict_question="两段关系都要吗？",
        )]
        _apply_fills(s, fills)
        key = _proposal_key("角色", "key_relations", "与师姐：互为软肋")

        result = resolve_proposal(s, key, "merge")

        assert result["applied"] is True
        node = s.answers[KEY_REL]
        assert isinstance(node, AnswerNode)
        assert node.text == "与大道系统：对抗"
        assert [c.text for c in node.children] == ["与师姐：互为软肋"]

    def test_resolve_merge_on_scalar_keeps_concat(self):
        s = make_session()
        s.answers["IP定位.name"] = "星陨大陆"
        fills = [InterviewFill(module="IP定位", subfield="name",
                               value="星穹大陆")]
        _apply_fills(s, fills)
        key = _proposal_key("IP定位", "name", "星穹大陆")

        resolve_proposal(s, key, "merge")

        assert s.answers["IP定位.name"] == "星陨大陆；星穹大陆"


class TestAnswerViewDeterminism:

    def test_str_passthrough(self):
        assert answer_view("abc") == "abc"

    def test_node_render_stable_and_roundtrip(self):
        node = AnswerNode(
            text="a",
            children=[
                AnswerNode(text="b"),
                AnswerNode(text="c", children=[AnswerNode(text="d")]),
            ],
        )
        assert answer_view(node) == "a；b；c；d"
        roundtrip = AnswerNode.model_validate(node.model_dump())
        assert answer_view(roundtrip) == answer_view(node)

    def test_legacy_str_equals_leaf_node_render(self):
        assert answer_view("a") == answer_view(AnswerNode(text="a"))

    def test_empty_parts_skipped(self):
        node = AnswerNode(text="", children=[AnswerNode(text="b")])
        assert answer_view(node) == "b"


class TestMultiValueFlag:

    def test_key_relations_multi_desire_scalar(self):
        assert is_multi_value("角色", "key_relations") is True
        assert is_multi_value("角色", "desire") is False


class TestHandleMessageDisclosure:

    def test_auto_merges_surface_and_question_not_suspended(self):
        from app.domains.creation.a1.guide_engine import handle_message

        s = make_session()
        s.answers[DESIRE] = "最想躺平，但家里条件不好，整天当牛马"
        s.current_module = "角色"
        s.current_subfield = "desire"
        fills = [InterviewFill(
            module="角色", subfield="desire", value="平凡的度过一生",
            relation="equivalent",
            merged_value="平凡的度过一生——最想躺平，但家里条件不好，整天当牛马",
        )]

        out = handle_message(
            s, "欲望就是平凡的度过一生！", FakeInterviewer(fills=fills),
        )

        assert "auto_merges" in out
        assert len(out["auto_merges"]) == 1
        assert out["auto_merges"][0]["merged"]
        assert out["next_question"] is not None

    def test_merged_value_short_circuits_repeat_fills(self):
        s = make_session()
        s.answers[DESIRE] = "躺平"
        fills = [InterviewFill(
            module="角色", subfield="desire", value="平凡的度过一生",
            relation="equivalent", merged_value="躺平＝平凡的度过一生",
        )]
        _apply_fills(s, fills)

        again = [InterviewFill(
            module="角色", subfield="desire", value="躺平＝平凡的度过一生",
        )]
        file_diff, proposals = _apply_fills(s, again)

        assert proposals == []
        assert s.auto_merge_log and s.merge_counts == {}
