"""A1 guide engine — LLM-guided interview state machine.

Philosophy (2026-08-24 redesign):
    The question tree is a PROGRESS FRAMEWORK, not a form. The user
    speaks freely; the injected Interviewer (LLM) understands the input
    and fills the structured file — possibly several subfields at once.
    The engine then jumps to the first unanswered subfield. Only
    content the LLM judges to be outside the 10-module taxonomy enters
    the innovation-confirmation flow. When the LLM is unavailable the
    user is asked to retry — nothing is ever recorded without LLM
    judgment (blind-recording fix, 2026-08-26).

State: (current_module, current_subfield) tracks the first unanswered
subfield. Phase becomes 'completed' when every subfield across every
module has been answered or skipped.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.domains.creation.a1.interviewer import Interviewer, InterviewFill
from app.domains.creation.seed.a1_question_tree import (
    MODULES,
    all_subfield_keys,
    first_module,
    first_subfield,
    get_module,
    get_subfield,
    is_finalizable,
    subs_for_module,
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
    # Anti-stall tracking (deterministic fallback after repeated stalls)
    stall_subfield: str = ""
    stall_count: int = 0
    # Seed-referenced examples offered by the anti-stall guard; the user
    # may reply with a bare number 1/2/3 to accept one directly.
    pending_suggestions: list[str] = Field(default_factory=list)


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
        "example": sf.get("example", ""),
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
        "example": sf.get("example", ""),
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


def _apply_fills(session: A1Session, fills: list[InterviewFill]) -> list[dict[str, Any]]:
    """Persist fills into session.answers (first write wins per turn).

    First writes AND meaningful overwrites produce a diff entry (an
    overwrite after finalization must revert the file to draft).
    """
    file_diff: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for fill in fills:
        key = f"{fill.module}.{fill.subfield}"
        if key in seen_keys:  # first write wins this turn
            continue
        seen_keys.add(key)
        sf = get_subfield(fill.module, fill.subfield)
        old = session.answers.get(key, "")
        if old != fill.value:
            file_diff.append({
                "field": sf["label"] if sf else fill.subfield,
                "module": fill.module,
                "section": sf["label"] if sf else fill.subfield,
                "old": old,
                "new": fill.value,
            })
        session.answers[key] = fill.value
    return file_diff


def _apply_stall_guard(
    session: A1Session,
    text: str,
    cur_key: str,
    result: dict[str, Any],
    interviewer: Interviewer,
) -> dict[str, Any] | None:
    """Anti-stall guard with LLM-understanding-first fallbacks.

    Stall 2 -> ask the interviewer for seed-referenced example answers
    (user may reply a bare number to accept one). When suggestions are
    unavailable, ask the user to rephrase or 跳过 — no fill.
    Stall >= 3 -> forced_allocate: the LLM judges whether the input
    belongs to ANY legal field; fills are applied, otherwise the user
    gets options (suggestion numbers / rephrase / 跳过).

    Nothing is ever recorded without LLM judgment (blind-recording fix,
    2026-08-26): the old deterministic raw-text fill is gone.

    Returns a *replacement* result dict when either fallback triggers,
    otherwise None.
    """
    if session.phase == PHASE_COMPLETED:
        return None

    # 1. current field was filled this turn -> reset everything
    if cur_key in session.answers:
        session.stall_subfield = ""
        session.stall_count = 0
        session.pending_suggestions = []
        return None

    # 2. user asked a question -> don't count stall
    if text.strip().endswith(("？", "?")):
        return None

    # 3. track stall count (capped at 3)
    if session.stall_subfield == cur_key:
        session.stall_count = min(session.stall_count + 1, 3)
    else:
        session.stall_subfield = cur_key
        session.stall_count = 1

    module_id, sub_id = cur_key.split(".", 1)
    sf = get_subfield(module_id, sub_id)
    label = sf["label"] if sf else sub_id

    # 4. stall 2 -> suggestion mode (rely on LLM understanding first)
    if session.stall_count == 2:
        try:
            examples = interviewer.suggest_examples(session, module_id, sub_id)
        except Exception:  # noqa: BLE001 — degrade, never crash
            examples = []
        if examples:
            session.pending_suggestions = examples
            seed_label = session.seed_name or session.seed_description[:12] or "种子"
            lines = "\n".join(
                f"{i}. {ex}" for i, ex in enumerate(examples, start=1)
            )
            result["reply"] = (
                f"我没能准确理解你的回答。参考种子「{seed_label}」，"
                f"这里有几个示例方向：\n{lines}\n"
                "你可以直接回复序号选一个、改写一个再回复、换种说法再答，或回复「跳过」。"
            )
            result["next_question"] = _question_payload(session)
            result["file_diff"] = []
            return result
        # suggestions unavailable -> no fill; ask the user to rephrase / skip
        result["reply"] = (
            f"我还没能理解这条输入与「{label}」的关系。"
            "你可以换种说法再答一次，或回复「跳过」先进入下一项。"
        )
        result["next_question"] = _question_payload(session)
        result["file_diff"] = []
        result["progress"] = progress(session)
        result["phase"] = session.phase
        return result

    # 5. stall >= 3 -> LLM forced allocation (judgment; never raw fill)
    if session.stall_count >= 3:
        try:
            alloc = interviewer.forced_allocate(session, text)
        except Exception:  # noqa: BLE001 — degrade, never crash
            alloc = None
        if alloc is not None and alloc.fills:
            file_diff = _apply_fills(session, alloc.fills)
            sync_position(session)
            if cur_key in session.answers:
                session.stall_subfield = ""
                session.stall_count = 0
                session.pending_suggestions = []
            result["reply"] = alloc.guidance_reply or "已记录。"
            result["next_question"] = _question_payload(session)
            result["file_diff"] = file_diff
            result["progress"] = progress(session)
            result["phase"] = session.phase
            return result

        # no fills (or forced_allocate unavailable) -> record nothing,
        # offer the user concrete options instead.
        if not session.pending_suggestions:
            try:
                examples = interviewer.suggest_examples(session, module_id, sub_id)
            except Exception:  # noqa: BLE001 — degrade, never crash
                examples = []
            if examples:
                session.pending_suggestions = examples
        if session.pending_suggestions:
            seed_label = session.seed_name or session.seed_description[:12] or "种子"
            lines = "\n".join(
                f"{i}. {ex}"
                for i, ex in enumerate(session.pending_suggestions, start=1)
            )
            fallback_reply = (
                f"我仍无法把这条输入对应到「{label}」或任何字段。"
                f"参考种子「{seed_label}」可以选择：\n{lines}\n"
                "直接回复序号、换种说法再答，或回复「跳过」。"
            )
        else:
            fallback_reply = (
                f"我仍无法把这条输入对应到「{label}」或任何字段。"
                "请换种说法再答一次，或回复「跳过」先进入下一项。"
            )
        result["reply"] = (
            (alloc.guidance_reply if alloc is not None and alloc.guidance_reply else "")
            or fallback_reply
        )
        result["next_question"] = _question_payload(session)
        result["file_diff"] = []
        result["progress"] = progress(session)
        result["phase"] = session.phase
        return result

    return None


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
    - phase 'completed' no longer blocks chat: the user may keep
      refining answers (fills overwrite) until they finalize.
    """
    if session.phase == PHASE_COMPLETED:
        # Completed tree: keep the conversation open for refinement.
        # Falls through to the interviewer below — same routing rules.
        pass

    # ---- skip ----
    if text.strip() == "跳过":
        answer_key = f"{session.current_module}.{session.current_subfield}"
        skipped_module = session.current_module
        skipped_sf = get_subfield(session.current_module, session.current_subfield)
        session.answers.setdefault(answer_key, "")
        sync_position(session)
        return {
            "reply": "已跳过，进入下一项。",
            "next_question": _question_payload(session),
            "file_diff": [{
                "field": skipped_sf["label"] if skipped_sf else answer_key,
                "module": skipped_module,
                "section": skipped_sf["label"] if skipped_sf else answer_key,
                "old": "",
                "new": "",
            }],
            "progress": progress(session),
            "phase": session.phase,
        }

    cur_key = f"{session.current_module}.{session.current_subfield}"

    # ---- pending-suggestion number pick ("1"/"2"/"3") ----
    stripped = text.strip()
    if (
        session.pending_suggestions
        and stripped in {"1", "2", "3"}
        and session.phase != PHASE_COMPLETED
    ):
        idx = int(stripped) - 1
        if 0 <= idx < len(session.pending_suggestions):
            value = session.pending_suggestions[idx]
            session.answers[cur_key] = value
            session.stall_subfield = ""
            session.stall_count = 0
            session.pending_suggestions = []
            sync_position(session)
            module_id, sub_id = cur_key.split(".", 1)
            picked_sf = get_subfield(module_id, sub_id)
            return {
                "reply": f"已按示例记录：{value}",
                "next_question": _question_payload(session),
                "file_diff": [{
                    "field": picked_sf["label"] if picked_sf else cur_key,
                    "module": module_id,
                    "section": picked_sf["label"] if picked_sf else cur_key,
                    "old": "",
                    "new": value,
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
        file_diff = _apply_fills(session, result.fills)
        sync_position(session)
        out_fills = {
            "reply": result.guidance_reply or "已记录。",
            "next_question": _question_payload(session),
            "file_diff": file_diff,
            "progress": progress(session),
            "phase": session.phase,
        }
        guard = _apply_stall_guard(session, text, cur_key, out_fills, interviewer)
        return guard if guard is not None else out_fills

    # ---- chat / off-topic: reply only, nothing persisted ----
    out_chat = {
        "reply": result.guidance_reply or "请围绕当前问题分享你的设定。",
        "next_question": _question_payload(session),
        "file_diff": [],
        "progress": progress(session),
        "phase": session.phase,
    }
    guard = _apply_stall_guard(session, text, cur_key, out_chat, interviewer)
    return guard if guard is not None else out_chat


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
        # Finalize gate: every module strictly over 50% subfields answered.
        "finalizable": is_finalizable(session.answers),
    }
