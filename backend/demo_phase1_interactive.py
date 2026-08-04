"""Phase 1 交互式验证 — 你输入数据，看模型怎么处理。

运行:
    cd backend
    python demo_phase1_interactive.py
"""
import io
import sys
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ── helpers ──────────────────────────────────────────────

def hr(c="=", n=60):
    print(c * n)

def ask(prompt, default=None):
    """问一个问题，返回用户输入。"""
    if default is not None:
        full = f"  {prompt} [{default}]: "
    else:
        full = f"  {prompt}: "
    val = input(full).strip()
    return val if val else (default if default is not None else val)

def ask_int(prompt, default):
    val = ask(prompt, str(default))
    try:
        return int(val)
    except ValueError:
        print(f"  输入不合法，使用默认值 {default}")
        return default

def show_json(obj):
    """打印 Pydantic 模型的 JSON (ensure_ascii=False 直接显示中文)。"""
    d = obj.model_dump()
    j = json.dumps(d, indent=2, ensure_ascii=False, default=str)
    print(j)

def pass_fail(obj):
    """序列化 -> 反序列化验证。"""
    cls = type(obj)
    j = obj.model_dump_json()
    obj2 = cls.model_validate_json(j)
    return obj2 == obj


# ── 1. StoryGraph ────────────────────────────────────────

def test_story():
    from app.models.story_graph import (
        StoryGraph, StoryNode, StoryNodeType, StoryEdge, StoryCondition, StoryChoice
    )
    hr()
    print("  1/5 StoryGraph — 剧情图")
    print("  你来构造一个剧情节点，看看模型怎么存它。")
    hr("-", 60)

    node_id = ask("节点ID", "start")
    node_name = ask("节点名称", "神殿入口")
    node_desc = ask("节点描述", "你站在神殿大门前")

    print("\n  节点类型可选:")
    for t in StoryNodeType:
        print(f"    {t.value}")
    type_input = ask("选一个类型", "start")
    try:
        node_type = StoryNodeType(type_input)
    except ValueError:
        print(f"  '{type_input}' 不是合法类型，用 START")
        node_type = StoryNodeType.START

    # 选择支
    choices = []
    while True:
        add = ask("\n  要加一个选择支吗？(y/n)", "n")
        if add.lower() != 'y':
            break
        choice_text = ask("  选择支文字", "开门")
        choice_target = ask("  目标节点ID", "end_good")
        choices.append(StoryChoice(text=choice_text, target_node=choice_target))

    # 组装
    node = StoryNode(
        id=node_id,
        type=node_type,
        name=node_name,
        description=node_desc,
        choices=choices,
    )
    graph = StoryGraph(
        id=ask("剧情图ID", "my_story"),
        name=ask("剧情图名称", "我的剧情"),
        description=ask("剧情图描述", "测试用"),
        nodes={node.id: node},
    )

    print("\n  --- 你的 StoryGraph 对象 ---")
    print(f"  节点数: {len(graph.nodes)}")
    print(f"  选择支数: {len(graph.nodes[node_id].choices)}")
    print(f"  创建时间: {graph.created_at}")

    print("\n  --- JSON 输出 ---")
    show_json(graph)

    print("\n  --- Round-trip 验证 ---")
    if pass_fail(graph):
        print("  [PASS] 序列化 -> 反序列化 -> 数据一致")
    else:
        print("  [FAIL] 数据不一致！")


# ── 2. EventGraph ────────────────────────────────────────

