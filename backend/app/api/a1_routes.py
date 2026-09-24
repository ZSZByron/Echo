"""A1 workspace API routes — 8 endpoints per A1-v0.5 plan Task 9.

Three-state flow: seed select → guided chat (10 sections) → finalize to
graph (+ IP poster). Constraint edges are injected at finalize via
apply_constraints (T-F hook); re-finalize issues W1-v2 and marks
downstream graphs stale (iron law: never delete, never overwrite).
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ValidationError

from app.ai.config import load_provider_config
from app.ai.provider import create_provider
from app.ai.visual_bg import run_visual_bg_pipeline
from app.config.paths import ASSETS_DIR
from app.domains.creation.a1.guide_engine import (
    A1Session,
    handle_message,
    progress,
    sync_position,
)
from app.domains.creation.a1.inference_pack import (
    InferencePacker,
    apply_pack_feedback,
)
from app.domains.creation.a1.innovation_capture import (
    Confirmation,
    confirm_proposal,
)
from app.domains.creation.a1.interaction_log import log_event
from app.domains.creation.a1.interviewer import (
    DegradingInterviewer,
    RealLLMInterviewer,
)
from app.domains.creation.a1.ip_poster import build_poster

logger = logging.getLogger(__name__)
from app.domains.creation.a1.open_questions import OpenQuestion, OpenQuestionLog
from app.domains.creation.a1.semantic_compiler import (
    derive_dice_recommendation,
)
from app.domains.creation.graph.constraint_topology import apply_constraints
from app.domains.creation.seed.a1_question_tree import (
    MODULES,
    all_subfield_keys,
    first_subfield,
    get_module,
    get_subfield,
    is_module_over_half,
    module_ids,
    subs_for_module,
)
from app.domains.creation.seed.preset_loader import load_presets
from app.domains.creation.shared import stale_marker
from app.domains.creation.shared.graph_code_issuer import GraphCodeIssuer
from app.domains.creation.shared.module_registry import (
    RECIPES,
    STORY_PRIMARY_TYPES,
    resolve_recipe_id,
)
from app.models.dimension import (
    ActOutput,
    DimensionResultSet,
    LawOutput,
    NarOutput,
    SocOutput,
    WstOutput,
)
from app.domains.creation.a1.concept_edge_extractor import (
    ConceptTerm,
    EdgesV2Result,
    extract_concept_relations,
)
from app.domains.creation.a1.concept_relation_vocab import RelationRegistry
from app.domains.creation.a1.graphify import (
    GraphifyResult,
    dedupe_items,
    depth_id,
    graphify_llm,
    is_title_truncated,
    validate_anchors,
)
from app.domains.creation.a1.warning_ledger import (
    SOURCE_ASSEMBLE,
    SOURCE_ANSWERS,
    SOURCE_FINALIZE,
    SOURCE_GRAPHIFY,
    SOURCE_UPLOAD,
    entry as ledger_entry,
    from_dead_edges,
    from_strings,
)
from app.domains.creation.modules.character_projector import (
    DiceRequiredError,
    project_character_template,
)
from app.domains.creation.modules.dice_projector import (
    DiceTemplate,
    project_dice_template,
)
from app.domains.creation.modules.main_module import (
    compile_document,
    render_markdown,
)
from app.domains.creation.a1.tier_map import TIER_MAP
from app.models.knowledge_graph import (
    EdgeType,
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
    NodeStatus,
)

router = APIRouter()

# MVP in-memory stores (per plan: sessions in memory, no persistence).
_SESSIONS: dict[str, A1Session] = {}
_FILES: dict[str, dict[str, Any]] = {}

# ---- Disk persistence (v0.5 A1: survive backend restarts) ----
# Lazy load: _load_once() runs on first access (not at import — import-time
# side effects would interfere with test collection). Save points sit at the
# tail of every mutating endpoint's success path.
from app.domains.creation.a1.store import A1Store  # noqa: E402

_STORE = A1Store()
_loaded = False


def _load_once() -> None:
    """Load persisted sessions/files into memory exactly once per process."""
    global _loaded
    if _loaded:
        return
    _loaded = True
    sessions, files = _STORE.load()
    _SESSIONS.update(sessions)
    _FILES.update(files)


def _save_store() -> None:
    """Snapshot in-memory state to disk (best-effort; never crash a request)."""
    try:
        _STORE.save(_SESSIONS, _FILES)
    except Exception as exc:  # noqa: BLE001 — persistence failure must not 500
        from app.domains.creation.a1.interaction_log import log_event as _log
        _log("a1_store", "save_failed", error=f"{type(exc).__name__}: {exc}"[:300])

# In-memory lock to prevent duplicate concurrent poster generation for the
# same file_id (mirrors _generation_tasks in assets_routes.py).
_poster_generation_tasks: dict[str, Any] = {}

_ISSUER_DB = Path(__file__).resolve().parents[2] / "data" / "a1_codes.db"
_ISSUER_DB.parent.mkdir(parents=True, exist_ok=True)


def _registry_db() -> str:
    """Path of the shared graph registry (stale_marker) database."""
    return str(ASSETS_DIR / "ugc.db")

_COMPILER = None  # deprecated: semantic compiler replaced by LLM interviewer

# LLM-guided interviewer (lazy singleton): created on first use so that
# main.py's load_dotenv() has run by then. Import-time creation would
# see no ACTIVE_PROVIDER and permanently degrade to offline mode.
_INTERVIEWER: DegradingInterviewer | None = None


def _get_interviewer() -> DegradingInterviewer:
    global _INTERVIEWER
    if _INTERVIEWER is None:
        try:
            provider = create_provider(load_provider_config())
        except Exception:  # noqa: BLE001 — no API key / bad config must not crash
            provider = None
        _INTERVIEWER = DegradingInterviewer(RealLLMInterviewer(provider))
    return _INTERVIEWER

# tag -> (dimension, output model class) for parsing answer writes into
# the DimensionResultSet consumed by apply_constraints.
_TAG_TO_OUTPUT = [
    ("LAW", LawOutput),
    ("ACT", ActOutput),
    ("NAR", NarOutput),
    ("WST", WstOutput),
    ("SOC", SocOutput),
]
_STRUCTURED_TAGS: dict[str, type] = {}
for _dim, _cls in _TAG_TO_OUTPUT:
    for _tag in _cls.model_fields:
        if _tag not in ("rules", "actions", "style", "tone", "keywords",
                        "effects", "relations", "mechanism", "note", "forbidden"):
            _STRUCTURED_TAGS[_tag] = _cls


class StartRequest(BaseModel):
    user_id: str
    seed_id: int | None = None
    custom_idea: str | None = None
    # E1-Lite 冲动卡入口（可选）：主/次冲动类型，白名单见 IMPULSE_TYPE_IDS。
    impulse_primary: str | None = None
    impulse_secondary: str | None = None


# E1-Lite 冲动类型白名单（spec §12.1，9 型逐字锁定，不允许增删改写）。
IMPULSE_TYPE_IDS: frozenset[str] = frozenset({
    "setting_heavy",
    "character_driven",
    "plot",
    "philosophy",
    "exploration",
    "romance",
    "nostalgia",
    "healing",
    "unsure",
})


class ChatRequest(BaseModel):
    session_id: str
    message: str
    # C7: 跳过某条待问开放问题（status=skipped 持久，upsert 不复活）
    skip_question_id: str | None = None


class ConfirmRequest(BaseModel):
    session_id: str
    proposal: dict
    choice: str
    kind: str = "classification"  # "classification" | "fill"


def _question_payload(session: A1Session) -> dict | None:
    if session.phase == "completed":
        return None

    # Get current module and subfield from session
    current_module_id = session.current_module
    current_subfield_id = session.current_subfield

    module = get_module(current_module_id)
    if not module:
        return None

    subfield = get_subfield(current_module_id, current_subfield_id)
    if not subfield:
        return None

    return {
        "section": current_module_id,
        "section_label": module["label"],
        "sub_id": subfield["id"],
        "sub_label": subfield["label"],
        "question": subfield["question"],
        "hint": subfield["hint"],
        "example": subfield.get("example", ""),
    }


def _open_question_payload(oq_log: OpenQuestionLog, session: A1Session) -> dict:
    """C7: 待问提示卡 + 状态角标数据。

    pending_question: 最老的一条 pending（一次一条）；提案卡片在场时挂起
    （None），前端以此实现单问句铁律。pending_questions_count 供"待问 N"角标。
    """
    count = sum(1 for q in oq_log.items if q.status == "pending")
    if session.pending_proposals:
        return {"pending_question": None, "pending_questions_count": count}
    q = oq_log.next_pending()
    return {
        "pending_question": (
            {"id": q.id, "question": q.question} if q is not None else None
        ),
        "pending_questions_count": count,
    }


def _build_dimension_result_set(session: A1Session) -> DimensionResultSet:
    """Parse `tag=value; ...` answer fragments into structured Outputs.

    # deprecated (A1 v0.5: constraint_fields 通道取代) — kept for
    # archaeology; still wired as the answers-channel source for
    # apply_constraints in _build_graph.
    """
    kwargs: dict[str, dict[str, str]] = {"LAW": {}, "ACT": {}, "NAR": {}, "WST": {}, "SOC": {}}
    dim_by_cls = {cls: dim for dim, cls in _TAG_TO_OUTPUT}
    for value in session.answers.values():
        if not value or value.startswith("[其他]"):
            continue
        for fragment in value.split(";"):
            fragment = fragment.strip()
            if "=" not in fragment:
                continue
            tag, _, val = fragment.partition("=")
            tag, val = tag.strip(), val.strip()
            if "." in tag:  # strip optional dim prefix (e.g. LAW.world_structure)
                tag = tag.split(".", 1)[1]
            cls = _STRUCTURED_TAGS.get(tag)
            if cls is None or not val:
                continue
            kwargs[dim_by_cls[cls]].setdefault(tag, val)
    drs_kwargs: dict[str, Any] = {}
    dim_map = {"LAW": LawOutput, "ACT": ActOutput, "NAR": NarOutput,
               "WST": WstOutput, "SOC": SocOutput}
    for dim, cls in dim_map.items():
        if kwargs[dim]:
            drs_kwargs[dim] = cls(**kwargs[dim])
    return DimensionResultSet(**drs_kwargs)


def _assemble_depth_tree(
    session: A1Session,
    llm_result: GraphifyResult,
    nodes: dict[str, GraphNode],
    edges: list[GraphEdge],
    module_serial_by_id: dict[str, int],
    entry_serial_by_id: dict[str, int],
    legal_anchors: set[str] | None = None,
) -> tuple[list[str], int]:
    """Mount the depth tree (L4 ``d:`` nodes) under answered concept-tree anchors.

    Governance §5b: node id = ``depth_id(anchor, title)``; serial =
    ``D{module_serial}-{entry_serial}-{k}``; TREE edge L3→L4 "分条目".
    T11: ``items[].children`` mount recursively (one extra level, depth cap
    2 = items→children; children with their own children are rejected with
    a warning). Child ids reuse the same ``d:{anchor}:{title}`` scheme
    (uniqueness within the anchor layer; title conflicts keep the first
    occurrence); child serials are ``D{module_serial}-{entry_serial}-{k}-{j}``;
    TREE edge parent→child "分条目". Env switch ``A1_DEPTH_CHILDREN``
    (default on) disables child mounting entirely.
    Returns ``(warnings, depth_node_count)``.
    """
    warnings: list[str] = []
    legal = legal_anchors if legal_anchors is not None else set(all_subfield_keys())
    illegal = set(validate_anchors(llm_result, legal_anchors=legal))
    warnings.extend(illegal)
    children_enabled = os.environ.get("A1_DEPTH_CHILDREN", "1") == "1"
    mounted = 0
    for group in llm_result.entries:
        if group.anchor not in legal:
            continue  # illegal anchor already reported via validate_anchors
        anchor_module = group.anchor.split(".", 1)[0]
        m_serial = module_serial_by_id.get(anchor_module)
        e_serial = entry_serial_by_id.get(group.anchor)
        if m_serial is None or e_serial is None:
            # anchor's L3 entry node absent (empty answer) → nothing to mount under
            warnings.append(f"锚点无已答条目节点，深度条目跳过: {group.anchor!r}")
            continue
        kept, dupes = dedupe_items(group.items)
        warnings.extend(f"重复条目去重: {t!r}" for t in dupes)
        for k, item in enumerate(kept, start=1):
            # J3 披露：32 字静默截断改为有痕（id 仍截断——稳定性契约不动）
            if is_title_truncated(item.title):
                warnings.append(f"标题超32字已截断: {item.title[:40]!r}")
            nid = depth_id(group.anchor, item.title)
            if nid not in nodes:
                nodes[nid] = GraphNode(
                    id=nid,
                    serial_number=f"D{m_serial}-{e_serial}-{k}",
                    level=4,
                    description=item.content or item.title,
                )
                edges.append(GraphEdge(
                    from_node_id=group.anchor,
                    to_node_id=nid,
                    edge_type=EdgeType.TREE,
                    visual_description="分条目",
                ))
                mounted += 1
            # ---- T11: children recursion (depth cap 2: items→children) ----
            if not item.children:
                continue
            if not children_enabled:
                warnings.append(
                    f"children 挂载已禁用(A1_DEPTH_CHILDREN=0): "
                    f"{group.anchor} / {item.title!r}"
                )
                continue
            kept_children, child_dupes = dedupe_items(item.children)
            warnings.extend(f"重复子条目去重: {t!r}" for t in child_dupes)
            for j, child in enumerate(kept_children, start=1):
                if child.children:
                    warnings.append(
                        f"children 深度超限(>2层)拒收: "
                        f"{group.anchor} / {child.title!r}"
                    )
                if is_title_truncated(child.title):
                    warnings.append(f"标题超32字已截断: {child.title[:40]!r}")
                cid = depth_id(group.anchor, child.title)
                if cid in nodes:
                    continue  # 层级内 title 唯一化：冲突保留首条
                nodes[cid] = GraphNode(
                    id=cid,
                    serial_number=f"D{m_serial}-{e_serial}-{k}-{j}",
                    level=4,
                    description=child.content or child.title,
                )
                edges.append(GraphEdge(
                    from_node_id=nid,
                    to_node_id=cid,
                    edge_type=EdgeType.TREE,
                    visual_description="分条目",
                ))
                mounted += 1
    return warnings, mounted


def _merge_llm_edges(
    session: A1Session,
    llm_result: GraphifyResult,
    nodes: dict[str, GraphNode],
    edges: list[GraphEdge],
    file_rec: dict,
    dead_edges: list[dict],
) -> int:
    """Merge ``llm_result.edges`` into the graph (governance §5c).

    Endpoint-missing edges go into ``dead_edges`` (dead zone, persisted on
    the file record) instead of being silently dropped. Re-finalize
    recovery: a (from, to, relation) triple present in
    ``file_rec["confirmed_edges"]`` restores ``confirmed=True`` (idempotent
    merge pattern, mirrors the confirmed-edge loop in finalize).
    Returns the number of edges actually added to the graph.
    """
    confirmed = file_rec.get("confirmed_edges", {})
    # C7: rationale 不入 GraphEdge（模型无此字段），持久化到 file 记录，
    # 供前端/审计验证「转正边 rationale 引用用户回答」。
    rationales = file_rec.setdefault("edge_rationales", {})
    added = 0
    for spec in llm_result.edges:
        fid, tid = spec.from_, spec.to
        if fid not in nodes or tid not in nodes:
            dead_edges.append({
                "from": fid, "to": tid, "relation": spec.relation,
                "confidence": spec.confidence, "reason": "endpoint_missing",
            })
            continue
        key = _make_edge_key(fid, tid, spec.relation)
        rationales[key] = spec.rationale
        edges.append(GraphEdge(
            from_node_id=fid,
            to_node_id=tid,
            edge_type=_CONFIDENCE_TO_EDGETYPE.get(spec.confidence, EdgeType.SEMANTIC),
            visual_description=spec.relation,
            relation=spec.relation,
            confidence=spec.confidence,
            confirmed=bool(key in confirmed),
        ))
        added += 1
    return added


def _build_constraint_result_set(
    constraint_fields: dict[str, str],
) -> tuple[DimensionResultSet, list[str]]:
    """cst channel (T11): LLM ``constraint_fields`` (``DIM.tag`` → str) →
    ``DimensionResultSet`` for ``apply_constraints``.

    Output-model fields are enum-validated, but graphify rule 4 only
    whitelists keys — values may be free-form LLM strings. On
    ``ValidationError`` the dim Output is built via ``model_construct``:
    values are recorded verbatim in the Constraint node description
    (description-only channel, not re-parsed as enums).
    Unknown dims / malformed keys are skipped with a warning.
    """
    warnings: list[str] = []
    per_dim: dict[str, dict[str, str]] = {}
    dim_map = {"LAW": LawOutput, "ACT": ActOutput, "NAR": NarOutput,
               "WST": WstOutput, "SOC": SocOutput}
    for key, value in constraint_fields.items():
        dim, _, tag = str(key).partition(".")
        if not tag or dim not in dim_map or not str(value):
            warnings.append(f"[constraint_fields] 非法键跳过: {key!r}")
            continue
        per_dim.setdefault(dim, {})[tag] = str(value)
    kwargs: dict[str, Any] = {}
    for dim, fields in per_dim.items():
        cls = dim_map[dim]
        try:
            kwargs[dim] = cls(**fields)
        except ValidationError:
            kwargs[dim] = cls.model_construct(**fields)
    return DimensionResultSet(**kwargs), warnings


def _apply_constraint_fields(
    graph: KnowledgeGraph,
    llm_result: GraphifyResult,
) -> list[str]:
    """Wire ``constraint_fields`` into ``cst_`` nodes / CROSS edges (T11,
    governance §5d — 考古断链闭合). Idempotent: ``apply_constraints``
    skips ``cst_`` ids that already exist (e.g. created by the answers
    channel), mirroring the confirmed-merge pattern in finalize."""
    if not llm_result.constraint_fields:
        return []
    drs, warnings = _build_constraint_result_set(llm_result.constraint_fields)
    apply_constraints(graph, drs, stage="A1")
    return warnings


def _assemble_assertions(
    session: A1Session,
    llm_result: GraphifyResult,
    nodes: dict[str, GraphNode],
    llm_semantic_added: int,
    input_edges: int,
) -> None:
    """Runtime assembly assertions (governance §5 invariant checks, log-only)."""
    if llm_result.constraint_fields and not any(
        nid.startswith("cst_") for nid in nodes
    ):
        log_event(
            session.session_id, "assemble_assertion",
            kind="constraint_fields_without_cst_nodes",
            constraint_fields=len(llm_result.constraint_fields),
        )
    if input_edges and llm_semantic_added == 0:
        log_event(
            session.session_id, "assemble_assertion",
            kind="edges_without_semantic_edge",
            input_edges=input_edges,
        )


def _build_graph(
    session: A1Session,
    file_rec: dict,
    llm_result: GraphifyResult | None = None,
    legal_anchors: set[str] | None = None,
) -> tuple[KnowledgeGraph, set[str]]:
    # M4b：bg/L2/L3 背景树纯装配段抽出至 live_projection.
    # assemble_background_tree（逐行保形——m1_default_snapshot 逐字节回归
    # 锚定），此处与 live_projection 共用同一确定性装配（图谱确定性装配
    # 铁律：同输入可复现，零 LLM）。
    from app.domains.creation.a1.live_projection import assemble_background_tree

    nodes, edges, bg_id, module_serial_by_id, entry_serial_by_id = (
        assemble_background_tree(
            session.answers, MODULES, session.ip_code, session.session_id,
            module_summaries=(
                llm_result.module_summaries if llm_result is not None else None
            ),
        )
    )

    # Dead-edge zone: rebuilt every assemble; finalize may append more
    # (confirmed-edge snapshots referencing endpoints absent from the graph).
    dead_edges: list[dict] = []

    # ---- A1 v0.5 dual-tree assembly (governance §2/§5) ----
    llm_warnings: list[str] = []
    input_edges = 0
    llm_semantic_added = 0
    if llm_result is not None:
        llm_warnings, _mounted = _assemble_depth_tree(
            session, llm_result, nodes, edges,
            module_serial_by_id, entry_serial_by_id,
            legal_anchors=legal_anchors,
        )
        input_edges = len(llm_result.edges)
        added = _merge_llm_edges(
            session, llm_result, nodes, edges, file_rec, dead_edges,
        )
        llm_semantic_added = sum(
            1 for e in edges[len(edges) - added:]
            if e.confidence == "semantic"
        ) if added else 0

    file_rec["dead_edges"] = dead_edges
    file_rec["assemble_warnings"] = llm_warnings

    graph = KnowledgeGraph(
        scene_id=session.session_id, background_node_id=bg_id,
        nodes=nodes, edges=edges,
    )
    graph = apply_constraints(graph, _build_dimension_result_set(session), stage="A1")
    if llm_result is not None:
        # T11 cst channel: constraint_fields → cst_ nodes (before the
        # runtime assertion so it counts real `cst_`-prefixed nodes).
        llm_warnings.extend(_apply_constraint_fields(graph, llm_result))
        file_rec["assemble_warnings"] = llm_warnings
        _assemble_assertions(
            session, llm_result, graph.nodes, llm_semantic_added, input_edges,
        )
    return graph, set(graph.nodes.keys())


@router.get("/api/a1/seeds")
def get_seeds() -> dict:
    return {
        "seeds": [
            {
                "id": p.id, "name": p.name, "genre": p.genre,
                "description": p.description,
                "dimension_defaults": p.dimension_defaults,
            }
            for p in load_presets()
        ]
    }


@router.post("/api/a1/session/start")
def start_session(req: StartRequest) -> dict:
    _load_once()
    if req.seed_id is None and not req.custom_idea:
        raise HTTPException(status_code=400, detail="seed_id 与 custom_idea 必须二选一")

    issuer = GraphCodeIssuer(_ISSUER_DB)
    ip_no = issuer.new_ip(req.user_id)
    session = A1Session(
        session_id=f"a1_{uuid.uuid4().hex[:12]}",
        user_id=req.user_id,
        ip_code=f"IP{ip_no:04d}",
    )

    # Carry seed context (preset or custom idea) into the session so the
    # LLM interviewer and the frontend both know where the user started.
    if req.seed_id is not None:
        preset = next((p for p in load_presets() if p.id == req.seed_id), None)
        if preset is None:
            raise HTTPException(status_code=404, detail="seed preset not found")
        session.seed_name = preset.name
        session.seed_genre = preset.genre
        session.seed_description = preset.description
        session.answers = {}
    else:
        session.seed_description = req.custom_idea[:500]
        session.answers = {}

    # E1-Lite 冲动类型档案写入（spec §11.1-①）：未知值不报错不 400，
    # 降级为空字段（队列与锚点走默认序）。
    if req.impulse_primary:
        if req.impulse_primary in IMPULSE_TYPE_IDS:
            session.creator_primary = req.impulse_primary
            if req.impulse_secondary:
                if req.impulse_secondary in IMPULSE_TYPE_IDS:
                    if req.impulse_secondary != session.creator_primary:
                        session.creator_secondary = req.impulse_secondary
                    else:
                        logger.warning(
                            "start_session: impulse_secondary %r equals "
                            "primary, ignored",
                            req.impulse_secondary,
                        )
                else:
                    logger.warning(
                        "start_session: unknown impulse_secondary %r ignored",
                        req.impulse_secondary,
                    )
        else:
            # 主冲动未知 → 三字段全空（降级默认序），次冲动不再消费。
            logger.warning(
                "start_session: unknown impulse_primary %r ignored, "
                "creator profile degraded to defaults",
                req.impulse_primary,
            )
    if session.creator_primary or session.creator_secondary:
        session.creator_profile_source = "impulse_cards"

    # M1 配方落定（确定性查表，LLM 不进控制流）：creator_primary 命中配方
    # → 落定 recipe_id/recipe_modules；无/未知 → default（recipe_modules
    # 留空 = 全集，G3 存量会话零迁移语义一致）。
    recipe_id = resolve_recipe_id(session.creator_primary)
    session.recipe_id = recipe_id
    session.recipe_modules = (
        [] if recipe_id == "default" else list(RECIPES[recipe_id].module_ids)
    )

    sync_position(session)

    # M4b 冲动坐标三件套初始化（spec §10.1：选卡定初值，行为接管修正值）。
    from app.domains.creation.a1.impulse_coords import init_impulse_coords
    init_impulse_coords(session)

    file_id = uuid.uuid4().hex
    _SESSIONS[session.session_id] = session
    _FILES[file_id] = {
        "session_id": session.session_id, "status": "draft",
        "ip": ip_no, "graph_code": None, "graph_json": None,
        "confirmed_edges": {}, "rejected_edges": {},
        "open_questions": [], "edge_stats": {
            "semantic_total": 0, "semantic_confirmed": 0,
            "rule_total": 0, "structure_total": 0, "pending_review": 0,
        },
    }
    log_event(
        session.session_id,
        "session_start",
        user_id=req.user_id,
        ip_code=session.ip_code,
        seed_id=req.seed_id,
        seed=session.seed_name or None,
        custom_idea=(req.custom_idea or "")[:100] or None,
        impulse_primary=req.impulse_primary,
        impulse_secondary=req.impulse_secondary,
    )
    _save_store()
    return {
        "session_id": session.session_id,
        "file_id": file_id,
        "ip_code": session.ip_code,
        # M2 additive：配方 id（前端配方感知元数据；default = "default"）
        "recipe_id": session.recipe_id,
        "first_question": _question_payload(session),
        "file": {
            "status": "draft",
            "answers": session.answers,
            "sections": _build_sections(session),
        },
        "seed": {
            "name": session.seed_name,
            "genre": session.seed_genre,
            "description": session.seed_description,
        },
    }


@router.post("/api/a1/chat")
async def chat(req: ChatRequest) -> dict:
    _load_once()
    session = _SESSIONS.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    log_event(
        session.session_id,
        "user_message",
        text=req.message[:300],
        position=f"{session.current_module}.{session.current_subfield}",
    )

    # ---- C7: 待问开放问题（提案在场时挂起——单问句铁律） ----
    rec_for_oq = next(
        (r for r in _FILES.values() if r["session_id"] == req.session_id), None
    )
    oq_log = (
        OpenQuestionLog.load(rec_for_oq.get("open_questions") or [])
        if rec_for_oq is not None
        else OpenQuestionLog()
    )

    # ---- C7: 跳过待问（status=skipped 持久，upsert 不复活） ----
    if req.skip_question_id:
        skipped = oq_log.mark_skipped(req.skip_question_id)
        if skipped and rec_for_oq is not None:
            rec_for_oq["open_questions"] = oq_log.dump()
        out: dict[str, Any] = {
            "reply": "好的，这个问题先跳过，我们继续。",
            "next_question": _question_payload(session),
            "file_diff": [],
            "progress": progress(session),
            "phase": session.phase,
            "proposals": [],
            "divergent_question": None,
        }
        out.update(_open_question_payload(oq_log, session))
        _save_store()
        return out

    interviewer = _get_interviewer()
    pending_oq = None if session.pending_proposals else oq_log.next_pending()
    if pending_oq is not None:
        interviewer.set_pending_open_question(pending_oq.model_dump())

    out = await asyncio.to_thread(
        handle_message, session, req.message, interviewer
    )
    nq = out.get("next_question") or {}
    log_event(
        session.session_id,
        "api_response",
        reply=out.get("reply", "")[:200],
        next_question=nq.get("sub_label"),
        phase=out.get("phase"),
        diffs=len(out.get("file_diff") or []),
    )

    # Ensure proposals field is always present (Task 6: shape stability)
    if "proposals" not in out:
        out["proposals"] = []

    # Add keys to proposals from pending_proposals (Task 6: frontend needs key for confirm)
    if out.get("proposals"):
        proposals_with_keys = []
        for proposal_dict in out["proposals"]:
            # Find the corresponding key in pending_proposals
            for key, entry in session.pending_proposals.items():
                proposal = entry["proposal"]
                # Match by module, subfield, and new value
                if (proposal.module == proposal_dict.get("module") and
                    proposal.subfield == proposal_dict.get("subfield") and
                    proposal.new == proposal_dict.get("new")):
                    # Add key to proposal dict
                    proposal_with_key = {**proposal_dict, "key": key}
                    proposals_with_keys.append(proposal_with_key)
                    break
            else:
                # No matching key found, keep as-is (shouldn't happen)
                proposals_with_keys.append(proposal_dict)
        out["proposals"] = proposals_with_keys

    # Ensure divergent_question is present (Task 6: field always present, None when not provided)
    if "divergent_question" not in out:
        out["divergent_question"] = None

    # ---- C7: 回收本轮待问回答 → mark_answered 持久化 + 待问角标 ----
    answered = interviewer.take_open_question_answered()
    if answered and rec_for_oq is not None:
        if oq_log.mark_answered(answered["id"], answered["answer"]):
            rec_for_oq["open_questions"] = oq_log.dump()
            log_event(
                session.session_id,
                "open_question_answered",
                question_id=answered["id"],
                answer=answered["answer"][:200],
            )
    out.update(_open_question_payload(oq_log, session))

    # Add dice recommendation when on 骰子设定 module and first subfield
    if session.current_module == "骰子设定":
        # Get first subfield of 骰子设定 module
        first_sf = first_subfield("骰子设定")
        if first_sf and session.current_subfield == first_sf["id"]:
            # Derive recommendation from current answers
            dice_rec = derive_dice_recommendation(session.answers)
            if dice_rec["recommendations"]:
                out["dice_recommendation"] = dice_rec

    # Any new write invalidates a previous finalization (file back to draft).
    for rec in _FILES.values():
        if rec["session_id"] == session.session_id and rec["status"] == "finalized" and out["file_diff"]:
            rec["status"] = "draft"

    # A 触发点：视觉设计模块填满时启动后台预生成
    await _trigger_visual_bg_if_filled(session.session_id)

    _save_store()
    return out


@router.post("/api/a1/chat/confirm")
def chat_confirm(req: ConfirmRequest) -> dict:
    _load_once()
    session = _SESSIONS.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")

    # Kind routing (Task 6): classification vs fill proposal confirmation
    if req.kind == "fill":
        # Natural language choice mapping (closed vocabulary)
        choice_lower = req.choice.strip().lower()
        choice_mapping = {
            "替换": "replace",
            "换成": "replace",
            "合并": "merge",
            "并存": "merge",
            "都保留": "merge",
            "两个都要": "merge",
            "放弃": "drop",
            "算了": "drop",
            "不要了": "drop",
        }

        # Check if choice needs clarification (ambiguous short responses)
        is_ambiguous = (
            len(req.choice.strip()) < 5 and
            not any(keyword in req.choice for keyword in
                    ["替换", "换成", "合并", "并存", "都保留", "两个都要", "放弃", "算了", "不要了"])
        )

        if is_ambiguous:
            # Return needs_clarification response without side effects
            proposal_key = req.proposal.get("key", "")
            proposal_entry = session.pending_proposals.get(proposal_key)
            if proposal_entry:
                proposal = proposal_entry["proposal"]
                return {
                    "needs_clarification": True,
                    "reply": (
                        f"你之前定过【{proposal.subfield}】是『{proposal.old}』。"
                        f"这次的『{proposal.new}』——是要**替换**它，"
                        f"还是两者**合并**（同一条里都保留），"
                        f"还是先**放弃**这条修改？"
                    ),
                    "next_question": None,
                }

        # Map natural language to canonical choice
        canonical_choice = choice_mapping.get(req.choice.strip(), req.choice)

        # Extract proposal key from request
        proposal_key = req.proposal.get("key", "")

        # Call resolve_proposal from guide_engine
        from app.domains.creation.a1.guide_engine import resolve_proposal
        # M4a：先取 entry（resolve 会 pop）——推断包提案 confirm → 判定双写
        pack_entry = session.pending_proposals.get(proposal_key)
        result = resolve_proposal(session, proposal_key, canonical_choice)
        if pack_entry is not None and pack_entry.get("source") == "inference_pack":
            apply_pack_feedback(session, applied=bool(result.get("applied")))
            # M4b 冲动坐标双写：推断包判定 = 显式信号（spec §10.1 L317）。
            from app.domains.creation.a1.impulse_coords import (
                SIGNAL_PACK_APPLIED,
                SIGNAL_PACK_REJECTED,
                apply_signal,
            )
            apply_signal(
                session,
                SIGNAL_PACK_APPLIED if result.get("applied")
                else SIGNAL_PACK_REJECTED,
            )

        # Build response
        reply = "已确认并记录。"
        if result.get("applied"):
            choice_desc = {"replace": "替换", "merge": "合并", "drop": "放弃"}.get(canonical_choice, "")
            reply = f"已{choice_desc}该内容。"
        else:
            reply = "已放弃该内容，可重新输入。"

        _save_store()
        return {
            "reply": reply,
            "next_question": _question_payload(session),
            "applied": result.get("applied", False),
        }
    # Default: classification proposal (existing innovation_capture path)
    from app.domains.creation.shared.semantic_compiler import ClassificationProposal
    proposal = ClassificationProposal(**req.proposal)
    log_event(
        session.session_id,
        "innovation_confirm",
        choice=req.choice,
        suggestions=[f"{s.get('field', '')[:60]}->{s.get('category', '')}" for s in (req.proposal.get("suggestions") or [])],
    )
    out = confirm_proposal(session, Confirmation(proposal=proposal, choice=req.choice))
    # Shape the response like /api/a1/chat so the frontend can render
    # the reply and the next question uniformly.
    if "reply" not in out:
        out["reply"] = "已确认并记录。" if out.get("persisted") else "已放弃该内容，可重新输入。"
    out["next_question"] = _question_payload(session)
    _save_store()
    return out


# ---------------------------------------------------------------------------
# M4a 推断包（DN5：A1 域新 LLM 生产方，单生产单消费留痕）
# ---------------------------------------------------------------------------

def _get_inference_packer() -> "InferencePacker":
    """Lazy packer factory（同 _get_interviewer 的降级姿态：构造失败 →
    provider=None → 免费线空包）。测试经 monkeypatch 覆盖本工厂。"""
    try:
        provider = create_provider(load_provider_config())
    except Exception:  # noqa: BLE001 — no API key / bad config must not crash
        provider = None
    return InferencePacker(provider)


@router.post("/api/a1/file/{file_id}/inference-pack")
def generate_inference_pack(file_id: str) -> dict:
    """推断包：单次 LLM 生成 3-5 条补全建议 → 装入 pending_proposals。

    **绝不直写 answers**（铁律）：落写只发生在既有 confirm 交互
    （/api/a1/chat/confirm kind="fill" → resolve_proposal，即 fills 通道，
    J1 已在生成侧拦截占位）。零 LLM → 空包 200 + note（免费线）。
    """
    _load_once()
    rec = _FILES.get(file_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="file not found")
    session = _SESSIONS.get(rec["session_id"])
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")

    packer = _get_inference_packer()
    pack = packer.build(session)
    installed = set(packer.install(session, pack))

    from app.domains.creation.a1.guide_engine import _proposal_key
    from app.domains.creation.seed.a1_question_tree import get_subfield

    suggestions: list[dict] = []
    for sug in pack.suggestions:
        pk = _proposal_key(sug.module, sug.subfield, sug.value)
        if pk not in installed:
            continue  # 装包间隙被并发写入跳过 → 不进响应
        sf = get_subfield(sug.module, sug.subfield)
        suggestions.append({
            "key": pk,
            "module": sug.module,
            "subfield": sug.subfield,
            "field_label": sf["label"] if sf else sug.subfield,
            "value": sug.value,
            "reason": sug.reason,
        })
    _save_store()
    return {
        "file_id": file_id,
        "session_id": session.session_id,
        "suggestions": suggestions,
        "note": pack.note,
    }


def _get_file(file_id: str) -> dict:
    _load_once()
    rec = _FILES.get(file_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="file not found")
    return rec


# ---------------------------------------------------------------------------
# M4b 冲动坐标观测（E2 只看不判）+ live_projection（零 LLM 投影）
# ---------------------------------------------------------------------------


def _session_for_file_or_404(file_id: str) -> A1Session:
    rec = _get_file(file_id)
    session = _SESSIONS.get(rec["session_id"])
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return session


@router.get("/api/a1/file/{file_id}/impulse-coords")
def get_impulse_coords(file_id: str) -> dict:
    """冲动坐标看板数据（E2 只看不判，spec §10.1 L322）。

    三件套（叙事-建构轴/置信度/安全旗）+ 审计轨迹只读投影；存量会话
    （无坐标）→ 按锚点惰性初始化后返回（确定性查表，无 LLM）。
    """
    _load_once()
    session = _session_for_file_or_404(file_id)
    from app.domains.creation.a1.impulse_coords import dashboard_data
    data = dashboard_data(session)
    _save_store()
    return {"file_id": file_id, "session_id": session.session_id, **data}


@router.get("/api/a1/file/{file_id}/live-projection")
def get_live_projection(file_id: str) -> dict:
    """半成品背景树 L0-L2 投影（零 LLM，确定性快照——plan §271）。

    复用 _build_graph 抽出的纯装配函数；返回可 JSON 化投影（非定稿
    KnowledgeGraph——note 披露），存量会话零迁移、门禁/路由零扰动。
    """
    _load_once()
    session = _session_for_file_or_404(file_id)
    from app.domains.creation.a1.live_projection import project_live
    return project_live(session)


@router.get("/api/a1/file/{file_id}/persona-card")
def get_persona_card(file_id: str) -> dict:
    """人格卡只读投影（M4c，零 LLM 确定性渲染）。

    命名（未决③占位）+ 视觉 + 一句话解读；数据源 = creator_profile +
    impulse_coords（只看不判，绝不回流路由）。存量会话惰性初始化坐标
    （确定性查表，与 impulse-coords 端点同款惯例）。
    """
    _load_once()
    session = _session_for_file_or_404(file_id)
    from app.domains.creation.a1.persona_card import render_persona_card
    card = render_persona_card(session)
    _save_store()
    return {"file_id": file_id, "session_id": session.session_id, **card}


def _recipe_module_ids(session: A1Session) -> list[str]:
    """Ordered in-recipe module ids (M1 recipe gate semantics).

    会话已落定配方（recipe_modules 非空）→ 配方序（故事型=子集）；
    存量/默认会话（空）→ 全集（G3，行为逐字节不变）。
    """
    return session.recipe_modules or module_ids()


def _recipe_legal_anchors(session: A1Session) -> set[str]:
    """Recipe union of legal "module.subfield" anchors for graphify validation."""
    return set(all_subfield_keys(recipe=_recipe_module_ids(session)))


def _build_sections(session: A1Session) -> list[dict]:
    """Hierarchical sections structure shared by start & get_file responses.

    M1 配方感知：遍历会话配方内的模块（default = 全集，结构与顺序不变）。
    """
    sections = []
    for module_id in _recipe_module_ids(session):
        module = get_module(module_id)
        if module is None:
            continue
        module_label = module["label"]

        # Collect all fields for this module
        fields = []
        for sf in module["fields"]:
            answer_key = f"{module_id}.{sf['id']}"
            value = session.answers.get(answer_key, "")
            fields.append({
                "id": sf["id"],
                "label": sf["label"],
                "content": value,
                "done": answer_key in session.answers,
            })

        # Module is done if all its fields are done
        module_done = all(f["done"] for f in fields)

        # Include module content (concatenation of non-empty field values)
        module_content = "; ".join([
            f"{f['label']}: {f['content']}" for f in fields if f["content"]
        ])

        sections.append({
            "id": module_id,
            "label": module_label,
            "done": module_done,
            "content": module_content,
            "subs": fields,
            "fields": fields,
        })
    return sections


@router.get("/api/a1/file/{file_id}")
def get_file(file_id: str) -> dict:
    rec = _get_file(file_id)
    session = _SESSIONS[rec["session_id"]]

    # Task 6: Add open_questions and edge_stats (always present, draft state = empty/zero)
    open_questions = rec.get("open_questions", [])
    edge_stats = rec.get("edge_stats", {
        "semantic_total": 0,
        "semantic_confirmed": 0,
        "rule_total": 0,
        "structure_total": 0,
        "pending_review": 0,
    })

    return {
        "file_id": file_id,
        "status": rec["status"],
        "answers": session.answers,
        "graph_code": rec["graph_code"],
        "session_id": session.session_id,
        "sections": _build_sections(session),
        "open_questions": open_questions,
        "edge_stats": edge_stats,
        "confirmed_edges": rec.get("confirmed_edges", {}),
        "rejected_edges": rec.get("rejected_edges", {}),
        # Task T-B: 常驻字段（draft 态为空）
        "concept_terms": rec.get("concept_terms", []),
        "proposed_relations": rec.get("proposed_relations", []),
        # v0.5: finalize warnings 常驻（draft/旧记录为空列表）
        "finalize_warnings": rec.get("finalize_warnings", []),
        # J3: 结构化警告 ledger 常驻（draft 态为空列表；四通道合并视图）
        "warnings": rec.get("warnings", []),
        # v0.5 T15: 失效区常驻（draft/旧记录为空列表；条目见 finalize 死区追加）
        "dead_edges": rec.get("dead_edges", []),
        # M4a additive：field_sources 平行溯源元数据（只看不判；缺省空 dict）
        "field_sources": dict(session.field_sources),
    }


# ---------------------------------------------------------------------------
# Task 7: Concept edge integration helpers
# ---------------------------------------------------------------------------


# Map confidence string to EdgeType
_CONFIDENCE_TO_EDGETYPE: dict[str, EdgeType] = {
    "semantic": EdgeType.SEMANTIC,
    "rule": EdgeType.RULE,
    "structure": EdgeType.STRUCTURE,
}


def _make_edge_key(from_id: str, to_id: str, relation: str) -> str:
    """Build stable edge key from (from, to, relation) triple (Metis A5/E6)."""
    return f"{from_id}/{to_id}/{relation}"


def _compute_edge_stats(edges: list[GraphEdge]) -> dict[str, int]:
    """Compute edge_stats dict (Metis S6 locked shape)."""
    stats = {
        "semantic_total": 0, "semantic_confirmed": 0,
        "rule_total": 0, "structure_total": 0, "pending_review": 0,
    }
    for e in edges:
        if e.confidence == "semantic":
            stats["semantic_total"] += 1
            if e.confirmed:
                stats["semantic_confirmed"] += 1
            else:
                stats["pending_review"] += 1
        elif e.confidence == "rule":
            stats["rule_total"] += 1
        elif e.confidence == "structure":
            stats["structure_total"] += 1
    return stats


def _add_concept_edges_to_graph(
    graph: KnowledgeGraph,
    extracted_edges: list[Any],
    valid_node_ids: set[str],
    confirmed_edges: dict[str, dict],
    rejected_edges: dict[str, dict],
) -> list[GraphEdge]:
    """[Task T-B 停用] 旧槽位级概念边合并——finalize 已改两阶段编排，不再调用.

    保留函数体仅作文件级兼容（历史 graph_json 迁移参考），新代码勿用。
    """
    added: list[GraphEdge] = []
    prior_confirmed = dict(confirmed_edges)  # snapshot BEFORE loop (fix intra-pass pollution)
    for ee in extracted_edges:
        from_id = ee.from_slot  # slot path = module.subfield = node ID in graph
        to_id = ee.to_slot

        # Node reference validation: skip edges referencing nonexistent nodes
        if from_id not in valid_node_ids or to_id not in valid_node_ids:
            continue

        # Skip rejected edges
        edge_key = _make_edge_key(from_id, to_id, ee.relation)
        if edge_key in rejected_edges:
            continue

        # Restore confirmed state from PRE-LOOP snapshot only
        confirmed = ee.confirmed
        if edge_key in prior_confirmed:
            confirmed = prior_confirmed[edge_key].get("confirmed", confirmed)

        # Map confidence to EdgeType
        edge_type = _CONFIDENCE_TO_EDGETYPE.get(ee.confidence, EdgeType.SEMANTIC)

        ge = GraphEdge(
            from_node_id=from_id,
            to_node_id=to_id,
            edge_type=edge_type,
            visual_description=ee.relation,
            relation=ee.relation,
            confidence=ee.confidence,
            confirmed=confirmed,
        )
        graph.edges.append(ge)
        added.append(ge)

        # Record in confirmed_edges for persistence (snapshot of edge state)
        confirmed_edges[edge_key] = {
            "from_node_id": from_id,
            "to_node_id": to_id,
            "relation": ee.relation,
            "confidence": ee.confidence,
            "confirmed": confirmed,
        }

    return added


@router.post("/api/a1/file/{file_id}/finalize")
def finalize(file_id: str) -> dict:
    rec = _get_file(file_id)
    session = _SESSIONS[rec["session_id"]]

    # Finalize gate (M1 DN1 subset semantics): every module *in the
    # session's recipe* must have STRICTLY more than 50% of its subfields
    # answered; out-of-recipe modules = 不适用 (never listed).
    missing = [
        mid for mid in _recipe_module_ids(session)
        if not is_module_over_half(mid, session.answers)
    ]
    if missing:
        # missing_sections is the contract key (v5 T9); missing_modules kept
        # as a legacy alias for older consumers.
        raise HTTPException(status_code=409, detail={
            "missing_sections": missing, "missing_modules": missing,
        })

    issuer = GraphCodeIssuer(_ISSUER_DB)
    new_code = issuer.next(session.user_id, ip=rec["ip"], stage="W")
    instance_no = int(new_code.split("-")[1][1:])
    version = int(new_code.rsplit("-v", 1)[1])

    # Mark downstream stale on re-finalize (old version kept, never deleted).
    registry_db = _registry_db()
    stale_marker.ensure_registry(registry_db)
    if rec["graph_code"] and rec["graph_code"] != new_code:
        stale_marker.mark_downstream_stale(
            registry_db, rec["graph_code"],
            {"diff_summary": f"{rec['graph_code']} -> {new_code}"},
        )

    # Provider 获取（与 extract-edges 端点一致的注入范式）；失败降级 None，
    # graphify_llm 内部对 None provider / 任何异常降级，永不抛出。
    try:
        provider = create_provider(load_provider_config())
    except Exception:  # noqa: BLE001
        provider = None

    # C7: 上一轮已回答的开放问题 → 转正证据注入 graphify prompt。
    # 证据在 graphify 前从旧记录导出；upsert 在 graphify 后合并新问句。
    oq_log = OpenQuestionLog.load(rec.get("open_questions") or [])
    answered_evidence = [
        f"用户已确认：{q.question}→{q.answer}"
        for q in oq_log.items
        if q.status == "answered" and q.question and q.answer
    ]

    llm_result = graphify_llm(
        session, provider, answered_evidence=answered_evidence or None,
        legal_anchors=_recipe_legal_anchors(session),
    )
    graph, valid_node_ids = _build_graph(
        session, rec, llm_result,
        legal_anchors=_recipe_legal_anchors(session),
    )
    warnings: list[str] = []

    # v0.5 (§8.1 两阶段): graphify 降级 warning 并入 finalize_warnings
    if not llm_result.success:
        warnings.append(llm_result.warning or "graphify failed")

    # v0.5 两阶段退役: finalize 不再调用 extract_concept_terms；
    # 概念词恢复/入图由 SIR entries + dead_edges 取代。
    # 旧 confirmed_edges 快照中端点已不在新图的边落入死区（不重入图）。
    confirmed_prev = rec.get("confirmed_edges", {})
    rejected_prev = rec.get("rejected_edges", {})
    for key, snap in confirmed_prev.items():
        if key in rejected_prev:
            continue
        fid = snap.get("from_node_id", "")
        tid = snap.get("to_node_id", "")
        if fid not in graph.nodes or tid not in graph.nodes:
            # Dead zone (T7): persist instead of silent drop; the
            # list itself was (re)initialized by _build_graph.
            rec.setdefault("dead_edges", []).append({
                "key": key, "from": fid, "to": tid,
                "relation": snap.get("relation", ""),
                "reason": "endpoint_missing",
            })

    rec["concept_terms"] = rec.get("concept_terms", [])

    # C6/C7: open_questions upsert 持久化——结构化 list[dict]（铁律：禁裸
    # list[str]）；已有 answered/skipped 条目不复活（upsert 保留语义）。
    existing_ids = {q.id for q in oq_log.items}
    existing_questions = {q.question for q in oq_log.items}
    seq = len(oq_log.items)
    for oq in llm_result.open_questions:
        qtext = oq.question.strip()
        if not qtext or qtext in existing_questions:
            continue
        seq += 1
        while f"oq-{seq:03d}" in existing_ids:
            seq += 1
        qid = f"oq-{seq:03d}"
        existing_ids.add(qid)
        existing_questions.add(qtext)
        oq_log.upsert(OpenQuestion(id=qid, question=qtext))
    rec["open_questions"] = oq_log.dump()

    # Compute edge_stats from all edges in the graph
    rec["edge_stats"] = _compute_edge_stats(graph.edges)

    # J3 披露协议：四处警告合并为结构化 ledger 落 file_rec["warnings"]。
    # - upload/answers 条目跨 finalize 存活（写入时落账，重建只动 finalize 时通道）
    # - graphify 通道仅在 success=True 时并入（degrade 警告已走 finalize
    #   通道，避免同文案双计）
    # - J4：session.answer_clips（fills 写入层预算截断）→ answers 通道
    ledger: list[dict] = [
        e for e in rec.get("warnings", [])
        if e.get("source") in (SOURCE_UPLOAD, SOURCE_ANSWERS)
    ]
    ledger += from_strings(SOURCE_ANSWERS, session.answer_clips)
    ledger += from_strings(SOURCE_ASSEMBLE, rec.get("assemble_warnings", []))
    ledger += from_strings(SOURCE_FINALIZE, warnings)
    if llm_result.success:
        ledger += from_strings(SOURCE_GRAPHIFY, llm_result.warnings)
    ledger += from_dead_edges(rec.get("dead_edges", []))
    rec["warnings"] = ledger

    graph_id = stale_marker.register_graph(
        registry_db, session.user_id, new_code, "W",
        instance_no, version, scene_id=session.session_id,
        display_name=session.ip_code,
    )

    rec.update({"status": "finalized", "graph_code": new_code,
                "graph_json": graph.model_dump(mode="json"), "graph_id": graph_id,
                "finalize_warnings": warnings})
    log_event(
        session.session_id,
        "finalize",
        graph_code=new_code,
        graph_id=graph_id,
        answered_fields=len(session.answers),
        re_finalize=bool(rec.get("graph_code") and rec["graph_code"] != new_code),
    )

    # B 触发点：finalize 时检查预生成状态，未完成则触发
    # Since endpoint is now sync (def), we need to run create_task in a new event loop
    if (rec.get("visual_bg_status") not in ("completed", "generating")
            and file_id not in _visual_bg_tasks):
        # Run in background thread to avoid blocking
        import threading
        def _run_background_task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                task = loop.create_task(_pregenerate_visual_bg(file_id))
                loop.run_until_complete(task)
            finally:
                loop.close()
        
        thread = threading.Thread(target=_run_background_task, daemon=True)
        thread.start()
        _visual_bg_tasks[file_id] = thread

    _save_store()
    # 旧 "warnings"（finalize 通道 list[str]）保留向后兼容；"ledger" 为 J3
    # 结构化全量视图（get_file 的 "warnings" 同源）。
    return {"graph_id": graph_id, "graph_code": new_code, "warnings": warnings,
            "ledger": ledger,
            "status": "finalized", "concept_terms_count": len(rec.get("concept_terms", []))}


@router.get("/api/a1/file/{file_id}/graph")
def get_graph(file_id: str) -> dict:
    rec = _get_file(file_id)
    if rec["status"] != "finalized":
        raise HTTPException(status_code=409, detail="pending_finalize")
    return rec["graph_json"]


@router.get("/api/a1/file/{file_id}/poster")
def get_poster(file_id: str) -> dict:
    rec = _get_file(file_id)
    if rec["status"] != "finalized":
        raise HTTPException(status_code=409, detail="pending_finalize")
    session = _SESSIONS[rec["session_id"]]
    poster = build_poster(session)

    # Merge cached generation state from the file record, overriding the
    # hardcoded "pending" from build_poster.
    cached_status = rec.get("poster_image_status")
    if cached_status is not None:
        poster["ai_image_status"] = cached_status
    if rec.get("poster_image_status") == "completed" and rec.get("poster_image_url"):
        poster["ai_image_url"] = rec["poster_image_url"]
    else:
        poster["ai_image_url"] = None

    # 返回视觉设计背景图预生成状态（A+B 双触发）
    poster["visual_bg_status"] = rec.get("visual_bg_status")
    poster["visual_bg_images"] = rec.get("visual_bg_images", [])
    poster["visual_bg_best"] = rec.get("visual_bg_best")
    poster["visual_bg_prompt"] = rec.get("visual_bg_prompt")

    return poster


@router.post("/api/a1/file/{file_id}/poster/generate")
async def generate_poster(file_id: str) -> dict:
    """Generate an AI poster image for a finalized A1 file."""
    rec = _get_file(file_id)
    if rec["status"] != "finalized":
        raise HTTPException(status_code=409, detail="pending_finalize")

    # Guard against duplicate concurrent generation
    if file_id in _poster_generation_tasks:
        raise HTTPException(status_code=409, detail="already_generating")

    session = _SESSIONS[rec["session_id"]]
    poster_data = build_poster(session)
    prompt = poster_data["ai_image_prompt"]

    try:
        from app.ai.image_generator import ImageGenerationError, ImageGenerator
    except ImportError:
        raise HTTPException(
            status_code=502, detail="image generator unavailable",
        )

    gen: Any = None
    try:
        _poster_generation_tasks[file_id] = True
        rec["poster_image_status"] = "generating"
        rec["poster_image_prompt"] = prompt

        gen = ImageGenerator()
        results = await gen.generate(
            prompt=prompt,
            asset_id=f"poster_{file_id}",
            num_candidates=1,
        )

        if not results:
            rec["poster_image_status"] = "failed"
            raise HTTPException(
                status_code=502, detail="no images generated",
            )

        first = results[0]
        if first.file_path:
            name = Path(first.file_path).name
            url = f"/assets/{name}"
        elif first.url:
            url = first.url
        else:
            rec["poster_image_status"] = "failed"
            raise HTTPException(
                status_code=502, detail="image generated but no file path or url",
            )

        rec["poster_image_url"] = url
        rec["poster_image_status"] = "completed"
        return {"ai_image_status": "completed", "ai_image_url": url}
    except HTTPException:
        raise
    except ImageGenerationError as exc:
        rec["poster_image_status"] = "failed"
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        rec["poster_image_status"] = "failed"
        raise HTTPException(
            status_code=502, detail=f"unexpected error: {exc}",
        )
    finally:
        _save_store()
        _poster_generation_tasks.pop(file_id, None)
        if gen is not None:
            await gen.close()


# ---------------------------------------------------------------------------
# Visual background pre-generation (A+B dual trigger, design:
# docs/plans/2026-08-27-visual-design-bg-pipeline-design.md)
# ---------------------------------------------------------------------------

# Module id for visual design (must match a1_question_tree.py MODULES).
_VISUAL_DESIGN_MODULE = "视觉设计"

# In-memory lock for background pre-generation (mirrors _poster_generation_tasks).
_visual_bg_tasks: dict[str, asyncio.Task] = {}


def _extract_visual_design(session: A1Session) -> dict[str, str]:
    """Extract visual design subfields from session.answers.

    Returns {"keywords": "...", "architecture": "...", "material": "..."}.
    Missing fields are omitted (caller can check completeness).
    """
    visual: dict[str, str] = {}
    for sf in subs_for_module(_VISUAL_DESIGN_MODULE):
        key = f"{_VISUAL_DESIGN_MODULE}.{sf['id']}"
        val = session.answers.get(key, "")
        if val:
            visual[sf["id"]] = val
    return visual


async def _pregenerate_visual_bg(file_id: str) -> None:
    """Background task: generate 3 visual bg candidates + GLM scoring.

    Triggered when visual design module is filled (A) or at finalize (B).
    Stores results in _FILES[file_id]["visual_bg_*"].
    """
    rec = _FILES.get(file_id)
    if rec is None:
        return
    session = _SESSIONS.get(rec["session_id"])
    if session is None:
        return

    visual_design = _extract_visual_design(session)
    if not visual_design:
        print(f"[visual_bg] {file_id}: visual design empty, skipping")
        return

    output_dir = ASSETS_DIR / "visual_bg" / file_id
    rec["visual_bg_status"] = "generating"
    rec["visual_bg_prompt"] = None
    rec["visual_bg_images"] = []
    rec["visual_bg_best"] = None

    try:
        report = await run_visual_bg_pipeline(visual_design, output_dir)
        # 修正 URL：/assets/visual_bg/{file_id}/{filename}（ASSETS_DIR mount 到 /assets）
        for img in report.get("images", []):
            img["url"] = f"/assets/visual_bg/{file_id}/{img['filename']}"
        rec["visual_bg_status"] = "completed"
        rec["visual_bg_prompt"] = report.get("prompt", "")
        rec["visual_bg_images"] = report.get("images", [])
        rec["visual_bg_best"] = report.get("best_candidate")
        print(f"[visual_bg] {file_id}: done, best={rec['visual_bg_best']}")
    except Exception as exc:
        rec["visual_bg_status"] = "failed"
        rec["visual_bg_error"] = str(exc)
        print(f"[visual_bg] {file_id}: failed: {exc}")
    finally:
        _save_store()
        _visual_bg_tasks.pop(file_id, None)


async def _trigger_visual_bg_if_filled(session_id: str) -> None:
    """A 触发点：视觉设计模块填满时启动后台预生成.

    在 chat/upload 端点调用。如果视觉设计已填满且无运行中的预生成，启动后台任务.
    """
    print(f"[visual_bg] _trigger called, session_id={session_id}", flush=True)
    session = _SESSIONS.get(session_id)
    if session is None:
        print("[visual_bg] session not found in _SESSIONS", flush=True)
        return
    visual_fields = subs_for_module(_VISUAL_DESIGN_MODULE)
    if not visual_fields:
        print(f"[visual_bg] no visual_fields for {_VISUAL_DESIGN_MODULE}", flush=True)
        return
    if not all(
        f"{_VISUAL_DESIGN_MODULE}.{sf['id']}" in session.answers
        for sf in visual_fields
    ):
        filled = [f"{_VISUAL_DESIGN_MODULE}.{sf['id']}" for sf in visual_fields if f"{_VISUAL_DESIGN_MODULE}.{sf['id']}" in session.answers]
        print(f"[visual_bg] not all filled: {filled}/{len(visual_fields)}", flush=True)
        return
    print("[visual_bg] all visual fields filled, searching _FILES...", flush=True)
    for fid, frec in _FILES.items():
        if (frec["session_id"] == session_id
                and fid not in _visual_bg_tasks
                and frec.get("visual_bg_status") not in ("completed", "generating")):
            print(f"[visual_bg] A 触发：file_id={fid}, session={session_id}", flush=True)
            task = asyncio.create_task(_pregenerate_visual_bg(fid))
            _visual_bg_tasks[fid] = task
            break
    else:
        status = next((frec.get("visual_bg_status") for fid, frec in _FILES.items() if frec["session_id"] == session_id), None)
        print(f"[visual_bg] skipped (status={status} or in tasks)", flush=True)


@router.post("/api/a1/file/{file_id}/visual-bg/pregenerate")
async def pregenerate_visual_bg(file_id: str) -> dict:
    """Manually trigger visual bg pre-generation (for testing/fallback)."""
    _get_file(file_id)  # validates file exists (404 if not)
    if file_id in _visual_bg_tasks:
        raise HTTPException(status_code=409, detail="already_generating")
    task = asyncio.create_task(_pregenerate_visual_bg(file_id))
    _visual_bg_tasks[file_id] = task
    return {"status": "started", "file_id": file_id}


# ---------------------------------------------------------------------------
# Worldview document upload (design: docs/plans/2026-08-25-a1-worldview-upload-design.md)
# ---------------------------------------------------------------------------

_UPLOADS: dict[str, dict[str, Any]] = {}

_UPLOAD_PROVIDER: Any | None = None


def _get_upload_provider() -> Any:
    """Lazy provider singleton for the upload pipeline (mirrors
    _get_interviewer: import-time creation would miss .env config)."""
    global _UPLOAD_PROVIDER
    if _UPLOAD_PROVIDER is None:
        provider = create_provider(load_provider_config())
        _UPLOAD_PROVIDER = provider
    return _UPLOAD_PROVIDER


class UploadRequest(BaseModel):
    user_id: str
    filename: str
    content: str
    # M2 additive（DN6 默认）：故事型冲动不暴露上传预填路径——走访谈。
    # 不传/None = 既有行为逐字节不变（default 路径零变化）。
    impulse_primary: str | None = None


class UploadConvertRequest(BaseModel):
    user_id: str
    upload_id: str
    decision: str  # "convert" | "cancel" only — do not extend


def _prefill_session(user_id: str, parsed: dict[str, Any]) -> dict[str, Any]:
    """Create an A1Session prefilled with parsed module answers, following
    the /session/start construction (issuer + _SESSIONS + _FILES + log)."""
    issuer = GraphCodeIssuer(_ISSUER_DB)
    ip_no = issuer.new_ip(user_id)
    session = A1Session(
        session_id=f"a1_{uuid.uuid4().hex[:12]}",
        user_id=user_id,
        ip_code=f"IP{ip_no:04d}",
    )
    session.answers = dict(parsed["answers"])
    # M4a 出口三（上传预填 → upload_prefill）：parse_modules 结果定格的唯一
    # 标记点（parse_modules 本身是纯函数不触碰 session——接线在会话构建处）。
    session.field_sources = {k: "upload_prefill" for k in session.answers}
    # J4 预算护栏披露：parse 出口截断的答案记入 session（finalize 并入 ledger）
    session.answer_clips.extend(
        f"答案超2000字已截断: {k}（上传解析）"
        for k in parsed.get("clipped_answers", [])
    )
    # Mark these as LLM guesses (unconfirmed by the user) so the write
    # guard lets user-spoken fills overwrite them directly instead of
    # converting every topup into a proposal (upload-deadlock fix).
    session.prefill_fields = list(session.answers.keys())
    sync_position(session)
    file_id = uuid.uuid4().hex
    _SESSIONS[session.session_id] = session
    _FILES[file_id] = {
        "session_id": session.session_id, "status": "draft",
        "ip": ip_no, "graph_code": None, "graph_json": None,
        "confirmed_edges": {}, "rejected_edges": {},
        "open_questions": [], "edge_stats": {
            "semantic_total": 0, "semantic_confirmed": 0,
            "rule_total": 0, "structure_total": 0, "pending_review": 0,
        },
    }
    log_event(
        session.session_id,
        "upload_prefill",
        user_id=user_id,
        ip_code=session.ip_code,
        prefilled_fields=len(session.answers),
        innovations=len(parsed.get("innovations") or []),
    )
    _save_store()
    return {
        # 供域内测试/内部链路直接取用会话对象；两个上传端点 return 前会
        # pop 掉，绝不外泄到 API 响应。
        "_session": session,
        "session_id": session.session_id,
        "file_id": file_id,
        "ip_code": session.ip_code,
        "first_question": _question_payload(session),
        "file": {
            "status": "draft",
            "answers": session.answers,
            "sections": _build_sections(session),
        },
        "innovations": parsed.get("innovations") or [],
        "truncated": parsed.get("truncated", False),
    }


@router.post("/api/a1/upload")
async def upload_worldview(req: UploadRequest) -> dict:
    from app.domains.creation.a1.worldview_upload import (
        check_copyright,
        extract_entities,
        parse_modules,
        validate_text,
    )

    # M2 DN6 默认：故事型冲动不暴露上传预填路径（世界建构 35 字段 schema
    # 与故事配方正交）——故事用户走访谈引导。确定性查表，LLM 不进控制流。
    if req.impulse_primary and resolve_recipe_id(req.impulse_primary) in (
        STORY_PRIMARY_TYPES
    ):
        raise HTTPException(
            status_code=409,
            detail="故事型创作请直接开始对话引导（不需要上传世界观文档）",
        )

    gate = validate_text(req.filename, req.content)
    if not gate["ok"]:
        raise HTTPException(status_code=422, detail=gate["reason"])

    try:
        provider = _get_upload_provider()
    except Exception:  # noqa: BLE001 — same degrade stance as _get_interviewer
        raise HTTPException(status_code=503, detail="上传解析需要 LLM 服务")

    try:
        entities = await extract_entities(provider, req.content)
        report = await check_copyright(provider, entities)
    except Exception as exc:  # noqa: BLE001 — log & surface upload failures
        log_event(
            "upload",
            "upload_failed",
            user_id=req.user_id,
            filename=req.filename[:100],
            stage="copyright_screening",
            error=f"{type(exc).__name__}: {exc}"[:300],
        )
        raise HTTPException(status_code=502, detail=f"上传解析失败：{exc}") from exc
    log_event(
        "upload",
        "copyright_check",
        user_id=req.user_id,
        filename=req.filename[:100],
        risk_level=report["risk_level"],
        matches=len(report["matches"]),
    )
    if report["risk_level"] == "high":
        upload_id = uuid.uuid4().hex
        _UPLOADS[upload_id] = {
            "user_id": req.user_id,
            "filename": req.filename,
            "content": req.content,
            "matches": report["matches"],
        }
        return {"status": "copyright_hit", "upload_id": upload_id, "report": report}

    try:
        parsed = await parse_modules(provider, req.content)
    except Exception as exc:  # noqa: BLE001
        log_event(
            "upload",
            "upload_failed",
            user_id=req.user_id,
            filename=req.filename[:100],
            stage="module_parsing",
            error=f"{type(exc).__name__}: {exc}"[:300],
        )
        raise HTTPException(status_code=502, detail=f"上传解析失败：{exc}") from exc
    if not parsed["answers"]:
        log_event(
            "upload",
            "upload_failed",
            user_id=req.user_id,
            filename=req.filename[:100],
            stage="module_parsing",
            error="LLM returned no parseable module answers (empty JSON content)",
        )
        raise HTTPException(
            status_code=422, detail="未能从文档中解析出任何模块内容，请检查文档质量"
        )
    upload_id = uuid.uuid4().hex
    body = _prefill_session(req.user_id, parsed)
    body.pop("_session", None)  # 内部对象不外泄（M4a）
    body.update({"status": "parsed", "upload_id": upload_id})
    # J3/J4 披露：截断与 cap 有痕落库（此前只在响应里闪现，不持久化）
    upload_notes: list[dict[str, Any]] = []
    if parsed.get("truncated"):
        upload_notes.append(
            ledger_entry(SOURCE_UPLOAD, "原文超20000字已截断后解析")
        )
    if entities.get("capped"):
        from app.domains.creation.a1.worldview_upload import PROPER_NOUN_LABELS

        cap_detail = "、".join(
            f"{PROPER_NOUN_LABELS.get(k, k)}超限丢弃 {v} 项"
            for k, v in entities["capped"].items()
        )
        upload_notes.append(
            ledger_entry(SOURCE_UPLOAD, f"专有名词每类上限10项已截断: {cap_detail}")
        )
    if upload_notes:
        _FILES[body["file_id"]].setdefault("warnings", []).extend(upload_notes)
    # A 触发点：上传填满视觉设计时启动后台预生成
    await _trigger_visual_bg_if_filled(body["session_id"])
    return body


@router.post("/api/a1/upload/convert")
async def upload_convert(req: UploadConvertRequest) -> dict:
    from app.domains.creation.a1.worldview_upload import (
        convert_text,
        parse_modules,
    )

    rec = _UPLOADS.get(req.upload_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="upload not found")
    if req.decision not in ("convert", "cancel"):
        raise HTTPException(status_code=422, detail="decision 必须是 convert 或 cancel")

    if req.decision == "cancel":
        del _UPLOADS[req.upload_id]
        return {"status": "cancelled"}

    try:
        provider = _get_upload_provider()
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="上传解析需要 LLM 服务")

    converted = await convert_text(provider, rec["content"], rec["matches"])
    parsed = await parse_modules(provider, converted)
    if not parsed["answers"]:
        raise HTTPException(
            status_code=422, detail="转换后未能解析出模块内容，请重新上传或手动创建"
        )
    del _UPLOADS[req.upload_id]
    log_event("upload", "convert_used", user_id=req.user_id, upload_id=req.upload_id)
    body = _prefill_session(req.user_id, parsed)
    body.pop("_session", None)  # 内部对象不外泄（M4a）
    body.update({"status": "parsed"})
    # J4 披露：convert 输入超预算截断 → upload ledger 条目
    from app.domains.creation.a1.worldview_upload import MAX_CONTENT_CHARS

    if len(rec["content"]) > MAX_CONTENT_CHARS:
        _FILES[body["file_id"]].setdefault("warnings", []).append(
            ledger_entry(SOURCE_UPLOAD, "原文超20000字已截断后转换")
        )
    # A 触发点：上传填满视觉设计时启动后台预生成
    await _trigger_visual_bg_if_filled(body["session_id"])
    return body


# ---------------------------------------------------------------------------
# Task 7: Edge confirm/reject API endpoints
# ---------------------------------------------------------------------------


@router.post("/api/a1/file/{file_id}/edge/{key:path}/confirm")
def confirm_edge(file_id: str, key: str) -> dict:
    """Confirm a concept edge — move from unconfirmed to confirmed state.

    If the edge was previously rejected, restore it (remove from rejected_edges).
    """
    rec = _get_file(file_id)
    confirmed = rec.get("confirmed_edges", {})
    rejected = rec.get("rejected_edges", {})

    # If edge was rejected, restore it (move rejected → confirmed)
    if key in rejected and key not in confirmed:
        edge_snapshot = rejected.pop(key)
        edge_snapshot["confirmed"] = True
        confirmed[key] = edge_snapshot

        # Re-add edge to graph_json if finalized
        if rec["status"] == "finalized" and rec.get("graph_json"):
            new_edge = {
                "from_node_id": edge_snapshot["from_node_id"],
                "to_node_id": edge_snapshot["to_node_id"],
                "edge_type": _CONFIDENCE_TO_EDGETYPE.get(
                    edge_snapshot.get("confidence", "semantic"), EdgeType.SEMANTIC
                ).value,
                "visual_description": edge_snapshot["relation"],
                "relation": edge_snapshot["relation"],
                "confidence": edge_snapshot["confidence"],
                "confirmed": True,
            }
            rec["graph_json"]["edges"].append(new_edge)

            # Recompute edge_stats
            from app.models.knowledge_graph import KnowledgeGraph as _KG
            g = _KG.model_validate(rec["graph_json"])
            rec["edge_stats"] = _compute_edge_stats(g.edges)

        # Task T-B: 新词入典流——确认含提议新关系的边 → relation 入典
        _induct_proposed_relation(rec, key)
        _save_store()
        return {"confirmed": True, "key": key}

    # v0.5 路径: pending 边只存在于 graph_json.edges（confirmed=False），
    # 未预写 confirmed_edges → 按三元组在图中匹配并升格为 confirmed。
    if key not in confirmed and key not in rejected:
        if rec["status"] == "finalized" and rec.get("graph_json"):
            for edge in rec["graph_json"]["edges"]:
                edge_key = _make_edge_key(
                    edge.get("from_node_id", ""),
                    edge.get("to_node_id", ""),
                    edge.get("relation", ""),
                )
                if edge_key == key:
                    confirmed[key] = {
                        "from_node_id": edge.get("from_node_id", ""),
                        "to_node_id": edge.get("to_node_id", ""),
                        "relation": edge.get("relation", ""),
                        "confidence": edge.get("confidence") or "semantic",
                        "confirmed": True,
                    }
                    edge["confirmed"] = True
                    break
            else:
                raise HTTPException(status_code=404, detail="edge not found")

            # Recompute edge_stats after pending → confirmed promotion
            from app.models.knowledge_graph import KnowledgeGraph as _KG05
            g05 = _KG05.model_validate(rec["graph_json"])
            rec["edge_stats"] = _compute_edge_stats(g05.edges)

            # Task T-B: 新词入典流——确认含提议新关系的边 → relation 入典
            _induct_proposed_relation(rec, key)
            _save_store()
            return {"confirmed": True, "key": key}

        raise HTTPException(status_code=404, detail="edge not found")

    # Update confirmed state
    confirmed[key]["confirmed"] = True

    # Restore from rejected if present (belt-and-suspenders)
    rejected.pop(key, None)

    # Update graph_json if finalized
    if rec["status"] == "finalized" and rec.get("graph_json"):
        for edge in rec["graph_json"]["edges"]:
            edge_key = _make_edge_key(
                edge.get("from_node_id", ""),
                edge.get("to_node_id", ""),
                edge.get("relation", ""),
            )
            if edge_key == key:
                edge["confirmed"] = True
                break

        # Recompute edge_stats after confirmed state flip
        from app.models.knowledge_graph import KnowledgeGraph as _KG2
        g2 = _KG2.model_validate(rec["graph_json"])
        rec["edge_stats"] = _compute_edge_stats(g2.edges)

    # Task T-B: 新词入典流——确认含提议新关系的边 → relation 入典
    _induct_proposed_relation(rec, key)
    _save_store()
    return {"confirmed": True, "key": key}


@router.post("/api/a1/file/{file_id}/edge/{key:path}/reject")
def reject_edge(file_id: str, key: str) -> dict:
    """Reject a concept edge — remove from graph and record in rejected_edges.

    Re-extraction will skip rejected edges.
    """
    rec = _get_file(file_id)
    confirmed = rec.get("confirmed_edges", {})
    rejected = rec.get("rejected_edges", {})

    if key not in confirmed:
        # v0.5 路径: pending 边只存在于 graph_json.edges → 从图中移除并记录快照。
        found = False
        if rec["status"] == "finalized" and rec.get("graph_json"):
            for edge in rec["graph_json"]["edges"]:
                edge_key = _make_edge_key(
                    edge.get("from_node_id", ""),
                    edge.get("to_node_id", ""),
                    edge.get("relation", ""),
                )
                if edge_key == key:
                    rejected[key] = {
                        "from_node_id": edge.get("from_node_id", ""),
                        "to_node_id": edge.get("to_node_id", ""),
                        "relation": edge.get("relation", ""),
                        "confidence": edge.get("confidence") or "semantic",
                        "confirmed": False,
                    }
                    found = True
                    break
            if found:
                rec["graph_json"]["edges"] = [
                    e for e in rec["graph_json"]["edges"]
                    if _make_edge_key(
                        e.get("from_node_id", ""),
                        e.get("to_node_id", ""),
                        e.get("relation", ""),
                    ) != key
                ]

                # Recompute edge_stats after pending → rejected removal
                from app.models.knowledge_graph import KnowledgeGraph as KG05
                g05 = KG05.model_validate(rec["graph_json"])
                rec["edge_stats"] = _compute_edge_stats(g05.edges)

                _save_store()
                return {"rejected": True, "key": key}

        raise HTTPException(status_code=404, detail="edge not found in confirmed_edges")

    # Move from confirmed to rejected
    edge_snapshot = confirmed.pop(key)
    rejected[key] = edge_snapshot

    # Remove from graph_json if finalized
    if rec["status"] == "finalized" and rec.get("graph_json"):
        edges = rec["graph_json"]["edges"]
        rec["graph_json"]["edges"] = [
            e for e in edges
            if _make_edge_key(
                e.get("from_node_id", ""),
                e.get("to_node_id", ""),
                e.get("relation", ""),
            ) != key
        ]

    # Recompute edge_stats
    if rec.get("graph_json"):
        from app.models.knowledge_graph import KnowledgeGraph as KG
        g = KG.model_validate(rec["graph_json"])
        rec["edge_stats"] = _compute_edge_stats(g.edges)

    _save_store()
    return {"rejected": True, "key": key}


# ---------------------------------------------------------------------------
# Task T-B: 两阶段编排——节点确认 + 阶段2概念边抽取端点
# ---------------------------------------------------------------------------


class TermsConfirmRequest(BaseModel):
    """批量确认概念词：terms=[词列表] 或 all=true."""
    terms: list[str] = []
    all: bool = False


def _registry_from_rec(rec: dict) -> RelationRegistry:
    """从 _FILES 持久化键 relation_registry 恢复词典（种子+运行时入典条目）."""
    registry = RelationRegistry()
    for name, spec in (rec.get("relation_registry") or {}).items():
        registry.add(name, level=spec.get("level", "semantic"),
                     gloss=spec.get("gloss", ""))
    return registry


def _persist_registry(rec: dict, registry: RelationRegistry) -> None:
    """序列化 RelationRegistry 当前条目到 _FILES.relation_registry（re-finalize 恢复用）."""
    rec["relation_registry"] = {
        s.name: {"level": s.level, "gloss": s.gloss} for s in registry.all_specs()
    }


def _induct_proposed_relation(rec: dict, key: str) -> None:
    """Task T-B 新词入典流：用户确认含提议新关系的边 → relation 入典（默认◆semantic）
    并从 proposed_relations 移除该条."""
    snap = rec.get("confirmed_edges", {}).get(key)
    if not snap:
        return
    relation = snap.get("relation", "")
    proposed = rec.get("proposed_relations", [])
    match = next(
        (p for p in proposed
         if p["name"] == relation
         and f"term:{p['from_term']}" == snap.get("from_node_id")
         and f"term:{p['to_term']}" == snap.get("to_node_id")),
        None,
    )
    if match is None:
        return
    registry = _registry_from_rec(rec)
    registry.add(relation)
    _persist_registry(rec, registry)
    proposed.remove(match)


@router.post("/api/a1/file/{file_id}/terms/confirm")
def confirm_terms(file_id: str, req: TermsConfirmRequest) -> dict:
    """批量确认概念词节点（阶段2前置：confirmed ≥ 2 才能抽边）."""
    rec = _get_file(file_id)
    terms = rec.get("concept_terms", [])
    for t in terms:
        if req.all or t["term"] in req.terms:
            t["confirmed"] = True
    rec["concept_terms"] = terms
    _save_store()
    return {"concept_terms": terms}


@router.post(
    "/api/a1/file/{file_id}/concept/extract-edges",
    deprecated=True,
)
def extract_concept_edges_v2(file_id: str) -> dict:
    """阶段2：在已确认概念词之间抽边（提议制）。失败降级 200+success=false.

    Deprecated (v0.5 两阶段退役, 治理文档 §8.1): finalize 不再产出 term:
    概念词节点，本端点仅作向后兼容保留；行为不变，计划 v0.5 末退役。
    """
    rec = _get_file(file_id)
    if rec["status"] != "finalized" or not rec.get("graph_json"):
        raise HTTPException(status_code=409, detail="pending_finalize")

    terms_all = [ConceptTerm(**t) for t in rec.get("concept_terms", [])]
    confirmed_terms = [t for t in terms_all if t.confirmed]
    if len(confirmed_terms) < 2:
        raise HTTPException(status_code=400, detail="需先确认至少2个概念词")

    registry = _registry_from_rec(rec)
    session = _SESSIONS[rec["session_id"]]

    try:
        try:
            provider = create_provider(load_provider_config())
        except Exception:  # noqa: BLE001
            provider = None
        result = extract_concept_relations(
            confirmed_terms, session, registry, provider=provider,
        )
    except Exception as exc:  # noqa: BLE001 — degrade, never crash
        return {"success": False,
                "warning": f"concept_edge extraction failed: {str(exc)[:200]}"}

    if not result.success:
        return {"success": False, "warning": result.warning}

    _persist_registry(rec, registry)

    confirmed = rec.setdefault("confirmed_edges", {})
    rejected = rec.get("rejected_edges", {})
    proposed = rec.setdefault("proposed_relations", [])
    proposed_names = {p["name"] for p in proposed}
    graph_nodes = rec["graph_json"]["nodes"]

    added = 0
    for e in result.edges:
        fid = f"term:{e.from_term}"
        tid = f"term:{e.to_term}"
        # 引用校验：词必须在已入图概念词节点内，缺失丢弃
        if fid not in graph_nodes or tid not in graph_nodes:
            continue
        key = _make_edge_key(fid, tid, e.relation)
        if key in rejected:
            continue
        confirmed_state = bool(confirmed.get(key, {}).get("confirmed", False))
        edge_type = _CONFIDENCE_TO_EDGETYPE.get(e.confidence, EdgeType.SEMANTIC)
        rec["graph_json"]["edges"].append({
            "from_node_id": fid, "to_node_id": tid,
            "edge_type": edge_type.value,
            "visual_description": e.relation,
            "relation": e.relation,
            "confidence": e.confidence,
            "confirmed": confirmed_state,
        })
        confirmed[key] = {
            "from_node_id": fid, "to_node_id": tid,
            "relation": e.relation, "confidence": e.confidence,
            "confirmed": confirmed_state,
        }
        # 新词入典流：提议新关系不直接确认，记入 proposed_relations 待用户裁决
        if (e.is_new_relation and not registry.is_known(e.relation)
                and e.relation not in proposed_names):
            proposed.append({
                "name": e.relation,
                "from_term": e.from_term, "to_term": e.to_term,
                "rationale": e.rationale,
            })
            proposed_names.add(e.relation)
        added += 1

    from app.models.knowledge_graph import KnowledgeGraph as _KG
    g = _KG.model_validate(rec["graph_json"])
    rec["edge_stats"] = _compute_edge_stats(g.edges)

    _save_store()
    return {"success": True, "added": added,
            "edges": [e.model_dump() for e in result.edges]}


# ---------------------------------------------------------------------------
# M3 产出模块端点（A2 资产回收三件；D15：资源名 doc＝界面「文档输出」）。
# 路径域裁决：随既有 a1_routes 惯例 /api/a1/file/{id}/*，不新开 /api/modules
# 域——会话/文件/发号器/registry 全部复用 A1 基建，跨域只增耦合。
# 契约族（S1:241-253 回收）：pending_finalize / missing_dice_template；
# stale 永不 409（消费留痕 used_stale）；LLM 仅 module_compile 单点（DN5
# 立项），失败降级确定性骨架 + ledger 披露；骰子/角色投影零 LLM 纯确定性。
# ---------------------------------------------------------------------------


def _graph_is_stale(user_id: str, graph_code: str) -> bool:
    """Upstream superseded check — informational only, never a 409 gate.

    Two signals (either ⇒ stale)：
    1. registry status = stale（``stale_marker.is_stale``，M3 新增）；
    2. 同 IP 同 stage 存在更高 (instance, version) 的产物（同代际已被
       重定稿/新实例取代——覆盖「W1 未注册但 W2 已注册」的测试与运行态）。
    """
    try:
        if stale_marker.is_stale(_registry_db(), graph_code):
            return True
        listing = stale_marker.list_user_graphs(_registry_db(), user_id)
    except Exception:  # noqa: BLE001 — 查询失败按未过期处理（不阻断）
        return False
    parts = graph_code.split("-")
    if len(parts) < 3:
        return False
    ip, stage_inst = parts[0], parts[1]
    stage = stage_inst[0]
    cur = (int(stage_inst[1:]), int(graph_code.rsplit("-v", 1)[1]))
    for group in listing.get("ips", []):
        for art in group.get("artifacts", []):
            if art.get("stage") != stage:
                continue
            if not str(art.get("graph_code", "")).startswith(f"{ip}-{stage}"):
                continue
            inst_str = str(art.get("graph_code", "")).split("-")[1][1:]
            try:
                cand = (int(inst_str), int(art.get("version", 0)))
            except ValueError:
                continue
            if cand > cur:
                return True
    return False


def _cst_constraints(rec: dict) -> list[str]:
    """cst_* 约束节点描述文本（骰子 Step4 边界钳制输入）。"""
    nodes = (rec.get("graph_json") or {}).get("nodes", [])
    return [
        str(n.get("description") or "")
        for n in nodes
        if str(n.get("id") or "").startswith("cst_") and n.get("description")
    ]


def _require_finalized(rec: dict) -> None:
    if rec.get("status") != "finalized" or not rec.get("graph_json"):
        raise HTTPException(status_code=409, detail="pending_finalize")


@router.post("/api/a1/file/{file_id}/doc")
def generate_module_doc(file_id: str) -> dict:
    """主模组文字版 finalize 八步（S1:397-410）：校验→拉输入→module_compile
    （LLM 单点+降级）→确定性装配→发号→registry 注册→ledger 透传→持久化。"""
    rec = _get_file(file_id)
    session = _SESSIONS[rec["session_id"]]
    _require_finalized(rec)

    registry_db = _registry_db()
    stale_marker.ensure_registry(registry_db)
    stale = _graph_is_stale(session.user_id, rec["graph_code"])
    if stale:
        stale_marker.record_stale_usage(registry_db, rec["graph_code"])

    # Provider 注入（与 finalize 同范式）；失败降级 None → 确定性骨架。
    try:
        provider = create_provider(load_provider_config())
    except Exception:  # noqa: BLE001
        provider = None

    issuer = GraphCodeIssuer(_ISSUER_DB)
    code = issuer.next(session.user_id, ip=rec["ip"], stage="M")
    instance_no = int(code.split("-")[1][1:])
    version = int(code.rsplit("-v", 1)[1])
    graph_id = stale_marker.register_graph(
        registry_db, session.user_id, code, "M",
        instance_no, version, scene_id=session.session_id,
        display_name=session.ip_code, parent_graph_code=rec["graph_code"],
    )

    ip_name = session.ip_code or session.seed_name or "未命名世界"
    doc, output_ledger = compile_document(
        session.answers,
        title=f"{ip_name}：主模组",
        ip_name=ip_name,
        graph_code=code,
        upstream_graph_code=rec["graph_code"],
        provider=provider,
        used_stale=stale,
        upstream_ledger=rec.get("warnings", []),
    )
    doc_json = doc.model_dump(mode="json")
    doc_md = render_markdown(doc)

    # 持久化（additive 键；产物 warnings 独立落键——重定稿 ledger 通道不混写）
    rec["module_doc"] = {
        "graph_id": graph_id, "doc_code": code,
        "doc_json": doc_json, "doc_md": doc_md,
        "warnings": output_ledger, "used_stale": stale,
    }
    _save_store()
    return {
        "doc_code": code, "graph_id": graph_id, "used_stale": stale,
        "ledger": list(rec.get("warnings", [])) + output_ledger,
    }


@router.get("/api/a1/file/{file_id}/doc")
def get_module_doc(file_id: str, format: str = "md") -> Any:
    rec = _get_file(file_id)
    stored = rec.get("module_doc")
    if not stored:
        raise HTTPException(status_code=409, detail="pending_finalize")
    if format == "json":
        return stored["doc_json"]
    return PlainTextResponse(
        stored["doc_md"], media_type="text/markdown; charset=utf-8")


@router.post("/api/a1/file/{file_id}/dice-template")
def generate_dice_template(file_id: str) -> dict:
    """骰子投影（TD）——确定性四步法，零 LLM（D-A2-3）。"""
    rec = _get_file(file_id)
    session = _SESSIONS[rec["session_id"]]
    _require_finalized(rec)

    registry_db = _registry_db()
    stale_marker.ensure_registry(registry_db)
    stale = _graph_is_stale(session.user_id, rec["graph_code"])
    if stale:
        stale_marker.record_stale_usage(registry_db, rec["graph_code"])

    issuer = GraphCodeIssuer(_ISSUER_DB)
    code = issuer.next(session.user_id, ip=rec["ip"], stage="TD")
    template = project_dice_template(
        session.answers,
        graph_code=code,
        upstream_graph_code=rec["graph_code"],
        used_stale=stale,
        constraints=_cst_constraints(rec),
    )
    dump = template.model_dump(mode="json")
    rec["dice_template"] = dump
    _save_store()
    return {"graph_code": code, "template": dump, "used_stale": stale,
            "warnings": template.warnings}


@router.post("/api/a1/file/{file_id}/character-template")
def generate_character_template(file_id: str) -> dict:
    """角色投影（TC）——4 相位；缺骰子产物 → 409 missing_dice_template
    （S1:247 契约逐字：模块间 hard 依赖的 API 表达）。"""
    rec = _get_file(file_id)
    session = _SESSIONS[rec["session_id"]]
    _require_finalized(rec)
    dice_dump = rec.get("dice_template")
    if not dice_dump:
        raise HTTPException(status_code=409, detail="missing_dice_template")

    registry_db = _registry_db()
    stale_marker.ensure_registry(registry_db)
    stale = _graph_is_stale(session.user_id, rec["graph_code"])
    if stale:
        stale_marker.record_stale_usage(registry_db, rec["graph_code"])

    dice = DiceTemplate.model_validate(dice_dump)
    issuer = GraphCodeIssuer(_ISSUER_DB)
    code = issuer.next(session.user_id, ip=rec["ip"], stage="TC")
    open_questions = [
        str(q.get("question") or "")
        for q in rec.get("open_questions", [])
        if isinstance(q, dict) and q.get("question")
    ]
    try:
        template = project_character_template(
            session.answers, dice,
            graph_code=code,
            upstream_graph_code=rec["graph_code"],
            used_stale=stale,
            open_questions=open_questions,
        )
    except DiceRequiredError:  # 防御：存储被外力清空的兜底契约
        raise HTTPException(status_code=409, detail="missing_dice_template")
    dump = template.model_dump(mode="json")
    rec["character_template"] = dump
    _save_store()
    return {"graph_code": code, "template": dump, "used_stale": stale,
            "warnings": template.warnings}