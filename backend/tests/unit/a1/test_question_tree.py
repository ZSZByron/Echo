"""Tests for the A1 two-layer question tree."""
from app.domains.creation.seed import a1_question_tree
from app.domains.creation.seed.a1_question_tree import (
    MODULES,
    all_subfield_keys,
    clip_answer,
    first_module,
    first_subfield,
    get_subfield,
    is_finalizable,
    is_module_done,
    is_module_over_half,
    is_truthy_answer,
    module_done_ratio,
    module_ids,
    next_subfield,
    total_subfield_count,
)


class TestModuleStructure:
    def test_10_modules(self):
        assert len(MODULES) == 10

    def test_module_ids_match_spec(self):
        expected = [
            "IP定位", "世界本体", "力量体系", "地理空间", "文明与社会",
            "历史时间线", "视觉设计", "玩法设计DNA", "骰子设定", "设定边界",
        ]
        assert module_ids() == expected

    def test_each_module_has_2_to_5_subs(self):
        for m in MODULES:
            n = len(m["fields"])
            assert 2 <= n <= 5, f"{m['id']} has {n} subfields"

    def test_total_sub_count_in_range(self):
        assert 25 <= total_subfield_count() <= 40

    def test_all_sub_keys_unique(self):
        keys = all_subfield_keys()
        assert len(keys) == len(set(keys))


class TestSubItems:
    def test_first_sub_is_ip_name(self):
        m = first_module()
        sub = first_subfield(m["id"])
        assert m["id"] == "IP定位"
        assert sub["id"] == "name"

    def test_get_sub_returns_correct_pair(self):
        sub = get_subfield("力量体系", "acquire")
        assert sub is not None
        assert sub["id"] == "acquire"
        assert sub["label"] == "获取方式"

    def test_get_sub_unknown_returns_none(self):
        assert get_subfield("力量体系", "nonexistent") is None

    def test_next_sub_advances(self):
        m = first_module()
        sub = first_subfield(m["id"])
        nxt = next_subfield(m["id"], sub["id"])
        assert nxt is not None
        assert nxt["id"] == "concept"

    def test_next_sub_at_end_returns_none(self):
        last_key = all_subfield_keys()[-1]
        # Parse last key to get module_id and subfield_id
        parts = last_key.split(".", 1)
        assert next_subfield(parts[0], parts[1]) is None

    def test_next_sub_none_returns_first(self):
        m = first_module()
        assert next_subfield(m["id"], None) == first_subfield(m["id"])


class TestModuleDone:
    def test_module_done_when_all_subs_answered(self):
        answers = {"IP定位.name": "a", "IP定位.concept": "b", "IP定位.world_type": "c", "IP定位.core_experience": "d"}
        assert is_module_done("IP定位", answers) is True

    def test_module_not_done_when_missing_sub(self):
        answers = {"IP定位.name": "a"}
        assert is_module_done("IP定位", answers) is False

    def test_module_not_done_when_empty(self):
        assert is_module_done("IP定位", {}) is False


class TestModuleOverHalf:
    """Finalize gate: strictly more than 50% of subfields answered."""

    def test_ratio_empty_is_zero(self):
        assert module_done_ratio("IP定位", {}) == 0.0

    def test_ratio_unknown_module_is_zero(self):
        assert module_done_ratio("不存在", {"IP定位.name": "a"}) == 0.0

    def test_over_half_true_when_majority_answered(self):
        # IP定位 has 4 subfields -> 3 answered = 75% > 50%
        answers = {"IP定位.name": "a", "IP定位.concept": "b", "IP定位.world_type": "c"}
        assert is_module_over_half("IP定位", answers) is True

    def test_over_half_false_at_exactly_half(self):
        # 2 of 4 = exactly 50% -> NOT finalizable (strictly greater required)
        answers = {"IP定位.name": "a", "IP定位.concept": "b"}
        assert is_module_over_half("IP定位", answers) is False

    def test_over_half_true_when_half_plus_one_on_odd_module(self):
        # Find a module with an odd subfield count; (n+1)/2 answered > 50%.
        odd = next((m for m in MODULES if len(m["fields"]) % 2 == 1), None)
        if odd is None:
            import pytest
            pytest.skip("no module with odd subfield count")
        need = len(odd["fields"]) // 2 + 1
        answers = {f"{odd['id']}.{f['id']}": "x" for f in odd["fields"][:need]}
        assert is_module_over_half(odd["id"], answers) is True

    def test_finalizable_requires_every_module_over_half(self):
        # Answer >50% in every module except the last one.
        answers: dict[str, str] = {}
        for m in MODULES:
            fields = m["fields"]
            need = len(fields) // 2 + 1
            for f in fields[:need]:
                answers[f"{m['id']}.{f['id']}"] = "x"
        assert is_finalizable(answers) is True

        # Drop one answer from the first module -> that module falls to
        # 50% or below -> not finalizable anymore.
        first = MODULES[0]
        answers.pop(f"{first['id']}.{first['fields'][0]['id']}")
        assert is_finalizable(answers) is False

    def test_finalizable_false_when_empty(self):
        assert is_finalizable({}) is False


class TestSeverityRemoved:
    """④稿去 severity：枚举与 hint 注记已整体移除（key_nodes 存自然语言，
    严重度归 graphify 推断）。用户侧文案不得再出现 severity 标注要求。"""

    def test_severity_values_enum_removed(self):
        assert not hasattr(a1_question_tree, "SEVERITY_VALUES")

    def test_no_severity_markers_in_copy(self):
        for module in MODULES:
            for field in module["fields"]:
                hint = field.get("hint", "")
                assert "severity" not in hint.lower()
                for val in ("COSMIC", "MAJOR", "REGIONAL", "MINOR"):
                    assert val not in hint, f"{module['id']}.{field['id']} 仍含 {val}"


