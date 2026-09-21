"""E1-Lite T3: 语气锚点模板变量注入测试。

覆盖：
1. happy：creator_primary=="plot" → interview prompt 与 suggestion prompt 均含锚点行
2. 逐型矩阵：9 型锚点串与 ANCHOR_BY_TYPE 值逐字断言（防拼写漂移）
3. 回归：creator_primary=="" → _seed_block 输出与改动前快照逐字节相等；
   creator_primary=="bogus" → 不追加锚点行不抛错
4. prompt 变体审计：interviewer.py 中 prompt 骨架串出现次数不变（R2 红线）
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.domains.creation.a1.interviewer import (
    ANCHOR_BY_TYPE,
    RealLLMInterviewer,
)

INTERVIEWER_PATH = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "domains"
    / "creation"
    / "a1"
    / "interviewer.py"
)

_MODULE = {"id": "世界本体", "label": "世界本体", "fields": []}
_SUBFIELD = {"id": "origin", "label": "世界起源", "question": "?", "example": ""}


def _make_session(**overrides) -> SimpleNamespace:
    defaults = dict(
        current_module="世界本体",
        current_subfield="origin",
        answers={},
        seed_name="",
        seed_description="",
        creator_primary="",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _interviewer() -> RealLLMInterviewer:
    return RealLLMInterviewer(provider=None)


class TestHappyPath:
    def test_interview_prompt_contains_plot_anchor(self) -> None:
        prompt = _interviewer()._build_prompt(_MODULE, _SUBFIELD, _make_session(creator_primary="plot"))
        assert '语气锚点（引导与反馈的基调，务必贯彻）：节奏导向："这个设定会制造什么事件？"' in prompt

    def test_suggestion_prompt_reuses_anchor(self) -> None:
        """suggest_examples 复用 _seed_block → 锚点同样生效（单 prompt 注入点证明）。"""
        captured: dict = {}

        class _FakeProvider:
            def chat_json(self, messages):  # noqa: ANN001, ANN202
                captured["content"] = messages[0]["content"]
                return {"examples": ["示例A"]}

        interviewer = RealLLMInterviewer(provider=_FakeProvider())
        interviewer.suggest_examples(
            _make_session(creator_primary="plot"), "世界本体", "origin"
        )
        system = captured["content"]
        assert "语气锚点（引导与反馈的基调，务必贯彻）" in system
        assert '节奏导向："这个设定会制造什么事件？"' in system


class TestMatrixNineTypes:
    """9 型锚点逐字断言（spec §5.2 防拼写漂移）。"""

    @pytest.mark.parametrize(
        ("type_key", "anchor"),
        sorted(ANCHOR_BY_TYPE.items()),
        ids=sorted(ANCHOR_BY_TYPE),
    )
    def test_anchor_verbatim_in_seed_block(self, type_key: str, anchor: str) -> None:
        out = RealLLMInterviewer._seed_block(_make_session(creator_primary=type_key))
        assert out == f"语气锚点（引导与反馈的基调，务必贯彻）：{anchor}"

    def test_matrix_has_exactly_nine_types(self) -> None:
        assert set(ANCHOR_BY_TYPE) == {
            "plot",
            "unsure",
            "philosophy",
            "romance",
            "character_driven",
            "setting_heavy",
            "exploration",
            "nostalgia",
            "healing",
        }


class TestEmptyProfileRegression:
    def test_empty_creator_primary_byte_identical_to_pre_change(self) -> None:
        """改动前录制的快照：空 profile → '（无，用户从空白开始）'，逐字节相等。"""
        out = RealLLMInterviewer._seed_block(_make_session())
        assert out == "（无，用户从空白开始）"

    def test_bogus_creator_primary_no_anchor_no_error(self) -> None:
        out = RealLLMInterviewer._seed_block(_make_session(creator_primary="bogus"))
        assert out == "（无，用户从空白开始）"
        assert "语气锚点" not in out


class TestSinglePromptVariant:
    def test_prompt_skeleton_not_duplicated(self) -> None:
        """prompt 骨架串在 interviewer.py 中出现次数不变（未复制/分支，R2 红线）。"""
        src = INTERVIEWER_PATH.read_text(encoding="utf-8")
        assert src.count("你是TRPG世界观设计的访谈引导者") == 3
