"""A1 IP poster — epic-atmosphere image prompt + overlay panel data."""
from __future__ import annotations

from typing import Any

from app.domains.creation.a1.guide_engine import A1Session
from app.domains.creation.seed.a1_question_tree import get_section

POSTER_STATUS_PENDING = "pending"


def build_poster(session: A1Session) -> dict[str, Any]:
    """Build poster data from the session's structured file.

    Returns {panels, ai_image_prompt, ai_image_status}:
    - panels: overlay panels for non-empty sections
    - ai_image_prompt: epic atmosphere prompt stitched from section values
    - ai_image_status: always "pending" (image generation is out of scope
      for this batch)
    """
    panels: list[dict[str, str]] = []
    fragments: list[str] = []
    for section_id, value in session.answers.items():
        if not value:
            continue
        label = get_section(section_id)["label"] if get_section(section_id) else section_id
        panels.append({"section": label, "value": value})
        fragments.append(f"{label}:{value}")

    prompt = "史诗氛围插画。" + "；".join(fragments) if fragments else "史诗氛围插画，留白待填充的世界。"
    return {
        "panels": panels,
        "ai_image_prompt": prompt,
        "ai_image_status": POSTER_STATUS_PENDING,
    }
