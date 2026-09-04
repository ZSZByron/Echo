"""C2 contract: graphify 输出字段 schema + 节点引用治理（d: 可解析锚点 + confirmed 匹配）。

治理文档 §6 C2 五类负向用例（全部必须走 warning 降级，不得 crash）：
1. 伪造 anchor（引用不存在的锚点）
2. 表外 relation（不在 relation vocab 白名单）
3. 超白名单 DIM.tag
4. Phase1 越权 children 嵌套
5. 幻觉节点引用（引用 graph 中不存在的节点 id）

实现依赖 T1 graphify.py —— 未就绪前 xfail(strict) 占位。
"""
from __future__ import annotations

import pytest


def _assert_degraded_to_warning(result) -> None:  # noqa: ANN001 - placeholder
    raise AssertionError("C2 not implemented")


@pytest.mark.xfail(strict=True, reason="C2: graphify 输出校验尚未实现（T1）")
def test_c2_valid_sir_schema_passes() -> None:
    pytest.fail("C2 contract not implemented yet")


@pytest.mark.xfail(strict=True, reason="C2 负向1: 伪造 anchor 应降级 warning")
def test_c2_negative_forged_anchor_degrades_to_warning() -> None:
    pytest.fail("C2 negative case not implemented yet")


@pytest.mark.xfail(strict=True, reason="C2 负向2: 表外 relation 应降级 warning")
def test_c2_negative_offvocab_relation_degrades_to_warning() -> None:
    pytest.fail("C2 negative case not implemented yet")


@pytest.mark.xfail(strict=True, reason="C2 负向3: 超白名单 DIM.tag 应降级 warning")
def test_c2_negative_outofwhitelist_dim_tag_degrades_to_warning() -> None:
    pytest.fail("C2 negative case not implemented yet")


@pytest.mark.xfail(strict=True, reason="C2 负向4: Phase1 越权 children 嵌套应降级 warning")
def test_c2_negative_phase1_children_nesting_degrades_to_warning() -> None:
    pytest.fail("C2 negative case not implemented yet")


@pytest.mark.xfail(strict=True, reason="C2 负向5: 幻觉节点引用应降级 warning")
def test_c2_negative_hallucinated_node_ref_degrades_to_warning() -> None:
    pytest.fail("C2 negative case not implemented yet")
