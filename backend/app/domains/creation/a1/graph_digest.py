"""T14: 图谱摘要构造器（graph_digest）。

定位（D20 域目录注入模式延伸 · DN5 第四处登记）：
- **纯代码确定性装配（零 LLM）**：同输入同输出；节点字典顺序无关。
- **只读消费**：读取会话图谱（graph_json 结构），产出紧凑摘要文本，
  不写回任何状态——图谱摘要注入 = 单生产（graphify/确定性编译）单消费
  （interviewer prompt 只读注入）。
- **G5 键域契约**：摘要块内绝不出现裸 ``{模块id}.`` 形态（任何 ``.`` 一律
  改写为全角间隔号 ``·``；「」括注中文标签，D20⑤ WORLDVIEW_DOMAIN_CATALOG
  先例）。
- **三态**：有图（非空摘要）/ 无图（返回空串，prompt 零变化）/ 部分图
  （只渲染存在的模块与条目，未知 id 安全跳过）。
"""

from __future__ import annotations

from typing import Any

from app.domains.creation.seed.a1_question_tree import (
    get_subfield,
    module_ids,
)

GRAPH_DIGEST_BEGIN = "【图谱摘要开始】"
GRAPH_DIGEST_END = "【图谱摘要结束】"

_DIGEST_HEADER = (
    "【图谱背景摘要】（只读参考——以下是本会话已确定设定的紧凑摘要，"
    "帮助你理解已有共识；不得据此新增设定或改变 fills 行为）"
)


def _safe(text: Any) -> str:
    """键域消毒：任何 ``.`` 改写为 ``·``，杜绝裸 ``{模块id}.`` 形态。"""
    return str(text).replace(".", "·").replace("\n", " ").strip()


def _node_desc(node: dict[str, Any]) -> str:
    desc = node.get("description") or ""
    return _safe(desc)


def lookup_graph_json(session: Any) -> dict[str, Any] | None:
    """只读查找会话图谱；无图返回 ``None``（prompt 零变化路径）。

    优先读会话对象自身属性（若未来直接挂载），否则懒加载路由层文件
    记录表按 ``session_id`` 反查——惰性导入避免模块级循环依赖。
    """
    direct = getattr(session, "graph_json", None)
    if isinstance(direct, dict) and isinstance(direct.get("nodes"), dict) and direct["nodes"]:
        return direct
    sid = getattr(session, "session_id", None)
    if not sid:
        return None
    try:
        from app.api import a1_routes  # 惰性导入：仅请求期执行，无导入环
    except Exception:
        return None
    files = getattr(a1_routes, "_FILES", {})
    if not isinstance(files, dict):
        return None
    for rec in files.values():
        if not isinstance(rec, dict) or rec.get("session_id") != sid:
            continue
        g = rec.get("graph_json")
        if isinstance(g, dict) and isinstance(g.get("nodes"), dict) and g["nodes"]:
            return g
    return None


def _group_nodes(
    nodes: dict[str, Any],
) -> tuple[dict[str, list[tuple[str, str, dict[str, Any]]]], int, int]:
    """按模块分组节点。

    返回 ``(groups, node_count, unknown_count)``，其中 ``groups[mid]``
    是 ``[(sid, title, node), ...]`` 列表（title 为空串表示子字段节点）。
    未知模块 id 的节点安全跳过（不计入 groups，计入 unknown_count）。
    """
    known = set(module_ids())
    groups: dict[str, list[tuple[str, str, dict[str, Any]]]] = {}
    unknown = 0
    for nid, node in nodes.items():
        if not isinstance(node, dict):
            unknown += 1
            continue
        mid: str | None = None
        sid = ""
        title = ""
        if nid.startswith("d:"):
            rest = nid[2:]
            head, sep, tail = rest.partition(":")
            # head = "{mid}.{sid}"
            if "." in head:
                mid, sub = head.split(".", 1)
                sid, _, _tail_sub = sub.partition(":")
                title = tail if sep else ""
        elif "." in nid:
            mid, sid = nid.split(".", 1)
        elif nid in known:
            mid = nid
        if mid not in known:
            unknown += 1
            continue
        assert mid is not None  # mid ∈ known ⊆ 非空模块 id 集（mypy 收窄）
        groups.setdefault(mid, []).append((sid, title, node))
    return groups, len(nodes), unknown


def build_graph_digest(
    graph: dict[str, Any] | None, invited: list[str] | None = None
) -> str:
    """构造紧凑图谱摘要（纯函数，确定性）。

    - 有图：``GRAPH_DIGEST_BEGIN``/``END`` 包裹的逐模块条目清单。
    - 无图 / 非法载荷：空串（prompt 零变化）。
    - ``invited``：本轮受邀模块 id（worldview_invites），命中模块标注
      「本轮重点」，输出仍确定性。
    """
    if not isinstance(graph, dict):
        return ""
    nodes = graph.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        return ""

    groups, node_count, _unknown = _group_nodes(nodes)
    if not groups:
        return ""

    invited_set = {m for m in (invited or []) if isinstance(m, str)}
    edges = graph.get("edges")
    edge_count = len(edges) if isinstance(edges, list) else 0

    lines: list[str] = [GRAPH_DIGEST_BEGIN, _DIGEST_HEADER, ""]
    rendered_modules = 0
    for mid in module_ids():
        entries = groups.get(mid)
        if not entries:
            continue
        rendered_modules += 1
        mark = "（本轮重点）" if mid in invited_set else ""
        lines.append(f"模块「{_safe(mid)}」{mark}：")
        # 确定性：按 serial_number 排序，节点字典顺序无关。
        entries_sorted = sorted(
            entries,
            key=lambda e: (
                str(e[2].get("serial_number") or ""),
                e[0],
                e[1],
            ),
        )
        seen_subs: set[str] = set()
        for sid, title, node in entries_sorted:
            if not title:
                # 子字段节点：渲染描述或子字段中文标签（绝不渲染裸 id）
                if sid in seen_subs:
                    continue
                seen_subs.add(sid)
                desc = _node_desc(node)
                if desc:
                    lines.append(f"　·{desc}")
                else:
                    sub_label = ""
                    try:
                        sf: Any = get_subfield(mid, sid) or {}
                        sub_label = _safe(sf.get("label") or "")
                    except Exception:
                        sub_label = ""
                    lines.append(f"　·「{sub_label or '已建档'}」")
            else:
                # 深化条目节点：标题 + 描述
                desc = _node_desc(node)
                line = f"　　·深化「{_safe(title)}」"
                if desc:
                    line += f"：{desc}"
                lines.append(line)
        lines.append("")

    lines.append(
        f"结构化标记：模块 {rendered_modules} 个；节点 {node_count} 个；"
        f"关联边 {edge_count} 条。"
    )
    lines.append(GRAPH_DIGEST_END)
    return "\n".join(lines)


def graph_digest_block(
    graph: dict[str, Any] | None, invited: list[str] | None = None
) -> list[str]:
    """摘要块行列表（供 prompt 注入）；无图返回空列表（零变化路径）。"""
    digest = build_graph_digest(graph, invited)
    if not digest:
        return []
    return digest.split("\n")
