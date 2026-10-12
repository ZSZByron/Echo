# -*- coding: utf-8 -*-
"""T6 守门测试：故事线 15 问「说人话」文案替换锁（拍1-1，④稿 §2 after 逐字）。

权威目录：docs/plans/2026-10-10-访谈问题文案说人话-逐句分析优化.md §2。
防漏改/多改：question/hint/example 三件套与④稿 after 文本逐字一致；
multi: True 标注原位不动（D23 红线）；三示例宇宙分配不变只做同宇宙展开。
"""
from app.domains.creation.seed.story_modules import STORY_MODULES


def _fields(module_id: str) -> dict:
    mod = next(m for m in STORY_MODULES if m["id"] == module_id)
    return {f["id"]: f for f in mod["fields"]}


# ── ④稿 §2 after 文本快照（example 的「如：」为代码统一前缀，④稿口径判一致）──

EXPECTED = {
    # M11 角色（6 问）
    ("角色", "identity"): (
        "主角是谁？他是干什么的、以什么身份活在故事里？",
        "说说他的职业和位置，再想想他自己怎么看自己——一句话就够。",
        "如：边城义庄的守夜人，白天入殓夜里记账",
    ),
    ("角色", "desire"): (
        "TA 最想要什么？",
        "他嘴上说想要的，和心里真正需要的，可以不是一回事——两样都想想。",
        "如：想要查清灭门真相，需要的是原谅自己当年逃走",
    ),
    ("角色", "flaw"): (
        "TA 的性格缺陷或软肋是什么？",
        "性格上或心里的软处——它会反复坑他、让他付出代价；不是缺钱缺帮手那种外部困难。",
        "如：不信任任何人，关键证据宁可烂在手里也不求助",
    ),
    ("角色", "key_relations"): (
        "TA 与谁的关系最要命？",
        "说说那个最能牵动他的人——家人、对手、亏欠过的人都算；想到几个就说几个。",
        "如：与叛出师门的师姐互为唯一软肋",
    ),
    ("角色", "arc_direction"): (
        "故事走完时，TA 会变成什么样？",
        "想想开头和结尾——他从什么样的人，变成什么样的人？也可以让他咬牙不变。",
        "如：从用谎言保护所有人→学会让真相先落地",
    ),
    ("角色", "character_visual"): (
        "他长什么样？有没有让人一眼就记住的外表特征？",
        "一件衣服、一个随身物件、一个小动作——别人一眼就能认出他的那种。",
        "如：左耳缺角的银质耳坠，紧张时摩挲它",
    ),
    # M12 剧情（9 问）
    ("剧情", "opening_event"): (
        "故事一开场，你的主角身上刚发生了什么大事？",
        "挑一件正在\"现在\"发生、只关乎他本人的大事——不是几百年前的传说，是他眼前的事。",
        "如：缉毒警员林澈在妹妹婚礼当夜接到卧底密令",
    ),
    ("剧情", "core_dilemma"): (
        "故事刚开场，你的主角就撞上一件躲不开的事——他必须马上选一边，而且不管选哪边，都得失去点什么。那是什么事？",
        "想象他被逼到墙角：往前一步要付出一样，退后一步要付出另一样。",
        "如：妹妹婚礼当晚，他接到命令去当卧底——去，就要骗过全家人；不去，线人今晚就活不成。",
    ),
    ("剧情", "tension_hole"): (
        "有没有一样东西，他特别想要却一直得不到——或者要得到它，必须拿别的重要东西去换？",
        "这样东西会一直吊着他，让他停不下来。",
        "如：想学火系禁术必须先背叛授业恩师",
    ),
    ("剧情", "lead_chain"): (
        "从头到尾，他一直放不下、一直在做的是哪件事？",
        "找一个人、查一件事、找回一样东西，都算。",
        "如：追查妹妹失踪前最后接触的三个人",
    ),
    ("剧情", "secret_layer"): (
        "谁不知道什么？哪条信息被谁隐瞒着？",
        "也可以是主角自己瞒着别人的秘密。想想它被戳穿的那一刻，会发生什么。",
        "如：恩师其实就是当年灭门案的目击者",
    ),
    ("剧情", "branch_trees"): (
        "如果他成了，故事会走向哪里？如果他输了呢？（两头都说说）",
        "一头是成了的样子，一头是砸了的样子。想让 AI 先各写一版给你改，也行。",
        "如：成功→洗清冤屈但失去身份；失败→被迫亡命江湖",
    ),
    ("剧情", "bound_characters"): (
        "谁在拼命把事情往前推？又是谁拦着他、跟他对着干？",
        "拦着他的人，可以是他最亲的人。",
        "如：拼命推的是林澈自己；拦着他的是把他养大的义父——那位黑警长官。",
    ),
    ("剧情", "arc_direction"): (
        "这段故事整体往哪个方向走？",
        "大方向是越变越好（上扬）、越变越糟（下沉）、来回打转（循环），还是没想好？先定一个。",
        "如：先扬后抑的悲剧循环，结局留一线微光",
    ),
    ("剧情", "scene_hooks"): (
        "关键场景发生在哪些地点、带什么氛围？",
        "说几个地点，每个配两三个气氛词就够——细节以后慢慢补。",
        "如：雨夜码头（潮湿、霓虹倒影、远处汽笛）",
    ),
}


class TestStoryCopyRewrite:
    def test_fifteen_questions_match_after_text(self):
        """15 问 q/h/e 三件套与④稿 after 逐字一致（防漏改/多改）。"""
        assert len(EXPECTED) == 15
        for (mid, fid), (q, h, e) in EXPECTED.items():
            field = _fields(mid)[fid]
            assert field["question"] == q, f"{mid}.{fid}.question 漂移"
            assert field["hint"] == h, f"{mid}.{fid}.hint 漂移"
            assert field["example"] == e, f"{mid}.{fid}.example 漂移"

    def test_key_relations_multi_flag_intact(self):
        """D23 红线：key_relations 的 multi: True 标注原位不动。"""
        assert _fields("角色")["key_relations"].get("multi") is True

    def test_example_universe_assignment(self):
        """三示例宇宙分配不变（林澈=剧情主线 / 守夜人=角色身份 / 仙侠=张力源等只做同宇宙展开）。"""
        角色 = _fields("角色")
        剧情 = _fields("剧情")
        # 守夜人宇宙：M11 identity（保留原句）
        assert "守夜人" in 角色["identity"]["example"]
        # 林澈宇宙：M12 开场/抉择/绑定三问咬合（示范稿例句同宇宙展开）
        assert "林澈" in 剧情["opening_event"]["example"]
        assert "婚礼" in 剧情["core_dilemma"]["example"]
        assert "卧底" in 剧情["core_dilemma"]["example"]
        assert "林澈" in 剧情["bound_characters"]["example"]
        # 仙侠宇宙：tension_hole / key_relations 例（保留原句，无解码门槛）
        assert "禁术" in 剧情["tension_hole"]["example"]
        assert "师门" in 角色["key_relations"]["example"]
        # 去表单腔：bound_characters 例不再有「执行者=」等号表单
        assert "执行者=" not in 剧情["bound_characters"]["example"]
