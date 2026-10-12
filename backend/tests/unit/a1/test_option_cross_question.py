"""P3 序号跨题错配病理红测（T2 RED 阶段，wave1 止血批 1.1）。

病理场景照说明书逐字复刻（2026-10-09-访谈知识求助搜索-问题说明书 L39）：
弧光题自由文本作答 → 引擎推进到下一问「外形记忆点」→ reply 附 3 选项
（实为上一题弧光的陈旧 examples 快照）→ 用户回 "3" → 序号被直选通道
吃掉，陈旧弧光选项写进当前题 character_visual。

根因（guide_engine.py:1344-1388 直选硬匹配）：cur_key 取「当前题」，
session.current_options 是「上一轮序列化时快照」——两来源解耦，序号
跨题错配回填。

文件组织照 test_option_forward.py（ExamplesFake 注入 examples）+
test_knowledge_request.py（engine 级 A1Session + handle_message）。
不依赖真实 LLM。

红线：本文件是 RED 阶段判据——禁止在本文件落地修复；
修复（T3 转绿）落在 guide_engine.py。
"""
from __future__ import annotations

from typing import Any

import pytest

from app.domains.creation.a1.guide_engine import (
    A1Session,
    handle_message,
)
from app.domains.creation.a1.interviewer import (
    FakeInterviewer,
    InterviewFill,
)
from app.domains.creation.seed.a1_question_tree import all_subfield_keys
from app.domains.creation.seed.story_modules import STORY_MODULES

# ---------------------------------------------------------------------------
# 病理常量（说明书 L39 逐字场景值）
# ---------------------------------------------------------------------------

ARC_KEY = "角色.arc_direction"          # 弧光方向（上一题）
VISUAL_KEY = "角色.character_visual"    # 外形记忆点（当前题，"标志性外形记忆点"）
ARC_ANSWER = "堂堂正正的生活"            # 弧光题自由文本作答（用户原话）

#: 弧光题 reply 附带的 3 选项（陈旧快照；选项 3 = 说明书点名的
#: "原谅自己并重新相信亲密关系"）
ARC_OPTIONS = [
    "从用谎言保护所有人到学会让真相先落地",
    "拒绝转变，守着旧的自己直到故事结束",
    "原谅自己并重新相信亲密关系",
]

STALE_OPTION_3 = ARC_OPTIONS[2]


