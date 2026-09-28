# -*- coding: utf-8 -*-
"""T16: 对齐四动作提案域（alignment_flow，D21⑬）。

铁律（D21⑬）：**LLM 只提议；应用 = 确定性代码执行；
LLM 绝不直写图谱/会话状态**。

四动作闭集（问题说明书 L181-188 逐字，不允许添加或修改）：
- ``link``       关联：输入与图谱条目相关 → 概念边提案
- ``dedupe``     去重：图谱已有 → 提示复用不重录
- ``contradict`` 矛盾：与已有内容冲突 → 提示二选一
- ``update``     更新：应改某条 → 提案 + 影响预警（「将使 … 过期」型）

流水线（推断包 M4a 最近亲先例）：
1. **LLM 提议层**（单次 chat_json，inference_pack/interviewer 模式）：
   输入 = 图谱摘要（T14 ``build_graph_digest`` 只读消费）+ 用户新输入；
   输出 = 0-N 条结构化提案（仅到提案池）。
2. **确定性校验器（唯一闸门，单点过滤）**：动作 ∈ 闭集、目标必须
   存在于图谱（节点 id 或边 key）、内容非占位真值——非法提案丢弃。
3. **装包**：提案入 ``session.pending_alignments``（additive 独立容器，
   照 pending_proposals 惯例但不动既有结构，G3 零迁移）。
4. **用户确认**（resolve_proposal 先例）：确认应用 / 拒绝丢弃零副作用。
   应用 = 确定性代码执行：open_question 归档 + 下游 stale 传播
   （复用 stale_marker.mark_downstream_stale）——全程无 LLM 写入。

文案契约：提案文案说人话（引原话转述），不报模块/字段名
（渲染文本无裸 ``{mid}.`` 形态，G5 同款雷区；节点 id 绝不外露）。
"""
from __future__ import annotations

import asyncio
import inspect
import sqlite3
from typing import Any

from pydantic import BaseModel, Field

from app.domains.creation.a1.graph_digest import build_graph_digest
from app.domains.creation.a1.interaction_log import log_event
from app.domains.creation.a1.open_questions import OpenQuestion

# 四动作闭集（逐字冻结；新增动作须走决策台账翻案，禁止就地追加）
ALIGN_ACTIONS = ("link", "dedupe", "contradict", "update")

ALIGN_MAX_PROPOSALS = 5

_ACTION_LABELS = {
    "link": "关联",
    "dedupe": "去重",
    "contradict": "矛盾",
    "update": "更新",
}

_PLACEHOLDER_WORDS = ("待补充", "占位", "todo", "tbd")


# ── 数据模型 ────────────────────────────────────────────────────────────────


class AlignProposal(BaseModel):
    """一条对齐提案（纯数据形态；stale 预警由确定性代码填充）。"""

    action: str
    target: str  # 图谱节点 id 或边 key
    content: str  # 人话转述（不报模块/字段名）
    quote: str = ""  # 用户原话引用
    graph_code: str = ""  # 提案关联的图谱版本（stale 传播用，确定性填）
    stale_warning: list[str] = Field(default_factory=list)


class AlignmentPack(BaseModel):
    """一次对齐提议的结果（合法提案 + 丢弃计数 + 降级披露）。"""

    proposals: list[AlignProposal] = Field(default_factory=list)
    dropped: int = 0
    note: str = ""


# ── 图谱目标键域（确定性装配，只读消费） ────────────────────────────────────


def graph_target_keys(graph: dict[str, Any]) -> set[str]:
    """收集图谱全部合法目标键：节点 id ∪ 边 key（确定性，纯函数）。"""
    keys: set[str] = set()
    if not isinstance(graph, dict):
        return keys
    nodes = graph.get("nodes")
    if isinstance(nodes, dict):
        keys.update(k for k in nodes.keys() if isinstance(k, str))
    edges = graph.get("edges")
    if isinstance(edges, list):
        for e in edges:
            if not isinstance(e, dict):
                continue
            key = e.get("key")
            if isinstance(key, str) and key:
                keys.add(key)
            else:
                src, dst = e.get("source"), e.get("target")
                if isinstance(src, str) and isinstance(dst, str):
                    keys.add(f"{src}->{dst}")
    return keys


def _target_display(graph: dict[str, Any], target: str) -> str:
    """目标的人话别名（标题/描述摘引）；绝不出节点 id（键域契约）。"""
    nodes = graph.get("nodes")
    if isinstance(nodes, dict) and isinstance(nodes.get(target), dict):
        node = nodes[target]
        title = str(node.get("title") or "")
        if title:
            return f"「{title}」"
        desc = str(node.get("description") or "")
        if desc:
            return f"「{desc[:20]}」"
        return "一条已有记录"
    return "一条已有记录"


# ── 确定性校验器（唯一闸门） ────────────────────────────────────────────────


def _is_truthy_content(value: str) -> bool:
    v = value.strip()
    if not v:
        return False
    low = v.lower()
    return not any(w in low for w in _PLACEHOLDER_WORDS)


