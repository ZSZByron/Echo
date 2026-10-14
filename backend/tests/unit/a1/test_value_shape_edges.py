# -*- coding: utf-8 -*-
"""T9（批E-1）：值形态答案 → 图谱新边类型确定性编译 + 上传预填值形状联动。

契约（施工单 a1-wave2 T9 / 值形态设计稿 §4 工程落点）：
1. ▶（from_to 形）→ **迁移边**：from 态节点→to 态节点，trigger 为边属性（非节点）
2. ⇄（dim_dir 形）→ **衔接边**：dimension+direction 落边语义；
   拒绝线 = magnitude 0 特例仍产边
3. 支线卡衔接（方式+点）→ 入既有**概念边家族**（SEMANTIC，confirmed=False 待审）
4. ●（point 形）→ 现行 flat NL 路径字节不变（值形状通道零产出）
半填：▶ 仅 to（from 缺省）仍产迁移边（from 缺省语义留痕）。
上传：worldview_upload 预填值按 THREE_TIER_TREE vs 闭集形状包装
（关键节点/弧光类 = ▶；● 位点原串直通，NL 路径字节不变）。
降级：图谱消费未知新边类型不炸（s2-unknown-enum-degrade 先例）。
铁律：LLM 只在 graphify 单点产 SIR；新边由确定性编译从 vs 形状装配（零 LLM）。
"""
import json

from app.domains.creation.a1.guide_engine import (
    A1Session,
    AnswerNode,
    answer_view,
    apply_l3_fill,
)
from app.domains.creation.a1.live_projection import compile_value_shape_edges
from app.domains.creation.a1.worldview_upload import shape_wrap_upload_value
from app.domains.creation.seed.story_modules import (
    VS_DIM_DIR,
    VS_DUAL,
    VS_ENUM,
    VS_FROM_TO,
    VS_POINT,
)
from app.models.knowledge_graph import (
    EdgeType,
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
)


def _node(text: str, source: str) -> AnswerNode:
    return AnswerNode(source=source, text=text)


def _shape_answer(**parts: str) -> AnswerNode:
    """形状部件 → 落库 AnswerNode（text 空，部件走 source 子节点——
    answer_view 渲染 = 部件叶值「；」连接，与纯串 NL 同形）。"""
    return AnswerNode(
        text="",
        children=[_node(v, k) for k, v in parts.items()],
    )


def _shape_session() -> A1Session:
    """四断言混合会话：● 点 + ▶ 全填 + ⇄(幅度0) + ▶ 半填 + 支线卡衔接。"""
    s = A1Session(session_id="t9", user_id="u", ip_code="IP0001")
    # ● 点（flat 现行路径，不得产新边）
    s.answers["世界本体.origin"] = "世界起源于一声钟响"
    # ▶ 全填（flat 平移字段：历史时间线.key_nodes 关键节点）
    s.answers["历史时间线.key_nodes"] = _shape_answer(
        **{"from": "平静村庄", "to": "战火边城", "trigger": "蛮族入侵"}
    )
    # ⇄（flat 平移字段：力量体系.cost），magnitude=0 拒绝线特例
    s.answers["力量体系.cost"] = _shape_answer(
        **{"dimension": "寿命", "direction": "增强", "magnitude": "0"}
    )
    # ▶ 半填（仅 to，from 缺省）
    s.answers["力量体系.acquire"] = _shape_answer(**{"to": "通过试炼获得"})
    # 支线卡衔接（方式+点，树内 L3，走批B apply_l3_fill 写入口）
    apply_l3_fill(s, "side_link_mode", "反哺")
    apply_l3_fill(s, "side_link_point", {"from": "支线终幕", "to": "主线决战"})
    return s


class TestVsEnumClosed:
    """vs 闭集逐字锁定（⑥稿 §0，不允许添加或修改）。"""

    def test_vs_enum_verbatim(self):
        assert VS_POINT == "point"
        assert VS_FROM_TO == "from_to"
        assert VS_DIM_DIR == "dim_dir"
        assert VS_DUAL == "dual"
        assert VS_ENUM == frozenset({"point", "from_to", "dim_dir", "dual"})