class ExamplesFake(FakeInterviewer):
    """FakeInterviewer + examples 透传（照 test_option_forward.py 同款）。"""

    def __init__(self, *args: Any, inject: Any = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._inject = inject

    def interview(self, session: Any, text: str) -> Any:
        result = super().interview(session, text)
        setattr(result, "examples", self._inject)
        return result


def _stale_tail_session() -> A1Session:
    """构造「只剩 弧光→外形 两问未答」的会话（保证推进确定性）。

    其余全部字段预填真实感文本（非占位词），使 sync_position 在弧光
    作答后恰好落在外形记忆点 character_visual（角色模块内相邻两问）。
    """
    s = A1Session(session_id="s_p3", user_id="u1", ip_code="IP0001")
    # 故事线配方（说明书场景为故事线访谈）：walk = 剧情 → 角色
    # （story recipe，_type_ordered_modules 走 recipe_modules 子集序）。
    s.creator_primary = "plot"
    s.recipe_modules = ["剧情", "角色"]
    # 全键 = 10 模块问卷树 + 故事模块族（M11 角色 / M12 剧情——
    # all_subfield_keys 只覆盖前者，故事模块在 MODULE_POOL 不在树序）。
    story_keys = [
        f'{m["id"]}.{f["id"]}' for m in STORY_MODULES for f in m["fields"]
    ]
    for key in [*all_subfield_keys(), *story_keys]:
        if key in (ARC_KEY, VISUAL_KEY):
            continue
        s.answers[key] = f"已答：{key} 的设定内容"
    s.current_module, s.current_subfield = ARC_KEY.split(".", 1)
    return s


# ---------------------------------------------------------------------------
# 病理复现用例（RED——当前必须失败：陈旧弧光选项 3 被写进 character_visual）
# ---------------------------------------------------------------------------


def test_p3_stale_option_number_cross_question_mismatch():
    """P3 病理逐字重放：弧光自由文本 → 推进外形记忆点 → "3" 错配。"""
    s = _stale_tail_session()

    # ---- 幕一：弧光题自由文本作答「堂堂正正的生活」，reply 附 3 选项 ----
    fake1 = ExamplesFake(
        fills=[InterviewFill(module="角色", subfield="arc_direction",
                             value=ARC_ANSWER)],
        guidance_reply="弧光方向已记录。",
        inject=list(ARC_OPTIONS),
    )
    out1 = handle_message(s, ARC_ANSWER, fake1)

    # 幕一前置断言（构造正确性，非病理断言）：
    assert s.answers[ARC_KEY] == ARC_ANSWER            # 弧光已记录
    assert (s.current_module, s.current_subfield) == (
        "角色", "character_visual")                    # 引擎推进到外形记忆点
    assert s.current_options == ARC_OPTIONS            # reply 附 3 选项
    assert "1. " in out1["reply"] and "3. " in out1["reply"]

    # ---- 幕二：用户对着「外形记忆点」问题回 "3"（意图选它的选项 3）----
    fake2 = ExamplesFake()
    out2 = handle_message(s, "3", fake2)

    # 病理断言（RED）：直选通道吃掉的 ARC_OPTIONS[2] 是上一题（弧光）的
    # 陈旧快照选项——绝不允许跨题写进当前题 character_visual。
    # 修复合入后（T3）：陈旧选项不得被当前题序号直选消费 → 本断言转绿。
    assert s.answers.get(VISUAL_KEY) != STALE_OPTION_3, (
        "P3 序号跨题错配：上一题（弧光）的陈旧选项 3 "
        f"被写进当前题【{s.current_module}.{s.current_subfield}】——"
        f"实得值：{s.answers.get(VISUAL_KEY)!r}"
    )
    # 弧光的自由文本作答不受扰动（保守伴随断言）。
    assert s.answers[ARC_KEY] == ARC_ANSWER


# ---------------------------------------------------------------------------
# 辅助用例 1：直选越界数字（"0"/"4"）走常规文本路径（现状锁定，GREEN）
# ---------------------------------------------------------------------------


class TestOutOfRangeNumberFallsThrough:
    def test_zero_and_overflow_not_consumed_by_pick(self):
        """越界序号（0 / 超出 len(current_options)）不进直选分支，
        走常规 interview 文本路径——现状行为锁定。"""
        s = _stale_tail_session()
        s.current_options = list(ARC_OPTIONS)
        fake = ExamplesFake(
            fills=[InterviewFill(module="角色", subfield="character_visual",
                                 value="左耳缺角的银质耳坠")],
            guidance_reply="外形记忆点已记录。",
        )
        out0 = handle_message(s, "0", fake)
        assert fake.calls == 1, '"0" 必须进入 interview 文本路径'
        assert s.answers[VISUAL_KEY] == "左耳缺角的银质耳坠"  # fills 正常消费
        assert "已按示例记录" not in out0["reply"]            # 未走直选话术

        s2 = A1Session(session_id="s_p3b", user_id="u1", ip_code="IP0001")
        s2.current_module, s2.current_subfield = "角色", "character_visual"
        s2.current_options = list(ARC_OPTIONS)  # len=3 → "4" 越界
        fake2 = ExamplesFake(guidance_reply="请描述外形记忆点。")
        out4 = handle_message(s2, "4", fake2)
        assert fake2.calls == 1, '"4"（超出选项数）必须进入文本路径'
        assert VISUAL_KEY not in s2.answers
        assert "已按示例记录" not in out4["reply"]


# ---------------------------------------------------------------------------
# 辅助用例 2：存量 stale 会话容忍（恢复后不崩溃、安全降级，GREEN）
# ---------------------------------------------------------------------------


class TestStaleSessionTolerance:
    def test_restored_stale_options_degrade_safely(self):
        """带旧 current_options 的会话经 model_validate 恢复后：
        自由文本/越界输入不崩溃，安全降级（chat 轮末清空残留选项）。"""
        # 模拟旧版本序列化数据恢复：带残留 current_options 指向已答字段。
        s = A1Session.model_validate({
            "session_id": "s_stale",
            "user_id": "u1",
            "ip_code": "IP0001",
            "current_module": "角色",
            "current_subfield": "character_visual",
            "answers": {ARC_KEY: ARC_ANSWER},
            "current_options": list(ARC_OPTIONS),
        })
        assert s.current_options == ARC_OPTIONS  # 恢复保真（前置）

        # 自由文本：正常处理，不崩溃；轮末无新 examples → 残留清空（降级）。
        fake = ExamplesFake(guidance_reply="继续说说外形的细节。")
        out = handle_message(s, "他就是总戴着一顶旧毡帽", fake)
        assert out["reply"] == "继续说说外形的细节。"
        assert s.current_options == []

        # 越界数字 "9"：同样不崩溃，走文本路径。
        fake2 = ExamplesFake(guidance_reply="请用自己的话描述。")
        out9 = handle_message(s, "9", fake2)
        assert fake2.calls == 1
        assert "已按示例记录" not in out9["reply"]


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
