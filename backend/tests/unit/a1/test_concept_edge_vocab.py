"""Test concept edge vocabulary compiled from v0.4 governance document §3.

TDD Approach:
1. These assertions were written BEFORE implementing concept_edge_vocab.py
2. They verify faithful transcription from the v0.4 document
3. Distribution validation evidence is written to .sisyphus/evidence/
"""

from collections import Counter

import pytest

from app.domains.creation.a1.concept_edge_vocab import (
    AXIS_SLOTS,
    EDGE_VOCAB,
    VOCAB_RELATION_NAMES,
    get_vocab_by_level,
    is_known_relation,
)


class TestEdgeVocabFaithfulTranscription:
    """Verify EDGE_VOCAB matches v0.4 §3 exactly."""

    def test_edge_count_matches_document(self):
        """§3 has exactly 16 edge entries (7★ + 5◆ + 4◇)."""
        assert len(EDGE_VOCAB) == 16, f"Expected 16 edges from v0.4 §3, got {len(EDGE_VOCAB)}"

    def test_level_distribution(self):
        """§3 distribution: 7 rule (★) + 5 semantic (◆) + 4 structure (◇)."""
        level_counter = Counter(edge.level for edge in EDGE_VOCAB)
        assert level_counter["rule"] == 7, f"Expected 7 rule edges, got {level_counter['rule']}"
        assert level_counter["semantic"] == 5, f"Expected 5 semantic edges, got {level_counter['semantic']}"
        assert level_counter["structure"] == 4, f"Expected 4 structure edges, got {level_counter['structure']}"

        # Write distribution evidence
        from pathlib import Path

        evidence_dir = Path(__file__).resolve().parents[4] / ".sisyphus" / "evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        with open(evidence_dir / "task-2-vocab-distribution.txt", "w", encoding="utf-8") as f:
            f.write("Edge Vocabulary Distribution (from v0.4 §3):\n")
            f.write(f"  Total edges: {len(EDGE_VOCAB)}\n")
            for level in ["rule", "semantic", "structure"]:
                f.write(f"  {level}: {level_counter[level]}\n")
            f.write(f"\nFull counter: {dict(level_counter)}\n")

    def test_each_edge_complete(self):
        """Every edge must have required fields (name, level, from_slots, to_slots)."""
        for edge in EDGE_VOCAB:
            assert edge.name, f"Edge missing name: {edge}"
            assert edge.level in {"rule", "semantic", "structure"}, f"Invalid level {edge.level} in {edge.name}"
            assert edge.from_slots, f"Edge {edge.name} has empty from_slots"
            assert edge.to_slots, f"Edge {edge.name} has empty to_slots"
            # At least one of hint or rule should be non-empty
            assert edge.hint or edge.rule, f"Edge {edge.name} has both empty hint and rule"

    def test_relation_names_unique(self):
        """No duplicate edge names (required for confirmed_edges key stability)."""
        names = [edge.name for edge in EDGE_VOCAB]
        name_counts = Counter(names)
        duplicates = {name: count for name, count in name_counts.items() if count > 1}

        # Write uniqueness evidence
        from pathlib import Path

        evidence_dir = Path(__file__).resolve().parents[4] / ".sisyphus" / "evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        with open(evidence_dir / "task-2-name-uniqueness.txt", "w", encoding="utf-8") as f:
            f.write(f"Total relation names: {len(names)}\n")
            f.write(f"Unique names: {len(set(names))}\n")
            if duplicates:
                f.write(f"\n❌ DUPLICATES FOUND:\n")
                for name, count in duplicates.items():
                    f.write(f"  {name}: {count} occurrences\n")
            else:
                f.write("\n✅ All relation names are unique\n")

        assert not duplicates, f"Duplicate edge names found: {duplicates}"

    def test_vocab_closed_set_enumeration(self):
        """VOCAB_RELATION_NAMES should enumerate all edge names exactly."""
        expected_names = frozenset(edge.name for edge in EDGE_VOCAB)
        assert VOCAB_RELATION_NAMES == expected_names, "VOCAB_RELATION_NAMES should match all edge names"

    def test_edge_names_use_v04_originals(self):
        """Edge internal names must use v0.4 original text (no LLM inventions)."""
        # Sample verification of key edges from §3
        edge_names = {edge.name for edge in EDGE_VOCAB}

        # Must-have ★ rule edges from v0.4 §3
        expected_rule_edges = {
            "DERIVES→骰子.概率分布",
            "DERIVES→骰子.骰子数量",
            "DERIVES→骰子.判定方式",
            "DERIVES→骰子.成功判定",
            "DERIVES→骰子.代价机制",
            "DERIVES→力量.交互拓扑",
            "COMPILES→Constraint(6维)",
        }
        assert expected_rule_edges.issubset(edge_names), f"Missing expected rule edges: {expected_rule_edges - edge_names}"

        # Must-have ◆ semantic edges from v0.4 §3
        expected_semantic_edges = {
            "DERIVES→视觉.建筑/材质",
            "DERIVES→文明.经济",
            "DERIVES→文明.阶层",
            "DERIVES→历史.主剧情4维",
            "DERIVES→IP.类型",
        }
        assert expected_semantic_edges.issubset(edge_names), f"Missing expected semantic edges: {expected_semantic_edges - edge_names}"


