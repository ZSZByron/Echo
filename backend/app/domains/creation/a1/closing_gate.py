"""closing_gate — 收尾双条件判定 + 输出前确定性图谱识别（D21 Task 6）。

Shared foundation consumed by T10 (收尾查询端点/排序) and T18 (D22 消费).

两个纯函数，零 LLM、零打分/权重（识别 = 事实盘点，只做拼装）：

1. ``is_preset_phase_complete(session)`` — 收尾双条件（spec v1.3 §5.4）：
   - 配方问题问完 = 问题树走查态 ``session.phase == PHASE_COMPLETED``
     （guide_engine.sync_position 在全部子字段已答/跳过时置位）；
   - fills 待确认清零 = ``len(session.pending_proposals) == 0``。
     pending_proposals 只持有 write-guard 拦截的冲突提案（guide_engine
     ``_apply_fills`` Branch 3）；auto fills（空字段直写 / prefill 豁免，
     FIELD_SOURCE_* 元数据标记）从不进 pending——auto fills 语义天然
     不阻塞收尾，契约测试见 test_closing_gate.py。

2. ``build_output_preview(file_id)`` — 输出前确定性图谱识别（收尾询问
   的唯一数据源，D22⑤）：模块覆盖（module_done_ratio）+ 缺口清单 +
   版本链（graph_code/instance/version/parent）+ stale 双信号
   （registry status = stale **或** 同 IP 同 stage 存在更高
   (instance, version) 产物——对齐 a1_routes._graph_is_stale 口径，
   stale 永不阻断，只披露）。输出含可生成物清单（D22 三件 + 跑团件，
   T10/T18 排序输入）、缺口披露、stale 预警。

file_id 查找默认走 a1_routes 的会话存储（``_SESSIONS`` / ``_FILES``，
A1Store 落盘 + 启动回载）；测试可用 sessions/files/registry_db 注入
纯 fixture。本模块不 import 任何 LLM / 打分层。
"""
from __future__ import annotations

from typing import Any

from app.domains.creation.a1.guide_engine import (
    A1Session,
    PHASE_COMPLETED,
    core_recipe_modules,
)
from app.domains.creation.seed.a1_question_tree import (
    get_module,
    get_subfield,
    is_truthy_answer,
    module_done_ratio,
)
from app.domains.creation.shared import stale_marker

# ---------------------------------------------------------------------------
# 可生成物清单（事实常量，非排序——排序规则归 T10）
# ---------------------------------------------------------------------------

#: D22 通用投影三件（id 与 T7 产出池注册一致）+ 跑团件（骰/角色投影）。
#: kind: "d22" | "trpg"。顺序即声明顺序，仅作为 T10 排序的输入。
CONSUMER_ARTIFACTS: tuple[dict[str, str], ...] = (
    {"id": "world_bible", "kind": "d22"},
    {"id": "character_codex", "kind": "d22"},
    {"id": "story_outline", "kind": "d22"},
    {"id": "dice_projection", "kind": "trpg"},
    {"id": "character_projection", "kind": "trpg"},
)


# ---------------------------------------------------------------------------
# 1. 收尾双条件
# ---------------------------------------------------------------------------


def closing_status(session: A1Session) -> dict[str, Any]:
    """Dual-condition breakdown（判定明细，供 UI/端点披露）."""
    questions_complete = session.phase == PHASE_COMPLETED
    pending_count = len(session.pending_proposals)
    return {
        "questions_complete": questions_complete,
        "pending_count": pending_count,
        "complete": questions_complete and pending_count == 0,
    }


def is_preset_phase_complete(session: A1Session) -> bool:
    """收尾双条件：配方问题问完 **且** fills 待确认清零。

    auto fills（FIELD_SOURCE 直写路径）不在 pending_proposals 中，
    不阻塞收尾——只有 write-guard 拦截的冲突提案算「待确认」。
    """
    return closing_status(session)["complete"]


# ---------------------------------------------------------------------------
# 2. 输出前确定性图谱识别
# ---------------------------------------------------------------------------


def _superseded_exists(listing: dict, graph_code: str) -> str | None:
    """同 IP 同 stage 存在更高 (instance, version) → 返回取代者代码。

    口径与 a1_routes._graph_is_stale 信号 2 一致（覆盖「W1 未注册但
    W2 已注册」的运行态）。纯查询，不改任何状态。
    """
    parts = graph_code.split("-")
    if len(parts) < 3:
        return None
    ip, stage_inst = parts[0], parts[1]
    stage = stage_inst[0]
    try:
        cur = (int(stage_inst[1:]), int(graph_code.rsplit("-v", 1)[1]))
    except (ValueError, IndexError):
        return None
    for group in listing.get("ips", []):
        for art in group.get("artifacts", []):
            code = str(art.get("graph_code", ""))
            if art.get("stage") != stage or not code.startswith(f"{ip}-{stage}"):
                continue
            try:
                cand = (int(code.split("-")[1][1:]), int(art.get("version", 0)))
            except (ValueError, IndexError):
                continue
            if cand > cur:
                return code
    return None


