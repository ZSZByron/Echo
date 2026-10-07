# -*- coding: utf-8 -*-
"""甲 M2：故事模块族数据（M11 角色 / M12 剧情）——独立于 a1_question_tree。

数据落位定死（Momus F2 修订，plan TODO 2）：故事模块放**独立本文件**经
``module_registry.MODULE_POOL`` 入池（family="story"），**不并入**
``a1_question_tree.MODULES``——MODULES 全集消费面（worldview_upload 上传
prompt schema / interviewer 全集目录 / ip_poster 展板 / tier 闭集断言）对
设定型路径零扰动，"设定型逐字节不变"由此在架构上成立。

字段形态镜像问卷树 ``Module``/``SubField`` TypedDict（id/label/question/
hint/example 五键），入池后由问卷树门面按配方参数解析。

字段文案 = **DECISION NEEDED 3 初稿，未经产品方终审不得定稿**
（权威定义：docs/plans/2026-09-22-jia-module-list-expansion.md §1.1，
A2-v0.2 叙事相位素材转化设计依据）。

2026-09-22 重锚定定版：
- M11 角色（产品方已定版 6 字段）：原"第 0 模块"落座；M0 的
  character_sketch 素材槽内容经 guide_engine 路由迁移入此（M2 实施）。
- M12 剧情（9 字段）：具体细节剧情的直接落点；**情感线不设独立模块**——
  并入 M12 场景化字段（opening_event 相遇化 / tension_hole 情感阻力化）
  + M10 爱情 preset（合规边界随 romance 配方 anchor，§9 措辞保留）。
"""
from __future__ import annotations

from typing import TypedDict


class StorySubField(TypedDict):
    """镜像 a1_question_tree.SubField 形态（不 import 问卷树，防依赖回头）。"""

    id: str
    label: str
    question: str
    hint: str
    example: str


class StoryModule(TypedDict):
    """镜像 a1_question_tree.Module 形态。"""

    id: str
    label: str
    fields: list[StorySubField]


#: M12 剧情模块（id: 剧情）——"主角的这段故事怎么走"（前景戏），
#: 区别于 M6 历史时间线.主剧情（世界历史脉络，背景板）。9 字段初稿。
M12_PLOT: StoryModule = {
    "id": "剧情",
    "label": "剧情",
    "fields": [
        {
            "id": "opening_event",
            "label": "开场事件",
            "question": "你的故事从哪一幕开始？最近发生了件什么大事？",
            "hint": "现在时、个人尺度的开场事件，故事的第一幕。",
            "example": "如：缉毒警员林澈在妹妹婚礼当夜接到卧底密令",
        },
        {
            "id": "core_dilemma",
            "label": "核心抉择",
            "question": "开场摆在眼前、必须立刻做出的抉择是什么？",
            "hint": "两难结构：选哪边都要付出代价，没有免费的选项。",
            "example": "如：上任务必暴露妹夫的私账，不上则线人今夜必死",
        },
        {
            "id": "tension_hole",
            "label": "张力源",
            "question": "什么「想要但不可得／要得到必须付代价」的东西在持续制造张力？",
            "hint": "结构洞=剧情发生器：不可得→张力→故事源源不断。",
            "example": "如：想学火系禁术必须先背叛授业恩师",
        },
        {
            "id": "lead_chain",
            "label": "线索链",
            "question": "贯穿整段故事的追求线是什么？",
            "hint": "throughline：一条可以一路追下去的线索（找人/查案/寻物）。",
            "example": "如：追查妹妹失踪前最后接触的三个人",
        },
        {
            "id": "secret_layer",
            "label": "秘密维度",
            "question": "谁不知道什么？哪条信息被谁隐瞒着？",
            "hint": "卧底/异端/隐瞒层——秘密被戳破的时刻就是爆点。",
            "example": "如：恩师其实就是当年灭门案的目击者",
        },
        {
            "id": "branch_trees",
            "label": "分支预案",
            "question": "核心抉择之后，成功与失败各把故事带向哪里？",
            "hint": "成功树/失败树各一条走向；AI 可先演示供你改写。",
            "example": "如：成功→洗清冤屈但失去身份；失败→被迫亡命江湖",
        },
        {
            "id": "bound_characters",
            "label": "人物绑定",
            "question": "这段剧情的执行者和对手分别是谁？",
            "hint": "挂角色模块的人物条目：谁推着事件走，谁挡在路上。",
            "example": "如：执行者=林澈；对手=义父兼黑警的养父",
        },
        {
            "id": "arc_direction",
            "label": "走向基调",
            "question": "这段故事整体往哪个方向走？",
            "hint": "上扬／下沉／循环／未定——决定叙事的底色。",
            "example": "如：先扬后抑的悲剧循环，结局留一线微光",
        },
        {
            "id": "scene_hooks",
            "label": "场景挂载",
            "question": "关键场景发生在哪些地点、带什么氛围？",
            "hint": "轻量钩子：地点+氛围关键词；详细场景留待后续扩写。",
            "example": "如：雨夜码头（潮湿、霓虹倒影、远处汽笛）",
        },
    ],
}

