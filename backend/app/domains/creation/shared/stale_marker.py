"""Graph registry + stale marker — independent table, sqlite3 sync.

This module provides a lightweight registry for graph artifacts with
stale-marking semantics. It uses synchronous sqlite3 (same pattern as
graph_code_issuer.py) for simplicity and thread-safety with WAL mode.

Iron law: stale items are NEVER deleted or blocked from consumption.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


# ── Schema ───────────────────────────────────────────────────────────────────


_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS graph_registry (
  graph_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  scene_id TEXT,
  graph_code TEXT NOT NULL,
  ip_code TEXT NOT NULL,
  display_name TEXT DEFAULT '',
  stage TEXT NOT NULL,
  instance_no INTEGER NOT NULL,
  version INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'finalized',
  parent_graph_code TEXT,
  change_set TEXT,
  used_stale INTEGER DEFAULT 0,
  created_at TEXT NOT NULL,
  UNIQUE(user_id, graph_code)
);
"""


# ── Connection helper ────────────────────────────────────────────────────────


def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


# ── Extract ip_code from graph_code ──────────────────────────────────────────


def _extract_ip_code(graph_code: str) -> str:
    """Extract the IP prefix from a graph code.

    IP0001-W1-v1 -> IP0001
    IP0001-M1-S1-v2 -> IP0001
    """
    # Split on first '-' to get IP part
    return graph_code.split("-")[0]


# ── Public API ───────────────────────────────────────────────────────────────


def ensure_registry(db_path: str | Path) -> None:
    """Create the graph_registry table if it does not exist."""
    with _connect(db_path) as conn:
        conn.execute(_CREATE_TABLE)
        conn.commit()


def register_graph(
    db_path: str | Path,
    user_id: str,
    graph_code: str,
    stage: str,
    instance_no: int,
    version: int,
    scene_id: str | None = None,
    display_name: str = "",
    parent_graph_code: str | None = None,
) -> str:
    """Register a graph artifact and return its graph_id (UUID)."""
    graph_id = str(uuid.uuid4())
    ip_code = _extract_ip_code(graph_code)
    created_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')

    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO graph_registry "
            "(graph_id, user_id, scene_id, graph_code, ip_code, display_name, "
            "stage, instance_no, version, status, parent_graph_code, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'finalized', ?, ?)",
            (
                graph_id, user_id, scene_id, graph_code, ip_code,
                display_name, stage, instance_no, version,
                parent_graph_code, created_at,
            ),
        )
        conn.commit()

    return graph_id


def mark_downstream_stale(
    db_path: str | Path,
    old_code: str,
    change_set: dict,
) -> int:
    """Mark all non-stale children of *old_code* as stale.

    Returns the number of rows marked. Idempotent — already-stale rows
    are not updated and not counted.
    """
    change_json = json.dumps(change_set, ensure_ascii=False)

    with _connect(db_path) as conn:
        cursor = conn.execute(
            "UPDATE graph_registry "
            "SET status = 'stale', change_set = ? "
            "WHERE parent_graph_code = ? AND status != 'stale'",
            (change_json, old_code),
        )
        count = cursor.rowcount
        conn.commit()

    return count


def record_stale_usage(db_path: str | Path, graph_code: str) -> None:
    """Mark a stale graph as having been consumed.

    Sets used_stale=1. Does not block or delete — iron law.
    """
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE graph_registry SET used_stale = 1 WHERE graph_code = ?",
            (graph_code,),
        )
        conn.commit()


def list_user_graphs(db_path: str | Path, user_id: str) -> dict:
    """List all graphs for a user, grouped by IP code.

    Returns::
        {
            "ips": [
                {
                    "ip_code": "IP0001",
                    "display_name": "",
                    "artifacts": [
                        {
                            "graph_id": "...",
                            "graph_code": "IP0001-W1-v2",
                            "stage": "W",
                            "instance_no": 1,
                            "version": 2,
                            "status": "finalized",
                            "created_at": "...",
                            "parent_graph_code": null,
                            "used_stale": 0,
                        },
                        ...
                    ]
                }
            ]
        }
    Artifacts within each IP group are ordered by created_at DESC.
    """
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT graph_id, graph_code, ip_code, display_name, stage, "
            "instance_no, version, status, parent_graph_code, change_set, "
            "used_stale, created_at "
            "FROM graph_registry "
            "WHERE user_id = ? "
            "ORDER BY ip_code ASC, created_at DESC, graph_code DESC",
            (user_id,),
        ).fetchall()

    # Group by ip_code
    ip_groups: dict[str, dict] = {}
    for row in rows:
        (
            graph_id, graph_code, ip_code, display_name, stage,
            instance_no, version, status, parent_graph_code, change_set,
            used_stale, created_at,
        ) = row
        if ip_code not in ip_groups:
            ip_groups[ip_code] = {"ip_code": ip_code, "display_name": display_name, "artifacts": []}
        ip_groups[ip_code]["artifacts"].append({
            "graph_id": graph_id,
            "graph_code": graph_code,
            "stage": stage,
            "instance_no": instance_no,
            "version": version,
            "status": status,
            "created_at": created_at,
            "parent_graph_code": parent_graph_code,
            "change_set": change_set,
            "used_stale": used_stale,
        })

    # Sort IP groups by ip_code ascending, then collect
    sorted_ips = sorted(ip_groups.values(), key=lambda g: g["ip_code"])
    return {"ips": sorted_ips}
