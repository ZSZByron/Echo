"""A1 guide engine — sequential section state machine with compiler injection.

The user cannot freely jump sections (计划: 用户不自由跳板块). LLM is only
used for wording/follow-up via the injected SemanticCompiler; the section
flow itself is deterministic.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.domains.creation.seed.a1_question_tree import (
    SECTIONS,
    first_section,
    get_section,
    next_section,
    section_ids,
)
from app.domains.creation.shared.semantic_compiler import (
    ClassificationProposal,
    CompileResult,
    SemanticCompiler,
)

PHASE_ASKING = "asking"
PHASE_COMPLETED = "completed"

_SECTION_IDS = section_ids()


class A1Session(BaseModel):
    """A1 guided-session state (10 sections, sequential)."""

    session_id: str
    user_id: str
    ip_code: str = ""
    current_section: str = Field(default_factory=lambda: first_section()["id"])
    answers: dict[str, str] = Field(default_factory=dict)
    phase: str = PHASE_ASKING


def handle_message(
    session: A1Session,
    text: str,
    compiler: SemanticCompiler,
) -> dict[str, Any]:
    """Process one user message in the current section.

    Returns dict with keys:
      reply / next_question / file_diff / progress / phase /
      classification_proposal (optional, pending user confirmation)

    Rules:
    - Regular statements (compiler writes) are persisted to the structured
      file (answers) and the section advances.
    - Innovative statements (proposal) are returned for user confirmation
      and the section does NOT advance until resolved.
    - A user message of "跳过" marks the section as skipped (empty answer)
      and advances.
    """
    section = get_section(session.current_section)
    if session.phase == PHASE_COMPLETED:
        return {
            "reply": "全部板块已完成，请定稿。",
            "next_question": None,
            "file_diff": [],
            "progress": progress(session),
            "phase": session.phase,
        }

    if text.strip() == "跳过":
        session.answers.setdefault(session.current_section, "")
        _advance(session)
        return {
            "reply": f"已跳过【{section['label']}】。",
            "next_question": _question_payload(session),
            "file_diff": [{"section": session.current_section, "value": ""}],
            "progress": progress(session),
            "phase": session.phase,
        }

    result: CompileResult = compiler.compile(session.session_id, text)

    if result.writes:
        value = "; ".join(f"{w.field}={w.value}" for w in result.writes)
        session.answers[session.current_section] = value
        _advance(session)
        return {
            "reply": f"已记录【{section['label']}】。",
            "next_question": _question_payload(session),
            "file_diff": [{"section": section["id"], "value": value}],
            "progress": progress(session),
            "phase": session.phase,
        }

    # Innovative statement → proposal pending; section does not advance.
    proposal = result.classification_proposal or ClassificationProposal(
        suggestions=[]
    )
    return {
        "reply": "这是一条创新语句，请先确认分类。",
        "next_question": None,
        "file_diff": [],
        "progress": progress(session),
        "phase": session.phase,
        "classification_proposal": proposal.model_dump(),
    }


def progress(session: A1Session) -> dict[str, Any]:
    """Return {done, total, sections:[{id,label,done}]} for the UI."""
    sections = [
        {
            "id": s["id"],
            "label": s["label"],
            "done": s["id"] in session.answers,
        }
        for s in SECTIONS
    ]
    return {
        "done": sum(1 for s in sections if s["done"]),
        "total": len(sections),
        "sections": sections,
    }


def _advance(session: A1Session) -> None:
    nxt = next_section(session.current_section)
    if nxt is None:
        session.phase = PHASE_COMPLETED
    else:
        session.current_section = nxt["id"]


def _question_payload(session: A1Session) -> dict[str, Any] | None:
    if session.phase == PHASE_COMPLETED:
        return None
    section = get_section(session.current_section)
    return {
        "section": section["id"],
        "question": section["question"],
        "hint": section["hint"],
    }
