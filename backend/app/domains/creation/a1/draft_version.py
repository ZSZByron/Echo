# -*- coding: utf-8 -*-
"""会话态草稿版本递进（α 体系）——T15 / D15③ α-β 语义延伸到输出层。

**硬红线：α 绝不进 graph_codes 表或任何持久层。**

本模块是**纯内存**的版本序标记：graph_code_issuer 的整型 vN 发号机制
零改动，finalize 落库仍只发整型 vN。α 标记只活在会话内存（A1Session
的 ``draft_alpha`` 字段，default 零迁移），产出物侧经文档模型的可选
``version_label`` 字段可见（D21⑬）。

版本序（D15③）::

    v1 会话定稿基线
      → 对齐循环草稿 α0.1
      → α0.11 / α0.12 …（循环内迭代）
      → 收口 finalize → 下一整型 vN+1（issuer 现行链）
      → 再轮草稿 α0.2 → α0.21 / α0.22 …（0.2 系）

状态是一个普通 ``dict[str, int]``（``{"baseline", "round", "step"}``），
无类实例、无文件、无 DB——从结构上杜绝落库可能。
"""
from __future__ import annotations

__all__ = [
    "new_draft_state",
    "start_draft_round",
    "next_draft",
    "draft_label",
    "finalize_version",
]

#: 草稿轮内步号 1 → 标记 ``α0.{round}``；步号 k>1 → ``α0.{round}{k-1}``。


def new_draft_state(baseline: int = 0) -> dict[str, int]:
    """新建纯内存草稿版本状态。

    Args:
        baseline: 当前会话定稿基线的整型版本号（v1 会话 → 1；
            未定稿新会话 → 0）。
    """
    return {"baseline": baseline, "round": 0, "step": 0}


def _label(state: dict[str, int]) -> str:
    r, s = state["round"], state["step"]
    return f"α0.{r}" if s <= 1 else f"α0.{r}{s - 1}"


def start_draft_round(state: dict[str, int]) -> str:
    """开启新一轮草稿（对齐循环首草稿）→ ``α0.{round}``。"""
    state["round"] += 1
    state["step"] = 1
    return _label(state)


def next_draft(state: dict[str, int]) -> str:
    """当前对齐循环内的后续草稿 → ``α0.{round}{n}``（α0.11/α0.12…）。"""
    state["step"] += 1
    return _label(state)


def draft_label(state: dict[str, int]) -> str | None:
    """当前 α 标记；草稿期返回形如 ``α0.11``，收口后/未开轮返回 None。

    步号 0 = 不在草稿期（``round`` 计数跨收口保留，供 0.2 系递进）。
    """
    if state["round"] == 0 or state["step"] == 0:
        return None
    return _label(state)


def finalize_version(state: dict[str, int]) -> int:
    """收口：推进到下一整型版本并复位草稿态。

    返回 ``baseline + 1``（与 graph_code_issuer 整型自增链一致的序关系；
    本函数只做内存记账，**不发生任何码**——落库发码仍由 issuer 现行
    ``next()`` 完成，本模块对其零调用零改动）。

    注意：``round`` 计数不复位（第二轮草稿须落 0.2 系 α0.21/α0.22），
    只清步号。
    """
    state["baseline"] += 1
    state["step"] = 0
    return state["baseline"]
