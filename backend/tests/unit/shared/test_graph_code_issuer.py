"""Tests for GraphCode value object and GraphCodeIssuer."""
from __future__ import annotations

import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

from app.domains.creation.shared.graph_code_issuer import (
    GraphCode,
    GraphCodeIssuer,
    StageCode,
)


# ---------- fixtures ----------


@pytest.fixture()
def tmp_db(tmp_path: Path) -> str:
    """Create a temporary SQLite database path for testing.
    
    Returns the database path as a string for GraphCodeIssuer.
    """
    db_path = tmp_path / "test_issuer.db"
    return str(db_path)


class TestGraphCodeValueObject:
    def test_code_property_format_ip_w(self):
        gc = GraphCode(ip_seq=1, stage=StageCode.WORKING, instance_no=1, version=1)
        assert gc.code == "IP0001-W1-v1"

    def test_code_property_format_ip_m(self):
        gc = GraphCode(ip_seq=1, stage=StageCode.MODULE, instance_no=1, version=1)
        assert gc.code == "IP0001-M1-v1"

    def test_code_property_format_with_s(self):
        gc = GraphCode(ip_seq=1, stage=StageCode.SECONDARY, instance_no=1, version=1, parent_m=1)
        assert gc.code == "IP0001-M1-S1-v1"

    def test_code_property_format_all_stages(self):
        expected = {
            StageCode.WORKING: "IP0001-W1-v1",
            StageCode.MODULE: "IP0001-M1-v1",
            StageCode.SECONDARY: "IP0001-M1-S1-v1",
            StageCode.TEMPLATE_DICE: "IP0001-TD1-v1",
            StageCode.TEMPLATE_CHARACTER: "IP0001-TC1-v1",
            StageCode.REPORT: "IP0001-R1-v1",
            StageCode.GRAPH: "IP0001-G1-v1",
        }
        for stage, code in expected.items():
            if stage == StageCode.SECONDARY:
                gc = GraphCode(ip_seq=1, stage=stage, instance_no=1, version=1, parent_m=1)
            else:
                gc = GraphCode(ip_seq=1, stage=stage, instance_no=1, version=1)
            assert gc.code == code, f"{stage}: expected {code}, got {gc.code}"

    def test_frozen_immutability(self):
        gc = GraphCode(ip_seq=1, stage=StageCode.WORKING, instance_no=1, version=1)
        with pytest.raises(AttributeError):
            gc.ip_seq = 999

    def test_eq_same_values(self):
        a = GraphCode(ip_seq=1, stage=StageCode.WORKING, instance_no=1, version=1)
        b = GraphCode(ip_seq=1, stage=StageCode.WORKING, instance_no=1, version=1)
        assert a == b

    def test_neq_different_version(self):
        a = GraphCode(ip_seq=1, stage=StageCode.WORKING, instance_no=1, version=1)
        b = GraphCode(ip_seq=1, stage=StageCode.WORKING, instance_no=1, version=2)
        assert a != b


class TestGraphCodeIssuer:
    def test_issue_and_bump(self, tmp_db: sqlite3.Connection):
        iss = GraphCodeIssuer(tmp_db)
        assert iss.new_ip("u1") == 1
        assert iss.next("u1", ip=1, stage="W") == "IP0001-W1-v1"
        assert iss.next("u1", ip=1, stage="W") == "IP0001-W1-v2"
        assert iss.next("u1", ip=1, stage="M") == "IP0001-M1-v1"
        assert iss.next("u1", ip=1, stage="S", parent_m=1) == "IP0001-M1-S1-v1"
        assert iss.next("u1", ip=1, stage="S", parent_m=1) == "IP0001-M1-S2-v1"

    def test_new_ip_increments_per_user(self, tmp_db: sqlite3.Connection):
        iss = GraphCodeIssuer(tmp_db)
        assert iss.new_ip("u1") == 1
        assert iss.new_ip("u2") == 1
        assert iss.new_ip("u1") == 2
        assert iss.new_ip("u2") == 2

    def test_m_instance_increments_within_ip(self, tmp_db: sqlite3.Connection):
        iss = GraphCodeIssuer(tmp_db)
        iss.new_ip("u1")
        assert iss.next("u1", ip=1, stage="M") == "IP0001-M1-v1"
        assert iss.next("u1", ip=1, stage="M") == "IP0001-M2-v1"
        assert iss.next("u1", ip=1, stage="M") == "IP0001-M3-v1"

    def test_version_never_overwrites(self, tmp_db: sqlite3.Connection):
        iss = GraphCodeIssuer(tmp_db)
        iss.new_ip("u1")
        assert iss.next("u1", ip=1, stage="W") == "IP0001-W1-v1"
        assert iss.next("u1", ip=1, stage="W") == "IP0001-W1-v2"
        assert iss.next("u1", ip=1, stage="W") == "IP0001-W1-v3"
        assert iss.next("u1", ip=1, stage="W") == "IP0001-W1-v4"

    def test_unique_constraint_prevents_duplicate_codes(self, tmp_db: str):
        iss = GraphCodeIssuer(tmp_db)
        iss.new_ip("u1")
        code1 = iss.next("u1", ip=1, stage="W")
        # Test UNIQUE constraint by trying to insert duplicate
        with pytest.raises(sqlite3.IntegrityError):
            conn = sqlite3.connect(tmp_db)
            conn.execute("INSERT INTO graph_codes (user_id, code) VALUES (?, ?)", ("u1", code1))
            conn.close()

    def test_invalid_stage_raises(self, tmp_db: sqlite3.Connection):
        iss = GraphCodeIssuer(tmp_db)
        iss.new_ip("u1")
        with pytest.raises(ValueError, match="Invalid stage code"):
            iss.next("u1", ip=1, stage="INVALID")

    def test_s_stage_requires_parent_m(self, tmp_db: sqlite3.Connection):
        iss = GraphCodeIssuer(tmp_db)
        iss.new_ip("u1")
        with pytest.raises(ValueError, match="parent_m is required"):
            iss.next("u1", ip=1, stage="S")