class TestMigrationEdge:
    """断言1：▶ from_to 形 → 迁移边（from→to 态节点，trigger 为边属性）。"""

    def test_full_from_to_produces_migration_edge(self):
        nodes, edges, _warnings = compile_value_shape_edges(_shape_session())
        mig = [e for e in edges if e.edge_type == EdgeType.MIGRATION]
        km = [e for e in mig if e.to_node_id == "vs:key_nodes:to"]
        assert len(km) == 1
        e = km[0]
        # from 态节点 → to 态节点
        assert e.from_node_id == "vs:key_nodes:from"
        assert e.relation == "迁移"
        # trigger 落边属性（visual_description），不是节点
        assert "蛮族入侵" in e.visual_description
        assert all("蛮族入侵" not in n.description for n in nodes)
        # 确定性编译自用户答案装配 → 无需审核
        assert e.confirmed is True
        # 两态节点存在且描述为态文本
        by_id = {n.id: n for n in nodes}
        assert by_id["vs:key_nodes:from"].description == "平静村庄"
        assert by_id["vs:key_nodes:to"].description == "战火边城"


class TestLinkageEdge:
    """断言2：⇄ dim_dir 形 → 衔接边（dimension+direction 落边语义）。"""

    def test_dim_dir_produces_linkage_edge(self):
        nodes, edges, _warnings = compile_value_shape_edges(_shape_session())
        lk = [e for e in edges if e.edge_type == EdgeType.LINKAGE]
        cost = [e for e in lk if e.from_node_id == "vs:cost:dim"]
        assert len(cost) == 1
        e = cost[0]
        assert e.to_node_id == "vs:cost:dir"
        assert e.relation == "衔接"
        # dimension + direction 落边语义（边属性），非节点描述堆叠
        assert "寿命" in e.visual_description
        assert "增强" in e.visual_description
        assert e.confirmed is True

    def test_magnitude_zero_rejection_line_still_produces_edge(self):
        """拒绝线 = 幅度 0 特例（⑥§2-16「从X到X」合法）：magnitude=0
        不是空值——衔接边仍产出，幅度 0 落边属性。"""
        _nodes, edges, _warnings = compile_value_shape_edges(_shape_session())
        lk = [e for e in edges if e.edge_type == EdgeType.LINKAGE]
        cost = [e for e in lk if e.from_node_id == "vs:cost:dim"]
        assert len(cost) == 1
        assert "0" in cost[0].visual_description


class TestSideCardLinkage:
    """断言3：支线卡衔接（方式+点）→ 入既有概念边家族（SEMANTIC 待审）。"""

    def test_side_link_joins_concept_edge_family(self):
        _nodes, edges, _warnings = compile_value_shape_edges(_shape_session())
        side = [e for e in edges if e.relation == "衔接·反哺"]
        assert len(side) == 1
        e = side[0]
        assert e.edge_type == EdgeType.SEMANTIC
        assert e.confirmed is False  # 概念边家族 = 待用户确认
        # 衔接点（from_to）两态为端点
        assert e.from_node_id == "vs:side_link_point:from"
        assert e.to_node_id == "vs:side_link_point:to"


class TestPointPathUntouched:
    """断言4：● point 形 → 现行 flat NL 路径字节不变（值形状通道零产出）。"""

    def test_point_only_session_zero_shape_output(self):
        s = A1Session(session_id="t9p", user_id="u", ip_code="IP0002")
        s.answers["世界本体.origin"] = "世界起源于一声钟响"
        s.answers["IP定位.name"] = "测试IP"
        nodes, edges, warnings = compile_value_shape_edges(s)
        assert nodes == []
        assert edges == []
        assert warnings == []

    def test_build_graph_point_only_has_no_vs_artifacts(self):
        """_build_graph 全链路：纯 ● 会话图谱零 vs 通道产物（回归面）。"""
        from app.api import a1_routes

        s = A1Session(session_id="t9p2", user_id="u", ip_code="IP0003")
        s.answers["世界本体.origin"] = "钟响"
        s.answers["IP定位.name"] = "测试IP"
        graph, _ids = a1_routes._build_graph(s, {})
        dumped = json.dumps(graph.model_dump(), ensure_ascii=False, sort_keys=True)
        assert "vs:" not in dumped
        assert not any(
            e.edge_type in (EdgeType.MIGRATION, EdgeType.LINKAGE)
            for e in graph.edges
        )


