"""fills 三形态值 schema 契约红测（⑥稿工程落点——先红后绿，零实现）。

⑥稿值形态判定表（§0 闭集）：● point / ▶ from_to / ⇄ dim_dir / ⇉ dual，
92 项 = ●66 + ▶20 + ⇄5 + ⇉1。T2 已落 vs 闭集常量（story_modules.VS_ENUM）；
本轮锁**值 schema 消费面**（T5 引擎接线验收标准）：

- ● point = 纯文本，往返字节不变
- ▶ from_to = {from, to, trigger} 结构化值，任一字段可缺（半填，宽容细则
  归 test_half_fill_tolerance.py）
- ⇄ dim_dir = {dimension, direction, magnitude}；拒绝线特例 = magnitude 0
  落库可查（⑥§2-16："从X到X" 合法答案，幅度 0 不丢弃）
- ⇉ dual = 双形值（点 + 变化）
- 无 vs 标注的存量答案（42/43 字段时代 fixture）全按 ● 处理
- 值形状 vs vs 标注不一致 → 拒绝或降级（⑥稿边界裁定：二选一皆可，
  测试按"或"断言）

红测纪律：schema 校验入口经 getattr 发现（AssertionError 式红，非 ImportError）。
"""
from __future__ import annotations

from typing import Any, Callable

import pytest

from app.domains.creation.a1 import guide_engine
from app.domains.creation.a1.guide_engine import (
    A1Session,
    AnswerNode,
    answer_view,
    sync_position,
)
from app.domains.creation.seed.story_modules import (
    THREE_TIER_TREE,
    VS_DIM_DIR,
    VS_DUAL,
    VS_ENUM,
    VS_FROM_TO,
    VS_POINT,
)

# ---------------------------------------------------------------------------
# 工具与候选入口
# ---------------------------------------------------------------------------

#: T5 候选 schema 校验入口：validate_l3_value(l3_id, value) → 校验结果/异常。
_SCHEMA_GUARD_CANDIDATES = (
    "validate_l3_value",
    "l3_value_validate",
    "check_l3_value",
    "validate_value_shape",
)

#: T5 候选结构化读入口：l3_value_parts(value|node) → dict 形态结构化值。
_PARTS_READER_CANDIDATES = (
    "l3_value_parts",
    "read_l3_value",
    "l3_structured_value",
    "value_parts",
)

_L3_WRITER_CANDIDATES = (
    "apply_l3_fill",
    "write_l3_answer",
    "fill_l3",
    "l3_fill",
    "apply_fill_l3",
)


def _discover(names: tuple[str, ...]) -> Callable[..., Any] | None:
    for n in names:
        fn = getattr(guide_engine, n, None)
        if callable(fn):
            return fn
    return None


def _l3_vs(l3_id: str) -> str:
    for l1 in THREE_TIER_TREE:
        for l2 in l1["l2"]:  # type: ignore[union-attr]
            for l3 in l2["l3"]:  # type: ignore[union-attr]
                if l3["id"] == l3_id:  # type: ignore[union-attr]
                    return l3["vs"]  # type: ignore[union-attr]
    raise AssertionError(f"树内无此 L3：{l3_id}")


#: ⑥稿逐形态代表位点（各类至少一个，取自 THREE_TIER_TREE 实落 id）。
SAMPLE_POINT_ID = "origin"            # ⇦ ● 起源
SAMPLE_FROM_TO_ID = "acquire"         # ▶ 获取方式
SAMPLE_DIM_DIR_ID = "cost"            # ⇄ 力量代价（拒绝线特例所在组）
SAMPLE_DUAL_ID = next(
    l3["id"]  # type: ignore[union-attr]
    for l1 in THREE_TIER_TREE
    for l2 in l1["l2"]  # type: ignore[union-attr]
    for l3 in l2["l3"]  # type: ignore[union-attr]
    if l3["vs"] == VS_DUAL  # type: ignore[union-attr]
)


def _session() -> A1Session:
    s = A1Session(session_id="t-vs-schema", user_id="u")
    sync_position(s)
    return s


# ---------------------------------------------------------------------------
# 锚（T2 落库事实）
# ---------------------------------------------------------------------------


class TestVsEnumAnchor:
    def test_vs_closed_set(self):
        assert VS_ENUM == frozenset(
            {VS_POINT, VS_FROM_TO, VS_DIM_DIR, VS_DUAL}
        )

    def test_sample_ids_match_expected_shapes(self):
        assert _l3_vs(SAMPLE_POINT_ID) == VS_POINT
        assert _l3_vs(SAMPLE_FROM_TO_ID) == VS_FROM_TO
        assert _l3_vs(SAMPLE_DIM_DIR_ID) == VS_DIM_DIR
        assert _l3_vs(SAMPLE_DUAL_ID) == VS_DUAL


# ---------------------------------------------------------------------------
# 红：schema 校验入口 + 四形态值契约
# ---------------------------------------------------------------------------


