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


def module_continent(module_id: str) -> str:
    """旧/新模块 id → THREE_TIER_TREE L1 归属；未知返回空串（诚实降级）。

    双匹配：L2 id（如 IP定位/identity/key_relations）直配；L1 label
    （剧情/角色 = 模块 id，与树 L2 字段 id 不同名）回退配 L1 label。
    """
    from app.domains.creation.seed.story_modules import THREE_TIER_TREE
    for l1 in THREE_TIER_TREE:
        for l2 in l1.get("l2", []):
            if l2.get("id") == module_id:
                return str(l1.get("id", ""))
        if l1.get("label") == module_id:
            return str(l1.get("id", ""))
    return ""


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
                continent=module_continent(module_id),
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


# ---------------------------------------------------------------------------
# 值形态 → 图谱新边 确定性编译（波次二批E-1，T9；值形态设计稿 §4 工程落点）
#
# 铁律：LLM 只在 graphify 单点产 SIR；本段是纯确定性装配——从会话 answers
# 的 vs 形状（fills/上传包装产物）直接装配迁移边/衔接边/支线衔接概念边，
# 同输入可复现、零 LLM。●（point 形）不进此通道：现行 flat NL 路径字节不变
# （旧会话无形状 fills → 本函数零产出 → _build_graph 输出逐字节不变）。
# ---------------------------------------------------------------------------

#: 支线卡衔接位点（branch_card 卡内：方式=point / 点=from_to）——改入既有
# 概念边家族（SEMANTIC 待审），不走迁移边通道。
_SIDE_LINK_MODE_L3 = "side_link_mode"
_SIDE_LINK_POINT_L3 = "side_link_point"


def compile_value_shape_edges(
    session: Any,
) -> tuple[list[GraphNode], list[GraphEdge], list[str]]:
    """vs 形状 answers → 迁移边/衔接边/支线衔接概念边（零 LLM，确定性）。

    - ▶（from_to）→ MIGRATION 迁移边：from 态节点→to 态节点，trigger 落
      边属性（visual_description）；半填宽容：仅 to 仍产边，from 缺省
      语义留痕（缺省态节点描述可辨 + warning）。
    - ⇄（dim_dir）→ LINKAGE 衔接边：dimension+direction 落边语义；
      拒绝线 = magnitude 0 特例仍产边（0 是真实内容不是空）。
    - 支线卡衔接（side_link_mode + side_link_point 双真）→ 既有概念边
      家族：SEMANTIC / relation="衔接·{方式}" / confirmed=False 待审。
    - ●（point / 降级点形态）→ 不产边（flat NL 路径字节不变）。

    Returns ``(nodes, edges, warnings)``——节点由调用方 setdefault 进
    节点表（id 前缀 ``vs:`` 不与既有 id 空间相交）。
    """
    # 局部导入：避免模块加载期拉起 guide_engine 全量依赖链（本模块保持轻量）。
    from app.domains.creation.a1.guide_engine import (
        AnswerNode,
        l3_value_parts,
    )
    from app.domains.creation.seed.story_modules import (
        THREE_TIER_TREE,
        VS_DIM_DIR,
        VS_FROM_TO,
    )

    answers = session.answers
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    warnings: list[str] = []
    serial = 0

    def _state_node(l3_id: str, role: str, text: str) -> str:
        """态节点（迁移边/衔接边端点）：id ``vs:{l3_id}:{role}``。"""
        nonlocal serial
        serial += 1
        nid = f"vs:{l3_id}:{role}"
        nodes.append(GraphNode(
            id=nid, serial_number=f"VS{serial}", level=4,
            description=text,
        ))
        return nid

    def _parts(l2_id: str, l3_id: str) -> dict[str, Any]:
        """位点值 → 部件 dict（平面 dict 直读；其余走批B l3_value_parts
        统一读入口——AnswerNode/纯串/树内 L3 全覆盖）。"""
        raw = answers.get(f"{l2_id}.{l3_id}", "")
        if isinstance(raw, dict):
            return raw
        return l3_value_parts(session, l3_id)

    side_mode_text = ""
    side_point_parts: dict[str, Any] | None = None

    for l1 in THREE_TIER_TREE:
        for l2 in l1["l2"]:
            for l3 in l2["l3"]:
                l3_id = str(l3["id"])
                vs = str(l3["vs"])
                parts = _parts(str(l2["id"]), l3_id)
                if not parts:
                    continue
                # 支线卡衔接位点先捕获（方式=●点形也要收——双真才入概念边）
                if l3_id == _SIDE_LINK_MODE_L3:
                    side_mode_text = "；".join(
                        str(v) for v in parts.values() if str(v)
                    )
                    continue
                if l3_id == _SIDE_LINK_POINT_L3:
                    side_point_parts = parts
                    continue
                if set(parts) == {"point"}:
                    continue  # ● 点/降级点形态 → 现行 flat NL 路径（零改动）
                if vs == VS_FROM_TO:
                    _emit_migration(l3_id, parts, _state_node, edges, warnings)
                elif vs == VS_DIM_DIR:
                    _emit_linkage(l3_id, parts, _state_node, edges)

    # 支线卡衔接：方式+点双真 → 概念边家族（SEMANTIC 待审）
    if side_mode_text and side_point_parts:
        _emit_side_link(
            side_mode_text, side_point_parts, _state_node, edges,
        )
    return nodes, edges, warnings


