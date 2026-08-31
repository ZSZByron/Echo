"""A1 interaction audit log — JSONL event trail per conversation turn.

Events (one JSON object per line) appended to data/a1_interaction_log.jsonl:
    user_message  — raw user input received by /api/a1/chat
    llm_raw       — raw LLM response before parsing (truncated)
    llm_parsed    — validated fills / innovation verdict after parsing
    api_response  — what the API returned to the frontend (reply/next/phase)
    error         — interviewer failure (degradation reason)

Usage: tail -f backend/data/a1_interaction_log.jsonl
Each line: {"ts", "session_id", "event", ...payload}
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from app.config.paths import DATA_DIR

_LOG_PATH = DATA_DIR / "a1_interaction_log.jsonl"
_LOCK = Lock()

_MAX_RAW_CHARS = 2000


def log_event(session_id: str, event: str, **payload: object) -> None:
    """Append one JSONL event. Never raises — logging must not break chat."""
    try:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "session_id": session_id,
            "event": event,
            **payload,
        }
        line = json.dumps(record, ensure_ascii=False, default=str)
        with _LOCK:
            _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with _LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:  # noqa: BLE001
        pass


def truncate(text: object, limit: int = _MAX_RAW_CHARS) -> str:
    s = str(text)
    return s if len(s) <= limit else s[:limit] + f"...[truncated {len(s) - limit} chars]"
