"""半填宽容契约红测（Metis CRITICAL#8——先红后绿，零实现）。

⑤⑥稿半填语义：
- ▶ from_to 仅 to / 仅 trigger、⇄ dim_dir 仅 dimension+direction —— 存储
  不拒绝不报错，落库**部分形状**（缺字段不炸、不丢已填部分）。
- 门禁完成度**计入**（真值闸：有真实内容即真值）——半填答案的模块完成度
  行为与全填一致（模块完成度层面：is_module_over_half / missing_sections
  语义不受半填形状拖累）。
- 选项补全为机会性后补（非门禁条件）——options 通道后续轮次提示补
  from/trigger，但**补全提示不阻塞门禁**。

红测纪律：schema 写入口经 getattr 发现；门禁断言用现行
is_module_over_half（真值语义已落地面）+ 树写入口结构面。
"""
from __future__ import annotations

from typing import Any, Callable

from app.domains.creation.a1 import guide_engine
from app.domains.creation.a1.guide_engine import A1Session, sync_position
from app.domains.creation.seed.story_modules import THREE_TIER_TREE

# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

_L3_WRITER_CANDIDATES = (
    "apply_l3_fill",
    "write_l3_answer",
    "fill_l3",
    "l3_fill",
    "apply_fill_l3",
)

_PARTS_READER_CANDIDATES = (
    "l3_value_parts",
    "read_l3_value",
    "l3_structured_value",
    "value_parts",
)

#: 树真值闸候选（结构化半填的真值判定——现行为 is_truthy_answer 的树扩展）。
_L3_TRUTH_CANDIDATES = (
    "l3_answer_truthy",
    "is_l3_truthy",
    "l3_truthy",
)


def _discover(names: tuple[str, ...]) -> Callable[..., Any] | None:
    for n in names:
        fn = getattr(guide_engine, n, None)
        if callable(fn):
            return fn
    return None


def _session() -> A1Session:
    s = A1Session(session_id="t-half-fill", user_id="u")
    sync_position(s)
    return s


SAMPLE_FROM_TO_ID = "acquire"   # ▶ 力量体系.获取方式
SAMPLE_DIM_DIR_ID = "cost"      # ⇄ 力量体系.力量代价

#: 力量体系 L2 组内 L3 全集（半填完成度对齐实验的对照组）。
_POWER_L3_IDS = [
    l3["id"]  # type: ignore[union-attr]
    for l1 in THREE_TIER_TREE
    for l2 in l1["l2"]  # type: ignore[union-attr]
    if l2["id"] == "力量体系"  # type: ignore[union-attr]
    for l3 in l2["l3"]  # type: ignore[union-attr]
]


# ---------------------------------------------------------------------------
# 红：半填落库不拒绝
# ---------------------------------------------------------------------------


class TestHalfFillStorage:
    def test_writer_exists(self):
        assert _discover(_L3_WRITER_CANDIDATES) is not None, (
            "缺 L3 树写入口——半填契约无落点"
        )

    def test_from_to_only_to(self):
        """▶ 仅 to：存储不拒绝不报错，已填部分可读回。"""
        write = _discover(_L3_WRITER_CANDIDATES)
        parts = _discover(_PARTS_READER_CANDIDATES)
        s = _session()
        write(s, SAMPLE_FROM_TO_ID, {"to": "剑仙"})  # type: ignore[misc]
        got = parts(s, SAMPLE_FROM_TO_ID)  # type: ignore[misc]
        assert got["to"] == "剑仙"

    def test_from_to_only_trigger(self):
        """▶ 仅 trigger：同样宽容落库。"""
        write = _discover(_L3_WRITER_CANDIDATES)
        parts = _discover(_PARTS_READER_CANDIDATES)
        s = _session()
        write(s, SAMPLE_FROM_TO_ID, {"trigger": "铸剑自焚"})  # type: ignore[misc]
        got = parts(s, SAMPLE_FROM_TO_ID)  # type: ignore[misc]
        assert got["trigger"] == "铸剑自焚"

    def test_dim_dir_dimension_direction_only(self):
        """⇄ 仅 dimension+direction（缺 magnitude）：不拒绝。"""
        write = _discover(_L3_WRITER_CANDIDATES)
        parts = _discover(_PARTS_READER_CANDIDATES)
        s = _session()
        write(s, SAMPLE_DIM_DIR_ID, {
            "dimension": "寿元", "direction": "减",
        })  # type: ignore[misc]
        got = parts(s, SAMPLE_DIM_DIR_ID)  # type: ignore[misc]
        assert got["dimension"] == "寿元"
        assert got["direction"] == "减"


