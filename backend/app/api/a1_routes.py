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
from app.domains.creation.a1.guide_engine import (
    A1Session,
    handle_message,
    progress,
)
from app.domains.creation.a1.innovation_capture import (
    Confirmation,
    confirm_proposal,
)
from app.domains.creation.a1.ip_poster import build_poster
from app.domains.creation.a1.semantic_compiler import RealSemanticCompiler
from app.domains.creation.graph.constraint_topology import apply_constraints
from app.domains.creation.seed.a1_question_tree import SECTIONS, first_section
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

_COMPILER = RealSemanticCompiler(provider=None)

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
    sec = next((s for s in SECTIONS if s["id"] == session.current_section), None)
    if sec is None:
        return None
    return {"section": sec["id"], "question": sec["question"], "hint": sec["hint"]}


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
    for sec in SECTIONS:
        value = session.answers.get(sec["id"], "")
        if not value:
            continue
        nodes[sec["id"]] = GraphNode(
            id=sec["id"], serial_number=str(len(nodes)), level=2,
            description=f"{sec['label']}: {value}",
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

    # Prefill non-empty defaults from the chosen preset.
    if req.seed_id is not None:
        preset = next((p for p in load_presets() if p.id == req.seed_id), None)
        if preset is None:
            raise HTTPException(status_code=404, detail="seed preset not found")
        session.answers = {
            k: v for k, v in preset.dimension_defaults.items() if v
        }
    else:
        session.answers["世界观"] = req.custom_idea[:200]

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
    }


@router.post("/api/a1/chat")
def chat(req: ChatRequest) -> dict:
    session = _SESSIONS.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    out = handle_message(session, req.message, _COMPILER)
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
    return confirm_proposal(session, Confirmation(proposal=proposal, choice=req.choice))


def _get_file(file_id: str) -> dict:
    rec = _FILES.get(file_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="file not found")
    return rec


@router.get("/api/a1/file/{file_id}")
def get_file(file_id: str) -> dict:
    rec = _get_file(file_id)
    session = _SESSIONS[rec["session_id"]]
    return {
        "file_id": file_id, "status": rec["status"],
        "answers": session.answers,
        "graph_code": rec["graph_code"],
        "session_id": session.session_id,
    }


@router.post("/api/a1/file/{file_id}/finalize")
def finalize(file_id: str) -> dict:
    rec = _get_file(file_id)
    session = _SESSIONS[rec["session_id"]]

    missing = [s["id"] for s in SECTIONS if s["id"] not in session.answers]
    if missing:
        raise HTTPException(status_code=409, detail={"missing_sections": missing})

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