def validate_raw_proposals(
    graph: dict[str, Any], raw: list[Any]
) -> tuple[list[AlignProposal], int]:
    """确定性校验：动作合法、目标存在于图谱、内容非占位。

    返回 ``(合法提案列表, 丢弃计数)``——此函数是提案池唯一入口闸门。
    """
    legal_targets = graph_target_keys(graph)
    valid: list[AlignProposal] = []
    dropped = 0
    for item in raw:
        if not isinstance(item, dict):
            dropped += 1
            continue
        action = item.get("action")
        target = item.get("target")
        content = item.get("content")
        if not (
            isinstance(action, str)
            and isinstance(target, str)
            and isinstance(content, str)
        ):
            dropped += 1
            continue
        if action not in ALIGN_ACTIONS:
            dropped += 1
            continue
        if target not in legal_targets:
            dropped += 1
            continue
        if not _is_truthy_content(content):
            dropped += 1
            continue
        if len(valid) >= ALIGN_MAX_PROPOSALS:
            dropped += 1
            continue
        quote = item.get("quote")
        valid.append(
            AlignProposal(
                action=action,
                target=target,
                content=content.strip()[:500],
                quote=quote.strip()[:200] if isinstance(quote, str) else "",
                graph_code=(
                    item["graph_code"]
                    if isinstance(item.get("graph_code"), str)
                    else ""
                ),
            )
        )
    return valid, dropped


# ── stale 影响预警（只读查询 graph_registry） ───────────────────────────────


def _registry_children(registry_db: str, graph_code: str) -> list[dict[str, Any]]:
    """只读查询某图谱版本的下游产物（parent_graph_code 反查）。"""
    if not registry_db:
        return []
    try:
        conn = sqlite3.connect(str(registry_db), timeout=30.0)
        try:
            rows = conn.execute(
                "SELECT graph_code, status FROM graph_registry "
                "WHERE parent_graph_code = ?",
                (graph_code,),
            ).fetchall()
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 — 查询失败降级，不阻断
        return []
    return [
        {"graph_code": r[0], "status": r[1]} for r in rows if isinstance(r, tuple)
    ]


def build_stale_warning(graph_code: str, registry_db: str | None = None) -> list[str]:
    """「将使 … 过期」型影响预警 + 下游产物清单（确定性，只读）。"""
    if not registry_db or not graph_code:
        return []
    children = _registry_children(registry_db, graph_code)
    if not children:
        return []
    lines = [f"这项修改会使已生成的成果「{graph_code}」过期"]
    downstream = [c["graph_code"] for c in children if c.get("graph_code")]
    if downstream:
        lines.append("受影响的下游产物：" + "、".join(f"「{c}」" for c in downstream))
    return lines


# ── LLM 提议层 ──────────────────────────────────────────────────────────────


class AlignmentProposer:
    """LLM 对齐提议器（单生产方；确定性过滤与装包，inference_pack 先例）。"""

    def __init__(self, provider: Any) -> None:
        self._provider = provider

    def propose(
        self,
        graph: dict[str, Any] | None,
        user_input: str,
        invited: list[str] | None = None,
    ) -> AlignmentPack:
        """单次 LLM 调用生成提案；任何失败路径降级为空包 + note。

        LLM 输出仅经确定性校验器进入提案池——绝不触碰图谱写入路径。
        """
        if self._provider is None:
            return AlignmentPack(note="无 LLM provider，对齐提议降级为空")
        if not isinstance(graph, dict) or not graph_target_keys(graph):
            return AlignmentPack(note="暂无已确定的设定记录，无需对齐")

        system = self._build_prompt(graph, user_input, invited)
        try:
            out = self._provider.chat_json([{"role": "system", "content": system}])
            if inspect.isawaitable(out):  # 同步/异步 provider 双兼容
                out = asyncio.run(out)  # type: ignore[arg-type]
        except Exception as e:  # noqa: BLE001 — degrade, never crash
            return AlignmentPack(note=f"对齐提议生成失败，已降级为空：{str(e)[:120]}")
        if not isinstance(out, dict):
            return AlignmentPack(note="对齐提议响应形状不符，已降级为空")
        raw = out.get("proposals")
        if not isinstance(raw, list):
            return AlignmentPack(note="对齐提议响应形状不符，已降级为空")

        proposals, dropped = validate_raw_proposals(graph, raw)
        note = "" if proposals else "对齐提议无有效建议（动作外/目标不存在/占位被过滤）"
        return AlignmentPack(proposals=proposals, dropped=dropped, note=note)

    @staticmethod
    def _build_prompt(
        graph: dict[str, Any], user_input: str, invited: list[str] | None
    ) -> str:
        digest = build_graph_digest(graph, invited)
        targets = sorted(graph_target_keys(graph))
        action_desc = "；".join(
            f"{_ACTION_LABELS[a]}（{a}）" for a in ALIGN_ACTIONS
        )
        return (
            "你是世界观设定对齐助手。以下是本会话已确定设定的紧凑摘要，"
            "以及用户刚刚说的新内容。请判断新内容与已有记录的关系，"
            "提出 0-5 条对齐提案。动作闭集（只能用这四个英文值）："
            f"{action_desc}。\n"
            "每条提案输出 JSON 对象："
            '{"action": "...", "target": "<必须是下方目标键列表中的一个>", '
            '"content": "<给用户看的说明，引用用户原话转述，禁止出现模块名/'
            '字段名/键名>", "quote": "<用户原话摘引（可空）>"}。\n'
            "顶层格式：{\"proposals\": [...]}。目标键列表：\n"
            + "\n".join(targets)
            + "\n\n【图谱摘要开始】\n"
            + digest
            + "\n【图谱摘要结束】\n\n用户刚说：\n"
            + user_input[:2000]
        )