def test_event():
    from app.models.event_graph import (
        EventGraph, EventNode, EventNodeType,
        EventTrigger, EventTriggerType,
        EventReward, EventRewardType,
    )
    hr()
    print("  2/5 EventGraph — 事件图")
    print("  构造一个游戏事件，设定触发条件和奖励。")
    hr("-", 60)

    evt_id = ask("事件ID", "evt_001")
    evt_name = ask("事件名称", "宝箱陷阱")
    print("\n  事件类型可选: combat / quest / exploration / social")
    type_input = ask("选一个类型", "exploration")
    try:
        evt_type = EventNodeType(type_input)
    except ValueError:
        print(f"  不合法，用 EXPLORATION")
        evt_type = EventNodeType.EXPLORATION

    # 触发条件
    print("\n  触发类型: time / location / state / custom")
    trig_input = ask("触发类型", "location")
    try:
        trig_type = EventTriggerType(trig_input)
    except ValueError:
        trig_type = EventTriggerType.LOCATION
    trig_cond = ask("触发条件描述", "dungeon_room_3")

    trigger = EventTrigger(type=trig_type, condition=trig_cond)

    # 奖励
    rewards = []
    print("\n  奖励类型: item / experience / story_unlock")
    rew_input = ask("奖励类型", "item")
    try:
        rew_type = EventRewardType(rew_input)
    except ValueError:
        rew_type = EventRewardType.ITEM
    rew_value = ask("奖励值 (物品名或经验数字)", "gold_coin")
    rew_prob = ask("掉落概率 (0.0-1.0)", "1.0")
    try:
        rew_prob = float(rew_prob)
    except ValueError:
        rew_prob = 1.0
    rewards.append(EventReward(type=rew_type, value=rew_value, probability=rew_prob))

    node = EventNode(
        id=evt_id, type=evt_type, name=evt_name,
        trigger_conditions=[trigger], rewards=rewards,
    )
    graph = EventGraph(
        id=ask("事件图ID", "evt_graph_1"),
        name=ask("事件图名称", "地下城事件"),
        description=ask("事件图描述", "测试"),
        nodes={node.id: node},
    )

    print("\n  --- 你的 EventGraph 对象 ---")
    print(f"  事件: {graph.nodes[evt_id].name}")
    print(f"  触发: {graph.nodes[evt_id].trigger_conditions[0].type.value}")
    print(f"  奖励概率: {graph.nodes[evt_id].rewards[0].probability}")

    print("\n  --- JSON 输出 ---")
    show_json(graph)

    print("\n  --- Round-trip 验证 ---")
    if pass_fail(graph):
        print("  [PASS]")
    else:
        print("  [FAIL]")


# ── 3. CultureTree ───────────────────────────────────────

def test_culture():
    from app.models.culture import CultureNode, CultureTree
    hr()
    print("  3/5 CultureTree — 文化树")
    print("  构造一个文化节点，支持递归子节点。")
    hr("-", 60)

    root_id = ask("根节点ID", "culture_root")
    root_name = ask("根节点名称", "东方文明")
    root_desc = ask("根节点描述", "东亚文化圈")

    vals_raw = ask("价值观 (逗号分隔)", "harmony, respect, wisdom")
    values = [v.strip() for v in vals_raw.split(",") if v.strip()]

    aesthetics_raw = ask("美学原则 (逗号分隔)", "balance, nature")
    aesthetics = [a.strip() for a in aesthetics_raw.split(",") if a.strip()]

    root = CultureNode(
        id=root_id, name=root_name, description=root_desc,
        values=values, aesthetic_principles=aesthetics,
    )

    # 子节点
    children = []
    while True:
        add = ask("\n  要加一个子文化吗？(y/n)", "n")
        if add.lower() != 'y':
            break
        c_id = ask("  子节点ID", "child_1")
        c_name = ask("  子节点名称", "子文化")
        c_desc = ask("  子节点描述", "描述")
        children.append(CultureNode(id=c_id, name=c_name, description=c_desc))

    root.child_nodes = children
    tree = CultureTree(
        id=ask("文化树ID", "tree_1"),
        name=ask("文化树名称", "文化体系"),
        root=root,
    )

    print("\n  --- 你的 CultureTree 对象 ---")
    print(f"  根: {tree.root.name}")
    print(f"  价值观: {tree.root.values}")
    print(f"  子节点数: {len(tree.root.child_nodes)}")

    print("\n  --- JSON 输出 ---")
    show_json(tree)

    print("\n  --- Round-trip 验证 ---")
    if pass_fail(tree):
        print("  [PASS]")
    else:
        print("  [FAIL]")


# ── 4. ConstraintTree ────────────────────────────────────

