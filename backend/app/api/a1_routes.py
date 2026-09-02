"""A1 workspace API routes — 8 endpoints per A1-v0.5 plan Task 9.

Three-state flow: seed select → guided chat (10 sections) → finalize to
graph (+ IP poster). Constraint edges are injected at finalize via
apply_constraints (T-F hook); re-finalize issues W1-v2 and marks
downstream graphs stale (iron law: never delete, never overwrite).
"""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ai.config import load_provider_config
from app.ai.provider import create_provider
from app.ai.visual_bg import run_visual_bg_pipeline
from app.config.paths import ASSETS_DIR
from app.domains.creation.a1.guide_engine import (
    A1Session,
    handle_message,
    sync_position,
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
from app.domains.creation.a1.semantic_compiler import (
    derive_dice_recommendation,
)
from app.domains.creation.graph.constraint_topology import apply_constraints
from app.domains.creation.seed.a1_question_tree import (
    MODULES,
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
from app.models.dimension import (
    ActOutput,
    DimensionResultSet,
    LawOutput,
    NarOutput,
    SocOutput,
    WstOutput,
)
from app.domains.creation.a1.concept_edge_extractor import ExtractResult, extract_concept_edges
from app.domains.creation.a1.concept_edge_vocab import EDGE_VOCAB
from app.models.knowledge_graph import EdgeType, GraphEdge, GraphNode, KnowledgeGraph

router = APIRouter()

# MVP in-memory stores (per plan: sessions in memory, no persistence).
_SESSIONS: dict[str, A1Session] = {}
_FILES: dict[str, dict[str, Any]] = {}

# In-memory lock to prevent duplicate concurrent poster generation for the
# same file_id (mirrors _generation_tasks in assets_routes.py).
_poster_generation_tasks: dict[str, Any] = {}

_ISSUER_DB = Path(__file__).resolve().parents[2] / "data" / "a1_codes.db"
_ISSUER_DB.parent.mkdir(parents=True, exist_ok=True)

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


class ChatRequest(BaseModel):
    session_id: str
    message: str


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


def _build_dimension_result_set(session: A1Session) -> DimensionResultSet:
    """Parse `tag=value; ...` answer fragments into structured Outputs."""
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


def _build_graph(session: A1Session, file_rec: dict) -> KnowledgeGraph:
    bg_id = f"bg_{session.session_id[:8]}"
    nodes: dict[str, GraphNode] = {
        bg_id: GraphNode(id=bg_id, serial_number="0", level=1,
                         description=f"[{session.ip_code}] 世界背景")
    }
    edges: list[GraphEdge] = []

    # Track module serial number (only for modules with non-empty answers)
    module_serial = 0

    # Build level=2 module nodes and level=3 entry nodes
    for module in MODULES:
        module_id = module["id"]
        module_label = module["label"]

        # Collect non-empty subfield answers for this module
        subfield_answers = []
        for sf in module["fields"]:
            answer_key = f"{module_id}.{sf['id']}"
            value = session.answers.get(answer_key, "")
            if value:
                subfield_answers.append((sf, value))

        # Only create module node if there are non-empty answers
        if subfield_answers:
            module_serial += 1
            # Level 2: Module node (description is just the label, not aggregated)
            nodes[module_id] = GraphNode(
                id=module_id,
                serial_number=str(module_serial),
                level=2,
                description=module_label,
            )

            # TREE edge: background -> module
            edges.append(GraphEdge(
                from_node_id=bg_id,
                to_node_id=module_id,
                edge_type=EdgeType.TREE,
                visual_description="包含",
            ))

            # Level 3: Entry nodes for each non-empty subfield answer
            entry_serial = 0
            for sf, value in subfield_answers:
                entry_serial += 1
                entry_id = f"{module_id}.{sf['id']}"
                nodes[entry_id] = GraphNode(
                    id=entry_id,
                    serial_number=f"{module_serial}-{entry_serial}",
                    level=3,
                    description=f"{sf['label']}: {value}",
                )

                # TREE edge: module -> entry
                edges.append(GraphEdge(
                    from_node_id=module_id,
                    to_node_id=entry_id,
                    edge_type=EdgeType.TREE,
                    visual_description="条目",
                ))

    graph = KnowledgeGraph(
        scene_id=session.session_id, background_node_id=bg_id,
        nodes=nodes, edges=edges,
    )
    graph = apply_constraints(graph, _build_dimension_result_set(session), stage="A1")
    return graph, set(nodes.keys())


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
        "session_start",
        user_id=req.user_id,
        ip_code=session.ip_code,
        seed_id=req.seed_id,
        seed=session.seed_name or None,
        custom_idea=(req.custom_idea or "")[:100] or None,
    )
    return {
        "session_id": session.session_id,
        "file_id": file_id,
        "ip_code": session.ip_code,
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
    session = _SESSIONS.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    log_event(
        session.session_id,
        "user_message",
        text=req.message[:300],
        position=f"{session.current_module}.{session.current_subfield}",
    )
    out = await asyncio.to_thread(
        handle_message, session, req.message, _get_interviewer()
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

    return out


@router.post("/api/a1/chat/confirm")
def chat_confirm(req: ConfirmRequest) -> dict:
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
        result = resolve_proposal(session, proposal_key, canonical_choice)

        # Build response
        reply = "已确认并记录。"
        if result.get("applied"):
            choice_desc = {"replace": "替换", "merge": "合并", "drop": "放弃"}.get(canonical_choice, "")
            reply = f"已{choice_desc}该内容。"
        else:
            reply = "已放弃该内容，可重新输入。"

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
    return out


def _get_file(file_id: str) -> dict:
    rec = _FILES.get(file_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="file not found")
    return rec


def _build_sections(session: A1Session) -> list[dict]:
    """Hierarchical sections structure shared by start & get_file responses."""
    sections = []
    for module in MODULES:
        module_id = module["id"]
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
    """Add concept edges to graph, with node validation and state restoration.

    Returns list of GraphEdge objects that were actually added.
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

    # Finalize gate: every module must have STRICTLY more than 50% of
    # its subfields answered (product rule, see a1_question_tree).
    missing = [mid for mid in module_ids() if not is_module_over_half(mid, session.answers)]
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
    registry_db = str(ASSETS_DIR / "ugc.db")
    stale_marker.ensure_registry(registry_db)
    if rec["graph_code"] and rec["graph_code"] != new_code:
        stale_marker.mark_downstream_stale(
            registry_db, rec["graph_code"],
            {"diff_summary": f"{rec['graph_code']} -> {new_code}"},
        )

    graph, valid_node_ids = _build_graph(session, rec)
    warnings: list[str] = []

    # Task 7: Extract concept edges and integrate into graph
    try:
        try:
            provider = create_provider(load_provider_config())
        except Exception:  # noqa: BLE001
            provider = None
        extract_result = extract_concept_edges(session, EDGE_VOCAB, provider=provider)
    except Exception as exc:  # noqa: BLE001 — degrade on any extraction error
        extract_result = ExtractResult(
            success=False,
            warning=f"concept_edge extraction failed: {str(exc)[:200]}",
        )

    if extract_result.success:
        # Ensure confirmed_edges/rejected_edges dicts exist (backward compat)
        confirmed = rec.get("confirmed_edges", {})
        rejected = rec.get("rejected_edges", {})

        _add_concept_edges_to_graph(
            graph, extract_result.edges, valid_node_ids, confirmed, rejected,
        )

        # Write open_questions to _FILES
        rec["open_questions"] = extract_result.open_questions
    else:
        # Degradation: pure TREE graph, warnings contain "concept_edge"
        warnings.append(extract_result.warning or "concept_edge extraction failed")
        rec["open_questions"] = rec.get("open_questions", [])

    # Compute edge_stats from all edges in the graph
    rec["edge_stats"] = _compute_edge_stats(graph.edges)

    graph_id = stale_marker.register_graph(
        registry_db, session.user_id, new_code, "W",
        instance_no, version, scene_id=session.session_id,
        display_name=session.ip_code,
    )

    rec.update({"status": "finalized", "graph_code": new_code,
                "graph_json": graph.model_dump(mode="json"), "graph_id": graph_id})
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

    return {"graph_id": graph_id, "graph_code": new_code, "warnings": warnings, "status": "finalized"}


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
    return {
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
    body.update({"status": "parsed", "upload_id": upload_id})
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
    body.update({"status": "parsed"})
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

        return {"confirmed": True, "key": key}

    if key not in confirmed:
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

    return {"rejected": True, "key": key}
