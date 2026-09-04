# -*- coding: utf-8 -*-
"""C6/C7 数据面：open_questions 结构化模型。

治理文档 §6 C6：open_questions file 记录格式必须为结构化记录
`list[{id, question, status, answer}]`，**禁止退化为裸 list[str]**
（R3：链路只活在注释里 = tag= 死路复发）。

`from_bare_list` 仅用于旧数据迁移读取，运行时禁止裸 list[str]。
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

QuestionStatus = Literal["pending", "asked", "answered", "skipped"]


class OpenQuestion(BaseModel):
    """单条结构化问句记录（C6）。"""

    id: str
    question: str
    status: QuestionStatus = "pending"
    answer: str = ""
    created_at: str = ""
    source_hint: str = ""


class AnsweredEvidence(BaseModel):
    """转正证据模型（C7 数据面）：供后续 graphify prompt 注入。"""

    question_id: str
    answer_text: str
    answered_at: str


class OpenQuestionLog(BaseModel):
    """list 封装：结构化问句日志。"""

    items: list[OpenQuestion] = Field(default_factory=list)

    def upsert(self, q: OpenQuestion) -> None:
        """按 id 更新/插入；已有条目若为 answered/skipped 则保留不覆盖。"""
        for i, existing in enumerate(self.items):
            if existing.id == q.id:
                if existing.status in ("answered", "skipped"):
                    return
                self.items[i] = q
                return
        self.items.append(q)

    def next_pending(self) -> OpenQuestion | None:
        """最老优先返回第一条 pending；无则 None。"""
        for q in self.items:
            if q.status == "pending":
                return q
        return None

    def mark_asked(self, question_id: str) -> bool:
        for q in self.items:
            if q.id == question_id and q.status == "pending":
                q.status = "asked"
                return True
        return False

    def mark_answered(self, question_id: str, answer: str) -> bool:
        for q in self.items:
            if q.id == question_id and q.status in ("pending", "asked"):
                q.status = "answered"
                q.answer = answer
                return True
        return False

    def mark_skipped(self, question_id: str) -> bool:
        for q in self.items:
            if q.id == question_id and q.status in ("pending", "asked"):
                q.status = "skipped"
                return True
        return False

    def answered_evidence(self) -> list[AnsweredEvidence]:
        """导出全部已回答条目为转正证据（C7）。"""
        return [
            AnsweredEvidence(
                question_id=q.id, answer_text=q.answer, answered_at=q.created_at
            )
            for q in self.items
            if q.status == "answered"
        ]

    def dump(self) -> list[dict]:
        """序列化为结构化记录列表（file 持久化格式，C6）。"""
        return [q.model_dump() for q in self.items]

    @classmethod
    def load(cls, records: list[dict]) -> "OpenQuestionLog":
        """从结构化记录列表反序列化。"""
        return cls(items=[OpenQuestion.model_validate(r) for r in records])


def from_bare_list(items: list[str]) -> OpenQuestionLog:
    """旧数据兼容迁移：裸 list[str] → 全 pending 结构化记录。

    仅作迁移读取用；运行时禁止裸 list[str]（C6 铁律）。
    """
    return OpenQuestionLog(
        items=[
            OpenQuestion(id=f"oq-{i + 1:03d}", question=text, status="pending")
            for i, text in enumerate(items)
        ]
    )