def _stale_info(
    registry_db: str, user_id: str, graph_code: str | None
) -> tuple[bool, str | None, str | None]:
    """stale 双信号判定。返回 (is_stale, reason, superseded_by)。

    查询失败按未过期处理（不阻断——与 a1_routes 同口径，信息性非门禁）。
    """
    if not graph_code:
        return False, None, None
    superseded_by: str | None = None
    try:
        if stale_marker.is_stale(registry_db, graph_code):
            return True, "registry_status_stale", None
        superseded_by = _superseded_exists(
            stale_marker.list_user_graphs(registry_db, user_id), graph_code
        )
    except Exception:  # noqa: BLE001 — 信息性披露，查询失败不阻断
        return False, None, None
    if superseded_by:
        return True, "superseded_by_newer_instance", superseded_by
    return False, None, None


def _module_coverage(session: A1Session) -> list[dict[str, Any]]:
    """模块覆盖盘点（recipe 顺序，module_done_ratio 真值化计数）。"""
    out: list[dict[str, Any]] = []
    for mid in core_recipe_modules(session):
        m = get_module(mid)
        if m is None:
            continue  # unknown recipe module — 未知 id 不入盘点（与 progress 同口径）
        fields = m["fields"]
        out.append({
            "module_id": mid,
            "done_ratio": module_done_ratio(mid, session.answers),
            "done_fields": sum(
                1 for f in fields
                if is_truthy_answer(session.answers.get(f"{mid}.{f['id']}"))
            ),
            "total_fields": len(fields),
        })
    return out


def _gap_list(session: A1Session) -> list[dict[str, Any]]:
    """缺口清单：recipe 内真值为空的子字段（占位/空 = 语义缺席，J1）。"""
    gaps: list[dict[str, Any]] = []
    for mid in core_recipe_modules(session):
        m = get_module(mid)
        if m is None:
            continue
        for f in m["fields"]:
            key = f"{mid}.{f['id']}"
            if not is_truthy_answer(session.answers.get(key)):
                sf = get_subfield(mid, f["id"])
                gaps.append({
                    "module_id": mid,
                    "field": f["id"],
                    "key": key,
                    "label": sf["label"] if sf else f["id"],
                })
    return gaps


def build_output_preview(
    file_id: str,
    *,
    sessions: dict[str, A1Session] | None = None,
    files: dict[str, dict[str, Any]] | None = None,
    registry_db: str | None = None,
) -> dict[str, Any]:
    """输出前确定性图谱识别（收尾询问唯一数据源，D22⑤/⑦）。

    零 LLM、零打分——纯拼装：模块覆盖 + 缺口 + 版本链 + stale 双信号
    + 可生成物清单。同输入同输出（纯函数；默认存储视图注入）。
    """
    if sessions is None or files is None:
        # 延迟默认：a1_routes 持有 A1Store 支撑的会话/文件存储
        from app.api.a1_routes import _FILES, _SESSIONS, _registry_db

        sessions = _SESSIONS if sessions is None else sessions
        files = _FILES if files is None else files
        if registry_db is None:
            registry_db = _registry_db()
    rec = files.get(file_id)
    if not rec:
        return {
            "file_id": file_id,
            "exists": False,
            "closing": closing_status(
                A1Session(session_id="missing", user_id="missing")
            ),
            "module_coverage": [],
            "gaps": [],
            "version_chain": None,
            "stale": False,
            "stale_warning": None,
            "consumers": [dict(c) for c in CONSUMER_ARTIFACTS],
        }
    session: A1Session | None = sessions.get(rec.get("session_id", ""))
    if session is None:
        session = A1Session(
            session_id=str(rec.get("session_id", "")), user_id="unknown"
        )
    graph_code = rec.get("graph_code") or None
    inst_no = ver_no = None
    if graph_code and "-" in graph_code and "-v" in graph_code:
        try:
            inst_no = int(graph_code.split("-")[1][1:])
            ver_no = int(graph_code.rsplit("-v", 1)[1])
        except (ValueError, IndexError):  # 畸形 code → 链条留空，不崩溃
            inst_no = ver_no = None
    is_stale, reason, superseded_by = _stale_info(
        registry_db or "", session.user_id, graph_code
    )
    return {
        "file_id": file_id,
        "exists": True,
        "closing": closing_status(session),
        "module_coverage": _module_coverage(session),
        "gaps": _gap_list(session),
        "version_chain": {
            "graph_code": graph_code,
            "ip_code": rec.get("ip"),
            "instance_no": inst_no,
            "version": ver_no,
            "superseded_by": superseded_by,
            "status": rec.get("status", "draft"),
        },
        "stale": is_stale,
        "stale_warning": (
            f"产物 {graph_code} 已过期（{reason}），消费前请知悉（stale 永不阻断）"
            if is_stale else None
        ),
        "consumers": [dict(c) for c in CONSUMER_ARTIFACTS],
    }
