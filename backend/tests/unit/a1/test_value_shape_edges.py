"""批E-1 红测：值形态 → 图谱边确定性编译 + 上传值形状联动 + 未知边类型降级。

契约面（TDD 红→绿）：
- ▶（from_to 全填）→ 迁移边 transition：from 态节点 → to 态节点，trigger 落边属性；
- ▶ 半填（仅 to）→ 仍产迁移边（from 缺省节点 + 披露警告）；
- ⇄（dim_dir）→ 衔接边 linkage：dimension+direction 落边语义；
  拒绝线（direction=拒绝 / magnitude=0 / ▶ from==to）语义保留（边上注记）；
- 支线卡衔接（side_link_mode ● + side_link_point ▶）→ 入概念边家族（linkage）；
- ●（point）→ 现行 flat NL 路径字节不变（零新边零新节点）；
- 旧会话回归锁：无形状 fills → graphify+确定性编译输出与升级前字节一致；
- 上传联动：worldview_upload 预填 key_nodes 含 A→B 文本 → ▶ shape 包装；
  点类字段 = ● 纯文本；
- 未知边类型降级：图谱装配（from_dict）遇未注册 edge_type → 跳过/降级标记，
  不抛异常（s2-unknown-enum-degrade 先例）。

铁律：LLM 只产 SIR 五字段；transition/linkage 边由确定性编译从 vs 形状装配，
绝不进 LLM prompt 词表（build_graphify_prompt 不含新边类型字样）。
"""
from __future__ import annotations

import hashlib
import importlib
import json
from typing import Any

import pytest


def _mod(name: str) -> Any:
    """导入域内模块；未实现 → fail（红态为 failed 而非 error）。"""
    try:
        return importlib.import_module(name)
    except ImportError as exc:  # pragma: no cover - 红态路径
        pytest.fail(f"批E-1 模块未实现：{name}（{exc}）")


# ---------------------------------------------------------------------------
# 测试会话构造
# ---------------------------------------------------------------------------


def _mk_session(answers: dict[str, Any]) -> Any:
    from app.domains.creation.a1.guide_engine import A1Session

    session = A1Session(session_id="s_e1", user_id="u_e1", ip_code="IP0001")
    session.answers = answers
    return session


def _fill(session: Any, l3_id: str, value: Any) -> None:
    from app.domains.creation.a1.guide_engine import apply_l3_fill

    apply_l3_fill(session, l3_id, value)


def _compile(session: Any) -> tuple[list, list, list]:
    mod = _mod("app.domains.creation.a1.value_shape_edges")
    return mod.compile_value_shape_edges(session)


# ---------------------------------------------------------------------------
# 1. ▶ 全填 → 迁移边（trigger 为边属性）
# ---------------------------------------------------------------------------


class TestTransitionEdge:
    def test_full_from_to_compiles_transition_edge(self):
        session = _mk_session({})
        _fill(session, "main_plot", {
            "from": "王朝初立", "to": "帝国崩塌", "trigger": "弑神事件",
        })
        nodes, edges, warnings = _compile(session)
        assert len(edges) == 1
        e = edges[0]
        assert e.edge_type == "transition"
        assert e.from_node_id == "v:历史时间线.main_plot:from"
        assert e.to_node_id == "v:历史时间线.main_plot:to"
        assert e.relation == "transition"
        assert "弑神事件" in e.visual_description
        from_ids = {n.id for n in nodes}
        assert {"v:历史时间线.main_plot:from", "v:历史时间线.main_plot:to"} <= from_ids
        from_node = next(n for n in nodes if n.id == "v:历史时间线.main_plot:from")
        assert from_node.description == "王朝初立"
        to_node = next(n for n in nodes if n.id == "v:历史时间线.main_plot:to")
        assert to_node.description == "帝国崩塌"
        assert warnings == []

    def test_half_filled_to_only_still_transition(self):
        """半填（仅 to）→ 仍产迁移边（from 缺省 + 披露）。"""
        session = _mk_session({})
        _fill(session, "main_plot", {"to": "帝国崩塌"})
        nodes, edges, warnings = _compile(session)
        assert len(edges) == 1
        e = edges[0]
        assert e.edge_type == "transition"
        assert e.from_node_id == "v:历史时间线.main_plot:from"
        assert e.to_node_id == "v:历史时间线.main_plot:to"
        from_node = next(n for n in nodes if n.id.endswith(":from"))
        assert "前态缺省" in from_node.description
        assert any("前态缺省" in w for w in warnings)


