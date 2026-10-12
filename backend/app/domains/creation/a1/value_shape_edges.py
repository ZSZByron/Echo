"""批E-1：值形态 → 图谱边确定性编译（迁移边/衔接边）。

⑥稿 §4 工程落点 2：● → 节点（现行路径不动）；▶ → **迁移边**（from 态节点
→ to 态节点，trigger 落边属性）；⇄ → 属性变更边（**衔接边**，dimension+
direction 落边语义）。支线卡衔接（side_link_mode ● + side_link_point ▶）
入概念边家族（linkage 扩展）。

三条铁律：
- LLM 只产 SIR 五字段——本模块不进任何 LLM prompt 词表
  （transition/linkage 不入 concept_edge_vocab.VOCAB_RELATION_NAMES）；
- 确定性编译：同输入可复现，零 LLM；
- 拒绝线语义保留：▶ from==to（"从X到X"，⑥§2-16）/ ⇄ direction=拒绝 或
  magnitude=0 → 边上注记「（拒绝线）」，边不丢。

⇉ dual 与渲染（状态轨迹条）为波次三范围，本批不产边（降级兼容）。
"""
from __future__ import annotations

from typing import Any

from app.domains.creation.a1.guide_engine import (
    _L3_INDEX,
    VS_DIM_DIR,
    VS_FROM_TO,
    l3_answer_truthy,
    l3_value_parts,
)
from app.models.knowledge_graph import GraphEdge, GraphNode

#: 边类型常量（EdgeType 枚举已注册；词表处仅此一处语义命名）。
EDGE_TRANSITION = "transition"
EDGE_LINKAGE = "linkage"

#: 拒绝线方向词（⇄ direction=拒绝 → 幅度 0 语义）。
_REFUSE_DIRECTION = "拒绝"

#: 半填 from 缺省节点描述与披露词。
_MISSING_FROM_NOTE = "（前态缺省）"

#: 支线卡衔接位点（⑥§2-13 整卡轨迹 ▶；方式 ● + 点 ▶）。
_SIDE_LINK_MODE = "side_link_mode"
_SIDE_LINK_POINT = "side_link_point"
_SIDE_CARD_SOURCE = f"branch_card.{_SIDE_LINK_POINT}"
_MAIN_STORY_TARGET = "story_line"


def _state_node_id(flat_key: str, side: str) -> str:
    """位点派生状态节点 id：``v:{l2}.{l3}:{from|to}``。"""
    return f"v:{flat_key}:{side}"


def _state_node(flat_key: str, side: str, description: str, serial: str) -> GraphNode:
    return GraphNode(
        id=_state_node_id(flat_key, side),
        serial_number=serial,
        level=4,
        description=description,
    )


def _refuse_note(parts: dict[str, Any]) -> str:
    """拒绝线特例判定（⑥§2-16）：命中 → 「（拒绝线）」注记。"""
    direction = str(parts.get("direction", "")).strip()
    magnitude = parts.get("magnitude")
    if direction == _REFUSE_DIRECTION:
        return "（拒绝线）"
    if isinstance(magnitude, (int, float)) and magnitude == 0:
        return "（拒绝线）"
    return ""


def _compile_transition(
    flat_key: str, parts: dict[str, Any], nodes: list[GraphNode],
    edges: list[GraphEdge], warnings: list[str], serial: str,
) -> None:
    """▶ → 迁移边：from 态节点 → to 态节点，trigger 落边属性。

    半填（仅 to）→ 仍产迁移边：from 缺省节点 + 披露警告。
    from==to → 拒绝线注记（"从X到X" 合法答案）。
    """
    from_text = str(parts.get("from", "") or "").strip()
    to_text = str(parts.get("to", "") or "").strip()
    if not from_text:
        from_text = _MISSING_FROM_NOTE
        warnings.append(f"[值形态编译] {flat_key} 前态缺省，迁移边以缺省节点出边")
    trigger = str(parts.get("trigger", "") or "").strip()
    visual = trigger or "迁移"
    if from_text == to_text:
        visual += "（拒绝线）"
    nodes.append(_state_node(flat_key, "from", from_text, f"{serial}-1"))
    nodes.append(_state_node(flat_key, "to", to_text, f"{serial}-2"))
    edges.append(GraphEdge(
        from_node_id=_state_node_id(flat_key, "from"),
        to_node_id=_state_node_id(flat_key, "to"),
        edge_type=EDGE_TRANSITION,
        visual_description=visual,
        relation=EDGE_TRANSITION,
        confidence="structure",
        confirmed=True,
    ))


