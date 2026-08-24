"""A1 IP poster -- epic-atmosphere image prompt + overlay panel data.
"""
from __future__ import annotations

from typing import Any

from app.domains.creation.a1.guide_engine import A1Session
from app.domains.creation.seed.a1_question_tree import MODULES, get_module, subs_for_module

POSTER_STATUS_PENDING = "pending"


def build_poster(session: A1Session) -> dict[str, Any]:
    """Build poster data from the session's structured file.

    Returns {panels, ai_image_prompt, ai_image_status}:
    - panels: overlay panels for non-empty modules
    - ai_image_prompt: epic atmosphere prompt stitched from module values
    - ai_image_status: always "pending" (image generation is out of scope
      for this batch)
    """
    panels: list[dict[str, str]] = []
    fragments: list[str] = []
    
    # Group answers by module
    module_answers: dict[str, list[tuple[str, str]]] = {}
    for answer_key, value in session.answers.items():
        if not value:
            continue
        # Parse answer key format: "module_id.subfield_id"
        if "." not in answer_key:
            continue
        module_id, subfield_id = answer_key.split(".", 1)
        if module_id not in module_answers:
            module_answers[module_id] = []
        module_answers[module_id].append((subfield_id, value))
    
    # Build panels for each module (in canonical module order)
    known_ids = {m["id"] for m in MODULES}
    for m in MODULES:
        module_id = m["id"]
        if module_id not in module_answers:
            continue
        label = m["label"]
        subfield_values = module_answers[module_id]

        # Combine all subfield values for this module
        combined_value = "；".join([f"{sf_id}:{val}" for sf_id, val in subfield_values])
        panels.append({"id": module_id, "title": label, "content": combined_value})
        fragments.append(f"{label}:{combined_value}")

    # Tolerate answer keys whose module part is unknown (legacy data)
    for module_id in module_answers:
        if module_id in known_ids:
            continue
        module = get_module(module_id)
        if not module:
            continue
        combined_value = "；".join(
            [f"{sf_id}:{val}" for sf_id, val in module_answers[module_id]]
        )
        panels.append({"id": module_id, "title": module["label"], "content": combined_value})
        fragments.append(f"{module['label']}:{combined_value}")

    prompt = "史诗氛围插画。" + "；".join(fragments) if fragments else "史诗氛围插画，留白待填充的世界。"
    return {
        "panels": panels,
        "ai_image_prompt": prompt,
        "ai_image_status": POSTER_STATUS_PENDING,
    }
