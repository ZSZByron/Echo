"""T14: 图谱摘要构造器（graph_digest）+ interviewer prompt 注入。

契约锚点：
- 纯代码确定性装配（零 LLM）：同输入同输出。
- 三态：有图 / 无图（返回空，prompt 零变化）/ 部分图。
- G5 键域契约：摘要块不含裸 ``{模块id}.`` 形态（「」括注中文标签，D20⑤ 先例）。
- 只读消费：不写回任何状态（DN5 第四处 LLM 消费路径治理登记，见 decision-log）。
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from app.domains.creation.a1 import graph_digest
from app.domains.creation.a1.graph_digest import (
    GRAPH_DIGEST_BEGIN,
    GRAPH_DIGEST_END,
    build_graph_digest,
    graph_digest_block,
)
from app.domains.creation.seed.a1_question_tree import module_ids


# ---------------------------------------------------------------------------
# fixtures


def _node(nid: str, serial: str, desc: str = "") -> dict[str, Any]:
    return {
        "id": nid,
        "serial_number": serial,
        "level": serial.count("-") + 1,
        "description": desc,
        "status": "pending",
        "tier": None,
    }


@pytest.fixture
def full_graph() -> dict[str, Any]:
    """有图：模块节点 + 条目节点 + 深化条目（深度树）+ 边。"""
    nodes = {
        "力量体系": _node("力量体系", "1"),
        "力量体系.source": _node("力量体系.source", "1-1", "力量来源"),
        "d:力量体系.source:古神遗骸": _node(
            "d:力量体系.source:古神遗骸", "1-1-d1", "散落地表的遗骸"
        ),
        "d:力量体系.source:圣地还是矿脉": _node(
            "d:力量体系.source:圣地还是矿脉", "1-1-d2", "文明的态度"
        ),
        "历史时间线": _node("历史时间线", "2"),
        "d:历史时间线.timeline:崩塌之夜": _node(
            "d:历史时间线.timeline:崩塌之夜", "2-1-d1", "关键节点"
        ),
    }
    return {
        "scene_id": "a1_test",
        "nodes": nodes,
        "edges": [
            {
                "from_node_id": "力量体系",
                "to_node_id": "力量体系.source",
                "edge_type": "tree",
                "visual_description": "",
                "relation": "",
                "confidence": "",
                "confirmed": True,
            }
        ],
        "background_node_id": None,
    }


# ---------------------------------------------------------------------------
# 三态：有图


class TestDigestHasGraph:
    def test_has_graph_returns_compact_summary(self, full_graph):
        digest = build_graph_digest(full_graph)
        assert digest, "有图必须产出非空摘要"
        assert GRAPH_DIGEST_BEGIN in digest
        assert GRAPH_DIGEST_END in digest
        # 中文标签 + 「」括注（G5 键域安全形态）
        assert "「力量体系」" in digest
        # 深化条目标题进入摘要（紧凑摘要非全图——每模块关键条目）
        assert "古神遗骸" in digest
        assert "崩塌之夜" in digest
        # 边计数结构化标记
        assert "1" in digest

    def test_digest_never_contains_bare_module_key_forms(self, full_graph):
        digest = build_graph_digest(full_graph)
        for mid in module_ids():
            assert f"{mid}." not in digest, f"裸 {mid}. 形态违反 G5 键域契约"

    def test_digest_does_not_leak_raw_anchor_keys(self, full_graph):
        digest = build_graph_digest(full_graph)
        assert "力量体系.source" not in digest
        assert "历史时间线.timeline" not in digest

    def test_title_containing_module_key_form_is_wrapped(self):
        """深化标题里出现 {mid}. 字面量 → 必须被改写，G5 断言不破。"""
        graph = {
            "scene_id": "s",
            "nodes": {
                "d:力量体系.source:世界本体.悖论": _node(
                    "d:力量体系.source:世界本体.悖论", "1-1-d1"
                ),
            },
            "edges": [],
        }
        digest = build_graph_digest(graph)
        for mid in module_ids():
            assert f"{mid}." not in digest
        assert "世界本体" in digest  # 内容仍在（改写非丢弃）


# ---------------------------------------------------------------------------
# 三态：无图 / 部分图


class TestDigestNoGraph:
    @pytest.mark.parametrize(
        "payload",
        [None, "", {}, {"nodes": {}, "edges": []}, "junk-string", 42],
    )
    def test_no_graph_returns_empty(self, payload):
        assert build_graph_digest(payload) == ""
        assert graph_digest_block(payload) == []

    def test_malformed_nodes_returns_empty(self):
        assert build_graph_digest({"nodes": "not-a-dict", "edges": []}) == ""


class TestDigestPartialGraph:
    def test_partial_graph_module_entries_only(self):
        graph = {
            "scene_id": "s",
            "nodes": {
                "力量体系": _node("力量体系", "1"),
                "力量体系.source": _node("力量体系.source", "1-1", "力量来源"),
                "历史时间线": _node("历史时间线", "2"),
            },
            "edges": [],
        }
        digest = build_graph_digest(graph)
        assert GRAPH_DIGEST_BEGIN in digest
        assert "「力量体系」" in digest
        assert "「历史时间线」" in digest
        for mid in module_ids():
            assert f"{mid}." not in digest

    def test_unknown_module_ids_are_skipped_safely(self):
        graph = {
            "scene_id": "s",
            "nodes": {"不明模块": _node("不明模块", "9")},
            "edges": [],
        }
        digest = build_graph_digest(graph)
        # 未知 id 不崩、不裸露（降级为跳过或括注，均须无裸键形态）
        for mid in module_ids():
            assert f"{mid}." not in digest


# ---------------------------------------------------------------------------
# 确定性


class TestDigestDeterminism:
    def test_same_input_same_output(self, full_graph):
        assert build_graph_digest(full_graph) == build_graph_digest(full_graph)

    def test_node_dict_order_does_not_matter(self, full_graph):
        shuffled = copy.deepcopy(full_graph)
        keys = list(shuffled["nodes"].keys())
        shuffled["nodes"] = {
            k: shuffled["nodes"][k] for k in reversed(keys)
        }
        assert build_graph_digest(shuffled) == build_graph_digest(full_graph)

    def test_invited_context_is_deterministic_and_marked(self, full_graph):
        a = build_graph_digest(full_graph, invited=["力量体系"])
        b = build_graph_digest(full_graph, invited=["力量体系"])
        assert a == b
        assert "力量体系" in a


# ---------------------------------------------------------------------------
# interviewer prompt 注入


def _build_prompt_for(session: Any) -> str:
    from app.domains.creation.seed.a1_question_tree import (
        get_module,
        get_subfield,
    )

    m = get_module(session.current_module) or {}
    sf = get_subfield(session.current_module, session.current_subfield) or {}
    from app.domains.creation.a1.interviewer import RealLLMInterviewer

    return RealLLMInterviewer(provider=None)._build_prompt(m, sf, session)


def _bare_session() -> Any:
    from app.domains.creation.a1.guide_engine import A1Session

    return A1Session(session_id="a1_digest_test", user_id="u")


class TestPromptInjection:
    def test_no_graph_prompt_unchanged(self):
        """无图：prompt 与 HEAD 基线逐字节一致（零回归）。"""
        from unittest.mock import patch

        s = _bare_session()
        baseline = _build_prompt_for(s)
        with patch.object(
            graph_digest, "lookup_graph_json", return_value=None
        ):
            after = _build_prompt_for(s)
        assert after == baseline
        assert GRAPH_DIGEST_BEGIN not in after

    def test_graph_present_injects_digest_block(self, full_graph):
        from unittest.mock import patch

        s = _bare_session()
        with patch.object(
            graph_digest, "lookup_graph_json", return_value=full_graph
        ):
            prompt = _build_prompt_for(s)
        assert GRAPH_DIGEST_BEGIN in prompt
        assert GRAPH_DIGEST_END in prompt
        assert "古神遗骸" in prompt
        # G5 键域契约作用域 = 摘要块内（任务规格「块内不得出现裸键」）。
        # prompt 其余部分（可填字段清单）按 M2 设计必须裸露 module.subfield
        # 填充键（test_dynamic_invites G5 liveness after_invite 依赖），
        # 故只对 BEGIN..END 块断言（微调理由：实现与测试规格冲突记录）。
        block = prompt.split(GRAPH_DIGEST_BEGIN, 1)[1].split(GRAPH_DIGEST_END, 1)[0]
        for mid in module_ids():
            assert f"{mid}." not in block

    def test_injection_is_deterministic(self, full_graph):
        from unittest.mock import patch

        s = _bare_session()
        with patch.object(
            graph_digest, "lookup_graph_json", return_value=full_graph
        ):
            p1 = _build_prompt_for(s)
            p2 = _build_prompt_for(s)
        assert p1 == p2
