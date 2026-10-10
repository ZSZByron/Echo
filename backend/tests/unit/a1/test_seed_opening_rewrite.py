"""波次一 T8：访谈开场引导语（seed 区）后端拼接替换守门。

④稿 §4 L328：开场引导语去系统视角官腔（「我将围绕它引导你展开世界观」
不存在于 backend——文档 before 描述与代码现状有出入），替换
interviewer.py `_seed_block` 的自定义创意行：

before: 用户的初始创意：{种子}
after:  记下你的创意了：{种子}。
        接下来我会一次问你一个问题，帮你把它变成一个完整的世界。
        每题都可以自己写、从我给的选项里挑，或者跳过。
"""
from __future__ import annotations

from types import SimpleNamespace

from app.domains.creation.a1.interviewer import RealLLMInterviewer

_MODULE = {"id": "世界本体", "label": "世界本体", "fields": []}
_SUBFIELD = {
    "id": "origin",
    "label": "世界起源",
    "question": "?",
    "example": "",
}


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


def _seed_block_text(session: SimpleNamespace) -> str:
    interviewer = RealLLMInterviewer(provider=None)
    return interviewer._build_prompt(_MODULE, _SUBFIELD, session)


class TestSeedOpeningRewrite:
    def test_custom_idea_opening_full_text(self) -> None:
        """自定义创意开场：新全文 + 种子插值 + 真实换行。"""
        prompt = _seed_block_text(_make_session(seed_description="我想看故事开场"))
        assert (
            "记下你的创意了：我想看故事开场\n"
            "接下来我会一次问你一个问题，帮你把它变成一个完整的世界。"
            "每题都可以自己写、从我给的选项里挑，或者跳过。"
        ) in prompt

    def test_old_opening_gone(self) -> None:
        prompt = _seed_block_text(_make_session(seed_description="任意创意"))
        assert "用户的初始创意" not in prompt
        assert "我将围绕它引导你展开世界观" not in prompt

    def test_preset_line_untouched(self) -> None:
        """种子预设行（波次三前端同源文案对应）保持原拼接不动。"""
        prompt = _seed_block_text(
            _make_session(
                seed_name="守夜人",
                seed_genre="怪谈",
                seed_description="灯塔上的守夜人",
            )
        )
        assert "用户选择的种子预设：守夜人（怪谈）— 灯塔上的守夜人" in prompt
        assert "记下你的创意了" not in prompt
