# -*- coding: utf-8 -*-
"""C6 契约测试：open_questions 结构化模型 round-trip + 状态机 + 迁移。"""
import pytest
from pydantic import ValidationError

from app.domains.creation.a1.open_questions import (
    AnsweredEvidence,
    OpenQuestion,
    OpenQuestionLog,
    from_bare_list,
)


def _sample() -> OpenQuestion:
    return OpenQuestion(
        id="oq-001",
        question="A 与 B 的关系是什么？",
        status="pending",
        answer="",
        created_at="2026-09-04T00:00:00",
        source_hint="concept_vocab",
    )


class TestOpenQuestion:
    def test_defaults(self):
        q = OpenQuestion(id="oq-1", question="q")
        assert q.status == "pending"
        assert q.answer == ""
        assert q.created_at == ""
        assert q.source_hint == ""

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            OpenQuestion(id="oq-1", question="q", status="done")


class TestRoundTrip:
    def test_dump_load_roundtrip_fieldwise(self):
        log = OpenQuestionLog(
            items=[
                _sample(),
                OpenQuestion(
                    id="oq-002",
                    question="第二问",
                    status="answered",
                    answer="用户回答内容",
                    created_at="2026-09-04T01:00:00",
                    source_hint="edge_violation",
                ),
            ]
        )
        records = log.dump()
        assert all(isinstance(r, dict) for r in records)
        restored = OpenQuestionLog.load(records)
        assert len(restored.items) == len(log.items)
        for a, b in zip(log.items, restored.items):
            assert a.id == b.id
            assert a.question == b.question
            assert a.status == b.status
            assert a.answer == b.answer
            assert a.created_at == b.created_at
            assert a.source_hint == b.source_hint


class TestStateMachine:
    def test_pending_asked_answered(self):
        log = OpenQuestionLog(items=[_sample()])
        q = log.next_pending()
        assert q is not None and q.id == "oq-001"
        assert log.mark_asked("oq-001")
        assert log.next_pending() is None  # asked 不再是 pending
        assert log.mark_answered("oq-001", "答案")
        assert log.items[0].status == "answered"
        assert log.items[0].answer == "答案"

    def test_pending_skipped(self):
        log = OpenQuestionLog(items=[_sample()])
        assert log.mark_skipped("oq-001")
        assert log.items[0].status == "skipped"
        assert log.next_pending() is None

    def test_answered_immutable_to_upsert(self):
        log = OpenQuestionLog(items=[_sample()])
        log.mark_answered("oq-001", "原答案")
        log.upsert(
            OpenQuestion(id="oq-001", question="改写", status="pending", answer="")
        )
        assert log.items[0].status == "answered"
        assert log.items[0].answer == "原答案"
        assert log.items[0].question == "A 与 B 的关系是什么？"

    def test_skipped_immutable_to_upsert(self):
        log = OpenQuestionLog(items=[_sample()])
        log.mark_skipped("oq-001")
        log.upsert(OpenQuestion(id="oq-001", question="改写", status="asked"))
        assert log.items[0].status == "skipped"

    def test_upsert_new_appends(self):
        log = OpenQuestionLog()
        log.upsert(_sample())
        assert len(log.items) == 1

    def test_next_pending_oldest_first(self):
        log = OpenQuestionLog(
            items=[
                OpenQuestion(id="a", question="q1"),
                OpenQuestion(id="b", question="q2"),
                OpenQuestion(id="c", question="q3"),
            ]
        )
        log.mark_answered("a", "x")
        assert log.next_pending().id == "b"


class TestFromBareList:
    def test_migration_all_pending(self):
        log = from_bare_list(["问题一", "问题二"])
        assert len(log.items) == 2
        assert all(q.status == "pending" for q in log.items)
        assert log.items[0].question == "问题一"
        assert log.items[0].id == "oq-001"
        assert log.items[1].id == "oq-002"

    def test_migration_empty(self):
        assert from_bare_list([]).items == []

    def test_migrated_roundtrips(self):
        log = from_bare_list(["q1", "q2"])
        restored = OpenQuestionLog.load(log.dump())
        assert [q.question for q in restored.items] == ["q1", "q2"]
        assert all(q.status == "pending" for q in restored.items)


class TestAnsweredEvidence:
    def test_export_only_answered(self):
        log = OpenQuestionLog(
            items=[
                OpenQuestion(id="a", question="q1"),
                OpenQuestion(id="b", question="q2", status="answered", answer="答2"),
                OpenQuestion(id="c", question="q3", status="skipped"),
            ]
        )
        ev = log.answered_evidence()
        assert len(ev) == 1
        assert isinstance(ev[0], AnsweredEvidence)
        assert ev[0].question_id == "b"
        assert ev[0].answer_text == "答2"
