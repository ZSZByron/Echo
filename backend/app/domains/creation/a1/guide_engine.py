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

import hashlib
from typing import Any

from pydantic import BaseModel, Field

from app.domains.creation.a1.interviewer import (
    Interviewer,
    InterviewFill,
    Proposal,
)
from app.domains.creation.seed.a1_question_tree import (
    MODULES,
    all_subfield_keys,
    first_module,
    first_subfield,
    get_module,
    get_subfield,
    is_finalizable,
    is_module_over_half,
    module_ids,
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
    # Write-guard proposals (Task 4): key=proposal_key, value=dict with
    # 'proposal' (Proposal model), 'options' (list[str]).
    # Semantically independent from pending_suggestions (Metis Q5).
    pending_proposals: dict[str, dict[str, Any]] = Field(default_factory=dict)
    # Merge count per field key (module.subfield). After 3 merges,
    # the 'merge' option is removed from future proposals.
    merge_counts: dict[str, int] = Field(default_factory=dict)
    # Fields whose current value came from upload prefill (LLM *guesses*,
    # never user-confirmed). User-spoken fills overwrite these directly
    # (write guard protects user-confirmed content only); the key is
    # removed after overwrite so the field returns to normal guard.
    prefill_fields: list[str] = Field(default_factory=list)
    # Field keys prefilled from the upload-pipeline LLM parse. These are
    # *guesses* the user never confirmed, so the write guard does NOT
    # protect them: a user-spoken fill overwrites a prefill directly
    # (after which the key is removed and the field is guarded normally).
    # Default empty keeps old sessions deserializable.
    prefill_fields: list[str] = Field(default_factory=list)


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
    """Jump to the first unanswered subfield; complete when none left.

    Gate-aware (user request: 有缺失，在窗口询问): modules still below the
    50% finalize gate are serviced FIRST, so the chat window proactively
    asks about missing modules instead of trailing minor fields elsewhere.
    """
    # 1) Prefer unfilled fields inside gate-failing modules.
    for mid in module_ids():
        if is_module_over_half(mid, session.answers):
            continue
        for f in subs_for_module(mid):
            key = f"{mid}.{f['id']}"
            if key not in session.answers:
                session.current_module = mid
                session.current_subfield = f["id"]
                return
    # 2) Fallback: global first unanswered (original behaviour).
    for key in all_subfield_keys():
        if key not in session.answers:
            module_id, sub_id = key.split(".", 1)
            session.current_module = module_id
            session.current_subfield = sub_id
            return
    session.phase = PHASE_COMPLETED


def resolve_proposal(session: A1Session, key: str, choice: str) -> dict[str, Any]:
    """Resolve a pending write-guard proposal.

    Choices: 'replace' | 'merge' | 'drop'.
    Returns dict with 'applied' (bool), 'choice', and optional 'already_resolved'.
    Idempotent: repeating the same key returns latest state without
    double-write (Metis E3).
    """
    entry = session.pending_proposals.get(key)
    if entry is None:
        return {"applied": False, "choice": choice, "error": "not_found"}

    proposal: Proposal = entry["proposal"]
    field_key = f"{proposal.module}.{proposal.subfield}"

    if choice == "replace":
        session.answers[field_key] = proposal.new
        applied = True
    elif choice == "merge":
        old_val = session.answers.get(field_key, proposal.old)
        session.answers[field_key] = f"{old_val}；{proposal.new}"
        session.merge_counts[field_key] = session.merge_counts.get(field_key, 0) + 1
        applied = True
    elif choice == "drop":
        applied = False
    else:
        return {"applied": False, "choice": choice, "error": "invalid_choice"}

    session.pending_proposals.pop(key, None)
    return {"applied": applied, "choice": choice}


def _fallback_divergent(session: A1Session, fills: list[InterviewFill]) -> str | None:
    """Code-level fallback for divergent_question (Metis AC-M8).

    When InterviewResult.divergent_question is None and fills are
    non-empty, generate a template question from fill value keywords
    × unfilled field labels.
    Template: "你提到【{keyword}】，这和＿＿（{unfilled_label}）有关系吗？"
    """
    if not fills:
        return None

    # Determine keys being filled this turn (to exclude them from targets)
    filling_keys = {f"{f.module}.{f.subfield}" for f in fills}

    # Collect unfilled field labels (up to 10, excluding the ones being filled)
    unfilled_labels: list[str] = []
    for key in all_subfield_keys():
        if key not in session.answers and key not in filling_keys:
            module_id, sub_id = key.split(".", 1)
            sf = get_subfield(module_id, sub_id)
            if sf:
                unfilled_labels.append(sf["label"])
        if len(unfilled_labels) >= 10:
            break

    if not unfilled_labels:
        return None

    # Use first fill's value (up to 8 chars or first punctuation segment)
    val = fills[0].value
    keyword = val[:8]
    # If there's punctuation within 8 chars, truncate there
    for i, ch in enumerate(val[:8]):
        if ch in ("，", "。", "、", "；", "！", "？", ",", "."):
            keyword = val[:i].strip()
            break

    if not keyword:
        return None

    target = unfilled_labels[0]
    return f"你提到【{keyword}】，这和＿＿（{target}）有关系吗？"


def _proposal_key(module: str, subfield: str, new: str) -> str:
    """Deterministic proposal key: module.subfield:md5[:8]."""
    h = hashlib.md5(new.encode()).hexdigest()[:8]
    return f"{module}.{subfield}:{h}"


def _apply_fills(
    session: A1Session, fills: list[InterviewFill]
) -> tuple[list[dict[str, Any]], list[Proposal]]:
    """Persist fills into session.answers with write-guard.

    Three-branch guard (Metis Q1/E2):
      1. Empty field (old=='') → direct write + file_diff(old='').
      2. Non-empty, new == old → skip (no proposal, no write).
      3. Non-empty, new != old → intercept: generate Proposal, do NOT
         write to answers.  The proposal is stored in
         session.pending_proposals.

    Returns (file_diff, intercepted_proposals).
    """
    file_diff: list[dict[str, Any]] = []
    intercepted: list[Proposal] = []
    seen_keys: set[str] = set()
    for fill in fills:
        key = f"{fill.module}.{fill.subfield}"
        if key in seen_keys:  # first write wins this turn
            continue
        seen_keys.add(key)
        sf = get_subfield(fill.module, fill.subfield)
        old = session.answers.get(key, "")

        # Branch 2: skip — same value
        if old and old == fill.value:
            continue

        # Branch 3: intercept — non-empty and different
        if old and old != fill.value:
            # Prefill exemption: prefill values are LLM guesses made at
            # upload time and were never confirmed by the user. A fill
            # spoken by the user directly overwrites them (recorded in
            # file_diff); afterwards the key reverts to normal guarding.
            if key in session.prefill_fields:
                session.prefill_fields.remove(key)
                file_diff.append({
                    "field": sf["label"] if sf else fill.subfield,
                    "module": fill.module,
                    "section": sf["label"] if sf else fill.subfield,
                    "old": old,
                    "new": fill.value,
                })
                session.answers[key] = fill.value
                continue
            proposal = Proposal(
                module=fill.module,
                subfield=fill.subfield,
                old=old,
                new=fill.value,
                conflict_note=fill.conflict_note,
            )
            intercepted.append(proposal)
            pk = _proposal_key(fill.module, fill.subfield, fill.value)
            # Determine available options (merge cap check)
            merge_count = session.merge_counts.get(key, 0)
            options = ["replace", "drop"]
            if merge_count < 3:
                options.insert(1, "merge")  # replace, merge, drop
            session.pending_proposals[pk] = {
                "proposal": proposal,
                "options": options,
            }
            continue

        # Branch 1: empty → direct write
        file_diff.append({
            "field": sf["label"] if sf else fill.subfield,
            "module": fill.module,
            "section": sf["label"] if sf else fill.subfield,
            "old": old,
            "new": fill.value,
        })
        session.answers[key] = fill.value

    return file_diff, intercepted


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
            file_diff, intercepted = _apply_fills(session, alloc.fills)
            if intercepted:
                # Write guard intercepted — generate confirmation reply
                prop = intercepted[0]
                sf = get_subfield(prop.module, prop.subfield)
                label = sf["label"] if sf else prop.subfield
                conflict_part = f"（{prop.conflict_note}）" if prop.conflict_note else ""
                result["reply"] = (
                    f"你之前定过【{label}】是『{prop.old}』{conflict_part}。"
                    f"这次的『{prop.new}』——是要**替换**它，"
                    f"还是两者**合并**（同一条里都保留），"
                    f"还是先**放弃**这条修改？"
                )
                result["next_question"] = None
                result["file_diff"] = []
                result["proposals"] = [p.model_dump() for p in intercepted]
                result["progress"] = progress(session)
                result["phase"] = session.phase
                return result
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
        file_diff, intercepted = _apply_fills(session, result.fills)

        # Advance position FIRST (when not intercepted) so next_question
        # reflects the post-fill state — asking the just-answered field
        # again ("问两遍" regression) otherwise.
        if not intercepted:
            sync_position(session)

        # Divergent fallback (Metis AC-M8)
        dq = result.divergent_question
        if dq is None:
            dq = _fallback_divergent(session, result.fills)

        # Build base result
        out_fills: dict[str, Any] = {
            "reply": result.guidance_reply or "已记录。",
            "next_question": _question_payload(session),
            "file_diff": file_diff,
            "progress": progress(session),
            "phase": session.phase,
        }
        if dq is not None:
            out_fills["divergent_question"] = dq

        # Write guard intercepted — override reply, suspend next_question
        if intercepted:
            prop = intercepted[0]
            sf = get_subfield(prop.module, prop.subfield)
            label = sf["label"] if sf else prop.subfield
            conflict_part = f"（{prop.conflict_note}）" if prop.conflict_note else ""
            out_fills["reply"] = (
                f"你之前定过【{label}】是『{prop.old}』{conflict_part}。"
                f"这次的『{prop.new}』——是要**替换**它，"
                f"还是两者**合并**（同一条里都保留），"
                f"还是先**放弃**这条修改？"
            )
            out_fills["next_question"] = None  # iron law
            out_fills["file_diff"] = []
            out_fills["proposals"] = [p.model_dump() for p in intercepted]

        # Let stall guard run (preserves stall tracking even when intercepted)
        guard = _apply_stall_guard(session, text, cur_key, out_fills, interviewer)
        if guard is not None:
            return guard

        return out_fills

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
