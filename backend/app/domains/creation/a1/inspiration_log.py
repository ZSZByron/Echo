# -*- coding: utf-8 -*-
"""方向A一期埋点（施工单 §2.5：不扩 impulse_coords 闭集，只落日志）。

事件四类：option_pick / option_reroll / skip / stall（option_reroll 为
Metis 成本对账要求，超出施工单三信号源一句，计划留痕）。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

# backend/data/inspiration_log.jsonl（a1 -> creation -> domains -> app -> backend）
LOG_PATH: Path = Path(__file__).resolve().parents[4] / "data" / "inspiration_log.jsonl"


def _write(record: dict) -> None:
    """单条 JSON 追加写（一行一事件，utf-8）。"""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def emit_event(event: str, session, **fields) -> None:
    """JSON-lines append 到 data/inspiration_log.jsonl；任何异常静默吞掉。"""
    try:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": session.session_id,
            "event": event,
            **fields,
        }
        _write(record)
    except Exception:  # noqa: BLE001 — 埋点永不破坏主流程
        pass