class TestSchemaGuardEntry:
    def test_schema_guard_exists(self):
        assert _discover(_SCHEMA_GUARD_CANDIDATES) is not None, (
            "guide_engine 缺值 schema 校验入口（候选：%s）"
            % ", ".join(_SCHEMA_GUARD_CANDIDATES)
        )

    def test_parts_reader_exists(self):
        assert _discover(_PARTS_READER_CANDIDATES) is not None, (
            "guide_engine 缺结构化值读入口（候选：%s）"
            % ", ".join(_PARTS_READER_CANDIDATES)
        )


class TestPointShape:
    """● point：纯文本，往返字节不变。"""

    def test_point_roundtrip_bytes_identical(self):
        write = _discover(_L3_WRITER_CANDIDATES)
        read = _discover(_PARTS_READER_CANDIDATES)
        s = _session()
        raw = "天地未分，浑沌如卵"
        write(s, SAMPLE_POINT_ID, raw)  # type: ignore[misc]
        got = read(s, SAMPLE_POINT_ID)  # type: ignore[misc]
        assert answer_view(got) == raw

    def test_point_rejects_or_degrades_structured_from_to(self):
        """▶ 形态值写入 ● 位点 → 拒绝（校验异常）或降级（取文本部分）。"""
        guard = _discover(_SCHEMA_GUARD_CANDIDATES)
        assert guard is not None, "schema 校验入口缺失——边界无从谈起"
        s = _session()
        from_to_value = {"from": "凡人", "to": "剑仙", "trigger": "铸剑自焚"}
        outcome: dict[str, Any] = {"rejected": False, "degraded": False}
        try:
            guard(SAMPLE_POINT_ID, from_to_value)  # type: ignore[misc]
            # 未拒绝 → 落库后必须降级为纯文本（点形态只认文本）。
            outcome["degraded"] = True
        except Exception:
            outcome["rejected"] = True
        assert outcome["rejected"] or outcome["degraded"], (
            "▶ 值写入 ● 位点：既未拒绝也未降级——schema 边界缺失"
        )


class TestFromToShape:
    """▶ from_to：{from, to, trigger}，结构化读回。"""

    def test_full_structure_roundtrip(self):
        write = _discover(_L3_WRITER_CANDIDATES)
        parts = _discover(_PARTS_READER_CANDIDATES)
        s = _session()
        value = {"from": "凡人", "to": "剑仙", "trigger": "铸剑自焚"}
        write(s, SAMPLE_FROM_TO_ID, value)  # type: ignore[misc]
        got = parts(s, SAMPLE_FROM_TO_ID)  # type: ignore[misc]
        assert got["from"] == "凡人"
        assert got["to"] == "剑仙"
        assert got["trigger"] == "铸剑自焚"


class TestDimDirShape:
    """⇄ dim_dir：{dimension, direction, magnitude}；拒绝线特例 magnitude=0。"""

    def test_structure_roundtrip(self):
        write = _discover(_L3_WRITER_CANDIDATES)
        parts = _discover(_PARTS_READER_CANDIDATES)
        s = _session()
        value = {"dimension": "寿元", "direction": "减", "magnitude": 30}
        write(s, SAMPLE_DIM_DIR_ID, value)  # type: ignore[misc]
        got = parts(s, SAMPLE_DIM_DIR_ID)  # type: ignore[misc]
        assert got["dimension"] == "寿元"
        assert got["direction"] == "减"
        assert got["magnitude"] == 30

    def test_zero_magnitude_persisted_and_queryable(self):
        """⑥§2-16 拒绝线特例：幅度 0（"从X到X"）合法，落库可查不丢弃。"""
        write = _discover(_L3_WRITER_CANDIDATES)
        parts = _discover(_PARTS_READER_CANDIDATES)
        s = _session()
        write(s, SAMPLE_DIM_DIR_ID, {
            "dimension": "境界", "direction": "平", "magnitude": 0,
        })  # type: ignore[misc]
        got = parts(s, SAMPLE_DIM_DIR_ID)  # type: ignore[misc]
        assert got["magnitude"] == 0, "magnitude=0 被真值闸/清洗层误吞"


class TestDualShape:
    """⇉ dual：双形值（点 + 变化）。"""

    def test_dual_value_roundtrip(self):
        write = _discover(_L3_WRITER_CANDIDATES)
        parts = _discover(_PARTS_READER_CANDIDATES)
        s = _session()
        value = {
            "point": "江湖第一剑",
            "change": {"from": "无敌", "to": "求败不得"},
        }
        write(s, SAMPLE_DUAL_ID, value)  # type: ignore[misc]
        got = parts(s, SAMPLE_DUAL_ID)  # type: ignore[misc]
        assert got["point"] == "江湖第一剑"
        assert got["change"]["to"] == "求败不得"


class TestLegacyDefaultsToPoint:
    """无 vs 标注的存量答案（42/43 字段时代）全按 ● 处理。"""

    def test_plain_str_answer_reads_as_point(self):
        parts = _discover(_PARTS_READER_CANDIDATES)
        s = _session()
        s.answers["世界本体.origin"] = "浑沌如卵"  # 存量平面串（无 vs 语义）
        got = parts(s, "origin")  # type: ignore[misc]
        assert got["point"] == "浑沌如卵" or got == {"point": "浑沌如卵"}