# ---------------------------------------------------------------------------
# 2. ⇄ → 衔接边（dimension+direction 落边语义；拒绝线保留）
# ---------------------------------------------------------------------------


class TestLinkageEdge:
    def test_dim_dir_compiles_linkage_edge(self):
        session = _mk_session({})
        _fill(session, "relation_card_format", {
            "dimension": "信任", "direction": "变强", "magnitude": 2,
        })
        nodes, edges, warnings = _compile(session)
        assert len(edges) == 1
        e = edges[0]
        assert e.edge_type == "linkage"
        assert e.relation == "linkage"
        assert "信任" in e.visual_description
        assert "变强" in e.visual_description
        # 两端均为该位点派生的状态节点
        assert e.from_node_id == "v:key_relations.relation_card_format:from"
        assert e.to_node_id == "v:key_relations.relation_card_format:to"

    def test_refusal_line_semantics_preserved(self):
        """拒绝线：direction=拒绝 / magnitude=0 → 语义在边上保留，不丢边。"""
        session = _mk_session({})
        _fill(session, "relation_card_format", {
            "dimension": "敌意", "direction": "拒绝", "magnitude": 0,
        })
        nodes, edges, _warnings = _compile(session)
        assert len(edges) == 1
        assert edges[0].edge_type == "linkage"
        assert "拒绝线" in edges[0].visual_description

    def test_refusal_line_from_to_equal(self):
        """▶ "从X到X"（幅度 0 特例）→ 迁移边上保留拒绝线语义。"""
        session = _mk_session({})
        _fill(session, "arc_refuse", {"from": "原地踏步", "to": "原地踏步"})
        _nodes, edges, _warnings = _compile(session)
        assert len(edges) == 1
        assert edges[0].edge_type == "transition"
        assert "拒绝线" in edges[0].visual_description


# ---------------------------------------------------------------------------
# 3. 支线卡衔接 → 概念边家族（linkage 扩展）
# ---------------------------------------------------------------------------


class TestSideCardLinkage:
    def test_side_link_mode_and_point_join_concept_edge_family(self):
        session = _mk_session({})
        _fill(session, "side_link_mode", "并入主线第三幕")
        _fill(session, "side_link_point", {"from": "邂逅", "to": "主线合流"})
        _nodes, edges, _warnings = _compile(session)
        # side_link_point 自身的 ▶ 迁移边 + 支线卡衔接的概念边
        link_edges = [e for e in edges
                      if e.from_node_id == "branch_card.side_link_point"]
        assert len(link_edges) == 1
        e = link_edges[0]
        assert e.edge_type == "linkage"
        assert e.to_node_id == "story_line"
        assert "并入主线第三幕" in e.visual_description
        assert "主线合流" in e.visual_description

    def test_side_link_mode_alone_no_concept_edge(self):
        """仅有衔接方式、缺衔接点 → 不产概念边（半边不硬接）。"""
        session = _mk_session({})
        _fill(session, "side_link_mode", "并入主线")
        _nodes, edges, _warnings = _compile(session)
        assert not any(
            e.from_node_id == "branch_card.side_link_point" for e in edges
        )


# ---------------------------------------------------------------------------
# 4. ● 点形态：现行 flat NL 路径零扰动
# ---------------------------------------------------------------------------


