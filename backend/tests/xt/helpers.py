"""Shared helpers for the xt (extreme-testing) suite.

Single source of truth for: FakeProvider (recording/replaying LLM stub),
canned graphify payload builder, twin-title sentinels (E3.1), dual-sentinel
document builder (E1.4).

Design doc: docs/plans/2026-09-09-a1-extreme-testing-design.md
"""
from __future__ import annotations

from typing import Any

from app.domains.creation.a1.concept_edge_vocab import VOCAB_RELATION_NAMES

#: Any relation name from the closed 26-item vocabulary works in canned
#: payloads; ``sorted()[0]`` is stable across vocab edits.
VALID_REL: str = sorted(VOCAB_RELATION_NAMES)[0]

#: A legal anchor that tests must also answer (depth mounting requires a
#: non-empty answer on the anchor field — see _assemble_depth_tree).
ANCHOR = "力量体系.acquire"


class FakeProvider:
    """Recording/replaying provider injected via monkeypatch.

    payload: a value returned on every call, or a callable
    ``fn(messages) -> value`` for per-call scripting (e.g. routing by
    system-prompt keyword across multi-stage pipelines).
    exc: raise on every call instead (provider-layer failure simulation).
    """

    def __init__(self, payload: Any = None, *, exc: Exception | None = None) -> None:
        self.payload = payload
        self.exc = exc
        self.calls: list[list[dict[str, str]]] = []

    async def chat_json(self, messages: list[dict[str, str]], **_: Any) -> Any:
        self.calls.append(messages)
        if self.exc is not None:
            raise self.exc
        if callable(self.payload):
            return self.payload(messages)
        return self.payload


def canned_graphify(
    entries: list[dict[str, Any]] | None = None,
    edges: list[dict[str, Any]] | None = None,
    module_summaries: dict[str, str] | None = None,
    constraint_fields: dict[str, str] | None = None,
    open_questions: list[Any] | None = None,
) -> dict[str, Any]:
    """Build a valid five-field graphify raw payload (D4: missing = empty)."""
    return {
        "module_summaries": module_summaries or {},
        "entries": entries or [],
        "edges": edges or [],
        "constraint_fields": constraint_fields or {},
        "open_questions": open_questions or [],
    }


# --- E3.1 twin-title sentinels (32-char collision) ---------------------------

PREFIX32 = "星" * 32
TWIN_T1 = PREFIX32 + "之上篇"
TWIN_T2 = PREFIX32 + "之下篇"


# --- E1.4 dual-sentinel document (truncation blind spot) ---------------------

def dual_sentinel_doc() -> str:
    """>24k doc: sentinel A (星陨大陆) inside the first 20000 chars,
    sentinel B (玄骸纹章) strictly beyond the truncation line."""
    head = (
        "开篇设定：星陨大陆的起源、力量体系与文明结构总述。"
        + "灵石矿脉争夺塑造了九州大陆的社会秩序与历史走向。" * 900
    )[:20000]
    tail = (
        "玄骸纹章与青铜荧光是这个世界独有的视觉符号。"
        + "视觉设计与骰子设定的全部细节都在文档后半部展开。" * 600
    )
    doc = head + tail
    # Contract of the builder itself: head is exactly the truncation window.
    assert len(doc) > 24000
    assert doc.index("星陨大陆") < 20000
    assert doc.index("玄骸纹章") >= 20000
    return doc