def test_constraint():
    from app.models.constraint import ConstraintType, ConstraintNode, ConstraintTree
    hr()
    print("  4/5 ConstraintTree — 约束树")
    print("  构造资产生成约束（硬约束/软约束）。")
    hr("-", 60)

    nodes = []
    while True:
        add = ask("\n  要加一条约束吗？(y/n)", "y")
        if add.lower() != 'y':
            break
        rule = ask("  规则描述", "禁止金属材质")
        print("  约束类型: hard(违反=失败) / soft(影响评分)")
        ctype = ask("  类型", "hard")
        try:
            ct = ConstraintType(ctype)
        except ValueError:
            ct = ConstraintType.HARD
        priority = ask_int("  优先级 (0-100)", 80)
        nodes.append(ConstraintNode(
            id=f"rule_{len(nodes)+1}",
            type=ct, rule=rule, priority=priority,
        ))

    scene = ask("场景ID (留空=全局约束)", "")
    tree = ConstraintTree(
        id=ask("约束树ID", "ct_1"),
        name=ask("约束树名称", "场景约束"),
        scene_id=scene if scene else None,
        nodes=nodes,
    )

    print("\n  --- 你的 ConstraintTree 对象 ---")
    print(f"  约束数: {len(tree.nodes)}")
    hard = sum(1 for n in tree.nodes if n.type == ConstraintType.HARD)
    soft = sum(1 for n in tree.nodes if n.type == ConstraintType.SOFT)
    print(f"  硬约束: {hard}, 软约束: {soft}")
    print(f"  场景: {tree.scene_id or '全局'}")

    print("\n  --- JSON 输出 ---")
    show_json(tree)

    print("\n  --- Round-trip 验证 ---")
    if pass_fail(tree):
        print("  [PASS]")
    else:
        print("  [FAIL]")


# ── 5. Asset ─────────────────────────────────────────────

def test_asset():
    from app.models.asset import Asset, AssetType, AssetClassification
    hr()
    print("  5/5 Asset — 资产模型 (含 Phase 1 新字段)")
    print("  创建一个资产，测试分类和图节点关联。")
    hr("-", 60)

    a_id = ask("资产ID", "asset_001")
    a_name = ask("资产名称", "魔法门")
    print("  资产类型: background / object")
    atype_input = ask("类型", "object")
    try:
        atype = AssetType(atype_input)
    except ValueError:
        atype = AssetType.OBJECT
    a_scene = ask("所属场景", "scene_1")

    print("\n  资产分类 (Phase 1 新增): story / event / environment")
    cls_input = ask("分类", "environment")
    try:
        classification = AssetClassification(cls_input)
    except ValueError:
        classification = AssetClassification.ENVIRONMENT

    related_story = ask("关联剧情节点ID (留空=None)", "")
    related_event = ask("关联事件节点ID (留空=None)", "")

    asset = Asset(
        id=a_id, type=atype, name=a_name, parent_scene=a_scene,
        classification=classification,
        related_story_node=related_story if related_story else None,
        related_event_node=related_event if related_event else None,
    )

    print("\n  --- 你的 Asset 对象 ---")
    print(f"  名称: {asset.name}")
    print(f"  状态: {asset.status.value}")
    print(f"  分类(Phase1新): {asset.classification.value}")
    print(f"  关联Story: {asset.related_story_node}")
    print(f"  关联Event: {asset.related_event_node}")
    print(f"  创建时间: {asset.created_at}")

    print("\n  --- JSON 输出 ---")
    show_json(asset)

    print("\n  --- Round-trip 验证 ---")
    if pass_fail(asset):
        print("  [PASS]")
    else:
        print("  [FAIL]")


# ── menu ────────────────────────────────────────────────

MENU = """
  ==================================================
    Phase 1 交互式验证 — 选一个模型来测试
  ==================================================
    1. StoryGraph   剧情图
    2. EventGraph   事件图
    3. CultureTree  文化树
    4. ConstraintTree 约束树
    5. Asset        资产(含新字段)
    6. 全部跑一遍
    0. 退出
  --------------------------------------------------
"""

FUNCS = {
    "1": test_story,
    "2": test_event,
    "3": test_culture,
    "4": test_constraint,
    "5": test_asset,
}

def main():
    while True:
        print(MENU)
        choice = input("  选哪个: ").strip()
        if choice == "0":
            print("  退出。")
            break
        elif choice == "6":
            for f in [test_story, test_event, test_culture, test_constraint, test_asset]:
                try:
                    f()
                except KeyboardInterrupt:
                    print("\n  跳过。")
                except Exception as e:
                    print(f"\n  出错: {e}")
                input("\n  按回车继续...")
        elif choice in FUNCS:
            try:
                FUNCS[choice]()
            except KeyboardInterrupt:
                print("\n  取消。")
            except Exception as e:
                print(f"\n  出错: {e}")
            input("\n  按回车继续...")
        else:
            print("  无效选择。")

if __name__ == "__main__":
    main()