class TestTruthyAnswer:
    """J1 答案真值闸 canonical 谓词（2-A1-v0.5.1 §3 J1）.

    占位词典精确匹配（归一化后）+ 空串/None → False；
    真实语义答案（含"无"、含占位词作子串的长句）→ True。
    """

    def test_none_and_empty_are_falsy(self):
        assert is_truthy_answer(None) is False
        assert is_truthy_answer("") is False
        assert is_truthy_answer("   ") is False
        assert is_truthy_answer("\t\n") is False

    def test_placeholder_dictionary_hits(self):
        for value in [
            "未提及", "未明确", "未知", "缺少依据", "未说明", "未指定",
            "未确定", "未定义", "未给出", "未提供", "未回答", "未涉及",
            "不明确", "不适用", "不详", "暂无", "暂缺", "无依据",
            "待定", "待补充", "待确认", "待填写", "无相关内容",
            "文中未提及", "原文未提及", "用户未提及", "资料未提及",
            "N/A", "n/a", "NA", "na", "N.A.", "None", "none", "null",
            "NULL", "nil", "unknown", "Unknown", "UNKNOWN",
            "not mentioned", "Not Specified", "unspecified",
            "not applicable", "no data", "no evidence", "tbd", "TBD",
            "todo", "TODO", "missing", "-", "——", "———",
        ]:
            assert is_truthy_answer(value) is False, value

    def test_placeholder_variants_normalized(self):
        # 全角 Ｎ／Ａ、包裹符号、首尾标点、前后空白都归一化后命中
        assert is_truthy_answer("Ｎ／Ａ") is False
        assert is_truthy_answer("（暂无）") is False
        assert is_truthy_answer("【未知】") is False
        assert is_truthy_answer("未知。") is False
        assert is_truthy_answer("，缺少依据！") is False
        assert is_truthy_answer("  Not Mentioned.  ") is False
        assert is_truthy_answer("「未提及」") is False

    def test_real_answers_are_truthy(self):
        for value in [
            "蒸汽朋克浮空城",
            "无",  # 合法否定答案（如"是否有神"→"无"），词典保守不收
            "未知种族的迁徙历史",  # 占位词作子串，非占位答案
            "尚未确定的三个王位继承人",  # 同上
            "N/A 机制不存在，灵气即货币",
            "0",
        ]:
            assert is_truthy_answer(value) is True, value


class TestGateCountsOnlyTruthy:
    """J1：门禁计数从 key 存在性升级为真值感知（治级联 A 的放行半边）."""

    def test_ratio_ignores_placeholder_and_empty_values(self):
        answers = {
            "IP定位.name": "未提及",
            "IP定位.concept": "",
            "IP定位.world_type": "N/A",
            "IP定位.core_experience": "浮空城",
        }
        # 只有 1 个真值 → 1/4 = 0.25（旧逻辑按 key 存在算 4/4 = 1.0）
        assert module_done_ratio("IP定位", answers) == 0.25

    def test_module_done_requires_truthy_values(self):
        answers = {"IP定位.name": "未知", "IP定位.concept": "暂无"}
        assert is_module_done("IP定位", answers) is False

    def test_finalizable_all_placeholders_is_false(self):
        answers = dict.fromkeys(all_subfield_keys(), "缺少依据")
        assert is_finalizable(answers) is False

    def test_finalizable_all_empty_strings_is_false(self):
        answers = dict.fromkeys(all_subfield_keys(), "")
        assert is_finalizable(answers) is False

    def test_finalizable_mixed_placeholders_count_truthy_only(self):
        # 每模块 >50% 真值 + 少量占位 → 可定稿；占位字段不计入分子
        answers: dict[str, str] = {}
        for m in MODULES:
            fields = m["fields"]
            need = len(fields) // 2 + 1
            for f in fields[:need]:
                answers[f"{m['id']}.{f['id']}"] = "真实答案"
            for f in fields[need:]:
                answers[f"{m['id']}.{f['id']}"] = "未提及"
        assert is_finalizable(answers) is True
        # 把任一模块的一个真值换成占位 → 该模块跌回 ≤50% → 不可定稿
        first = MODULES[0]
        answers[f"{first['id']}.{first['fields'][0]['id']}"] = "未提及"
        assert is_finalizable(answers) is False


class TestClipAnswer:
    """J4 预算护栏：answer value ≤2000 字（超限截断，配 J3 披露）."""

    def test_short_answer_unchanged(self):
        value = "蒸汽朋克浮空城" * 100  # 800 字
        clipped, was_clipped = clip_answer(value)
        assert clipped == value
        assert was_clipped is False

    def test_exact_limit_unchanged(self):
        value = "灵" * 2000
        clipped, was_clipped = clip_answer(value)
        assert clipped == value
        assert was_clipped is False

    def test_over_limit_clipped_to_2000(self):
        value = "灵" * 2500
        clipped, was_clipped = clip_answer(value)
        assert len(clipped) == 2000
        assert clipped == value[:2000]
        assert was_clipped is True

    def test_custom_limit(self):
        clipped, was_clipped = clip_answer("abcdefgh", limit=3)
        assert clipped == "abc"
        assert was_clipped is True
