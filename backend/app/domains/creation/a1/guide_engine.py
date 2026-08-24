"""A1 guide engine — LLM-guided interview state machine.

Philosophy (2026-08-24 redesign):
    The question tree is a PROGRESS FRAMEWORK, not a form. The user
    speaks freely; the injected Interviewer (LLM) understands the input
    and fills the structured file — possibly several subfields at once.
    The engine then jumps to the first unanswered subfield. Only
    content the LLM judges to be outside the 10-module taxonomy enters
    the innovation-confirmation flow. When the LLM is unavailable, the
    raw text is stored directly into the current subfield (a name is
    just a name — never an innovation).

State: (current_module, current_subfield) tracks the first unanswered
subfield. Phase becomes 'completed' when every subfield across every
module has been answered or skipped.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.domains.creation.a1.interviewer import Interviewer
from app.domains.creation.seed.a1_question_tree import (
    MODULES,
    all_subfield_keys,
    first_module,
    first_subfield,
    get_module,
    get_subfield,
    is_module_done,
    module_ids,
    next_module,
    next_subfield,
    subs_for_module,
    total_subfield_count,
)
from app.domains.creation.shared.semantic_compiler import (
    ClassificationProposal,
    Suggestion,
)

PHASE_ASKING = "asking"
PHASE_COMPLETED = "completed"


def _initial_subfield() -> str:
    """Return the id of the first subfield of the first module."""
    m = first_module()
    sf = first_subfield(m["id"])
    return sf["id"]


class A1Session(BaseModel):
    """A1 guided-session state (10 modules x subfields, sequential)."""

    session_id: str
    user_id: str
    ip_code: str = ""
    current_module: str = Field(default_factory=lambda: first_module()["id"])
    current_subfield: str = Field(default_factory=_initial_subfield)
    answers: dict[str, str] = Field(default_factory=dict)
    phase: str = PHASE_ASKING
    # Seed context (chosen preset or custom idea) — injected into the
    # interviewer prompt so the LLM guides consistently with the seed.
    seed_name: str = ""
    seed_genre: str = ""
    seed_description: str = ""


def first_question() -> dict[str, Any]:
    """Return the question payload for the very first subfield."""
    m = first_module()
    sf = first_subfield(m["id"])
    return {
        "section": m["id"],
        "section_label": m["label"],
        "sub_id": sf["id"],
        "sub_label": sf["label"],
        "question": sf["question"],
        "hint": sf["hint"],
    }


def _question_payload(session: A1Session) -> dict[str, Any] | None:
    """Build the question payload for the current subfield."""
    if session.phase == PHASE_COMPLETED:
        return None
    m = get_module(session.current_module)
    sf = get_subfield(session.current_module, session.current_subfield)
    if m is None or sf is None:
        return None
    return {
        "section": m["id"],
        "section_label": m["label"],
        "sub_id": sf["id"],
        "sub_label": sf["label"],
        "question": sf["question"],
        "hint": sf["hint"],
    }


def sync_position(session: A1Session) -> None:
    """Jump to the first unanswered subfield; complete when none left."""
    for key in all_subfield_keys():
        if key not in session.answers:
            module_id, sub_id = key.split(".", 1)
            session.current_module = module_id
            session.current_subfield = sub_id
            return
    session.phase = PHASE_COMPLETED


def handle_message(
    session: A1Session,
    text: str,
    interviewer: Interviewer,
) -> dict[str, Any]:
    """Process one user message with LLM understanding.

    Returns dict with keys:
      reply / next_question / file_diff / progress / phase /
      classification_proposal (optional, only for genuine innovations)

    Rules:
    - "跳过" stores empty string for the current subfield and advances.
    - interviewer fills (possibly many subfields) are persisted; the
      position jumps to the first unanswered subfield.
    - fills empty + is_innovative -> innovation proposal, nothing
      persisted until confirmed.
    - fills empty + not innovative (chat/off-topic) -> reply only.
    """
    if session.phase == PHASE_COMPLETED:
        return {
            "reply": "全部板块已完成，请定稿。",
            "next_question": None,
            "file_diff": [],
            "progress": progress(session),
            "phase": session.phase,
        }

    # ---- skip ----
    if text.strip() == "跳过":
        answer_key = f"{session.current_module}.{session.current_subfield}"
        session.answers.setdefault(answer_key, "")
        sync_position(session)
        sf = get_subfield(session.current_module, session.current_subfield)
        return {
            "reply": "已跳过，进入下一项。",
            "next_question": _question_payload(session),
            "file_diff": [{
                "field": sf["label"] if sf else answer_key,
                "module": session.current_module,
                "section": sf["label"] if sf else answer_key,
                "old": "",
                "new": "",
            }],
            "progress": progress(session),
            "phase": session.phase,
        }

    result = interviewer.interview(session, text)

    # ---- genuine innovation -> confirmation flow ----
    if not result.fills and result.is_innovative:
        return {
            "reply": result.guidance_reply or "这段内容超出当前分类体系，请确认是否新增。",
            "next_question": None,
            "file_diff": [],
            "progress": progress(session),
            "phase": session.phase,
            "classification_proposal": ClassificationProposal(
                suggestions=[
                    Suggestion(
                        field=text.strip()[:50],
                        category=result.innovative_category or "其他",
                    )
                ]
            ).model_dump(),
        }

    # ---- fills (possibly many) -> persist + jump to first unanswered ----
    if result.fills:
        file_diff: list[dict[str, Any]] = []
        for fill in result.fills:
            key = f"{fill.module}.{fill.subfield}"
            if key not in session.answers:  # first write wins this turn
                sf = get_subfield(fill.module, fill.subfield)
                file_diff.append({
                    "field": sf["label"] if sf else fill.subfield,
                    "module": fill.module,
                    "section": sf["label"] if sf else fill.subfield,
                    "old": "",
                    "new": fill.value,
                })
            session.answers[key] = fill.value
        sync_position(session)
        return {
            "reply": result.guidance_reply or "已记录。",
            "next_question": _question_payload(session),
            "file_diff": file_diff,
            "progress": progress(session),
            "phase": session.phase,
        }

    # ---- chat / off-topic: reply only, nothing persisted ----
    return {
        "reply": result.guidance_reply or "请围绕当前问题分享你的设定。",
        "next_question": _question_payload(session),
        "file_diff": [],
        "progress": progress(session),
        "phase": session.phase,
    }


def progress(session: A1Session) -> dict[str, Any]:
    """Return {done, total, sections:[{id,label,done,done_fields,total_fields}]} for the UI."""
    sections = []
    done_count = 0
    for m in MODULES:
        fields = subs_for_module(m["id"])
        done_fields = sum(
            1 for f in fields if f"{m['id']}.{f['id']}" in session.answers
        )
        module_done = done_fields == len(fields) and len(fields) > 0
        if module_done:
            done_count += 1
        sections.append({
            "id": m["id"],
            "label": m["label"],
            "done": module_done,
            "done_fields": done_fields,
            "total_fields": len(fields),
            "subs": [
                {
                    "id": f["id"],
                    "label": f["label"],
                    "done": f"{m['id']}.{f['id']}" in session.answers,
                }
                for f in fields
            ],
        })
    return {
        "done": done_count,
        "total": len(MODULES),
        "sections": sections,
    }