class TestConcurrentIssuance:
    def test_concurrent_issue_is_atomic(self, tmp_db: sqlite3.Connection):
        iss = GraphCodeIssuer(tmp_db)
        iss.new_ip("u1")
        codes = []
        lock = threading.Lock()
        def issue_code(_idx):
            return iss.next("u1", ip=1, stage="W")
        with ThreadPoolExecutor(max_workers=50) as pool:
            futures = [pool.submit(issue_code, i) for i in range(50)]
            for f in as_completed(futures):
                result = f.result()
                with lock:
                    codes.append(result)
        assert len(codes) == 50
        assert len(set(codes)) == 50, f"Duplicates found: {codes}"
        for c in codes:
            assert c.startswith("IP0001-W"), f"Bad format: {c}"

    def test_concurrent_new_ip_across_users(self, tmp_db: sqlite3.Connection):
        iss = GraphCodeIssuer(tmp_db)
        results = {}
        lock = threading.Lock()
        def create_ip(user):
            seq = iss.new_ip(user)
            with lock:
                results[user] = seq
        with ThreadPoolExecutor(max_workers=50) as pool:
            futures = [pool.submit(create_ip, f"user_{i}") for i in range(50)]
            for f in as_completed(futures):
                f.result()
        assert len(results) == 50
        assert all(v == 1 for v in results.values())


# ---------- D22③ B/C/O stage codes (task-8) ----------


class TestStageCodeBCO:
    """2026-09-28 D22 施工翻案：B/C/O 三字母加入（decision-log D22③）。"""

    def test_enum_members_exist(self):
        assert StageCode.BIBLE.value == "B"
        assert StageCode.CODEX.value == "C"
        assert StageCode.OUTLINE.value == "O"

    def test_bco_format_and_from_str_roundtrip(self):
        for name, letter in ((StageCode.BIBLE, "B"), (StageCode.CODEX, "C"), (StageCode.OUTLINE, "O")):
            gc = GraphCode(ip_seq=1, stage=name, instance_no=1, version=1)
            assert gc.code == f"IP0001-{letter}1-v1"
            assert StageCode.from_str(letter) is name

    def test_bco_issuer_new_instance_each_time(self, tmp_db: str):
        """B/C/O behave like M/TD/TC: new instance each time (W is the only version-bump stage)."""
        iss = GraphCodeIssuer(tmp_db)
        iss.new_ip("u1")
        assert iss.next("u1", ip=1, stage="B") == "IP0001-B1-v1"
        assert iss.next("u1", ip=1, stage="B") == "IP0001-B2-v1"
        assert iss.next("u1", ip=1, stage="C") == "IP0001-C1-v1"
        assert iss.next("u1", ip=1, stage="C") == "IP0001-C2-v1"
        assert iss.next("u1", ip=1, stage="O") == "IP0001-O1-v1"
        assert iss.next("u1", ip=1, stage="O") == "IP0001-O2-v1"

    def test_from_str_error_lists_bco(self):
        with pytest.raises(ValueError) as exc:
            StageCode.from_str("X")
        msg = str(exc.value)
        for letter in ("B", "C", "O", "W", "M", "TD", "TC", "R", "G"):
            assert letter in msg

    def test_db_legacy_stages_no_bco_conflict(self, tmp_db: str):
        """DB 存量回归：既有持久化 stage 值 ⊆ {W,M,S,TD,TC,R,G}，B/C/O 互不冲突。"""
        legacy = {"W", "M", "S", "TD", "TC", "R", "G"}
        assert not (legacy & {"B", "C", "O"}), "B/C/O must not collide with legacy persisted stages"
        iss = GraphCodeIssuer(tmp_db)
        iss.new_ip("u1")
        for stage in sorted(legacy - {"S"}):
            iss.next("u1", ip=1, stage=stage)
        # mixed issuance must not produce duplicates
        codes = set()
        for stage in ("B", "C", "O"):
            codes.add(iss.next("u1", ip=1, stage=stage))
        assert codes == {"IP0001-B1-v1", "IP0001-C1-v1", "IP0001-O1-v1"}
