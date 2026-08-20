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
