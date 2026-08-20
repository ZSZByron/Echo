"""Four-layer atomic code issuer for graph entities.

Format: IP{序号}-{阶段路径}-v{版本}
Example: IP0142-M2-S1-v2

Rules:
- IP序号: 4位零填充 (IP0001), 每次new_ip递增, 废弃归档不回收
- 阶段码: 封闭枚举 W/M/S/TD/TC/R/G (不允许添加或修改)
- 实例号: 同范围最大+1 (S在其父M内递增, 其余IP内递增)
- 版本号: 同实例当前+1, 永不覆盖只追加

NOTE: This is a synchronous implementation. The project uses aiosqlite for async
operations, but the issuer uses synchronous sqlite3 for thread-safety with
WAL mode. Wrap in asyncio.to_thread() if async usage needed.
"""
from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


# ── Closed stage code enumeration ──────────────────────────────────────────
# DO NOT add or modify these values.


class StageCode(str, Enum):
    """Closed enumeration of stage codes.

    W=Working  M=Module  S=Secondary(次级)
    TD=Template Dice  TC=Template Character
    R=Report  G=Graph
    """
    WORKING = "W"
    MODULE = "M"
    SECONDARY = "S"
    TEMPLATE_DICE = "TD"
    TEMPLATE_CHARACTER = "TC"
    REPORT = "R"
    GRAPH = "G"

    @classmethod
    def from_str(cls, value: str) -> StageCode:
        """Parse a string to StageCode, raising ValueError on invalid input."""
        try:
            return cls(value)
        except ValueError:
            raise ValueError(
                f"Invalid stage code: {value!r}. "
                f"Must be one of: {', '.join(s.value for s in cls)}"
            ) from None


# ── Frozen value object ────────────────────────────────────────────────────


@dataclass(frozen=True)
class GraphCode:
    """Immutable value object for a four-layer graph code.

    Internal representation is decoupled from the string format.
    Use the code property to get the formatted string.
    """
    ip_seq: int
    stage: StageCode
    instance_no: int
    version: int
    parent_m: int | None = None

    @property
    def code(self) -> str:
        """Return the formatted code string.

        Format: IP{IP}-{STAGE_PATH}-v{VERSION}
        Examples: IP0001-W1-v1, IP0001-M1-S1-v2
        """
        ip_part = f"IP{self.ip_seq:04d}"

        if self.stage is StageCode.SECONDARY and self.parent_m is not None:
            stage_path = f"M{self.parent_m}-{self.stage.value}{self.instance_no}"
        else:
            stage_path = f"{self.stage.value}{self.instance_no}"

        return f"{ip_part}-{stage_path}-v{self.version}"


# ── Atomic issuer ───────────────────────────────────────────────────────────