# ---------------------------------------------------------------------------
# 红：门禁完成度计入（真值闸——有真实内容即真值）
# ---------------------------------------------------------------------------


class TestGateCountsHalfFill:
    def test_truth_predicate_exists(self):
        """树真值谓词存在（is_truthy_answer 的结构化扩展）。"""
        assert _discover(_L3_TRUTH_CANDIDATES) is not None, (
            "缺结构化半填真值谓词（候选：%s）" % ", ".join(_L3_TRUTH_CANDIDATES)
        )

    def test_half_fill_truthy_like_full_fill(self):
        """半填（仅 to）与全填在真值谓词上同判：有真实内容即真值。"""
        truth = _discover(_L3_TRUTH_CANDIDATES)
        full = {"from": "凡人", "to": "剑仙", "trigger": "铸剑自焚"}
        half = {"to": "剑仙"}
        assert truth(half) is True  # type: ignore[misc]
        assert truth(full) is True  # type: ignore[misc]

    def test_module_completion_unaffected_by_half_shape(self):
        """模块完成度层面：含半填答案的会话与全填行为一致。

        同一模块（力量体系组）逐位写入；半填位点与全填位点在
        is_module_over_half 判定下不得出现"半填被漏计"。
        """
        write = _discover(_L3_WRITER_CANDIDATES)
        s = _session()
        for l3_id in _POWER_L3_IDS:
            if l3_id == SAMPLE_FROM_TO_ID:
                write(s, l3_id, {"to": "剑仙"})  # 半填位点  # type: ignore[misc]
            else:
                write(s, l3_id, f"{l3_id} 的完整答案")  # type: ignore[misc]
        # 半填位点真值 = True → 该组完成度与全填写法一致。
        half_session = _session()
        for l3_id in _POWER_L3_IDS:
            write(half_session, l3_id, f"{l3_id} 的完整答案")  # type: ignore[misc]
        # 两者在力量体系组的真值计数一致（半填不拖累完成度）。
        truth = _discover(_L3_TRUTH_CANDIDATES)
        assert truth is not None
        # 真语义断言：会话答案经树真值闸过滤后，半填位点计数 = 全填位点计数。
        answers_s = s.answers
        answers_full = half_session.answers
        count_s = sum(1 for k in _POWER_L3_IDS if truth(answers_s, k))  # type: ignore[misc]
        count_full = sum(1 for k in _POWER_L3_IDS if truth(answers_full, k))  # type: ignore[misc]
        assert count_s == count_full == len(_POWER_L3_IDS)


# ---------------------------------------------------------------------------
# 红：补全提示机会性、不阻塞门禁
# ---------------------------------------------------------------------------


class TestCompletionPromptNonBlocking:
    def test_completion_prompt_does_not_block_gate(self):
        """options 通道的 from/trigger 补全提示存在与否，门禁结论不变。"""
        write = _discover(_L3_WRITER_CANDIDATES)
        s = _session()
        write(s, SAMPLE_FROM_TO_ID, {"to": "剑仙"})  # type: ignore[misc]
        # 场景 B：同会话追加"补全提示挂起"状态（机会性后补通道）。
        s_pending = s.model_copy(deep=True)
        # 挂起状态以任意提示容器表达（options/current_options 先例）；
        # 契约：无论提示挂起与否，门禁真值一致。
        s_pending.current_options = ["补全 from：他从哪里来？"]
        truth = _discover(_L3_TRUTH_CANDIDATES)
        assert truth(s.answers, SAMPLE_FROM_TO_ID) is True  # type: ignore[misc]
        assert truth(s_pending.answers, SAMPLE_FROM_TO_ID) is True  # type: ignore[misc]