def _emit_migration(
    l3_id: str,
    parts: dict[str, Any],
    state_node: Any,
    edges: list[GraphEdge],
    warnings: list[str],
) -> None:
    """▶ from_to 部件 → 迁移边（半填宽容；from 缺省语义留痕）。"""
    from_text = str(parts.get("from", "") or "").strip()
    to_text = str(parts.get("to", "") or "").strip()
    trigger = str(parts.get("trigger", "") or "").strip()
    if not from_text and not to_text:
        return  # 无端点部件：无边可装配（真值闸上游已滤占位）
    if from_text:
        fid = state_node(l3_id, "from", from_text)
    else:
        fid = state_node(l3_id, "from", "（from 缺省·留痕）")
        warnings.append(f"▶ from 缺省留痕: {l3_id}")
    if to_text:
        tid = state_node(l3_id, "to", to_text)
    else:
        tid = state_node(l3_id, "to", "（to 缺省·留痕）")
        warnings.append(f"▶ to 缺省留痕: {l3_id}")
    # trigger 为边属性（非节点）——落 visual_description
    edges.append(GraphEdge(
        from_node_id=fid, to_node_id=tid,
        edge_type=EdgeType.MIGRATION,
        visual_description=trigger or "状态迁移",
        relation="迁移", confidence="", confirmed=True,
    ))


def _emit_linkage(
    l3_id: str,
    parts: dict[str, Any],
    state_node: Any,
    edges: list[GraphEdge],
) -> None:
    """⇄ dim_dir 部件 → 衔接边（dimension+direction 落边语义；
    拒绝线 = magnitude 0 特例仍产边——0 不做真值过滤）。"""
    dimension = parts.get("dimension")
    direction = parts.get("direction")
    magnitude = parts.get("magnitude")
    if (
        dimension is None and direction is None and magnitude is None
    ):
        return
    dim_text = str(dimension or "").strip()
    dir_text = str(direction or "").strip()
    fid = state_node(l3_id, "dim", dim_text or "（dimension 缺省·留痕）")
    tid = state_node(l3_id, "dir", dir_text or "（direction 缺省·留痕）")
    desc = "·".join(x for x in (dim_text, dir_text) if x)
    # magnitude=0（拒绝线特例）是真实内容：仅 None/空串不落，0 照落
    if magnitude is not None and str(magnitude).strip() != "":
        desc = f"{desc}（幅度 {str(magnitude).strip()}）" if desc else (
            f"（幅度 {str(magnitude).strip()}）"
        )
    edges.append(GraphEdge(
        from_node_id=fid, to_node_id=tid,
        edge_type=EdgeType.LINKAGE,
        visual_description=desc or "属性衔接",
        relation="衔接", confidence="", confirmed=True,
    ))


def _emit_side_link(
    mode_text: str,
    point_parts: dict[str, Any],
    state_node: Any,
    edges: list[GraphEdge],
) -> None:
    """支线卡衔接（方式+点）→ 既有概念边家族（SEMANTIC，confirmed=False）。"""
    from_text = str(point_parts.get("from", "") or "").strip()
    to_text = str(point_parts.get("to", "") or "").strip()
    if not from_text and not to_text:
        return
    fid = state_node(
        _SIDE_LINK_POINT_L3, "from", from_text or "（from 缺省·留痕）"
    )
    tid = state_node(_SIDE_LINK_POINT_L3, "to", to_text or "（to 缺省·留痕）")
    edges.append(GraphEdge(
        from_node_id=fid, to_node_id=tid,
        edge_type=EdgeType.SEMANTIC,
        visual_description="支线衔接",
        relation=f"衔接·{mode_text}", confidence="semantic",
        confirmed=False,
    ))
