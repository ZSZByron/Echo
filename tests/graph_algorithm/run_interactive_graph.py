"""
交互式知识图谱生成测试脚本
=====================================

一步一步手动验证：
  1. AI 从文字提取知识图谱 → 看 JSON
  2. 转成 KnowledgeGraph 对象 → 看节点和边
  3. 环检测 → 看有没有环
  4. 拓扑排序 / 波次 → 看生成顺序
  5. 存入数据库 → 用 SQL 查看表数据

使用方法 (任选一种):

  PyCharm:  右键运行此文件 (解释器选 backend/.venv)
  终端:     cd H:/UGC/backend
            .venv/Scripts/python ../tests/graph_algorithm/run_interactive_graph.py

  每一步会暂停等你按键，可以慢慢看输出。

前置要求:
  - backend/.env 已配置好 LLM API Key
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# ── 路径设置 ──────────────────────────────────────────────
# 本文件: H:/UGC/tests/graph_algorithm/run_interactive_graph.py
# 向上两级到项目根，再进 backend
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent   # H:/UGC
BACKEND_DIR = PROJECT_ROOT / "backend"                          # H:/UGC/backend
GRAPH_ALGO_DIR = Path(__file__).resolve().parent                # H:/UGC/tests/graph_algorithm
sys.path.insert(0, str(GRAPH_ALGO_DIR))

# 加载 .env (显式指定路径，不依赖 cwd)
os.chdir(BACKEND_DIR)
from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")


def pause(msg: str = "") -> None:
    """暂停，等用户按键继续。"""
    if msg:
        print(f"\n  {msg}")
    input("  >> 按 Enter 继续 ...")


def print_separator(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_json(data: dict, label: str = "") -> None:
    """漂亮的 JSON 输出。"""
    if label:
        print(f"\n  ── {label} ──")
    print(json.dumps(data, indent=2, ensure_ascii=False))


# =========================================================================
#  Step 1: AI 提取知识图谱
# =========================================================================


async def step1_extract(scene_desc: str) -> dict:
    """调用 LLM 从场景描述提取知识图谱。"""
    from app.services.graph_extractor import GraphExtractor

    extractor = GraphExtractor()

    print(f"  场景描述: \"{scene_desc}\"")
    print("  正在调用 LLM ... (可能需要几秒)\n")

    raw = await extractor.extract_from_text(scene_desc)

    print_json(raw, "LLM 返回的原始结构化数据")
    pause("这是 AI 从文字中提取出来的知识图谱 JSON。看看节点和边对不对。")

    return raw


# =========================================================================
#  Step 2: 转成 KnowledgeGraph 对象
# =========================================================================


async def step2_to_graph(raw: dict) -> "KnowledgeGraph":
    from app.services.graph_extractor import GraphExtractor

    print_separator("STEP 2: 转换为 KnowledgeGraph 对象")

    graph = GraphExtractor.to_knowledge_graph(raw, scene_id="interactive_test")

    print(f"  scene_id:          {graph.scene_id}")
    print(f"  background_node_id: {graph.background_node_id}")
    print(f"  节点数量:           {len(graph.nodes)}")
    print(f"  边数量:             {len(graph.edges)}")

    print(f"\n  ── 节点列表 ──")
    for nid, node in graph.nodes.items():
        bg_tag = " [背景]" if nid == graph.background_node_id else ""
        print(f"    {nid} (L{node.level}){bg_tag}: {node.description}")

    print(f"\n  ── 边列表 ──")
    for edge in graph.edges:
        arrow = "→"
        etype = "TREE" if edge.edge_type.value == "tree" else "CROSS"
        print(f"    {edge.from_node_id} {arrow} {edge.to_node_id}  [{etype}]")

    pause("看看节点层级和依赖关系是否合理。")

    return graph


# =========================================================================
#  Step 3: 环检测
# =========================================================================


async def step3_cycle_check(graph) -> None:
    from cycle_detector import detect_cycle, validate_graph, find_all_cycles

    print_separator("STEP 3: 环检测 (DFS 三色标记法)")

    cycle = detect_cycle(graph)
    if cycle:
        print(f"  ⚠ 发现环! 路径: {' → '.join(cycle)}")
    else:
        print("  ✓ 无环 (图是合法的 DAG)")

    is_valid, cycles = validate_graph(graph)
    print(f"  validate_graph → is_valid={is_valid}, 发现 {len(cycles)} 个环")

    if cycles:
        for i, c in enumerate(cycles):
            print(f"    环 #{i+1}: {' → '.join(c)}")

    pause()


# =========================================================================
#  Step 4: 拓扑排序 & 生成波次
# =========================================================================


async def step4_topo_and_waves(graph) -> None:
    from topo_sort import layered_topological_sort, get_generation_waves

    print_separator("STEP 4: 拓扑排序 & 生成波次")

    # 拓扑排序
    order = layered_topological_sort(graph)
    print("  ── 拓扑排序 (串行生成顺序) ──")
    print(f"    {' → '.join(order)}")
    print(f"\n    即: 先生成 {order[0]}，最后生成 {order[-1]}")

    pause("这是 AI 资产应该按什么顺序一个个生成。")

    # 波次
    waves = get_generation_waves(graph)
    print("\n  ── 生成波次 (并行调度) ──")
    for i, wave in enumerate(waves):
        if len(wave) == 1:
            print(f"    Wave {i}: ['{wave[0]}']  (单独生成)")
        else:
            print(f"    Wave {i}: {wave}  ← 可同时并行生成!")

    pause("同一个 Wave 里的节点互相独立，可以并行生成。")


# =========================================================================
#  Step 5: 存入数据库 & 查看表数据
# =========================================================================


async def step5_save_and_query(graph) -> str:
    import aiosqlite
    from app.state.graph_store import GraphStore

    print_separator("STEP 5: 存入 SQLite 数据库 & 查看原始表数据")

    # 用一个临时库，不污染正式数据
    db_path = PROJECT_ROOT / "data" / "interactive_test.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # 如果已存在就先删
    if db_path.exists():
        db_path.unlink()

    store = GraphStore(db_path=db_path)
    await store.init_db()
    await store.save_graph(graph)
    print(f"  已保存到: {db_path}")

    # ── 直接用 SQL 查看原始表 ──
    conn = await aiosqlite.connect(str(db_path))

    print("\n  ── graph_nodes 表 (所有节点) ──")
    cursor = await conn.execute(
        "SELECT id, serial_number, level, description, status, background_flag "
        "FROM graph_nodes WHERE scene_id = ? ORDER BY level, serial_number",
        ("interactive_test",),
    )
    rows = await cursor.fetchall()
    print(f"    {'ID':<10} {'Serial':<10} {'Level':<6} {'BG':<4} {'Status':<10} Description")
    print(f"    {'-'*10} {'-'*10} {'-'*6} {'-'*4} {'-'*10} {'-'*30}")
    for row in rows:
        nid, serial, level, desc, status, bg = row
        bg_str = "✓" if bg else ""
        print(f"    {nid:<10} {serial:<10} {level:<6} {bg_str:<4} {status:<10} {desc}")

    print("\n  ── graph_edges 表 (所有边) ──")
    cursor = await conn.execute(
        "SELECT from_node_id, to_node_id, edge_type, visual_description "
        "FROM graph_edges WHERE scene_id = ?",
        ("interactive_test",),
    )
    rows = await cursor.fetchall()
    print(f"    {'From':<10} {'To':<10} {'Type':<8} Visual Description")
    print(f"    {'-'*10} {'-'*10} {'-'*8} {'-'*30}")
    for row in rows:
        from_id, to_id, etype, vdesc = row
        print(f"    {from_id:<10} {to_id:<10} {etype:<8} {vdesc}")

    await cursor.close()
    await conn.close()
    await store.close()

    print(f"\n  数据库文件位置: {db_path}")
    print(f"  你也可以用 DB Browser for SQLite 打开查看。")
    pause("所有数据已存入 SQLite。核心流程验证完毕!")

    return str(db_path)


# =========================================================================
#  主流程
# =========================================================================


# 预设几个场景描述，你也可以自己改
DEFAULT_SCENE = "一座废弃的古代神殿，入口处有一扇上锁的石门，旁边墙壁上刻着发光的符文。门后是一个祭坛，上面放着一把生锈的钥匙。"


async def main():
    print_separator("交互式知识图谱生成测试")
    print("  这个脚本会一步步展示 AI 如何从文字生成知识图谱。")
    print("  每一步都会暂停，你可以仔细看输出。\n")
    print(f"  场景描述 (可改脚本里的 DEFAULT_SCENE):\n    \"{DEFAULT_SCENE}\"")

    pause("准备好了就开始!")

    # Step 1: AI 提取
    raw = await step1_extract(DEFAULT_SCENE)

    # Step 2: 转 KnowledgeGraph
    graph = await step2_to_graph(raw)

    # Step 3: 环检测
    await step3_cycle_check(graph)

    # Step 4: 拓扑排序 & 波次
    await step4_topo_and_waves(graph)

    # Step 5: 存库 & 查表
    db_path = await step5_save_and_query(graph)

    print_separator("全部完成!")
    print(f"  数据库: {db_path}")
    print(f"  用 DB Browser for SQLite 打开可以继续查看/编辑。\n")


if __name__ == "__main__":
    asyncio.run(main())
