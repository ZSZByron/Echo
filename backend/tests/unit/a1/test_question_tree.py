"""Tests for the A1 question tree (static structure + state machine)."""
from app.domains.creation.seed.a1_question_tree import (
    SECTIONS,
    first_section,
    get_section,
    next_section,
    section_ids,
)


class TestQuestionTree:
    def test_has_10_sections(self):
        assert len(SECTIONS) == 10

    def test_first_section_is_worldview(self):
        assert first_section()["id"] == "世界观"

    def test_next_section_walks_in_order(self):
        ids = []
        cur = None
        while True:
            nxt = next_section(cur)
            if nxt is None:
                break
            ids.append(nxt["id"])
            cur = nxt["id"]
        assert ids == section_ids()

    def test_next_section_after_last_returns_none(self):
        assert next_section("核心冲突") is None

    def test_get_section_unknown_returns_none(self):
        assert get_section("不存在") is None

    def test_each_section_has_question_and_hint(self):
        for s in SECTIONS:
            assert s["question"]
            assert s["hint"]
            assert s["label"]