def _compile_linkage(
    flat_key: str, parts: dict[str, Any], nodes: list[GraphNode],
    edges: list[GraphEdge], warnings: list[str], serial: str,
) -> None:
    """⇄ → 衔接边：dimension+direction 落边语义（属性变更边）。

    拒绝线（direction=拒绝 / magnitude=0）语义在边上保留，边不丢。
    拒绝线命中同时落披露（warnings）。
    """
    dimension = str(parts.get("dimension", "") or "").strip()
    direction = str(parts.get("direction", "") or "").strip()
    refuse = _refuse_note(parts)
    if refuse:
        warnings.append(f"[值形态编译] {flat_key} 拒绝线特例（幅度0语义），边上注记保留")
    visual = f"{dimension}·{direction}".strip("·") or "衔接"
    visual += refuse
    nodes.append(_state_node(flat_key, "from", dimension or "（维度缺省）", f"{serial}-1"))
    nodes.append(_state_node(flat_key, "to", direction or "（方向缺省）", f"{serial}-2"))
    edges.append(GraphEdge(
        from_node_id=_state_node_id(flat_key, "from"),
        to_node_id=_state_node_id(flat_key, "to"),
        edge_type=EDGE_LINKAGE,
        visual_description=visual,
        relation=EDGE_LINKAGE,
        confidence="structure",
        confirmed=True,
    ))


def _compile_side_card_linkage(
    session: Any, edges: list[GraphEdge], warnings: list[str]
) -> None:
    """支线卡衔接 → 概念边家族扩展：branch_card.side_link_point → story_line。

    方式（side_link_mode ●）+ 点（side_link_point ▶ 后态）双真值才接边；
    仅有方式（半边）不硬接。端点为概念树位点，节点由背景树按已答条目装配；
    端点缺席时由装配层落 dead_edges（披露沿 warnings 通道）。
    """
    mode = l3_value_parts(session, _SIDE_LINK_MODE)
    mode_text = str(mode.get("point", "") or "").strip()
    if not mode_text:
        return
    parts = l3_value_parts(session, _SIDE_LINK_POINT)
    to_text = str(parts.get("to", "") or "").strip()
    if not to_text:
        return
    warnings.append(
        f"[值形态编译] 支线卡衔接边挂接: {_SIDE_CARD_SOURCE} → {_MAIN_STORY_TARGET}"
    )
    edges.append(GraphEdge(
        from_node_id=_SIDE_CARD_SOURCE,
        to_node_id=_MAIN_STORY_TARGET,
        edge_type=EDGE_LINKAGE,
        visual_description=f"{mode_text}·{to_text}",
        relation=EDGE_LINKAGE,
        confidence="structure",
        confirmed=True,
    ))


def compile_value_shape_edges(
    session: Any,
) -> tuple[list[GraphNode], list[GraphEdge], list[str]]:
    """值形态 → 图谱边确定性编译入口（批E-1）。

    遍历 L3 索引：vs=from_to → 迁移边；vs=dim_dir → 衔接边；
    支线卡衔接 → 概念边家族（linkage）。● 位点与无形状旧式文本值
    零产出（现行 flat NL 路径字节不变——旧会话回归锁 0 diff）。
    ⇉ dual 不产边（渲染波次三）。

    Returns:
        ``(minted_nodes, compiled_edges, warnings)``——节点/边由调用方
        并入装配图；warnings 为披露（半填缺省等），从不抛异常。
    """
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    warnings: list[str] = []
    serial = 0
    for l3_id, meta in _L3_INDEX.items():
        vs = meta["vs"]
        if vs not in (VS_FROM_TO, VS_DIM_DIR):
            continue  # ● / ⇉：本批零产出
        parts = l3_value_parts(session, l3_id)
        # 无形状（纯文本 ● 降级 / 未写入）→ 不产边
        if not parts or set(parts) == {"point"}:
            continue
        if not l3_answer_truthy(session, l3_id):
            continue
        serial += 1
        flat_key = f"{meta['l2_id']}.{l3_id}"
        if vs == VS_FROM_TO:
            _compile_transition(flat_key, parts, nodes, edges, warnings, f"VS{serial}")
        else:
            _compile_linkage(flat_key, parts, nodes, edges, warnings, f"VS{serial}")
    _compile_side_card_linkage(session, edges, warnings)
    return nodes, edges, warnings
