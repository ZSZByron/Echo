# -*- coding: utf-8 -*-
"""live_projection（半成品背景树投影）——M4b，plan TODO 5 §271。

零新 LLM：半成品 answers → 背景树 L0-L2 投影（bg 根节点 level=1 +
有答案模块节点 level=2 + TREE 边）——图谱确定性装配铁律的观测面复用。

装配函数 ``assemble_background_tree`` 从 a1_routes._build_graph 的纯装配
段抽出（同序同形：模块序 × 字段序 × 首写序），``_build_graph`` 改为消费
此函数（default finalize 路径逐字节等价，m1_default_snapshot 回归锚定）；
``project_live`` 是其只读投影封装（配方内模块、确定性快照 + 披露 note）。
"""
from __future__ import annotations

from typing import Any

from app.domains.creation.a1.tier_map import TIER_MAP
from app.models.knowledge_graph import EdgeType, GraphEdge, GraphNode


def assemble_background_tree(
    answers: dict[str, str],
    modules: list[dict[str, Any]],
    ip_code: str,
    session_id: str,
    module_summaries: dict[str, str] | None = None,
) -> tuple[
    dict[str, GraphNode], list[GraphEdge], str,
    dict[str, int], dict[str, int],
]:
    """背景树纯装配（L1 bg 根 + L2 模块 + L3 条目；零 LLM，确定性）。

    从 _build_graph 抽出的纯装配段（逐行保形）：遍历给定模块序列，非空
    答案字段 → L3 条目节点；模块有任一非空答案 → L2 模块节点。
    返回 ``(nodes, edges, bg_id, module_serial_by_id, entry_serial_by_id)``。
    """
    bg_id = f"bg_{session_id[:8]}"
    nodes: dict[str, GraphNode] = {
        bg_id: GraphNode(id=bg_id, serial_number="0", level=1,
                         description=f"[{ip_code}] 世界背景")
    }
    edges: list[GraphEdge] = []

    module_serial = 0
    module_serial_by_id: dict[str, int] = {}
    entry_serial_by_id: dict[str, int] = {}

    for module in modules:
        module_id = module["id"]
        module_label = module["label"]

        subfield_answers = []
        for sf in module["fields"]:
            answer_key = f"{module_id}.{sf['id']}"
            value = answers.get(answer_key, "")
            if value:
                subfield_answers.append((sf, value))

        if subfield_answers:
            module_serial += 1
            module_serial_by_id[module_id] = module_serial
            # L2 描述：graphify 摘要优先（governance §5a），无则模块名
            l2_description = module_label
            if module_summaries:
                l2_description = module_summaries.get(module_id) or module_label
            nodes[module_id] = GraphNode(
                id=module_id,
                serial_number=str(module_serial),
                level=2,
                description=l2_description,
                tier=TIER_MAP.get(module_id),
            )
            edges.append(GraphEdge(
                from_node_id=bg_id,
                to_node_id=module_id,
                edge_type=EdgeType.TREE,
                visual_description="包含",
            ))

            entry_serial = 0
            for sf, value in subfield_answers:
                entry_serial += 1
                entry_id = f"{module_id}.{sf['id']}"
                entry_serial_by_id[entry_id] = entry_serial
                nodes[entry_id] = GraphNode(
                    id=entry_id,
                    serial_number=f"{module_serial}-{entry_serial}",
                    level=3,
                    description=f"{sf['label']}: {value}",
                )
                edges.append(GraphEdge(
                    from_node_id=module_id,
                    to_node_id=entry_id,
                    edge_type=EdgeType.TREE,
                    visual_description="条目",
                ))

    return nodes, edges, bg_id, module_serial_by_id, entry_serial_by_id


def project_live(session: Any) -> dict[str, Any]:
    """半成品 answers → 背景树 L0-L2 只读投影（零 LLM，确定性快照）。

    只投影配方内模块（default = 全集）；L3 条目在装配函数内一并产出，
    投影层按 spec "L0-L2" 口径裁剪输出（bg + 模块节点）。返回可 JSON
    化 dict（nodes/edges/note），**不是** KnowledgeGraph——半成品快照
    不得与定稿图谱混流（诚实可观测：note 披露非定稿）。
    """
    from app.domains.creation.seed.a1_question_tree import get_module

    ordered = session.recipe_modules or []
    modules = [m for m in (get_module(mid) for mid in ordered) if m]
    nodes, edges, _bg, _ms, _es = assemble_background_tree(
        session.answers, modules, session.ip_code, session.session_id,
    )
    proj_nodes = [
        {
            "id": n.id, "serial_number": n.serial_number,
            "level": n.level, "description": n.description,
            "tier": n.tier,
        }
        for n in nodes.values()
        if n.level <= 2
    ]
    proj_edges = [
        {
            "from": e.from_node_id, "to": e.to_node_id,
            "edge_type": e.edge_type.value
            if hasattr(e.edge_type, "value") else str(e.edge_type),
            "visual_description": e.visual_description,
        }
        for e in edges
        if e.visual_description == "包含"
    ]
    return {
        "session_id": session.session_id,
        "nodes": proj_nodes,
        "edges": proj_edges,
        "note": "live projection：半成品背景树快照（非定稿图谱，零 LLM 装配）",
    }