class TestPointNoEdge:
    def test_point_value_compiles_nothing(self):
        session = _mk_session({"ip.name": "星陨大陆"})
        _fill(session, "name", "星陨大陆")  # ● 位点
        nodes, edges, warnings = _compile(session)
        assert nodes == []
        assert edges == []
        assert warnings == []

    def test_plain_string_from_to_site_degrades_to_point(self):
        """vs=from_to 位点的旧式纯文本值（无形状）→ 不产边（●降级）。"""
        session = _mk_session({"历史时间线.main_plot": "王朝建立到帝国崩塌"})
        nodes, edges, warnings = _compile(session)
        assert nodes == []
        assert edges == []
        assert warnings == []

    def test_dual_shape_wave3_no_edge(self):
        """⇉ dual → 渲染零实现（波次三），本批不产边。"""
        session = _mk_session({})
        _fill(session, "growth", {"point": "变强", "change": {"速度": "快"}})
        nodes, edges, _warnings = _compile(session)
        assert nodes == []
        assert edges == []


# ---------------------------------------------------------------------------
# 5. 旧会话回归锁：无形状 fills → 装配输出与升级前字节一致（0 diff）
# ---------------------------------------------------------------------------


class TestOldSessionRegressionLock:
    def _fixture_session(self) -> Any:
        return _mk_session({
            "ip.name": "星陨大陆",
            "世界本体.origin": "星核炸裂后形成的大陆",
            "历史时间线.key_nodes": "王朝建立→帝国崩塌",  # 旧式纯文本，无形状
        })

    def test_compile_empty_for_no_shape_session(self):
        nodes, edges, warnings = _compile(self._fixture_session())
        assert nodes == []
        assert edges == []
        assert warnings == []

    def test_build_graph_output_byte_identical(self):
        """预部署 fixture → graphify+确定性编译输出与升级前快照字节一致。"""
        routes = importlib.import_module("app.api.a1_routes")
        session = self._fixture_session()
        graph, _valid = routes._build_graph(session, {})
        payload = json.dumps(graph.to_dict(), ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        # 升级前基线快照（af5f565 时代行为，实测固化）
        assert digest == REGRESSION_SNAPSHOT_SHA
        assert not any(
            str(getattr(e.edge_type, "value", e.edge_type)) in ("transition", "linkage")
            for e in graph.edges
        )
        assert not any(nid.startswith("v:") for nid in graph.nodes)


REGRESSION_SNAPSHOT_SHA = (
    "fe3545a8ef0993f590700aaedcb0f1c288b9c386e14507be554907568afb5f82"
)


# ---------------------------------------------------------------------------
# 6. 上传联动：key_nodes ▶ 包装；点类字段纯文本
# ---------------------------------------------------------------------------


class _FakeProvider:
    def __init__(self, response: dict):
        self._response = response

    async def chat_json(self, messages, **kwargs):  # noqa: ARG002
        return self._response


class TestUploadValueShape:
    def test_key_nodes_arrow_text_wrapped_to_from_to(self):
        import asyncio

        from app.domains.creation.a1.worldview_upload import parse_modules

        provider = _FakeProvider({
            "answers": {
                "历史时间线.key_nodes": "王朝建立→帝国崩塌",
                "世界本体.origin": "星核炸裂",
            },
            "innovations": [],
        })
        out = asyncio.run(parse_modules(provider, "星陨大陆设定。" + "这是一个世界。" * 40))
        assert out["answers"]["历史时间线.key_nodes"] == {
            "from": "王朝建立", "to": "帝国崩塌",
        }
        # 点类字段 = ● 纯文本
        assert out["answers"]["世界本体.origin"] == "星核炸裂"

    def test_key_nodes_variant_cong_dao_wrapped(self):
        import asyncio

        from app.domains.creation.a1.worldview_upload import parse_modules

        provider = _FakeProvider({
            "answers": {"历史时间线.main_plot": "从割据到一统"},
            "innovations": [],
        })
        out = asyncio.run(parse_modules(provider, "星陨大陆设定。" + "这是一个世界。" * 40))
        assert out["answers"]["历史时间线.main_plot"] == {
            "from": "割据", "to": "一统",
        }

    def test_key_nodes_non_arrow_text_stays_plain(self):
        """无 A→B 形状的文本 → 保持纯文本（●降级，不硬拆）。"""
        import asyncio

        from app.domains.creation.a1.worldview_upload import parse_modules

        provider = _FakeProvider({
            "answers": {"历史时间线.key_nodes": "王朝更迭频繁"},
            "innovations": [],
        })
        out = asyncio.run(parse_modules(provider, "星陨大陆设定。" + "这是一个世界。" * 40))
        assert out["answers"]["历史时间线.key_nodes"] == "王朝更迭频繁"

    def test_prefill_session_accepts_wrapped_shape(self):
        """_prefill_session 消费 ▶ 包装值 → 会话 l3_value_parts 可读回部件。"""
        routes = importlib.import_module("app.api.a1_routes")
        from app.domains.creation.a1.guide_engine import l3_value_parts

        parsed = {
            "answers": {
                "历史时间线.key_nodes": {"from": "王朝建立", "to": "帝国崩塌"},
                "ip.name": "星陨大陆",
            },
            "innovations": [],
            "clipped_answers": [],
        }
        out = routes._prefill_session("u_e1", parsed)
        session = out["_session"]
        parts = l3_value_parts(session, "key_nodes")
        assert parts.get("from") == "王朝建立"
        assert parts.get("to") == "帝国崩塌"
        assert session.answers["ip.name"] == "星陨大陆"


# ---------------------------------------------------------------------------
# 7. 未知边类型降级 + 词表注册
# ---------------------------------------------------------------------------


class TestEdgeTypeVocab:
    def test_transition_linkage_registered_in_enum(self):
        from app.models.knowledge_graph import EdgeType

        assert EdgeType("transition").name == "TRANSITION"
        assert EdgeType("linkage").name == "LINKAGE"

    def test_not_in_llm_prompt_vocab(self):
        """铁律：transition/linkage 绝不进 LLM prompt 词表。"""
        from app.domains.creation.a1.concept_edge_vocab import VOCAB_RELATION_NAMES

        assert "transition" not in VOCAB_RELATION_NAMES
        assert "linkage" not in VOCAB_RELATION_NAMES
        graphify = _mod("app.domains.creation.a1.graphify")
        prompt = graphify.build_graphify_prompt({"ip.name": "X"})
        assert "transition" not in prompt
        assert "linkage" not in prompt

    def test_unknown_edge_type_degrades_not_raises(self):
        """未注册边类型 → 跳过 + 降级标记，不抛异常（s2-unknown-enum 先例）。"""
        from app.models.knowledge_graph import KnowledgeGraph

        raw = {
            "scene_id": "s1",
            "nodes": {
                "a": {"id": "a", "serial_number": "1", "level": 1},
                "b": {"id": "b", "serial_number": "1-1", "level": 2},
            },
            "edges": [
                {"from_node_id": "a", "to_node_id": "b",
                 "edge_type": "totally_unknown_type"},
                {"from_node_id": "a", "to_node_id": "b", "edge_type": "tree"},
            ],
        }
        graph = KnowledgeGraph.from_dict(raw)  # 不得抛异常
        assert len(graph.edges) == 1  # 未知边被跳过
        assert graph.edges[0].edge_type.value == "tree"
        assert getattr(graph, "degraded_edge_count", 0) == 1  # 降级标记

    def test_transition_roundtrip_via_from_dict(self):
        from app.models.knowledge_graph import KnowledgeGraph

        raw = {
            "scene_id": "s1",
            "nodes": {
                "a": {"id": "a", "serial_number": "1", "level": 1},
                "b": {"id": "b", "serial_number": "1-1", "level": 2},
            },
            "edges": [
                {"from_node_id": "a", "to_node_id": "b",
                 "edge_type": "transition", "relation": "transition"},
            ],
        }
        graph = KnowledgeGraph.from_dict(raw)
        assert len(graph.edges) == 1
        assert graph.edges[0].edge_type.value == "transition"
        assert graph.degraded_edge_count == 0