class TestAxisSlotsFaithfulTranscription:
    """Verify AXIS_SLOTS match v0.4 §2 exactly."""

    def test_axis_count(self):
        """§2 has exactly 8 AXIS slot definitions."""
        assert len(AXIS_SLOTS) == 8, f"Expected 8 AXIS slots from v0.4 §2, got {len(AXIS_SLOTS)}"

    def test_each_axis_has_binary_spectrum(self):
        """Every AXIS slot must have exactly 2 spectrum values (binary)."""
        for slot_path, spectrum_values in AXIS_SLOTS:
            assert len(spectrum_values) == 2, f"AXIS {slot_path} should have 2 binary values, got {len(spectrum_values)}: {spectrum_values}"
            assert slot_path, f"Empty slot path in AXIS_SLOTS"

    def test_known_axis_slots_present(self):
        """Key AXIS slots from v0.4 §2 must be present."""
        axis_paths = {slot_path for slot_path, _ in AXIS_SLOTS}

        # Required AXIS slots from v0.4 §2
        required_axes = {
            "世界本体.起源.起源力量",
            "世界本体.现实规则",
            "力量.溯源.来源底层",
            "力量.溯源.影响生灵比例",
            "力量.载体.层级拓扑",
            "力量.载体.权限映射",
            "力量.机制.交互拓扑",
            "力量.代价.平衡拓扑",
        }
        assert required_axes.issubset(axis_paths), f"Missing required AXIS slots: {required_axes - axis_paths}"


class TestHelperFunctions:
    """Test utility functions provided by the vocabulary module."""

    def test_get_vocab_by_level(self):
        """get_vocab_by_level should filter edges by level."""
        rule_edges = get_vocab_by_level("rule")
        assert len(rule_edges) == 7, f"Expected 7 rule edges, got {len(rule_edges)}"
        assert all(edge.level == "rule" for edge in rule_edges)

        semantic_edges = get_vocab_by_level("semantic")
        assert len(semantic_edges) == 5, f"Expected 5 semantic edges, got {len(semantic_edges)}"
        assert all(edge.level == "semantic" for edge in semantic_edges)

        structure_edges = get_vocab_by_level("structure")
        assert len(structure_edges) == 4, f"Expected 4 structure edges, got {len(structure_edges)}"
        assert all(edge.level == "structure" for edge in structure_edges)

    def test_is_known_relation(self):
        """is_known_relation should return True only for edges in vocab."""
        # Known relations
        assert is_known_relation("DERIVES→骰子.概率分布")
        assert is_known_relation("DERIVES→文明.经济")

        # Unknown relations
        assert not is_known_relation("FAKE→NOT_IN_VOCAB")
        assert not is_known_relation("")

    def test_static_module_zero_llm(self):
        """Verify this is a pure static constant module (no dynamic LLM generation)."""
        # All top-level exports should be constants or pure functions
        import app.domains.creation.a1.concept_edge_vocab as vocab_module

        # Check for problematic dynamic attributes
        assert not hasattr(vocab_module, "generate"), "Module should not have generate() function"
        assert not hasattr(vocab_module, "llm"), "Module should not have llm attribute"

        # EDGE_VOCAB and AXIS_SLOTS should be constants (same object on repeated access)
        assert vocab_module.EDGE_VOCAB is EDGE_VOCAB
        assert vocab_module.AXIS_SLOTS is AXIS_SLOTS
