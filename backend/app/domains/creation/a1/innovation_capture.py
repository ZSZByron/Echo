"""A1 innovation capture — proposal confirmation flow.

Innovative statements (compiler could not map them to dictionary enums)
surface as a ClassificationProposal; the user must confirm before anything
is persisted. Choosing "其他" stores ONLY the inconsistent content.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.domains.creation.a1.guide_engine import A1Session, _advance, progress  # noqa: PLC2701
from app.domains.creation.shared.semantic_compiler import ClassificationProposal

CHOICE_OTHER = "其他"
CHOICE_DISCARD = "放弃"


class Confirmation(BaseModel):
    """User's decision on a pending classification proposal."""

    proposal: ClassificationProposal
    choice: str  # a suggested category, "其他", or "放弃"


def confirm_proposal(session: A1Session, confirmation: Confirmation) -> dict[str, Any]:
    """Resolve a pending proposal.

    - choice == "放弃": nothing is persisted, section unchanged.
    - choice == "其他": ONLY the inconsistent content (the original text /
      suggestion field) is stored under the current section with an
      [其他] marker, then the section advances.
    - otherwise (a suggested category): the chosen category label is stored
      as the section value, then the section advances.
    """
    if confirmation.choice == CHOICE_DISCARD:
        return {
            "persisted": False,
            "file_diff": [],
            "progress": progress(session),
            "phase": session.phase,
        }

    if confirmation.choice == CHOICE_OTHER:
        raw = "; ".join(s.field for s in confirmation.proposal.suggestions) or "未分类创新内容"
        value = f"[其他] {raw}"
    else:
        value = confirmation.choice

    section_id = session.current_section
    session.answers[section_id] = value
    _advance(session)
    return {
        "persisted": True,
        "file_diff": [{"section": section_id, "value": value}],
        "progress": progress(session),
        "phase": session.phase,
    }
