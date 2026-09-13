"""J3 披露协议 / warning ledger — 2-A1-v0.5.1 §3 J3.

所有丢弃点的统一出口：assemble / finalize / dead_edges / graphify 四处
警告合并为一个结构化 ledger 落 ``file_rec["warnings"]``，get_file 暴露，
前端出角标。级联 C「截断链」的修复：警告链不再断裂（有的落库有的蒸发）。

设计纪律（治理文档钦定）：
  - additive：assemble_warnings / finalize_warnings / dead_edges 三个既有
    通道原样保留（既有消费方契约不动），ledger 是合并视图 + 唯一新增落点；
  - 分级防警告疲劳：丢失性=warn，转换性/开关性=info；
  - 纯确定性分类（前缀表），不引入 LLM。
"""
from __future__ import annotations

from typing import Any, TypedDict

LEVEL_WARN = "warn"
LEVEL_INFO = "info"

# ledger 条目来源（source 枚举，不允许新增无名来源——扩充需治理评审）
SOURCE_ASSEMBLE = "assemble"
SOURCE_FINALIZE = "finalize"
SOURCE_GRAPHIFY = "graphify"
SOURCE_DEAD_EDGES = "dead_edges"
SOURCE_UPLOAD = "upload"
SOURCE_ANSWERS = "answers"  # J4：答案写入层预算截断（fills/上传解析）


class LedgerEntry(TypedDict):
    """结构化警告条目（file_rec["warnings"] 元素）。"""

    source: str    # assemble | finalize | graphify | dead_edges | upload
    detail: str    # 人类可读描述（沿用既有 warning 文案，含前缀标记）
    count: int     # 受影响条数（默认 1；dead_edges 按 reason 聚合计数）
    level: str     # warn | info


# info 级前缀白名单：转换/跳过类，非内容丢失。
# 未列出的前缀一律 warn（保守：宁可多报丢失，不可漏报）。
_INFO_PREFIXES: tuple[str, ...] = (
    "[edges] 词表外关系已转为开放问题",   # 关系转为 open_question，内容仍在
    "children 挂载已禁用",                # 环境开关 A1_DEPTH_CHILDREN=0
    "锚点无已答条目节点",                 # 用户未答该字段，正常空态
)


def classify_level(detail: str) -> str:
    """Deterministic level grading by message prefix (J3 分级)."""
    return LEVEL_INFO if detail.startswith(_INFO_PREFIXES) else LEVEL_WARN


def entry(
    source: str, detail: str, *, count: int = 1, level: str | None = None
) -> LedgerEntry:
    """Mint one ledger entry; level auto-classified when omitted."""
    return {
        "source": source,
        "detail": detail,
        "count": count,
        "level": level or classify_level(detail),
    }


def from_strings(source: str, warnings: list[str]) -> list[LedgerEntry]:
    """Convert a legacy ``list[str]`` warning channel into ledger entries."""
    return [entry(source, w) for w in warnings]


def from_dead_edges(dead_edges: list[dict[str, Any]]) -> list[LedgerEntry]:
    """Aggregate dead-zone entries into per-reason ledger entries.

    死区本身已有结构化展示（审核台失效区）；ledger 条目只作聚合计数
    指针，保证角标总数诚实。
    """
    if not dead_edges:
        return []
    by_reason: dict[str, int] = {}
    for d in dead_edges:
        reason = str(d.get("reason") or "unknown")
        by_reason[reason] = by_reason.get(reason, 0) + 1
    return [
        entry(
            SOURCE_DEAD_EDGES,
            f"失效边入死区({reason}): {count} 条",
            count=count,
        )
        for reason, count in sorted(by_reason.items())
    ]
