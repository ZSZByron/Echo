"""A1 disk persistence (v0.5 A1) — sessions + file records as one JSON doc.

``_SESSIONS``/``_FILES`` in ``a1_routes`` are process memory; a backend
restart used to lose every knowledge graph built through the guided-chat
flow ("知识图谱白建了"). ``A1Store`` snapshots both dicts to a single JSON
file after each mutating endpoint and reloads them lazily on first access.

Design constraints:
- Single-user local app → one JSON file, tens of KB, no sharding/SQLite.
- Atomic write: ``path.tmp`` then ``os.replace`` (no torn reads).
- Corrupt/missing file → empty state + warning, never raise (same degrade
  stance as the rest of the A1 domain).
- Iron-law compatible: persistence only dumps in-memory state; it never
  deletes or overwrites version history inside a file record (``rec``
  ``graph_code``/``graph_json`` versions pass through untouched).
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from app.domains.creation.a1.guide_engine import A1Session

logger = logging.getLogger(__name__)

_STORE_VERSION = 1

#: J4 预算护栏：备份轮转保留份数（path → .bak1 → .bak2 → .bak3）。
_BACKUP_COUNT = 3


def _default_path() -> Path:
    # store.py = backend/app/domains/creation/a1/store.py -> parents[4] = backend/
    return Path(__file__).resolve().parents[4] / "data" / "a1_store.json"


class A1Store:
    """JSON-file persistence for A1 sessions + file records.

    Path resolution is LAZY (per call, not at construction): the
    ``A1_STORE_PATH`` env override is re-read on every load/save so that
    process-wide test isolation (see tests/conftest.py session fixture)
    covers even late background-thread writes that outlive per-test
    monkeypatches.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._explicit_path = path

    @property
    def path(self) -> Path:
        if self._explicit_path is not None:
            return self._explicit_path
        env_path = os.environ.get("A1_STORE_PATH")
        return Path(env_path) if env_path else _default_path()

    # -- load ------------------------------------------------------------

    def _backup_paths(self) -> list[Path]:
        """Backup slots, newest first: [.bak1, .bak2, ...]."""
        return [
            self.path.with_name(f"{self.path.name}.bak{i}")
            for i in range(1, _BACKUP_COUNT + 1)
        ]

    def load(self) -> tuple[dict[str, A1Session], dict[str, dict[str, Any]]]:
        """Read sessions/files from disk (J4: with backup recovery).

        Tries the main path first, then backups newest-first. Missing or
        corrupt candidates are skipped (warning logged, never raised);
        exhausting all candidates → empty dicts (same degrade stance).
        Returns ``(sessions, files)`` where sessions are reconstructed
        ``A1Session`` pydantic models and files are raw dicts.
        """
        for candidate in [self.path, *self._backup_paths()]:
            if not candidate.exists():
                continue
            try:
                raw = json.loads(candidate.read_text(encoding="utf-8"))
                sessions = {
                    sid: A1Session.model_validate(s)
                    for sid, s in raw.get("sessions", {}).items()
                }
                files: dict[str, dict[str, Any]] = raw.get("files", {})
                return sessions, files
            except Exception as exc:  # noqa: BLE001 — corrupt candidate: try next
                logger.warning(
                    "A1Store: corrupt store candidate %s, trying next backup "
                    "(%s: %s)",
                    candidate, type(exc).__name__, exc,
                )
        return {}, {}

    # -- save ------------------------------------------------------------

    def _rotate_backups(self) -> None:
        """J4: rotate backups before overwriting the main file.

        path → .bak1 → .bak2 → .bak3（更旧的删除）。Best-effort：备份失败
        绝不阻塞主写（OSError 静默跳过——主写的原子性优先）。
        """
        baks = self._backup_paths()
        try:
            if baks[-1].exists():
                baks[-1].unlink()
            for i in range(len(baks) - 1, 0, -1):
                if baks[i - 1].exists():
                    os.replace(baks[i - 1], baks[i])
            if self.path.exists():
                os.replace(self.path, baks[0])
        except OSError:
            return

    def save(
        self,
        sessions: dict[str, A1Session],
        files: dict[str, dict[str, Any]],
    ) -> None:
        """Atomically snapshot sessions + files to disk.

        Sessions are serialized via ``A1Session.model_dump()``; file records
        are plain dicts passed through as-is (``default=str`` guards any
        non-JSON value such as datetimes). Iron law: this is a pure dump of
        the in-memory state — nothing is filtered or rewritten.
        J4: existing file is rotated into the .bak chain before replace.
        """
        payload = {
            "version": _STORE_VERSION,
            "sessions": {
                sid: s.model_dump() for sid, s in sessions.items()
            },
            "files": files,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        self._rotate_backups()
        os.replace(tmp, self.path)