# ── 装包（additive 容器，绝不直写图谱） ─────────────────────────────────────


def install_proposals(
    session: Any,
    proposals: list[AlignProposal],
    registry_db: str | None = None,
) -> list[str]:
    """提案装入 ``session.pending_alignments``（additive 独立容器）。

    同时确定性填充 stale 影响预警（下游产物清单）。返回提案 key 列表。
    此函数是提案与图谱之间唯一许可的交互面，且只写提案池。
    """
    keys: list[str] = []
    for i, p in enumerate(proposals, start=1):
        key = f"align-{i:03d}"
        while key in session.pending_alignments:
            key = f"align-{i:03d}-{len(keys) + 1}"
        p.stale_warning = build_stale_warning(p.graph_code, registry_db)
        session.pending_alignments[key] = {
            "proposal": p,
            "source": "alignment_flow",
        }
        keys.append(key)
        log_event(
            getattr(session, "session_id", ""),
            "alignment_proposal_installed",
            action=p.action,
            dropped=len(p.stale_warning),
        )
    return keys


# ── 用户确认（resolve_proposal 先例：确认应用 / 拒绝零副作用） ──────────────


def resolve_alignment(
    session: Any, key: str, accept: bool, registry_db: str | None = None
) -> dict[str, Any]:
    """解析一条待定对齐提案。

    - ``accept=True``：确定性应用——open_question 归档（引用用户原话）
      + 下游 stale 传播（复用 stale_marker，仅当提案带 graph_code 且
      提供 registry_db）。全程无 LLM 写入。
    - ``accept=False``：丢弃，零副作用（不碰图谱/归档/registry）。
    - 幂等兜底：未知 key 返回 not_found，不抛错（Metis E3 先例）。
    """
    entry = session.pending_alignments.get(key)
    if entry is None:
        return {"applied": False, "accept": accept, "error": "not_found"}

    proposal: AlignProposal = entry["proposal"]

    if not accept:
        session.pending_alignments.pop(key, None)
        log_event(getattr(session, "session_id", ""), "alignment_declined")
        return {"applied": False, "accept": False}

    # 确定性应用 ①：open_question 归档（C6 结构化记录，OpenQuestion.dump 格式）
    question = render_proposal(proposal)
    qid = f"oq-align-{key}"
    if not any(r.get("id") == qid for r in session.open_question_archive):
        session.open_question_archive.append(
            OpenQuestion(
                id=qid,
                question=question,
                status="answered",
                answer=proposal.content,
                source_hint=f"alignment:{proposal.action}",
            ).model_dump()
        )

    # 确定性应用 ②：下游 stale 传播（复用 stale_marker 既有函数）
    if registry_db and proposal.graph_code:
        from app.domains.creation.shared.stale_marker import mark_downstream_stale

        mark_downstream_stale(
            registry_db,
            proposal.graph_code,
            change_set={
                "action": proposal.action,
                "target": proposal.target,
                "via": "alignment_flow",
            },
        )

    session.pending_alignments.pop(key, None)
    log_event(
        getattr(session, "session_id", ""),
        "alignment_applied",
        action=proposal.action,
    )
    return {"applied": True, "accept": True, "action": proposal.action}


# ── 文案渲染（说人话：引原话转述，不报模块/字段名） ────────────────────────


def render_proposal(p: AlignProposal, graph: dict[str, Any] | None = None) -> str:
    """渲染用户可见提案文案（人话，键域消毒）。

    节点 id / 边 key 绝不外露；动作以中文标签呈现；引原话转述。
    """
    label = _ACTION_LABELS.get(p.action, "对齐")
    alias = _target_display(graph, p.target) if graph else "一条已有记录"
    parts = [f"【{label}】"]
    if p.quote:
        parts.append(f"你说过「{p.quote}」——")
    parts.append(p.content)
    parts.append(f"（涉及{alias}）")
    if p.stale_warning:
        parts.append("；".join(p.stale_warning))
    text = "".join(parts)
    # 键域消毒兜底：任何裸 ".{mid}." 形态改写（G5 同款，防御性）
    return text.replace("d:", "条目·")
