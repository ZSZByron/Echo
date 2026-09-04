"""C7 contract: 回答驱动转正映射（e2e 闭环）。

治理文档 §6 C7：访谈器追问 + 记录 answer → 下次对话读取 answered 条目
注入 graphify prompt 作为转正证据 → 装配层产出 confirmed=true 节点 +
rationale 引用用户回答。端到端验证三处必须同时可见。

依赖 graphify.py（T1）+ 装配层（T6/T7/T8）—— 未就绪前 xfail(strict) 占位。
数据面（OpenQuestionLog.answered_evidence）已由 T3 提供，其单测归 C6/T4。
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(strict=True, reason="C7: 回答驱动转正 e2e 尚未实现")
async def test_c7_answered_question_becomes_confirmed_node_e2e() -> None:
    pytest.fail("C7 e2e not implemented yet")


@pytest.mark.xfail(strict=True, reason="C7: graphify prompt 必须注入 answered 证据")
async def test_c7_answered_evidence_injected_into_graphify_prompt() -> None:
    pytest.fail("C7 prompt injection not implemented yet")


@pytest.mark.xfail(strict=True, reason="C7: confirmed 节点 rationale 必须引用用户回答")
async def test_c7_confirmed_node_rationale_cites_user_answer() -> None:
    pytest.fail("C7 rationale citation not implemented yet")