#: M11 角色模块（id: 角色）——产品方定版 6 字段；character_sketch 素材槽
#: 内容迁移落座（归 M2 路由实施）。
M11_CHARACTER: StoryModule = {
    "id": "角色",
    "label": "角色",
    "fields": [
        {
            "id": "identity",
            "label": "身份",
            "question": "主角是谁？什么身份立在这段故事里？",
            "hint": "社会位置+自我认同，一句话立住这个人。",
            "example": "如：边城义庄的守夜人，白天入殓夜里记账",
        },
        {
            "id": "desire",
            "label": "欲望",
            "question": "TA 最想要什么？",
            "hint": "外显目标（想要）与深层动机（需要）可以不一致。",
            "example": "如：想要查清灭门真相，需要的是原谅自己当年逃走",
        },
        {
            "id": "flaw",
            "label": "缺陷",
            "question": "TA 的性格缺陷或软肋是什么？",
            "hint": "会反复让 TA 付出代价的内在弱点，不是外部障碍。",
            "example": "如：不信任任何人，关键证据宁可烂在手里也不求助",
        },
        {
            "id": "key_relations",
            "label": "关键关系",
            "question": "TA 与谁的关系最要命？",
            "hint": "2-3 段塑造性的关系：家人/对手/亏欠的人。",
            "example": "如：与叛出师门的师姐互为唯一软肋",
            # D23：多值字段声明——complement relation 在此字段追加子条目。
            "multi": True,
        },
        {
            "id": "arc_direction",
            "label": "弧光方向",
            "question": "故事走完时，TA 会变成什么样？",
            "hint": "从 X 到 Y 的内在转变方向（也可以是拒绝转变）。",
            "example": "如：从用谎言保护所有人→学会让真相先落地",
        },
        {
            "id": "character_visual",
            "label": "角色视觉",
            "question": "TA 的标志性外形记忆点是什么？",
            "hint": "一眼认出的视觉锚：服饰/随身物/习惯动作。",
            "example": "如：左耳缺角的银质耳坠，紧张时摩挲它",
        },
    ],
}

#: 故事模块族（M11 角色在前——plan §230-231 M11/M12 编号序即清单序；
#: 配方内的出场序由 module_registry 配方矩阵决定，与本清单序解耦）。
STORY_MODULES: list[StoryModule] = [M11_CHARACTER, M12_PLOT]

_STORY_BY_ID: dict[str, StoryModule] = {m["id"]: m for m in STORY_MODULES}


def get_story_module(mid: str) -> StoryModule | None:
    """Return the story module dict for mid, or None."""
    return _STORY_BY_ID.get(mid)


def get_story_subfield(mid: str, sid: str) -> StorySubField | None:
    """Return the story subfield dict for (mid, sid), or None."""
    m = _STORY_BY_ID.get(mid)
    if m is None:
        return None
    return next((f for f in m["fields"] if f["id"] == sid), None)
