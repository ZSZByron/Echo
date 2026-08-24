"""A1 workspace API routes — 8 endpoints per A1-v0.5 plan Task 9.

Three-state flow: seed select → guided chat (10 sections) → finalize to
graph (+ IP poster). Constraint edges are injected at finalize via
apply_constraints (T-F hook); re-finalize issues W1-v2 and marks
downstream graphs stale (iron law: never delete, never overwrite).
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config.paths import ASSETS_DIR
from app.ai.config import load_provider_config
from app.ai.provider import create_provider
from app.domains.creation.a1.guide_engine import (
    A1Session,
    handle_message,
    progress,
    sync_position,
)
from app.domains.creation.a1.interviewer import (
    DegradingInterviewer,
    RealLLMInterviewer,
)
from app.domains.creation.a1.innovation_capture import (
    Confirmation,
    confirm_proposal,
)
from app.domains.creation.a1.ip_poster import build_poster
from app.domains.creation.a1.semantic_compiler import (
    RealSemanticCompiler,
    derive_dice_recommendation,
)
from app.domains.creation.graph.constraint_topology import apply_constraints
from app.domains.creation.seed.a1_question_tree import (
    MODULES,
    first_module,
    first_subfield,
    get_subfield,
    module_ids,
    get_module,
    is_module_done,
    subs_for_module,
)
from app.domains.creation.seed.preset_loader import load_presets
from app.domains.creation.shared.graph_code_issuer import GraphCodeIssuer
from app.domains.creation.shared import stale_marker
from app.models.dimension import (
    DimensionResultSet,
    LawOutput,
    ActOutput,
    NarOutput,
    WstOutput,
    SocOutput,
)
from app.models.knowledge_graph import GraphNode, KnowledgeGraph

router = APIRouter()

# MVP in-memory stores (per plan: sessions in memory, no persistence).
_SESSIONS: dict[str, A1Session] = {}
_FILES: dict[str, dict[str, Any]] = {}

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
    seed_id: Optional[int] = None
    custom_idea: Optional[str] = None


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ConfirmRequest(BaseModel):
    session_id: str
    proposal: dict
    choice: str


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
    
    # Build level=2 nodes for each module with non-empty content
    for module in MODULES:
        module_id = module["id"]
        module_label = module["label"]
        
        # Collect all non-empty subfield answers for this module
        subfield_summaries = []
        for sf in module["fields"]:
            answer_key = f"{module_id}.{sf['id']}"
            value = session.answers.get(answer_key, "")
            if value:
                subfield_summaries.append(f"{sf['label']}: {value}")
        
        if subfield_summaries:
            description = f"{module_label}: " + "; ".join(subfield_summaries)
            nodes[module_id] = GraphNode(
                id=module_id, serial_number=str(len(nodes)), level=2,
                description=description,
            )
    
    graph = KnowledgeGraph(
        scene_id=session.session_id, background_node_id=bg_id,
        nodes=nodes, edges=[],
    )
    return apply_constraints(graph, _build_dimension_result_set(session), stage="A1")


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
    }
    return {
        "session_id": session.session_id,
        "file_id": file_id,
        "ip_code": session.ip_code,
        "first_question": _question_payload(session),
        "file": {"status": "draft", "answers": session.answers},
        "seed": {
            "name": session.seed_name,
            "genre": session.seed_genre,
            "description": session.seed_description,
        },
    }


@router.post("/api/a1/chat")
def chat(req: ChatRequest) -> dict:
    session = _SESSIONS.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    out = handle_message(session, req.message, _get_interviewer())
    
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
    return out


@router.post("/api/a1/chat/confirm")
def chat_confirm(req: ConfirmRequest) -> dict:
    session = _SESSIONS.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    from app.domains.creation.shared.semantic_compiler import ClassificationProposal
    proposal = ClassificationProposal(**req.proposal)
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


@router.get("/api/a1/file/{file_id}")
def get_file(file_id: str) -> dict:
    rec = _get_file(file_id)
    session = _SESSIONS[rec["session_id"]]
    
    # Build hierarchical sections structure
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
    
    return {
        "file_id": file_id, 
        "status": rec["status"],
        "answers": session.answers,
        "graph_code": rec["graph_code"],
        "session_id": session.session_id,
        "sections": sections,
    }


@router.post("/api/a1/file/{file_id}/finalize")
def finalize(file_id: str) -> dict:
    rec = _get_file(file_id)
    session = _SESSIONS[rec["session_id"]]

    # Check if all modules are done using the new API
    missing = [mid for mid in module_ids() if not is_module_done(mid, session.answers)]
    if missing:
        raise HTTPException(status_code=409, detail={"missing_modules": missing})

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

    graph = _build_graph(session, rec)
    graph_id = stale_marker.register_graph(
        registry_db, session.user_id, new_code, "W",
        instance_no, version, scene_id=session.session_id,
        display_name=session.ip_code,
    )

    rec.update({"status": "finalized", "graph_code": new_code,
                "graph_json": graph.model_dump(mode="json"), "graph_id": graph_id})
    return {"graph_id": graph_id, "graph_code": new_code, "warnings": []}


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
    return build_poster(session)