_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS graph_codes (
    id         TEXT PRIMARY KEY,
    user_id    TEXT    NOT NULL,
    ip         INTEGER NOT NULL,
    stage      TEXT    NOT NULL,
    instance_no INTEGER NOT NULL,
    version    INTEGER NOT NULL,
    parent_m   INTEGER,
    code       TEXT    NOT NULL,
    UNIQUE(user_id, code)
);
"""


class GraphCodeIssuer:
    """Atomic four-layer code issuer backed by SQLite.

    Accepts a database path (str or Path) and creates fresh connections
    for each operation with BEGIN IMMEDIATE transactions for thread-safety.
    Uses SELECT MAX ... INSERT inside single-writer transactions
    with UNIQUE(user_id, code) as the safety net for retries.

    Thread-safety: each call creates its own connection with IMMEDIATE transaction.
    SQLite file locking serializes writes automatically.
    """

    _MAX_RETRIES = 3  # Reduced for connection-per-operation pattern

    def __init__(self, db_path: str | Path) -> None:
        """Initialize issuer with database path.
        
        Args:
            db_path: Path to SQLite database file (will be created if doesn't exist)
        """
        self._db_path = str(db_path)
        # Initialize database schema on first connection
        self._ensure_schema()

    # ── initialization ─────────────────────────────────────────────────────

    def _ensure_schema(self) -> None:
        """Ensure database schema exists on initialization."""
        with self._get_connection() as conn:
            conn.execute(_CREATE_TABLE)

    def _get_connection(self) -> sqlite3.Connection:
        """Create a fresh database connection with proper settings.
        
        Each operation gets its own connection for thread safety.
        """
        conn = sqlite3.connect(self._db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    # ── public API ──────────────────────────────────────────────────────────

    def new_ip(self, user_id: str) -> int:
        """Allocate the next IP sequence number for *user_id*.

        Returns the 1-based sequence number (e.g. 1, 2, 3 …).
        """
        for attempt in range(self._MAX_RETRIES):
            try:
                with self._get_connection() as conn:
                    # Begin immediate transaction for write
                    conn.execute("BEGIN IMMEDIATE")
                    
                    cur = conn.execute(
                        "SELECT MAX(ip) FROM graph_codes WHERE user_id = ?",
                        (user_id,),
                    )
                    row = cur.fetchone()
                    cur.close()
                    next_ip = (row[0] if row[0] is not None else 0) + 1

                    conn.execute(
                        "INSERT INTO graph_codes (id, user_id, ip, stage, instance_no, version, code) "
                        "VALUES (?, ?, ?, 'W', 0, 0, ?)",
                        (str(uuid.uuid4()), user_id, next_ip, f"IP{next_ip:04d}-RESERVED-v0"),
                    )
                    conn.commit()
                    return next_ip
            except sqlite3.IntegrityError:
                if attempt == self._MAX_RETRIES - 1:
                    raise
                continue

        raise RuntimeError("unreachable")  # pragma: no cover

    def next(
        self,
        user_id: str,
        ip: int,
        stage: str,
        parent_m: int | None = None,
    ) -> str:
        """Issue the next code string.

        For **non-S stages** (W/M/TD/TC/R/G):
          - instance_no = max(instance_no for same user/ip/stage) + 1
          - version is always 1 for a new instance

        For **S stage**:
          - parent_m is required
          - instance_no = max(instance_no for same user/ip/stage/parent_m) + 1
          - version is always 1 for a new instance

        Version bump: call `next` with identical (user_id, ip, stage[, parent_m]).
        The issuer detects that the same instance already exists and increments
        version instead of creating a new instance.

        Returns the full code string (e.g. `IP0001-W1-v1`).
        """
        sc = StageCode.from_str(stage)

        if sc is StageCode.SECONDARY and parent_m is None:
            raise ValueError("parent_m is required when stage='S'")

        for attempt in range(self._MAX_RETRIES):
            try:
                with self._get_connection() as conn:
                    return self._issue(user_id, ip, sc, parent_m, conn, attempt)
            except sqlite3.IntegrityError:
                if attempt == self._MAX_RETRIES - 1:
                    raise
                continue

        raise RuntimeError("unreachable")  # pragma: no cover

    # ── internals ───────────────────────────────────────────────────────────

    def _issue(
        self,
        user_id: str,
        ip: int,
        stage: StageCode,
        parent_m: int | None,
        conn: sqlite3.Connection,
        attempt: int = 0,
    ) -> str:
        """Single attempt: compute next (instance, version) and INSERT.

        On first attempt (attempt=0), try to bump version of existing instance.
        On retry (attempt>0), create new instance.
        
        Args:
            conn: Database connection to use for this operation
        """
        # Begin immediate transaction for write operation
        conn.execute("BEGIN IMMEDIATE")
        
        if stage is StageCode.SECONDARY and parent_m is not None:
            # S: scope = (user_id, ip, stage, parent_m)
            cur = conn.execute(
                "SELECT MAX(instance_no), MAX(version) "
                "FROM graph_codes "
                "WHERE user_id=? AND ip=? AND stage=? AND parent_m=?",
                (user_id, ip, stage.value, parent_m),
            )
        else:
            # Non-S: scope = (user_id, ip, stage)
            cur = conn.execute(
                "SELECT MAX(instance_no), MAX(version) "
                "FROM graph_codes "
                "WHERE user_id=? AND ip=? AND stage=? AND parent_m IS NULL",
                (user_id, ip, stage.value),
            )
        row = cur.fetchone()
        cur.close()

        max_inst, max_ver = row  # type: ignore[misc]

        if max_inst is None or max_inst == 0:
            # First code in this scope → instance=1, version=1
            instance_no = 1
            version = 1
        elif stage is StageCode.WORKING and attempt == 0:
            # W stage: try to bump version of existing instance on first attempt
            instance_no = max_inst
            version = (max_ver if max_ver is not None else 0) + 1
        else:
            # All other stages (and W retries): create new instance
            instance_no = max_inst + 1
            version = 1

        gc = GraphCode(
            ip_seq=ip,
            stage=stage,
            instance_no=instance_no,
            version=version,
            parent_m=parent_m,
        )
        code = gc.code

        conn.execute(
            "INSERT INTO graph_codes (id, user_id, ip, stage, instance_no, version, parent_m, code) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, ip, stage.value, instance_no, version, parent_m, code),
        )
        
        conn.commit()

        return code
