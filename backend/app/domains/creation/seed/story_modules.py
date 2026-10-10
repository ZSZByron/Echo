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
            "question": "故事一开场，你的主角身上刚发生了什么大事？",
            "hint": "挑一件正在\"现在\"发生、只关乎他本人的大事"
                    "——不是几百年前的传说，是他眼前的事。",
            "example": "如：缉毒警员林澈在妹妹婚礼当夜接到卧底密令",
        },
        {
            "id": "core_dilemma",
            "label": "核心抉择",
            "question": "故事刚开场，你的主角就撞上一件躲不开的事"
                        "——他必须马上选一边，而且不管选哪边，都得失去点什么。那是什么事？",
            "hint": "想象他被逼到墙角：往前一步要付出一样，退后一步要付出另一样。",
            "example": "如：妹妹婚礼当晚，他接到命令去当卧底"
                       "——去，就要骗过全家人；不去，线人今晚就活不成。",
        },
        {
            "id": "tension_hole",
            "label": "张力源",
            "question": "有没有一样东西，他特别想要却一直得不到"
                        "——或者要得到它，必须拿别的重要东西去换？",
            "hint": "这样东西会一直吊着他，让他停不下来。",
            "example": "如：想学火系禁术必须先背叛授业恩师",
        },
        {
            "id": "lead_chain",
            "label": "线索链",
            "question": "从头到尾，他一直放不下、一直在做的是哪件事？",
            "hint": "找一个人、查一件事、找回一样东西，都算。",
            "example": "如：追查妹妹失踪前最后接触的三个人",
        },
        {
            "id": "secret_layer",
            "label": "秘密维度",
            "question": "谁不知道什么？哪条信息被谁隐瞒着？",
            "hint": "也可以是主角自己瞒着别人的秘密。想想它被戳穿的那一刻，会发生什么。",
            "example": "如：恩师其实就是当年灭门案的目击者",
        },
        {
            "id": "branch_trees",
            "label": "分支预案",
            "question": "如果他成了，故事会走向哪里？如果他输了呢？（两头都说说）",
            "hint": "一头是成了的样子，一头是砸了的样子。想让 AI 先各写一版给你改，也行。",
            "example": "如：成功→洗清冤屈但失去身份；失败→被迫亡命江湖",
        },
        {
            "id": "bound_characters",
            "label": "人物绑定",
            "question": "谁在拼命把事情往前推？又是谁拦着他、跟他对着干？",
            "hint": "拦着他的人，可以是他最亲的人。",
            "example": "如：拼命推的是林澈自己；拦着他的是把他养大的义父——那位黑警长官。",
        },
        {
            "id": "arc_direction",
            "label": "走向基调",
            "question": "这段故事整体往哪个方向走？",
            "hint": "大方向是越变越好（上扬）、越变越糟（下沉）、来回打转（循环），"
                    "还是没想好？先定一个。",
            "example": "如：先扬后抑的悲剧循环，结局留一线微光",
        },
        {
            "id": "scene_hooks",
            "label": "场景挂载",
            "question": "关键场景发生在哪些地点、带什么氛围？",
            "hint": "说几个地点，每个配两三个气氛词就够——细节以后慢慢补。",
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
            "question": "主角是谁？他是干什么的、以什么身份活在故事里？",
            "hint": "说说他的职业和位置，再想想他自己怎么看自己——一句话就够。",
            "example": "如：边城义庄的守夜人，白天入殓夜里记账",
        },
        {
            "id": "desire",
            "label": "欲望",
            "question": "TA 最想要什么？",
            "hint": "他嘴上说想要的，和心里真正需要的，可以不是一回事——两样都想想。",
            "example": "如：想要查清灭门真相，需要的是原谅自己当年逃走",
        },
        {
            "id": "flaw",
            "label": "缺陷",
            "question": "TA 的性格缺陷或软肋是什么？",
            "hint": "性格上或心里的软处——它会反复坑他、让他付出代价；不是缺钱缺帮手那种外部困难。",
            "example": "如：不信任任何人，关键证据宁可烂在手里也不求助",
        },
        {
            "id": "key_relations",
            "label": "关键关系",
            "question": "TA 与谁的关系最要命？",
            "hint": "说说那个最能牵动他的人——家人、对手、亏欠过的人都算；想到几个就说几个。",
            "example": "如：与叛出师门的师姐互为唯一软肋",
            # D23：多值字段声明——complement relation 在此字段追加子条目。
            "multi": True,
        },
        {
            "id": "arc_direction",
            "label": "弧光方向",
            "question": "故事走完时，TA 会变成什么样？",
            "hint": "想想开头和结尾——他从什么样的人，变成什么样的人？也可以让他咬牙不变。",
            "example": "如：从用谎言保护所有人→学会让真相先落地",
        },
        {
            "id": "character_visual",
            "label": "角色视觉",
            "question": "他长什么样？有没有让人一眼就记住的外表特征？",
            "hint": "一件衣服、一个随身物件、一个小动作——别人一眼就能认出他的那种。",
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
