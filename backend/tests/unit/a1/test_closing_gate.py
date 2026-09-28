"""Contract tests for closing_gate — 收尾双条件 + 确定性图谱识别 (D21 Task 6).

Pure-function contracts, zero LLM:

1. Dual-condition matrix (spec v1.3 §5.4):
   - 配方问题问完 + pending_proposals 清零  → is_preset_phase_complete True
   - 配方问题问完 + pending 未清零        → False
   - 未问完（walk 仍在 asking）           → False regardless of pending
2. Auto fills boundary: fields written by auto-fill (FIELD_SOURCE path,
   e.g. llm_fill / dice_rec / upload_prefill metadata) NEVER live in
   pending_proposals — when only auto fills exist and pending is empty,
   closing MUST trigger.
3. build_output_preview: deterministic pre-output graph inventory —
   module coverage (module_done_ratio) + gap list + version chain +
   stale dual-signal (registry status OR higher same-stage instance/
   version). Zero scoring/weights — factual assembly only.
4. Determinism: same fixture called twice → identical result.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from app.domains.creation.a1.closing_gate import (
    CONSUMER_ARTIFACTS,
    build_output_preview,
    closing_status,
    is_preset_phase_complete,
)
from app.domains.creation.a1.guide_engine import (
    A1Session,
    PHASE_ASKING,
    PHASE_COMPLETED,
)
from app.domains.creation.shared import stale_marker


# ── fixtures ─────────────────────────────────────────────────────────────────


def _session(
    *, phase: str = PHASE_ASKING, pending: int = 0, answers: int = 0
) -> A1Session:
    s = A1Session(session_id="s1", user_id="u1", phase=phase)
    # Seed a few truthy answers (any module: use the first recipe module's
    # first subfield deterministically via the walk default position).
    from app.domains.creation.seed.a1_question_tree import first_module

    mid = first_module()["id"]
    sid = first_module()["fields"][0]["id"]
    for i in range(answers):
        s.answers[f"{mid}.{sid}"] = f"回答{i}"
    for i in range(pending):
        s.pending_proposals[f"{mid}.{sid}:key{i}"] = {
            "proposal": {"module": mid, "subfield": sid, "old": "旧", "new": "新"},
            "options": ["replace", "drop"],
        }
    return s


def _registry(tmp_path: Path) -> str:
    db = str(tmp_path / "registry.db")
    stale_marker.ensure_registry(db)
    return db


# ── 1. dual-condition matrix ─────────────────────────────────────────────────


class TestDualConditionMatrix:
    def test_asked_complete_and_pending_empty_is_true(self):
        s = _session(phase=PHASE_COMPLETED, pending=0)
        assert is_preset_phase_complete(s) is True

    def test_asked_complete_but_pending_not_cleared_is_false(self):
        s = _session(phase=PHASE_COMPLETED, pending=1)
        assert is_preset_phase_complete(s) is False

    def test_not_asked_complete_is_false_even_with_empty_pending(self):
        s = _session(phase=PHASE_ASKING, pending=0)
        assert is_preset_phase_complete(s) is False

    def test_status_reports_each_condition(self):
        s = _session(phase=PHASE_COMPLETED, pending=2)
        st = closing_status(s)
        assert st["questions_complete"] is True
        assert st["pending_count"] == 2
        assert st["complete"] is False


# ── 2. auto fills boundary ───────────────────────────────────────────────────


class TestAutoFillsBoundary:
    def test_auto_fills_only_never_blocks_closing(self):
        """Auto-filled fields (FIELD_SOURCE llm_fill/dice_rec) bypass
        pending_proposals — they must NOT count as pending."""
        s = _session(phase=PHASE_COMPLETED, pending=0)
        # simulate auto fills recorded in answers + field_sources metadata
        s.answers["world.time_span"] = "帝国历300年"
        s.field_sources["world.time_span"] = "llm_fill"
        s.answers["world.geography"] = "大陆西部"
        s.field_sources["world.geography"] = "dice_rec"
        assert len(s.pending_proposals) == 0
        assert is_preset_phase_complete(s) is True

    def test_conflict_proposals_are_pending_and_block(self):
        """Only intercepted conflict proposals (write-guard) are pending."""
        s = _session(phase=PHASE_COMPLETED, pending=0)
        s.answers["world.time_span"] = "旧设定"
        s.field_sources["world.time_span"] = "human"
        s.pending_proposals["world.time_span:abc12345"] = {
            "proposal": {
                "module": "world", "subfield": "time_span",
                "old": "旧设定", "new": "新设定",
            },
            "options": ["replace", "merge", "drop"],
        }
        assert is_preset_phase_complete(s) is False


# ── 3. build_output_preview ──────────────────────────────────────────────────


class TestBuildOutputPreview:
    def test_missing_file_reports_exists_false(self, tmp_path):
        out = build_output_preview(
            "missing-file", sessions={}, files={}, registry_db=_registry(tmp_path)
        )
        assert out["exists"] is False
        assert out["file_id"] == "missing-file"
        assert out["stale_warning"] is None

    def test_module_coverage_uses_recipe_and_ratio(self, tmp_path):
        from app.domains.creation.seed.a1_question_tree import (
            first_module, module_done_ratio,
        )

        mid = first_module()["id"]
        sid = first_module()["fields"][0]["id"]
        s = _session(phase=PHASE_ASKING)
        s.answers[f"{mid}.{sid}"] = "真话"
        files = {"f1": {"session_id": "s1", "status": "draft"}}
        out = build_output_preview(
            "f1", sessions={"s1": s}, files=files,
            registry_db=_registry(tmp_path),
        )
        assert out["exists"] is True
        cov = {c["module_id"]: c for c in out["module_coverage"]}
        assert cov[mid]["done_ratio"] == module_done_ratio(mid, s.answers)
        assert cov[mid]["done_ratio"] > 0.0
        # gap disclosure: first_module has other unfilled subfields
        assert any(g["module_id"] == mid for g in out["gaps"])

    def test_stale_registry_signal_returns_warning(self, tmp_path):
        db = _registry(tmp_path)
        stale_marker.register_graph(
            db, "u1", "IP0001-M1-v1", stage="M", instance_no=1, version=1
        )
        # child artifact of a superseded upstream becomes stale (signal 1)
        stale_marker.register_graph(
            db, "u1", "IP0001-M2-v1", stage="M", instance_no=2, version=1,
            parent_graph_code="IP0001-M1-v1",
        )
        assert stale_marker.mark_downstream_stale(
            db, "IP0001-M1-v1", {"reason": "refinalize"}
        ) == 1
        s = _session(phase=PHASE_COMPLETED)
        out = build_output_preview(
            "f1", sessions={"s1": s},
            files={"f1": {"session_id": "s1", "status": "finalized",
                          "graph_code": "IP0001-M2-v1",
                          "ip": 1, "graph_json": {}}},
            registry_db=db,
        )
        assert out["stale"] is True
        assert out["stale_warning"]
        assert out["version_chain"]["graph_code"] == "IP0001-M2-v1"
        assert out["version_chain"]["version"] == 1

    def test_stale_superseded_signal_higher_same_stage(self, tmp_path):
        """Signal 2: 同 IP 同 stage 存在更高 (instance, version) 产物
        — covers 'W1 未注册但 W2 已注册' semantics (a1_routes._graph_is_stale)."""
        db = _registry(tmp_path)
        stale_marker.register_graph(
            db, "u1", "IP0001-W2-v1", stage="W", instance_no=2, version=1
        )
        s = _session(phase=PHASE_COMPLETED)
        out = build_output_preview(
            "f1", sessions={"s1": s},
            files={"f1": {"session_id": "s1", "status": "finalized",
                          "graph_code": "IP0001-W1-v1", "ip": 1}},
            registry_db=db,
        )
        assert out["stale"] is True
        assert out["stale_warning"]
        assert out["version_chain"]["superseded_by"] == "IP0001-W2-v1"

    def test_fresh_graph_no_stale_warning(self, tmp_path):
        db = _registry(tmp_path)
        stale_marker.register_graph(
            db, "u1", "IP0001-W1-v1", stage="W", instance_no=1, version=1
        )
        s = _session(phase=PHASE_COMPLETED)
        out = build_output_preview(
            "f1", sessions={"s1": s},
            files={"f1": {"session_id": "s1", "status": "finalized",
                          "graph_code": "IP0001-W1-v1", "ip": 1}},
            registry_db=db,
        )
        assert out["stale"] is False
        assert out["stale_warning"] is None

    def test_consumer_list_contains_d22_trio_and_trpg(self, tmp_path):
        s = _session(phase=PHASE_COMPLETED)
        out = build_output_preview(
            "f1", sessions={"s1": s},
            files={"f1": {"session_id": "s1", "status": "draft"}},
            registry_db=_registry(tmp_path),
        )
        ids = [c["id"] for c in out["consumers"]]
        # D22 三件 (ordering input for T10/T18) + 跑团件
        assert ids[:3] == ["world_bible", "character_codex", "story_outline"]
        assert "dice_projection" in ids
        assert "character_projection" in ids
        assert CONSUMER_ARTIFACTS[0]["kind"] == "d22"

    def test_determinism_same_fixture_twice_equal(self, tmp_path):
        db = _registry(tmp_path)
        stale_marker.register_graph(
            db, "u1", "IP0001-W1-v1", stage="W", instance_no=1, version=1
        )
        s = _session(phase=PHASE_COMPLETED, pending=1)
        files = {"f1": {"session_id": "s1", "status": "finalized",
                        "graph_code": "IP0001-W1-v1", "ip": 1}}
        a = build_output_preview(
            "f1", sessions={"s1": s}, files=files, registry_db=db
        )
        b = build_output_preview(
            "f1", sessions={"s1": s}, files=files, registry_db=db
        )
        assert a == b


# ── 4. robustness / resolution paths ─────────────────────────────────────────


class TestRobustnessPaths:
    def test_malformed_graph_code_never_stale_never_crash(self, tmp_path):
        db = _registry(tmp_path)
        s = _session(phase=PHASE_COMPLETED)
        for bad in ("IP0001-W1", "IP0001-W1-vX", "solo", ""):
            out = build_output_preview(
                "f1", sessions={"s1": s},
                files={"f1": {"session_id": "s1", "status": "finalized",
                              "graph_code": bad, "ip": 1}},
                registry_db=db,
            )
            assert out["stale"] is False
            assert out["stale_warning"] is None

    def test_registry_query_failure_degrades_to_not_stale(self, tmp_path):
        """查询失败按未过期处理（不阻断——a1_routes 同口径）。"""
        s = _session(phase=PHASE_COMPLETED)
        out = build_output_preview(
            "f1", sessions={"s1": s},
            files={"f1": {"session_id": "s1", "status": "finalized",
                          "graph_code": "IP0001-W1-v1", "ip": 1}},
            registry_db=str(tmp_path / "no" / "such" / "dir" / "x.db"),
        )
        assert out["stale"] is False

    def test_unknown_recipe_module_skipped_in_gaps(self, tmp_path):
        s = _session(phase=PHASE_COMPLETED)
        s.recipe_modules = ["mystery_mod", s.current_module]
        out = build_output_preview(
            "f1", sessions={"s1": s},
            files={"f1": {"session_id": "s1", "status": "draft"}},
            registry_db=_registry(tmp_path),
        )
        assert all(g["module_id"] != "mystery_mod" for g in out["gaps"])
        assert all(
            c["module_id"] != "mystery_mod" for c in out["module_coverage"]
        )

    def test_file_record_without_session_uses_fallback(self, tmp_path):
        out = build_output_preview(
            "f1", sessions={},
            files={"f1": {"session_id": "ghost", "status": "draft"}},
            registry_db=_registry(tmp_path),
        )
        assert out["exists"] is True
        assert out["closing"]["complete"] is False

    def test_default_storage_resolution_via_a1_routes(self, tmp_path):
        """sessions/files 缺省 → a1_routes A1Store 支撑的存储视图。"""
        out = build_output_preview("never-exists", registry_db=_registry(tmp_path))
        assert out["exists"] is False

    def test_listing_artifact_with_bad_parse_is_skipped(self, tmp_path):
        """同 stage 候选产物解析失败 → 跳过不崩溃。"""
        from app.domains.creation.a1.closing_gate import _superseded_exists

        listing = {"ips": [{"ip_code": "IP0001", "artifacts": [
            {"graph_code": "IP0001-W1-vX", "stage": "W", "version": "x"},
            {"graph_code": "IP0001-Z9-v1", "stage": "Z", "version": 1},
        ]}]}
        assert _superseded_exists(listing, "IP0001-W1-v1") is None
        assert _superseded_exists(listing, "bad-code") is None
