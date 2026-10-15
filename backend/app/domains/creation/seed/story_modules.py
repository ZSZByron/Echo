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
            "label": "核心两难",
            "question": "故事刚开场，你的主角就撞上一件躲不开的事"
                        "——他必须马上选一边，而且不管选哪边，都得失去点什么。那是什么事？",
            "hint": "想象他被逼到墙角：往前一步要付出一样，退后一步要付出另一样。",
            "example": "如：妹妹婚礼当晚，他接到命令去当卧底"
                       "——去，就要骗过全家人；不去，线人今晚就活不成。",
        },
        {
            "id": "tension_hole",
            "label": "张力",
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
            "label": "分支走向",
            "question": "如果他成了，故事会走向哪里？如果他输了呢？（两头都说说）",
            "hint": "一头是成了的样子，一头是砸了的样子。想让 AI 先各写一版给你改，也行。",
            "example": "如：成功→洗清冤屈但失去身份；失败→被迫亡命江湖",
        },
        {
            "id": "bound_characters",
            "label": "关键人物",
            "question": "谁在拼命把事情往前推？又是谁拦着他、跟他对着干？",
            "hint": "拦着他的人，可以是他最亲的人。",
            "example": "如：拼命推的是林澈自己；拦着他的是把他养大的义父——那位黑警长官。",
        },
        {
            "id": "arc_direction",
            "label": "走向",
            "question": "这段故事整体往哪个方向走？",
            "hint": "大方向是越变越好（上扬）、越变越糟（下沉）、来回打转（循环），"
                    "还是没想好？先定一个。",
            "example": "如：先扬后抑的悲剧循环，结局留一线微光",
        },
        {
            "id": "scene_hooks",
            "label": "关键场景",
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
            "label": "弧光",
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


# ---------------------------------------------------------------------------
# 三级分类树（波次二 T2 落库——⑤稿 docs/plans/2026-10-10-A1模块三级分类体系
# 设计.md §1-§7 + ⑥稿值形态 92 项判定表 + §9 清单型机制）。
#
# 契约面（tests/unit/a1/test_three_tier_contract.py）：L1×7 → L2×26 → L3×92；
# 15 个升格 L2 与 35 个平移 L3 沿用现行字段 id（label 改 id 不动，零语义漂移）；
# 57 个新增 L3 用描述性英文小写下划线新 id（用户全局命名规则——不复用项目
# 已用字母系列 A-J/J1-J4/D#/P#/C1-C5/T#/F#/L1-L3 前缀）。
#
# 值形态 vs 枚举（⑥稿 §0，闭集逐字）：point(●)/from_to(▶)/dim_dir(⇄)/
# dual(⇉)——92 项 = ●66 + ▶20 + ⇄5 + ⇉1。拒绝线特例（⑥§2-16 幅度 0 语义
# "从X到X" 合法答案）用注释表达，不新增字段。
#
# 清单型标注（⑤稿 §9）：``list: True`` + ``item_template``（卡内追问维度组）
# + ``LIST_CAPS`` 位点上限表（灵感架/关键节点/存在物=12，其余=6；灵感架为
# 会话级位点 material_pool，非树内节点）。首批 15 处 = 13 个 L3 位点 +
# 支线卡 L2（卡式，六件套即模板）+ 灵感架。
# ---------------------------------------------------------------------------

#: vs 枚举闭集（⑥稿 §0；不允许添加或修改）。
VS_POINT = "point"
VS_FROM_TO = "from_to"
VS_DIM_DIR = "dim_dir"
VS_DUAL = "dual"
VS_ENUM: frozenset[str] = frozenset({VS_POINT, VS_FROM_TO, VS_DIM_DIR, VS_DUAL})

# 卡内条目模板（⑤稿 §9.3 追问维度组——清单停驻循环逐字段追问的模板）。
_RELATION_TEMPLATE = ["什么关系", "为什么要命", "变化维度"]
_INFO_GAP_TEMPLATE = ["谁", "瞒着什么", "什么时候炸"]


def _l3(lid: str, label: str, vs: str, **extra: object) -> dict[str, object]:
    """L3 节点构造（vs 必填；list/item_template 走 extra）。"""
    node: dict[str, object] = {"id": lid, "label": label, "vs": vs}
    node.update(extra)
    return node


THREE_TIER_TREE: list[dict[str, object]] = [
    # ── L1① IP —— 世界的名片（⑤§1，4 L3 全平移）─────────────────────
    {
        "id": "ip",
        "label": "IP",
        "l2": [
            {
                "id": "IP定位",
                "label": "IP名片",
                "l3": [
                    _l3("name", "世界名称", VS_POINT),
                    _l3("concept", "核心概念", VS_POINT),
                    _l3("world_type", "类型标签", VS_POINT),
                    _l3("core_experience", "核心体验", VS_POINT),
                ],
            },
        ],
    },
    # ── L1② 世界观 —— 世界本身的构造（⑤§2，5 L2 / 17 L3 全平移）────
    {
        "id": "worldview",
        "label": "世界观",
        "l2": [
            {
                "id": "世界本体",
                "label": "世界本体",
                "l3": [
                    _l3("origin", "起源", VS_POINT),
                    _l3(
                        "existence", "存在物", VS_POINT,
                        list=True, item_template=["名", "一句话"],
                    ),
                    _l3("reality_rule", "现实规则", VS_POINT),
                ],
            },
            {
                "id": "力量体系",
                "label": "力量体系",
                "l3": [
                    _l3("source", "力量来源", VS_POINT),
                    _l3("acquire", "获取方式", VS_FROM_TO),
                    _l3("mechanism", "运作法则", VS_POINT),
                    _l3("cost", "力量代价", VS_DIM_DIR),
                ],
            },
            {
                "id": "地理空间",
                "label": "地理空间",
                "l3": [
                    _l3("terrain", "主要地形", VS_POINT),
                    _l3("vertical", "垂直层级", VS_POINT),
                    _l3("special_geo", "特殊地理", VS_POINT),
                ],
            },
            {
                "id": "文明与社会",
                "label": "文明与社会",
                "l3": [
                    _l3("core_value", "核心价值", VS_POINT),
                    _l3(
                        "conflict", "冲突来源", VS_POINT,
                        list=True, item_template=["冲突双方", "争什么"],
                    ),
                    _l3(
                        "faction_type", "势力版图", VS_POINT,
                        list=True,
                        item_template=["势力名", "谁说了算", "怎么传位"],
                    ),
                    _l3("economy", "经济命脉", VS_POINT),
                ],
            },
            {
                "id": "历史时间线",
                "label": "历史时间线",
                "l3": [
                    _l3("time_span", "纪元划分", VS_POINT),
                    _l3(
                        "key_nodes", "关键节点", VS_FROM_TO,
                        list=True,
                        item_template=["前态", "触发事件", "后态", "时间", "波及面"],
                    ),
                    _l3("main_plot", "当代主剧情", VS_FROM_TO),
                ],
            },
        ],
    },
    # ── L1③ 剧情 —— 主角的这段故事（⑤§3，10 L2 / 32 L3 全新增）─────
    {
        "id": "story_line",
        "label": "剧情",
        "l2": [
            {
                "id": "opening_event",
                "label": "开场事件",
                "l3": [
                    _l3("daily_life", "开场前的日常", VS_POINT),
                    _l3("breaking_incident", "破局大事", VS_FROM_TO),
                    _l3("incident_scene", "事发画面", VS_POINT),
                ],
            },
            {
                "id": "core_dilemma",
                "label": "核心两难",
                "l3": [
                    _l3("option_one_cost", "选项一与代价", VS_FROM_TO),
                    _l3("option_two_cost", "选项二与代价", VS_FROM_TO),
                    _l3("dilemma_stall_cost", "僵局的代价", VS_FROM_TO),
                ],
            },
            {
                "id": "tension_hole",
                "label": "张力",
                "l3": [
                    _l3("desired_object", "渴望之物", VS_POINT),
                    _l3("blocking_wall", "高墙", VS_POINT),
                    _l3("exchange_scale", "交换之秤", VS_DIM_DIR),
                ],
            },
            {
                "id": "lead_chain",
                "label": "主线明线",
                "l3": [
                    _l3("first_thread", "第一根线头", VS_POINT),
                    _l3("mid_twist", "中途转折", VS_FROM_TO),
                    _l3("final_thread", "最后的线头", VS_POINT),
                ],
            },
            {
                "id": "secret_layer",
                "label": "主线暗线",
                "l3": [
                    _l3(
                        "unknown_to_hero", "他不知道的", VS_POINT,
                        list=True, item_template=_INFO_GAP_TEMPLATE,
                    ),
                    _l3(
                        "hidden_by_hero", "他瞒着别人的", VS_POINT,
                        list=True, item_template=_INFO_GAP_TEMPLATE,
                    ),
                    _l3(
                        "audience_foreshadow", "观众先知道的", VS_POINT,
                        list=True, item_template=_INFO_GAP_TEMPLATE,
                    ),
                    _l3("darklight_cross", "明暗交汇点", VS_FROM_TO),
                ],
            },
            {
                "id": "branch_trees",
                "label": "分支走向",
                "l3": [
                    _l3("success_path", "成功线", VS_FROM_TO),
                    _l3("failure_path", "失败线", VS_FROM_TO),
                ],
            },
            {
                "id": "bound_characters",
                "label": "关键人物",
                "l3": [
                    _l3("pusher", "推动者", VS_POINT),
                    _l3("blocker", "阻拦者", VS_POINT),
                    _l3("swing_third", "摇摆的第三者", VS_DIM_DIR),
                ],
            },
            {
                "id": "arc_direction",
                "label": "走向",
                "l3": [
                    _l3("overall_tone", "大方向", VS_DIM_DIR),
                    _l3("ending_aftertaste", "结局滋味", VS_POINT),
                ],
            },
            {
                "id": "scene_hooks",
                "label": "关键场景",
                "l3": [
                    _l3(
                        "core_scene_list", "核心场景清单", VS_POINT,
                        list=True, item_template=["地点", "氛围词", "意象"],
                    ),
                    _l3("scene_mood", "场景氛围", VS_POINT),
                    _l3("signature_image", "标志性意象", VS_POINT),
                ],
            },
            {
                # 支线卡：卡式清单位点（multi 同族）——六件套即条目模板，
                # 整卡轨迹 ▶（⑥§2-13）。
                "id": "branch_card",
                "label": "支线卡",
                "list": True,
                "item_template": [
                    "side_summary", "side_carrier", "side_type",
                    "side_link_mode", "side_link_point", "side_ending",
                ],
                "l3": [
                    _l3("side_summary", "支线一句话", VS_POINT),
                    _l3("side_carrier", "承载者", VS_POINT),
                    _l3("side_type", "支线类型", VS_POINT),
                    _l3("side_link_mode", "衔接方式", VS_POINT),
                    _l3("side_link_point", "衔接点", VS_FROM_TO),
                    _l3("side_ending", "支线结局", VS_FROM_TO),
                ],
            },
        ],
    },
    # ── L1④ 角色 —— 主角这个人（⑤§4，6 L2 / 25 L3 全新增）──────────
    {
        "id": "character",
        "label": "角色",
        "l2": [
            {
                "id": "identity",
                "label": "身份",
                "l3": [
                    _l3("social_identity", "社会身份", VS_POINT),
                    _l3("self_identity", "自我认同", VS_POINT),
                    _l3("one_line_intro", "一句介绍", VS_POINT),
                ],
            },
            {
                "id": "desire",
                "label": "欲望",
                "l3": [
                    _l3("outer_goal", "外显目标", VS_POINT),
                    _l3("inner_need", "深层需要", VS_POINT),
                    _l3("deepest_fear", "最深恐惧", VS_POINT),
                    _l3("desire_root", "欲望的根", VS_POINT),
                ],
            },
            {
                "id": "flaw",
                "label": "缺陷",
                "l3": [
                    _l3("trait_weakness", "性格弱点", VS_POINT),
                    _l3("fatal_softspot", "致命软肋", VS_POINT),
                    _l3(
                        "cost_history", "代价史", VS_FROM_TO,
                        list=True, item_template=["发作前", "触发", "发作后"],
                    ),
                    _l3("flaw_origin", "根源", VS_POINT),
                ],
            },
            {
                "id": "key_relations",
                "label": "关键关系",
                "l3": [
                    _l3(
                        "family_bond", "家人", VS_POINT,
                        list=True, item_template=_RELATION_TEMPLATE,
                    ),
                    _l3(
                        "rival", "对手", VS_POINT,
                        list=True, item_template=_RELATION_TEMPLATE,
                    ),
                    _l3(
                        "owed_person", "亏欠的人", VS_POINT,
                        list=True, item_template=_RELATION_TEMPLATE,
                    ),
                    _l3(
                        "ally", "盟友", VS_POINT,
                        list=True, item_template=_RELATION_TEMPLATE,
                    ),
                    # 关系卡变化方向件（⑥§2-15 ⇄ 附件：信任/亲密/敌意维度表）。
                    _l3("relation_card_format", "关系卡格式", VS_DIM_DIR),
                ],
            },
            {
                "id": "arc_direction",
                "label": "弧光",
                "l3": [
                    _l3("arc_start", "起点", VS_FROM_TO),
                    _l3("arc_turning", "转折事件", VS_FROM_TO),
                    _l3("arc_end", "终点", VS_FROM_TO),
                    # 拒绝线 = 幅度 0 特例（⑥§2-16："从X到X" 合法答案——
                    # 语义注记，不新增字段）。
                    _l3("arc_refuse", "拒绝线", VS_FROM_TO),
                ],
            },
            {
                "id": "character_visual",
                "label": "角色视觉",
                "l3": [
                    _l3("visual_trait", "外貌辨识点", VS_POINT),
                    _l3("signature_outfit", "标志服饰", VS_POINT),
                    _l3("carry_item", "随身物", VS_POINT),
                    _l3("habitual_gesture", "习惯动作", VS_POINT),
                    _l3("voice_temperament", "声线气质", VS_POINT),
                ],
            },
        ],
    },
    # ── L1⑤ 玩法 —— 走进世界的人做什么（⑤§5，2 L2 / 9 L3 全平移）───
    {
        "id": "gameplay",
        "label": "玩法",
        "l2": [
            {
                "id": "玩法骨架",
                "label": "玩法骨架",
                "l3": [
                    _l3("player_role", "玩家身份", VS_FROM_TO),
                    _l3("main_action", "主要行为", VS_POINT),
                    _l3("growth", "成长方式", VS_DUAL),
                    _l3("growth_end", "成长尽头", VS_FROM_TO),
                ],
            },
            {
                "id": "骰子设定",
                "label": "骰子设定",
                "l3": [
                    _l3("probability", "概率分布", VS_POINT),
                    _l3("dice_count", "骰子数量", VS_POINT),
                    _l3("check_mode", "判定方式", VS_POINT),
                    _l3("success_check", "成功判定", VS_POINT),
                    _l3("cost_mech", "代价机制", VS_POINT),
                ],
            },
        ],
    },
    # ── L1⑥ 视觉 —— 世界的长相（⑤§6，1 L2 / 3 L3 平移；候选◇2 不加）─
    {
        "id": "visual",
        "label": "视觉",
        "l2": [
            {
                "id": "视觉设计",
                "label": "视觉设计",
                "l3": [
                    _l3("keywords", "视觉关键词", VS_POINT),
                    _l3("architecture", "建筑风格", VS_POINT),
                    _l3("material", "材质偏好", VS_POINT),
                ],
            },
        ],
    },
    # ── L1⑦ 设定边界 —— AI 的权限（⑤§7，1 L2 / 2 L3 全平移）────────
    {
        "id": "setting_boundary",
        "label": "设定边界",
        "l2": [
            {
                "id": "设定边界",
                "label": "设定边界",
                "l3": [
                    _l3("immutable_core", "不可变设定", VS_POINT),
                    _l3("ai_fill", "AI补充范围", VS_POINT),
                ],
            },
        ],
    },
]

#: 清单位点上限表（⑤稿 §9.2-4：默认继承 D23 的 6；大容量清单放宽 12）。
#: 位点键 = 树内 L3 id / 支线卡 L2 id / 会话级 material_pool（灵感架）。
#: 供批 B 停驻追加循环读取；灵感架/关键节点/存在物 = 12，其余 = 6。
LIST_CAPS: dict[str, int] = {
    "material_pool": 12,       # 灵感架（会话级，⑦稿 ⑤§9.3）
    "key_nodes": 12,           # 历史时间线.关键节点（大容量）
    "existence": 12,           # 世界本体.存在物（大容量）
    "family_bond": 6,
    "rival": 6,
    "owed_person": 6,
    "ally": 6,
    "branch_card": 6,
    "cost_history": 6,
    "core_scene_list": 6,
    "faction_type": 6,
    "conflict": 6,
    "key_relations": 6,        # 批B additive：旧字段宇宙清单位点（T4 红测契约
                               # LIST_CAPS["key_relations"] 直读；6 帽档）
    "unknown_to_hero": 6,
    "hidden_by_hero": 6,
    "audience_foreshadow": 6,
}

# ---------------------------------------------------------------------------
# ⑨稿 Q16 支线主问（拍2-7 已拍"加"——故事线 15 问 → 16 问，可跳过）。
# 原文：docs/plans/2026-10-10-新结构引导话术设计.md §4-2。独立常量落库，
# 不并入 M11/M12 fields（门禁计数/35 字段宇宙零扰动）；序列挂接归批 B。
# ---------------------------------------------------------------------------

#: Q16 支线主问（⑨稿原文 question；hint 含"可跳过"退出语义）。
Q16_BRANCH_CARD: dict[str, str] = {
    "id": "branch_card",
    "label": "支线卡",
    "question": "除了主线，有没有一条副线你也想看着它长出来？（可以跳过）",
    "hint": "可跳过——只想好主线也完全没问题；副线可以是感情线、成长线、"
            "世界揭示线或对手线，说一句它讲什么就够。",
    "example": "如：他偷偷照顾线人的女儿——成长线，高潮前夜反哺主线",
}

#: 故事线配方序列（④稿 15 问序：剧情 9 + 角色 6，配方出场序）+ Q16 第 16 位。
STORYLINE_ORDER: list[str] = (
    [f["id"] for f in M12_PLOT["fields"]]
    + [f["id"] for f in M11_CHARACTER["fields"]]
    + [Q16_BRANCH_CARD["id"]]
)

# ---------------------------------------------------------------------------
# 批C（拍2-15）：⑨稿动态问句模板数据区（§1 两族 26 项，槽位变量化）。
# 纯数据字典 + 按需取用（半填补问 ▶⇄ 时机由 guide_engine 决定）——
# 不造模板引擎抽象（批C 施工单红线）。situation 闭集六值：
# ▶ 全问/补from/补to/补trigger 四情形 + ⇄ 全问/补方向两情形；
# 第 26 项 = 支线主问（side_card_full_question，Q16 同源话术的模板态）。
# ---------------------------------------------------------------------------

#: ▶ 起终点式情形闭集（⑨稿 §1.1）。
SITUATION_ARROW_FULL = "arrow_full_question"
SITUATION_ARROW_FROM_MISSING = "arrow_from_missing"
SITUATION_ARROW_TO_MISSING = "arrow_to_missing"
SITUATION_ARROW_TRIGGER_MISSING = "arrow_trigger_missing"
#: ⇄ 属性维度式情形闭集。
SITUATION_DIM_FULL = "dim_full_question"
SITUATION_DIM_DIRECTION_MISSING = "dim_direction_missing"
#: 支线主问（第 26 项，⑥稿 §0 咬合：▶20 + ⇄5 + 支线1 = 26）。
SITUATION_SIDE_CARD_FULL = "side_card_full_question"

#: 26 动态问句模板（⑨稿 §1.1 骨架 + §1.2 逐项实例化；槽位用 {变量}）。
DYNAMIC_INVITE_TEMPLATES: list[dict[str, str]] = [
    # ── ▶ 起终点式 · 全问（from/to 都空）──
    {"situation": SITUATION_ARROW_FULL, "target": "力量.获取方式",
     "template": "得到{力量}之前{角色}是什么人？得到之后成了什么？走的是哪条路？"},
    {"situation": SITUATION_ARROW_FULL, "target": "历史.关键节点",
     "template": "这件大事之前{世界}什么样？之后变成了什么样？是哪件事促成的？"},
    {"situation": SITUATION_ARROW_FULL, "target": "历史.当代主剧情",
     "template": "这个时代从什么{起点局面}开始，正被推向什么{终点局面}？"},
    {"situation": SITUATION_ARROW_FULL, "target": "支线.衔接点",
     "template": "{支线}在哪个节骨眼上碰到{主线}？碰之前之后各什么样？"},
    {"situation": SITUATION_ARROW_FULL, "target": "玩法.玩家身份",
     "template": "{玩家}从什么{起点身份}起步，最后站到什么{终点位置}？"},
    # ── ▶ 起终点式 · 补 from（只知终点，问起点）──
    {"situation": SITUATION_ARROW_FROM_MISSING, "target": "剧情.破局大事",
     "template": "他如今{后态}——他原来的日子什么样？是哪件事把它砸碎的？"},
    {"situation": SITUATION_ARROW_FROM_MISSING, "target": "角色.代价史",
     "template": "这个缺陷每次发作——发作前{角色}什么样、发作后什么样？"},
    {"situation": SITUATION_ARROW_FROM_MISSING, "target": "角色.弧光起点",
     "template": "结尾时他是{终点人格}——开头的他是什么人？"},
    {"situation": SITUATION_ARROW_FROM_MISSING, "target": "玩法.成长尽头",
     "template": "一路变强，变到头是{终点形态}——起步时的他是什么样？"},
    {"situation": SITUATION_ARROW_FROM_MISSING, "target": "剧情.支线结局",
     "template": "这条支线走到头落在{终点}——它是从哪里长出来的？"},
    # ── ▶ 起终点式 · 补 to（只知起点，问终点）──
    {"situation": SITUATION_ARROW_TO_MISSING, "target": "剧情.选项一",
     "template": "选{选项一}这边：得到什么、失去什么？最后把他推向哪里？"},
    {"situation": SITUATION_ARROW_TO_MISSING, "target": "剧情.选项二",
     "template": "选{选项二}这边：得到什么、失去什么？最后把他推向哪里？"},
    {"situation": SITUATION_ARROW_TO_MISSING, "target": "剧情.僵局的代价",
     "template": "如果{角色}一直拖着不选，每天会塌掉什么？塌到最后是什么局面？"},
    {"situation": SITUATION_ARROW_TO_MISSING, "target": "角色.弧光终点",
     "template": "从{起点人格}出发的这个人，你想让他最后变成什么样？"},
    {"situation": SITUATION_ARROW_TO_MISSING, "target": "剧情.成功线",
     "template": "赢到{成功线那头}，世界和他各是什么样？要走过什么才能到？"},
    # ── ▶ 起终点式 · 补 trigger（两态都有，问促成事件）──
    {"situation": SITUATION_ARROW_TRIGGER_MISSING, "target": "剧情.中途转折",
     "template": "是什么事，让{角色}从{误向}转到了{真相}？"},
    {"situation": SITUATION_ARROW_TRIGGER_MISSING, "target": "剧情.明暗交汇点",
     "template": "是什么事，让{暗线}浮出水面、和{明线}撞上？"},
    {"situation": SITUATION_ARROW_TRIGGER_MISSING, "target": "剧情.失败线",
     "template": "是什么事，把他从{现状}推到了{败局}那一步？"},
    {"situation": SITUATION_ARROW_TRIGGER_MISSING, "target": "角色.弧光转折",
     "template": "是哪件事，把他从{起点}推成了{终点}？"},
    {"situation": SITUATION_ARROW_TRIGGER_MISSING, "target": "历史.关键节点",
     "template": "是什么事，把世界从{前态}推成了{后态}？"},
    # ── ⇄ 属性维度式 ──
    {"situation": SITUATION_DIM_FULL, "target": "力量.力量代价",
     "template": "用{力量}要付代价——在{维度}上，是变多了还是变少了？变化有多猛？"},
    {"situation": SITUATION_DIM_FULL, "target": "剧情.交换之秤",
     "template": "他要的东西在{维度}上往哪边走？那跌下去的是什么？"},
    {"situation": SITUATION_DIM_FULL, "target": "角色.关系卡变化",
     "template": "这段关系里，{维度}现在是多是少？往后会怎么走？"},
    {"situation": SITUATION_DIM_DIRECTION_MISSING, "target": "剧情.摇摆第三者",
     "template": "{人物}的立场——是往{我方}的方向走，还是往{对方}的方向走？"},
    {"situation": SITUATION_DIM_DIRECTION_MISSING, "target": "剧情.大方向",
     "template": "整个故事的情绪——{故事}是往涨的方向走，还是往跌的方向走？"},
    # ── 支线主问（第 26 项）──
    {"situation": SITUATION_SIDE_CARD_FULL, "target": "支线.主问",
     "template": "除了{主线}，有没有一条{副线}你也想看着它长出来？（可以跳过）"},
]

# ---------------------------------------------------------------------------
# 批C（拍2-15）：⑨稿 §2 L3 追问话术（57 项 = 剧情 32 + 角色 25）。
# 场景：自由流程细化 / 半填补问 / AI 选项生成素材——追问体（短、口语、
# 问句形态）。按 l3 id 表驱动挂入 THREE_TIER_TREE 的 ``followup`` 键
# （纯数据追加，树形态契约 {id,label,vs,...} 之上 additive，零消费面扰动；
# 挂点消费归 guide_engine 半填补问/L3 追问时机，批D 回收）。
# ---------------------------------------------------------------------------

_L3_FOLLOWUPS: dict[str, str] = {
    # ── 剧情 32 ──
    "daily_life": "大事来之前，他平常的一天怎么过？",
    "breaking_incident": "这事是怎么砸到他头上的？",
    "incident_scene": "把这一幕想成一幅画：几点、在哪、谁在场？",
    "option_one_cost": "选这边，他心里先想到的是谁？",
    "option_two_cost": "选这边，他心里先想到的是谁？",
    "dilemma_stall_cost": "如果拖着不选，最先塌的是什么？",
    "desired_object": "这东西为什么对他这么重要？",
    "blocking_wall": "谁、或什么，拦着他得不到？",
    "exchange_scale": "他要的东西在涨，那跌下去的是什么？",
    "first_thread": "追踪是从哪件事正式开始的？",
    "mid_twist": "哪次变化让他发现——自己一直追错了方向？",
    "final_thread": "追到最后，真相是什么形状？",
    "unknown_to_hero": "有什么事，别人都知道、只有他蒙在鼓里？",
    "hidden_by_hero": "他自己死死藏着什么？",
    "audience_foreshadow": "读者早早知道、他却不知道的雷——什么时候炸？",
    "darklight_cross": "瞒着的那条线，哪一刻浮出水面、和明线撞上？",
    "success_path": "成功那头，他失去了谁？",
    "failure_path": "失败那头，他还剩下什么？",
    "pusher": "除了他自己，谁还在推着这事走？",
    "blocker": "拦着的人——他图什么？",
    "swing_third": "那个人立场往哪边偏？什么事会让他倒戈？",
    "overall_tone": "这个方向上，最狠的一段起伏在哪？",
    "ending_aftertaste": "合上故事那一刻，你想让读者心里留什么滋味？",
    "core_scene_list": "故事反复发生的地方有哪几处？",
    "scene_mood": "每个地方，用两三个词形容气氛？",
    "signature_image": "读者会记住的那个画面是什么？",
    "side_summary": "这条支线，一句话讲什么？",
    "side_carrier": "它挂在谁身上？",
    "side_type": "它是感情线、成长线、世界揭示线还是对手线？",
    "side_link_mode": "它怎么接上主线——送线索、改选择、回个味、还是爆炸？",
    "side_link_point": "支线在哪个节骨眼上碰到主线？碰之前之后各什么样？",
    "side_ending": "这条支线走到头，落在哪里？",
    # ── 角色 25 ──
    "social_identity": "除了这份身份，他私下还靠什么过日子？",
    "self_identity": "他自己怎么看自己——和别人眼里的他差在哪？",
    "one_line_intro": "他妈妈会怎么介绍他？仇人呢？",
    "outer_goal": "嘴上这个目标，他打算从哪一步开始动手？",
    "inner_need": "他嘴上要那个，心里缺的是什么？",
    "deepest_fear": "他最怕失去什么？",
    "desire_root": "这份想要，是从哪件事上长出来的？",
    "trait_weakness": "什么软处会反复坑他？",
    "fatal_softspot": "哪个点一戳他就失控？哪个人一出现他就乱？",
    "cost_history": "这个缺陷每次发作——发作前他什么样、发作后什么样？",
    "flaw_origin": "这毛病怎么长出来的？",
    "family_bond": "说说这个人——什么关系、为什么要命？",
    "rival": "说说这个人——什么关系、为什么要命？",
    "owed_person": "说说这个人——什么关系、为什么要命？",
    "ally": "说说这个人——什么关系、为什么要命？",
    "relation_card_format": "这段关系里，信任是多是少？往后会怎么走？",
    "arc_start": "开头的他是什么人？",
    "arc_turning": "哪件事逼他开始变？",
    "arc_end": "结尾他变成什么人？",
    "arc_refuse": "有没有可能——全世界都变了，他偏不变？",
    "visual_trait": "人群里一眼认出他，靠哪个特征？",
    "signature_outfit": "他常穿什么？什么场合会换？",
    "carry_item": "一直带在身上的东西？有来历吗？",
    "habitual_gesture": "紧张时、说谎时，各有什么小动作？",
    "voice_temperament": "他说话什么调子？第一面给人什么感觉？",
}

# 表驱动挂接：followup 键 additive 写入树内 L3 节点（57 项逐字对应）。
for _l1_node in THREE_TIER_TREE:
    for _l2_node in _l1_node["l2"]:
        for _l3_node in _l2_node["l3"]:
            _followup_text = _L3_FOLLOWUPS.get(str(_l3_node["id"]), "")
            if _followup_text:
                _l3_node["followup"] = _followup_text