class TestHalfFillTolerance:
    """半填兼容：▶ 仅 to（from 缺省）仍产迁移边（from 缺省语义留痕）。"""

    def test_from_missing_still_produces_migration_edge(self):
        s = A1Session(session_id="t9h", user_id="u", ip_code="IP0004")
        s.answers["力量体系.acquire"] = _shape_answer(**{"to": "通过试炼获得"})
        nodes, edges, warnings = compile_value_shape_edges(s)
        mig = [e for e in edges if e.edge_type == EdgeType.MIGRATION]
        assert len(mig) == 1
        e = mig[0]
        assert e.from_node_id == "vs:acquire:from"
        assert e.to_node_id == "vs:acquire:to"
        # from 缺省语义留痕：缺省态节点描述可辨 + warning 留痕
        by_id = {n.id: n for n in nodes}
        assert "缺省" in by_id["vs:acquire:from"].description
        assert any("acquire" in w and "缺省" in w for w in warnings)


class TestUploadShapeWrap:
    """上传联动：预填值按 THREE_TIER_TREE vs 闭集形状包装（关键节点=▶）。"""

    def test_from_to_key_wrapped_as_half_shape(self):
        wrapped = shape_wrap_upload_value("历史时间线.key_nodes", "五次大战")
        assert isinstance(wrapped, AnswerNode)
        parts = {c.source: c.text for c in wrapped.children if c.source}
        assert parts == {"to": "五次大战"}  # ▶ 半填形（to 先落）

    def test_dim_dir_key_wrapped_as_dimension(self):
        wrapped = shape_wrap_upload_value("力量体系.cost", "寿命减半")
        assert isinstance(wrapped, AnswerNode)
        parts = {c.source: c.text for c in wrapped.children if c.source}
        assert parts == {"dimension": "寿命减半"}

    def test_point_key_passthrough_verbatim(self):
        assert shape_wrap_upload_value("世界本体.origin", "钟响") == "钟响"

    def test_wrapped_value_renders_identical_nl(self):
        """包装后 answer_view 渲染与原串逐字节一致（NL 路径不变）。"""
        for key, val in (
            ("历史时间线.key_nodes", "五次大战"),
            ("力量体系.cost", "寿命减半"),
        ):
            assert answer_view(shape_wrap_upload_value(key, val)) == val

    def test_unknown_key_passthrough(self):
        assert shape_wrap_upload_value("不存在的键", "x") == "x"


class TestUnknownEdgeTypeDegrade:
    """降级：图谱消费未知新边类型不炸（s2-unknown-enum-degrade 先例）。"""

    def test_new_edge_types_json_round_trip(self):
        g = KnowledgeGraph(
            scene_id="t9d",
            background_node_id="bg",
            nodes={
                "bg": GraphNode(id="bg", serial_number="0", level=1),
                "a": GraphNode(id="a", serial_number="1", level=4),
                "b": GraphNode(id="b", serial_number="2", level=4),
            },
            edges=[
                GraphEdge(
                    from_node_id="a", to_node_id="b",
                    edge_type=EdgeType.MIGRATION,
                    visual_description="蛮族入侵", relation="迁移",
                    confidence="", confirmed=True,
                ),
                GraphEdge(
                    from_node_id="a", to_node_id="b",
                    edge_type=EdgeType.LINKAGE,
                    visual_description="寿命·增强（幅度 0）", relation="衔接",
                    confidence="", confirmed=True,
                ),
            ],
        )
        raw = json.dumps(g.model_dump(), ensure_ascii=False)
        assert '"migration"' in raw and '"linkage"' in raw
        g2 = KnowledgeGraph.model_validate(json.loads(raw))
        assert {e.edge_type for e in g2.edges} == {
            EdgeType.MIGRATION, EdgeType.LINKAGE,
        }

    def test_edge_type_value_plain_string_for_consumers(self):
        """消费侧 ``edge_type.value`` 通道（投影/序列化）为新枚举产纯串，
        前端未知类型按 s2 先例走 default 分支降级，不炸。"""
        assert EdgeType.MIGRATION.value == "migration"
        assert EdgeType.LINKAGE.value == "linkage"
