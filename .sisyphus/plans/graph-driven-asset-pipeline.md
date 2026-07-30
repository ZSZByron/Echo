# 图谱驱动的分层资产生成系统

## TL;DR

> **Quick Summary**: 将资产生成从「并发独立生成」重新设计为「图谱驱动的分层串行生成」。资产是知识图谱的节点，生成顺序由 DAG 拓扑排序决定，prompt 融合节点主体+关联衔接+背景光影。分三阶段交付：Phase 1 纯算法验证（排序+环检测），Phase 2 后端集成（服务+API+调度器），Phase 3 前端（共享层+React Flow编辑器+资产生成页）。
>
> **Deliverables**:
> - Phase 1: 算法验证套件（KnowledgeGraph模型 + 序号解析 + 分层拓扑排序 + 环检测 + pytest测试）
> - Phase 2: 后端（SQLite图谱持久化 + LLM提取服务 + Prompt融合服务 + 串行调度器 + API端点）
> - Phase 3: 前端（共享基础设施 + React Flow图谱编辑器 + 资产生成页面变体）
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 8 waves total (2+4+2+FINAL)
> **Critical Path**: T1(模型) → T3(排序) → T8(Prompt融合) → T9(调度器) → T10(API) → T12(前端共享层) → T13(编辑器) → T15(测试) → F1-F3

---

## Context

### Original Request
当前资产生成系统的核心断裂：`generate-all` 和 `orchestrate_scene` 虽然调用 GenerationPlanner 排序，但用 `asyncio.create_task` 全部并发丢出，排序形同虚设。资产B开始生成时资产A可能还没完成，`reference_asset_ids` 里过滤 APPROVED/COMPLETED 的参考全为空。PromptBuilder 写好了但没接入生成流程。所有资产实际是各自独立生成的，彼此之间没有任何逻辑关联。

用户要求：资产必须是知识图谱的节点，生成顺序由图的拓扑结构决定，prompt 必须融合节点描述+边描述+背景信息。

### Interview Summary
**Key Discussions**:
- **图谱构建**: LLM从自由文本提取骨架 → 用户在React Flow界面编辑 → 每条边必须手写视觉关系描述
- **层级定义**: 0级=背景视角, 1级=一次互动, 2级=两次互动, N级=N次嵌套
- **序号编码**: 树形路径 `1`, `1-1`, `2-1`, 位数越多越下级，同位数按描述顺序
- **生成算法**: 自底向上（叶子先），1对多星型（叶子先→核心后），跨树边=全局依赖
- **环检测**: 钥匙→箱子→线索→钥匙=死锁，建图谱时警告
- **Prompt融合**: 【生成主体】+【关联衔接描述】+【背景光影】，只含视觉信息不含游戏逻辑
- **两个界面**: 图谱编辑器（React Flow）+ 资产生成页面（AssetReview变体）

### Metis Review
**Identified Gaps** (addressed):
- 序号编码与生成顺序混淆 → 明确为两个独立概念，序号=层级标识，生成顺序=DAG拓扑排序
- 串行vs并发 → B方案：依赖串行+无关并发（asyncio信号量实现）
- 0级背景顺序 → 永远第一个生成（当前系统是最后，需反转）
- PromptBuilder命运 → 替换为新3段结构，旧的标记legacy
- 星型叶子失败策略 → 跳过失败叶子的引用，核心节点用已有完成节点生成
- 数据持久化 → SQLite（graph_nodes + graph_edges表），不用manifest.json存图数据
- 资产创建时机 → 图谱编辑完成后一次性创建所有Asset对象

---

## Work Objectives

### Core Objective
资产是知识图谱节点，生成顺序由分层拓扑排序决定，生成时融合节点+边+背景的视觉描述。Phase 1 验证算法正确性，Phase 2-3 构建完整系统。

### Concrete Deliverables
- `tests/graph_algorithm/` — 算法验证套件（Phase 1）
- `backend/app/models/knowledge_graph.py` — 核心数据模型
- `backend/app/services/graph_extractor.py` — LLM图谱提取服务
- `backend/app/services/prompt_fusion.py` — 3段prompt融合服务
- `backend/app/services/generation_scheduler.py` — 串行生成调度器
- `backend/app/api/graph_routes.py` — 图谱API端点
- `frontend/src/api/graph.ts` — 图谱API客户端（共享层）
- `frontend/src/types/graph.ts` — TypeScript类型定义（共享层）
- `frontend/src/components/graph/` — 共享UI组件（NodeBadge/WaveDivider/PromptPreview）
- `frontend/src/pages/GraphEditor.tsx` — React Flow图谱编辑器
- `frontend/src/pages/GraphAssetReview.tsx` — 资产生成页面变体

### Definition of Done
- [ ] Phase 1: 算法测试全部PASS（6+核心用例，覆盖率≥95%）
- [ ] Phase 2: 后端API可创建/编辑图谱，触发串行生成
- [ ] Phase 3: 前端共享层+可视化编辑图谱+按生成顺序查看资产
- [ ] 生成顺序：0级背景先 → 叶子节点 → 核心节点 → 逐级向上
- [ ] 环检测：建图谱时检测并报告环路径
- [ ] Prompt融合：3段结构正确发送给ImageGenerator

### Must Have
- KnowledgeGraph数据模型（节点+边+序号+层级）
- 分层拓扑排序算法（自底向上+度数优先+序号次优先）
- 环检测算法（返回环路径，不只True/False）
- LLM自由文本→图谱骨架提取
- 串行生成调度器（依赖串行+无关并发）
- Prompt 3段融合（主体+关联衔接+背景光影）
- 前端共享基础设施（API客户端+类型定义+共享组件）
- React Flow图谱编辑器
- 资产生成页面（按生成顺序排列+prompt预览+Generation Timeline视图）
- SQLite图谱持久化

### Must NOT Have (Guardrails)
- **不修改**现有 SceneGraph / PuzzleGraph / PromptBuilder（标记legacy）
- **不修改**现有 ImageGenerator（直接复用）
- **不实现**自动边描述生成（用户必须手写）
- **不实现**自动图谱布局算法（React Flow默认布局）
- **不实现**实时协同编辑（WebSocket）
- **不实现**图谱版本控制/历史回退
- **不实现**多场景图谱管理（demo只支持单场景）
- **不实现**生成重试/退避策略
- **不实现**自动重新生成prompt（用户修改边描述后手动触发）
- **不实现**完整剧情编号+地点编号+视角编号体系（demo简化为0级）
- **不加**无用注释/过度抽象/AI slop
- **不在**Phase 1触碰任何现有业务代码或前端

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: YES (pytest + pytest-cov)
- **Automated tests**: TDD for Phase 1 algorithm, Tests-after for Phase 2-3
- **Framework**: pytest (backend), Playwright (frontend)

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Algorithm**: Bash (pytest) — run test suite, assert all pass
- **Backend API**: Bash (curl) — call endpoints, assert response
- **Frontend UI**: Playwright — navigate, interact, assert DOM, screenshot
- **Generation Flow**: Bash (python -c) — mock ImageGenerator, assert order + reference passing

---

## Execution Strategy

### Phase 1 — 算法验证 (test文件夹, 不触碰现有代码)

```
Wave 1 (Start Immediately - 算法核心, ALL PARALLEL):
├── Task 1: KnowledgeGraph数据模型 [deep]
├── Task 2: 序号编码解析器 [quick]
├── Task 3: 分层拓扑排序算法 [deep]
└── Task 4: 环检测算法 [deep]

Wave 2 (After Wave 1 - 测试验证):
└── Task 5: 算法测试套件 (6+核心用例) [unspecified-high]
```

### Phase 2 — 后端集成

```
Wave 3a (After Phase 1 PASS - 后端服务, 3 PARALLEL):
├── Task 6: SQLite图谱持久化 [deep] (depends: 1)
├── Task 7: LLM图谱提取服务 [deep] (depends: 1)
└── Task 8: Prompt融合服务 [deep] (depends: 1)

Wave 3b (After Wave 3a - 调度器, depends on T8):
└── Task 9: 串行生成调度器 [deep] (depends: 3, 4, 8)

Wave 4 (After Wave 3b - API + 集成):
├── Task 10: 图谱API端点 [deep] (depends: 6, 7, 8, 9)
└── Task 11: 后端集成测试 [unspecified-high] (depends: 10)
```

### Phase 3 — 前端

```
Wave 5 (After Wave 4 - 前端共享基础设施):
└── Task 12: 前端共享层 (graph.ts + types + 共享组件) [visual-engineering] (depends: 10)

Wave 6 (After Wave 5 - 前端页面, PARALLEL):
├── Task 13: React Flow图谱编辑器 [visual-engineering] (depends: 12)
└── Task 14: 资产生成页面变体 [visual-engineering] (depends: 12)

Wave 7 (After Wave 6 - 前端测试):
└── Task 15: 前端Playwright测试 [unspecified-high] (depends: 13, 14)
```

### Final Verification Wave

```
Wave FINAL (After ALL tasks — 3 parallel reviews):
├── Task F1: 合规审计 + 代码质量 (oracle)
├── Task F2: 端到端QA (unspecified-high + playwright)
└── Task F3: 范围一致性检查 (deep)
-> Present results -> Get explicit user okay
```

### Dependency Matrix

| Task | Depends On | Blocks | Phase |
|------|-----------|--------|-------|
| 1 | - | 5, 6, 7, 8, 9 | 1 |
| 2 | - | 5 | 1 |
| 3 | - | 5, 9 | 1 |
| 4 | - | 5, 9 | 1 |
| 5 | 1, 2, 3, 4 | 6-15 | 1 |
| 6 | 1, 5 | 10 | 2 |
| 7 | 1, 5 | 10 | 2 |
| 8 | 1, 5 | 9, 10 | 2 |
| 9 | 3, 4, 5, **8** | 10 | 2 |
| 10 | 6, 7, 8, 9 | 11, 12 | 2 |
| 11 | 10 | F1-F3 | 2 |
| 12 | 10 | 13, 14 | 3 |
| 13 | 12 | 15 | 3 |
| 14 | 12 | 15 | 3 |
| 15 | 13, 14 | F1-F3 | 3 |

Critical Path: T1 → T3 → T8 → T9 → T10 → T12 → T13 → T15 → F1-F3

### Agent Dispatch Summary

- **Wave 1**: 4 tasks — T1 → `deep`, T2 → `quick`, T3 → `deep`, T4 → `deep`
- **Wave 2**: 1 task — T5 → `unspecified-high`
- **Wave 3a**: 3 tasks — T6 → `deep`, T7 → `deep`, T8 → `deep`
- **Wave 3b**: 1 task — T9 → `deep` (after T8)
- **Wave 4**: 2 tasks — T10 → `deep`, T11 → `unspecified-high`
- **Wave 5**: 1 task — T12 → `visual-engineering`
- **Wave 6**: 2 tasks — T13 → `visual-engineering`, T14 → `visual-engineering`
- **Wave 7**: 1 task — T15 → `unspecified-high`
- **FINAL**: 3 tasks — F1 → `oracle`, F2 → `unspecified-high`, F3 → `deep`

---

## TODOs

- [ ] 1. **KnowledgeGraph 数据模型**

  **What to do**:
  - 新建根目录 `tests/graph_algorithm/` 目录（用户明确要求"根目录的测试文件夹"）
  - 新建 `backend/app/models/knowledge_graph.py` — **正式模型定义（canonical）**，Phase 2 服务从此导入
  - 新建 `tests/graph_algorithm/models.py` — 从 `backend/app/models/knowledge_graph.py` re-export（`from backend.app.models.knowledge_graph import *`），供算法测试直接导入
  - 定义 `GraphNode` 模型：id, serial_number(如"1-1-1"), level(0/1/2...), description(资产视觉描述), status(pending/generating/completed/failed)
  - 定义 `GraphEdge` 模型：from_node_id, to_node_id, edge_type(tree/cross), visual_description(用户手写的视觉关系描述)
  - 定义 `KnowledgeGraph` 模型：scene_id, nodes(dict), edges(list), background_node_id
  - `KnowledgeGraph.add_node(serial, description)` — 自动解析level
  - `KnowledgeGraph.add_edge(from_id, to_id, visual_desc, edge_type)` — 添加边
  - `KnowledgeGraph.get_dependencies(node_id)` — 返回该节点的所有入边来源
  - `KnowledgeGraph.get_dependents(node_id)` — 返回该节点的所有出边目标
  - 序列化/反序列化方法：`to_dict()` / `from_dict()`
  - **重要**: 所有类定义写在 `backend/app/models/knowledge_graph.py`，`tests/graph_algorithm/models.py` 只做 re-export，避免代码重复

  **Must NOT do**:
  - 不修改现有 scene_graph.py / puzzle_graph.py
  - 不连接数据库（Phase 1纯模型）
  - 不调用LLM
  - 不实现排序算法（Task 3）或环检测（Task 4）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 核心数据模型设计，需要深入理解层级和依赖关系
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 2, 3, 4)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 5, 6, 7, 8, 9
  - **Blocked By**: None

  **References**:
  - `backend/app/models/puzzle_graph.py` — Pydantic模型模式参考（BaseModel + 类方法）
  - `backend/app/models/asset.py` — Asset模型字段参考（status枚举等）
  - `backend/app/models/scene_graph.py` — 现有图模型参考（但独立实现）

  **WHY Each Reference Matters**:
  - puzzle_graph.py: 展示了如何用Pydantic建图模型 + from_yaml类方法模式
  - asset.py: 提供AssetStatus枚举值，GraphNode.status应对齐
  - scene_graph.py: 展示现有图结构，新模型必须独立不依赖它

  **Acceptance Criteria**:
  - [ ] GraphNode, GraphEdge, KnowledgeGraph 三个类定义完成
  - [ ] 正式模型在 `backend/app/models/knowledge_graph.py`，测试 re-export 在 `tests/graph_algorithm/models.py`
  - [ ] `add_node("1-1-1", "test")` 自动解析 level=3
  - [ ] `add_edge("1", "1-1", "visual desc", "tree")` 成功添加边
  - [ ] `get_dependencies("1-1")` 返回 `["1"]`
  - [ ] `to_dict()` / `from_dict()` 往返一致

  **QA Scenarios**:
  ```
  Scenario: Node creation and level parsing
    Tool: Bash (python -c)
    Preconditions: models.py 已创建
    Steps:
      1. cd H:\UGC && python -c "
         import sys; sys.path.insert(0, 'tests/graph_algorithm')
         from models import KnowledgeGraph, GraphNode
         g = KnowledgeGraph(scene_id='test')
         g.add_node('1', 'background scene')
         g.add_node('1-1', 'altar')
         g.add_node('1-1-1', 'crystal on altar')
         assert g.nodes['1'].level == 1
         assert g.nodes['1-1'].level == 2
         assert g.nodes['1-1-1'].level == 3
         print('PASS')"
    Expected Result: 输出 PASS
    Failure Indicators: AssertionError 或 ImportError
    Evidence: .sisyphus/evidence/task-1-node-creation.txt

  Scenario: Edge and dependencies
    Tool: Bash (python -c)
    Steps:
      1. cd H:\UGC && python -c "
         import sys; sys.path.insert(0, 'tests/graph_algorithm')
         from models import KnowledgeGraph
         g = KnowledgeGraph(scene_id='test')
         g.add_node('1', 'corpse')
         g.add_node('1-1', 'book on corpse')
         g.add_node('2', 'door')
         g.add_edge('1', '1-1', 'book is on top of corpse', 'tree')
         g.add_edge('1-1', '2', 'book clue relates to door', 'cross')
         deps = g.get_dependencies('1-1')
         assert '1' in deps
         deps2 = g.get_dependencies('2')
         assert '1-1' in deps2
         print('PASS')"
    Expected Result: 输出 PASS
    Evidence: .sisyphus/evidence/task-1-edge-deps.txt
  ```

  **Commit**: YES
  - Message: `feat(algorithm): create KnowledgeGraph data model with nodes, edges, and level parsing`
  - Files: `backend/app/models/knowledge_graph.py`, `tests/graph_algorithm/models.py`

---

- [ ] 2. **序号编码解析器**

  **What to do**:
  - 新建 `tests/graph_algorithm/serial_parser.py`
  - 定义 `parse_serial(serial: str) -> dict` 函数
  - 解析 `"1"` → `{"path": [1], "level": 1, "segments": 1}`
  - 解析 `"1-1"` → `{"path": [1, 1], "level": 2, "segments": 2}`
  - 解析 `"1-1-1"` → `{"path": [1, 1, 1], "level": 3, "segments": 3}`
  - 定义 `compare_serial(s1: str, s2: str) -> int` 函数
    - 位数多的排后面（更深层级）
    - 同位数按路径数值排（1 < 2, 1-1 < 1-2, 1-1 < 2-1）
    - 返回 -1/0/1
  - 定义 `get_generation_priority(serial: str, degree: int) -> tuple` 函数
    - 返回排序键 `(degree, serial_path)` 用于拓扑排序同级节点排序
    - degree = 入度（度数低的优先，Kahn's 中天然处理）
    - serial_path = 路径元组（序号小的优先，用户描述顺序）
    - 注：level 不作为排序键——Kahn's 保证依赖先于被依赖生成，层级关系已由边编码

  **Must NOT do**:
  - 不依赖 Task 1 的模型（独立函数）
  - 不处理环检测（Task 4）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 纯函数工具，逻辑清晰
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 1, 3, 4)
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 5
  - **Blocked By**: None

  **References**:
  - 无代码参考（纯数学函数）
  - 用户定义的序号规则：位数越多越下级，同位数按描述顺序

  **Acceptance Criteria**:
  - [ ] `parse_serial("1-1-1")` 返回 level=3, path=[1,1,1]
  - [ ] `compare_serial("1", "1-1")` 返回 -1（1在1-1前面）
  - [ ] `compare_serial("1-1", "2-1")` 返回 -1（1-1在2-1前面）
  - [ ] `compare_serial("1-2", "1-1")` 返回 1（1-2在1-1后面）
  - [ ] `get_generation_priority("1-1", 0)` 返回的元组 < `get_generation_priority("2-1", 0)` 返回的元组（同度数序号小优先）

  **QA Scenarios**:
  ```
  Scenario: Serial parsing
    Tool: Bash (python -c)
    Steps:
      1. cd H:\UGC && python -c "
         import sys; sys.path.insert(0, 'tests/graph_algorithm')
         from serial_parser import parse_serial, compare_serial, get_generation_priority
         r = parse_serial('1-1-1')
         assert r['level'] == 3
         assert r['path'] == [1, 1, 1]
         assert compare_serial('1', '1-1') == -1
         assert compare_serial('1-1', '2-1') == -1
         assert compare_serial('1-2', '1-1') == 1
         # 同度数时序号小优先
         p1 = get_generation_priority('1-1', 0)
         p2 = get_generation_priority('2-1', 0)
         assert p1 < p2
         print('PASS')"
    Expected Result: 输出 PASS
    Evidence: .sisyphus/evidence/task-2-serial-parser.txt
  ```

  **Commit**: YES (groups with Task 1)
  - Message: `feat(algorithm): implement serial number parser with level and priority comparison`
  - Files: `tests/graph_algorithm/serial_parser.py`

---

- [ ] 3. **分层拓扑排序算法**

  **What to do**:
  - 新建 `tests/graph_algorithm/topo_sort.py`
  - 实现 `layered_topological_sort(graph: KnowledgeGraph) -> list[str]` 函数
  - **算法逻辑**:
    1. 先取出 `background_node_id`（0级背景）作为顺序的第一个，无论入度如何
    2. 对剩余节点运行 Kahn's 算法：
       - 计算每个节点入度（依赖数量 = 指向该节点的边数）
       - 每次取入度为0的节点中，序号最小（serial_asc）的优先
       - 取出后减少其后继节点的入度
       - 重复直到所有节点取出
    3. 注意：degree_asc 在 Kahn's 中天然满足（入度0=无依赖=叶子），无需单独作为排序键
    4. 0级背景已在步骤1取出，不参与 Kahn's 排序
  - **排序规则说明**（澄清用户意图）:
    - 链式结构（1对1）：序号小的是前置，先生成（如 1 先于 1-1）
    - 星型结构（1对多）：叶子（入度0）先，核心（入度>0）后
    - 这两种情况都由 Kahn's "入度0先 + 序号小优先" 自然处理，无需"自底向上"特殊逻辑
  - 实现 `get_generation_waves(graph: KnowledgeGraph) -> list[list[str]]` 函数
    - 返回分波列表：同一波内的节点可以并发生成（无依赖关系）
    - Wave 0: [background_node_id]（背景永远单独第一波）
    - Wave N (N>=1): 当前所有入度0的节点（扣除背景后）
    - 波之间严格串行（前一波全部完成才能开始下一波）

  **Must NOT do**:
  - 不实现环检测（Task 4负责，但调用方应先检查）
  - 不修改 Task 1 的模型
  - 不处理生成失败重试

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 核心算法，需要正确处理优先级和依赖关系
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 1, 2, 4)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 5, 9
  - **Blocked By**: None

  **References**:
  - `backend/app/services/generation_planner.py` — 现有Kahn's算法实现参考（全文237行，重点关注拓扑排序逻辑）
  - **⚠️ 警告**: generation_planner.py 使用 LOD priority (near→mid→far→**bg最后**)，新系统的背景排序**完全相反**（0级背景永远第一个）。参考其 Kahn's 基本结构即可，**绝对不要照搬其 LOD priority 逻辑或背景排序逻辑**。
  - Task 2 的 `get_generation_priority()` 函数 — 优先级计算

  **WHY Each Reference Matters**:
  - generation_planner.py: 展示了Kahn's算法的基本结构，但需要加入序号优先级和0级背景特殊处理
  - serial_parser: 提供优先级排序键，拓扑排序中用于同级节点的排序

  **Acceptance Criteria**:
  - [ ] `layered_topological_sort(graph)` 返回有序节点ID列表
  - [ ] 0级背景节点在列表第一位
  - [ ] 叶子节点（入度0）在核心节点之前
  - [ ] 同层节点按序号排序
  - [ ] `get_generation_waves(graph)` 返回分波列表，同波内无依赖关系
  - [ ] 星型结构：叶子在同一波，核心在下一波

  **QA Scenarios**:
  ```
  Scenario: Linear chain ordering
    Tool: Bash (python -c)
    Preconditions: Task 1 models.py 存在
    Steps:
      1. cd H:\UGC && python -c "
         import sys; sys.path.insert(0, 'tests/graph_algorithm')
         from models import KnowledgeGraph
         from topo_sort import layered_topological_sort
         g = KnowledgeGraph(scene_id='test')
         g.background_node_id = '0'
         g.add_node('0', 'background')
         g.add_node('1', 'corpse')
         g.add_node('1-1', 'book')
         g.add_edge('0', '1', 'bg to corpse', 'tree')
         g.add_edge('1', '1-1', 'corpse to book', 'tree')
         order = layered_topological_sort(g)
         assert order[0] == '0'
         assert order.index('1') < order.index('1-1')
         print('PASS')"
    Expected Result: 输出 PASS
    Evidence: .sisyphus/evidence/task-3-linear-chain.txt

  Scenario: Star structure (1-to-many)
    Tool: Bash (python -c)
    Steps:
      1. cd H:\UGC && python -c "
         import sys; sys.path.insert(0, 'tests/graph_algorithm')
         from models import KnowledgeGraph
         from topo_sort import layered_topological_sort, get_generation_waves
         g = KnowledgeGraph(scene_id='test')
         g.background_node_id = '0'
         g.add_node('0', 'bg')
         g.add_node('1', 'parent')
         g.add_node('1-1', 'child1')
         g.add_node('1-2', 'child2')
         g.add_node('1-3', 'child3')
         g.add_edge('0', '1', '', 'tree')
         g.add_edge('1-1', '1', '', 'tree')
         g.add_edge('1-2', '1', '', 'tree')
         g.add_edge('1-3', '1', '', 'tree')
         waves = get_generation_waves(g)
         # Wave 0: bg, Wave 1: children (parallel), Wave 2: parent
         assert waves[0] == ['0']
         assert set(waves[1]) == {'1-1', '1-2', '1-3'}
         assert waves[2] == ['1']
         print('PASS')"
    Expected Result: 输出 PASS
    Evidence: .sisyphus/evidence/task-3-star-structure.txt

  Scenario: Cross-tree dependency
    Tool: Bash (python -c)
    Steps:
      1. cd H:\UGC && python -c "
         import sys; sys.path.insert(0, 'tests/graph_algorithm')
         from models import KnowledgeGraph
         from topo_sort import layered_topological_sort
         g = KnowledgeGraph(scene_id='test')
         g.background_node_id = '0'
         g.add_node('0', 'bg')
         g.add_node('1', 'corpse')
         g.add_node('1-1', 'book')
         g.add_node('1-1-1', 'password')
         g.add_node('2', 'door')
         g.add_node('2-1', 'lock')
         # Tree edges
         g.add_edge('0', '1', '', 'tree')
         g.add_edge('1', '1-1', '', 'tree')
         g.add_edge('1-1', '1-1-1', '', 'tree')
         g.add_edge('0', '2', '', 'tree')
         g.add_edge('2', '2-1', '', 'tree')
         # Cross-tree: lock depends on password
         g.add_edge('1-1-1', '2-1', 'password opens lock', 'cross')
         order = layered_topological_sort(g)
         assert order[0] == '0'
         assert order.index('1-1-1') < order.index('2-1')
         print('PASS')"
    Expected Result: 输出 PASS
    Evidence: .sisyphus/evidence/task-3-cross-tree.txt
  ```

  **Commit**: YES
  - Message: `feat(algorithm): implement layered topological sort with depth-first and degree priority`
  - Files: `tests/graph_algorithm/topo_sort.py`

---

- [ ] 4. **环检测算法**

  **What to do**:
  - 新建 `tests/graph_algorithm/cycle_detector.py`
  - 实现 `detect_cycle(graph: KnowledgeGraph) -> list[str] | None` 函数
  - **算法**: DFS三色标记法（White/Gray/Black）
    - White: 未访问, Gray: 正在访问（在当前DFS路径上）, Black: 已完成
    - 遇到Gray节点 = 发现环
    - 回溯收集环路径
  - 返回环路径列表（如 `["钥匙", "箱子", "线索", "钥匙"]`），无环返回None
  - 实现 `find_all_cycles(graph: KnowledgeGraph) -> list[list[str]]` 函数
    - 找出图中所有独立的环
    - 用于前端高亮显示所有冲突边
  - 实现 `validate_graph(graph: KnowledgeGraph) -> tuple[bool, list[list[str]]]` 函数
    - 返回 (is_valid, cycles)
    - is_valid=True 当且仅当无环

  **Must NOT do**:
  - 不修改图（只读检测）
  - 不自动断开环（只报告，由用户决定如何处理）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 环检测需要正确回溯路径，边界情况多
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 1, 2, 3)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 5, 9
  - **Blocked By**: None

  **References**:
  - 无代码参考（标准图论算法）
  - 用户场景：钥匙→箱子→线索→钥匙 = 死锁

  **Acceptance Criteria**:
  - [ ] 无环图: `detect_cycle(graph)` 返回 None
  - [ ] 有环图: `detect_cycle(graph)` 返回环路径列表
  - [ ] 环路径首尾相同（如 `["A", "B", "C", "A"]`）
  - [ ] `find_all_cycles(graph)` 找出所有独立环
  - [ ] `validate_graph(graph)` 返回 (True, []) 对无环图
  - [ ] `validate_graph(graph)` 返回 (False, cycles) 对有环图

  **QA Scenarios**:
  ```
  Scenario: No cycle detection
    Tool: Bash (python -c)
    Steps:
      1. cd H:\UGC && python -c "
         import sys; sys.path.insert(0, 'tests/graph_algorithm')
         from models import KnowledgeGraph
         from cycle_detector import detect_cycle, validate_graph
         g = KnowledgeGraph(scene_id='test')
         g.add_node('1', 'a')
         g.add_node('1-1', 'b')
         g.add_node('2', 'c')
         g.add_edge('1', '1-1', '', 'tree')
         g.add_edge('1-1', '2', '', 'cross')
         assert detect_cycle(g) is None
         is_valid, cycles = validate_graph(g)
         assert is_valid is True
         assert len(cycles) == 0
         print('PASS')"
    Expected Result: 输出 PASS
    Evidence: .sisyphus/evidence/task-4-no-cycle.txt

  Scenario: Cycle detection with path
    Tool: Bash (python -c)
    Steps:
      1. cd H:\UGC && python -c "
         import sys; sys.path.insert(0, 'tests/graph_algorithm')
         from models import KnowledgeGraph
         from cycle_detector import detect_cycle, find_all_cycles
         g = KnowledgeGraph(scene_id='test')
         g.add_node('1', 'key')
         g.add_node('2', 'box')
         g.add_node('3', 'clue')
         g.add_edge('1', '2', '', 'cross')
         g.add_edge('2', '3', '', 'cross')
         g.add_edge('3', '1', '', 'cross')  # cycle: 1->2->3->1
         cycle = detect_cycle(g)
         assert cycle is not None
         assert len(cycle) >= 4  # path includes return to start
         assert cycle[0] == cycle[-1]  # first == last
         all_cycles = find_all_cycles(g)
         assert len(all_cycles) >= 1
         print('PASS')"
    Expected Result: 输出 PASS
    Evidence: .sisyphus/evidence/task-4-cycle-detection.txt
  ```

  **Commit**: YES
  - Message: `feat(algorithm): implement cycle detection with DFS three-color marking and path reporting`
  - Files: `tests/graph_algorithm/cycle_detector.py`

---

- [ ] 5. **算法测试套件 (Phase 1 Gate)**

  **What to do**:
  - 新建 `tests/graph_algorithm/test_algorithm.py`
  - 编写6+核心测试用例，覆盖所有算法场景：
    1. **空图**: 空KnowledgeGraph的排序和环检测
    2. **单节点**: 只有0级背景的图
    3. **纯链**: 0→1→1-1→1-1-1 线性依赖
    4. **纯星型**: 0→1, 1-1→1, 1-2→1, 1-3→1（叶子并发生成）
    5. **多树+跨树边**: 两棵子树 + 跨树依赖（密码→锁）
    6. **环图**: A→B→C→A 死锁检测
  - 每个测试用例使用具体数据（具体节点ID、具体描述、具体边）
  - 覆盖率目标: ≥95%
  - 新建 `tests/graph_algorithm/__init__.py` 使其成为可导入包

  **Must NOT do**:
  - 不修改 Task 1-4 的实现代码（只写测试）
  - 不使用mock（算法是纯函数/纯模型，不需要mock）
  - 不创建占位符测试（每个测试必须有具体断言）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 综合测试任务，需要验证所有算法的正确性
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (Phase 1 gate)
  - **Blocks**: Tasks 6-14 (Phase 2 starts after this passes)
  - **Blocked By**: Tasks 1, 2, 3, 4

  **References**:
  - `backend/tests/unit/test_asset_store.py` — 现有测试风格参考
  - Tasks 1-4 的产出代码

  **Acceptance Criteria**:
  - [ ] 6+核心测试用例全部PASS
  - [ ] 覆盖率 ≥ 95%
  - [ ] 纯链测试: 排序顺序正确
  - [ ] 星型测试: 叶子在同一波，核心在下一波
  - [ ] 跨树测试: 跨树依赖影响排序
  - [ ] 环测试: 返回具体环路径

  **QA Scenarios**:
  ```
  Scenario: Full algorithm test suite
    Tool: Bash (pytest)
    Preconditions: Tasks 1-4 全部完成
    Steps:
      1. cd H:\UGC && backend\.venv\Scripts\python -m pytest tests/graph_algorithm/ -v --cov=tests/graph_algorithm --cov-report=term-missing
    Expected Result: 6+ tests PASS, coverage ≥ 95%
    Failure Indicators: 任何测试FAIL 或 覆盖率 < 95%
    Evidence: .sisyphus/evidence/task-5-test-suite.txt

  Scenario: Star structure wave verification
    Tool: Bash (python -c)
    Steps:
      1. cd H:\UGC && python -c "
         import sys; sys.path.insert(0, 'tests/graph_algorithm')
         from models import KnowledgeGraph
         from topo_sort import get_generation_waves
         g = KnowledgeGraph(scene_id='star')
         g.background_node_id = '0'
         g.add_node('0', 'bg')
         g.add_node('1', 'core')
         g.add_node('1-1', 'leaf1')
         g.add_node('1-2', 'leaf2')
         g.add_node('1-3', 'leaf3')
         g.add_edge('0', '1', '', 'tree')
         g.add_edge('1-1', '1', '', 'tree')
         g.add_edge('1-2', '1', '', 'tree')
         g.add_edge('1-3', '1', '', 'tree')
         waves = get_generation_waves(g)
         assert len(waves) == 3  # bg, leaves, core
         assert set(waves[1]) == {'1-1', '1-2', '1-3'}  # leaves in same wave
         assert waves[2] == ['1']  # core in last wave
         print('PASS')"
    Expected Result: 输出 PASS
    Evidence: .sisyphus/evidence/task-5-star-waves.txt
  ```

  **Commit**: YES
  - Message: `test(algorithm): comprehensive test suite for graph algorithm (6+ cases, 95%+ coverage)`
  - Files: `tests/graph_algorithm/test_algorithm.py`, `tests/graph_algorithm/__init__.py`

---

- [ ] 6. **SQLite 图谱持久化**

  **What to do**:
  - 新建 `backend/app/state/graph_store.py`
  - 使用 aiosqlite 创建两张表:
    - `graph_nodes`: id, scene_id, serial_number, level, description, status, background_flag, created_at
    - `graph_edges`: id, scene_id, from_node_id, to_node_id, edge_type, visual_description, created_at
  - 实现 `GraphStore` 类:
    - `async save_graph(graph: KnowledgeGraph)` — 保存整个图（upsert）
    - `async load_graph(scene_id: str) -> KnowledgeGraph` — 加载图
    - `async delete_graph(scene_id: str)` — 删除图
    - `async add_node(scene_id, node: GraphNode)` — 增量添加
    - `async add_edge(scene_id, edge: GraphEdge)` — 增量添加
    - `async update_node_description(scene_id, node_id, description)` — 更新描述
    - `async update_edge_description(scene_id, edge_id, visual_desc)` — 更新边描述
  - 数据库路径: `data/assets/graph.db`（与现有 manifest.json 同目录）
  - 在 `backend/app/state/migrations.py` 中添加建表SQL（如文件不存在则新建）

  **Must NOT do**:
  - 不修改现有 AssetStore（manifest.json 保留给Asset用）
  - 不修改现有 scene_graph.py / puzzle_graph.py
  - 不用 SQLAlchemy（直接用 aiosqlite，保持轻量）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 数据库层设计，需要正确的async操作和schema设计
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 7, 8)
  - **Parallel Group**: Wave 3a
  - **Blocks**: Task 10
  - **Blocked By**: Task 1 (模型), Task 5 (Phase 1 gate)

  **References**:
  - `backend/app/state/asset_store.py` — 现有存储模式参考（但用JSON，这里用SQLite）
  - `backend/app/models/knowledge_graph.py` — KnowledgeGraph/GraphNode/GraphEdge 模型定义(Task 1 canonical产出)
  - 项目已有 aiosqlite 依赖

  **Acceptance Criteria**:
  - [ ] `graph_nodes` 和 `graph_edges` 两张表创建成功
  - [ ] `save_graph` + `load_graph` 往返一致
  - [ ] `add_node` / `add_edge` 增量操作正确
  - [ ] `update_node_description` / `update_edge_description` 更新正确
  - [ ] `delete_graph` 清除指定场景的所有节点和边

  **QA Scenarios**:
  ```
  Scenario: Graph persistence round-trip
    Tool: Bash (python -c)
    Preconditions: 后端环境可用
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         import asyncio
         import sys; sys.path.insert(0, '../tests/graph_algorithm')
         from models import KnowledgeGraph, GraphNode, GraphEdge
         from app.state.graph_store import GraphStore
         async def test():
             store = GraphStore()
             g = KnowledgeGraph(scene_id='test_persist')
             g.background_node_id = '0'
             g.add_node('0', 'bg desc')
             g.add_node('1', 'corpse desc')
             g.add_edge('0', '1', 'visual relation', 'tree')
             await store.save_graph(g)
             loaded = await store.load_graph('test_persist')
             assert '0' in loaded.nodes
             assert '1' in loaded.nodes
             assert loaded.nodes['1'].description == 'corpse desc'
             assert len(loaded.edges) == 1
             assert loaded.edges[0].visual_description == 'visual relation'
             await store.delete_graph('test_persist')
             print('PASS')
         asyncio.run(test())"
    Expected Result: 输出 PASS
    Evidence: .sisyphus/evidence/task-6-persistence.txt
  ```

  **Commit**: YES
  - Message: `feat(backend): SQLite graph store with node/edge persistence`
  - Files: `backend/app/state/graph_store.py`, `backend/app/state/migrations.py`

---

- [ ] 7. **LLM 图谱提取服务**

  **What to do**:
  - 新建 `backend/app/services/graph_extractor.py`
  - 实现 `GraphExtractor` 类:
    - `async extract_from_text(scene_description: str) -> dict` 方法
    - 调用现有 LLM provider（复用 backend/app/services/ 下的 provider 抽象）
    - Prompt设计: 给LLM一段场景描述，要求输出JSON:
      ```json
      {
        "background": {"description": "场景背景视觉描述"},
        "nodes": [
          {"serial": "1", "description": "资产视觉描述", "parent_serial": null},
          {"serial": "1-1", "description": "...", "parent_serial": "1"}
        ],
        "edges": [
          {"from": "1-1", "to": "2-1", "edge_type": "cross", "visual_description": ""}
        ]
      }
      ```
    - LLM提取的边 `visual_description` 为空字符串（用户必须手动填写）
    - 将LLM输出转换为 KnowledgeGraph 对象
  - 错误处理: LLM返回非JSON时尝试修复，修复失败抛出异常
  - 支持 ACTIVE_PROVIDER 环境变量选择provider

  **Must NOT do**:
  - 不自动生成边的 visual_description（用户必须手写）
  - 不在前端直接调用LLM（通过后端API）
  - 不修改现有 provider 代码

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: LLM prompt设计 + JSON解析 + 错误处理
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 6, 8)
  - **Parallel Group**: Wave 3a
  - **Blocks**: Task 10
  - **Blocked By**: Task 1 (模型), Task 5 (Phase 1 gate)

  **References**:
  - `backend/app/ai/provider.py` — 现有LLM provider抽象（LLMProvider ABC + OpenAICompatibleProvider）
  - `backend/app/ai/config.py` — ACTIVE_PROVIDER 配置 + ProviderConfig
  - `backend/app/models/knowledge_graph.py` — KnowledgeGraph模型(Task 1 canonical产出)

  **Acceptance Criteria**:
  - [ ] 输入自由文本，输出包含background+nodes+edges的JSON
  - [ ] 节点有正确的 serial_number 和 parent_serial
  - [ ] 边的 visual_description 为空（等用户填写）
  - [ ] LLM返回非JSON时有错误处理
  - [ ] 可通过 ACTIVE_PROVIDER 切换LLM

  **QA Scenarios**:
  ```
  Scenario: LLM extraction from free text (mock provider)
    Tool: Bash (python -c)
    Preconditions: 无需真实API key（mock LLMProvider）
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         import asyncio, sys, json
         sys.path.insert(0, '../tests/graph_algorithm')
         from unittest.mock import AsyncMock, patch
         from models import KnowledgeGraph
         from app.services.graph_extractor import GraphExtractor
         async def test():
             extractor = GraphExtractor()
             mock_response = {
                 'background': {'description': 'cyberpunk temple ruins'},
                 'nodes': [
                     {'serial': '1', 'description': 'priest corpse', 'parent_serial': None},
                     {'serial': '1-1', 'description': 'ritual book', 'parent_serial': '1'},
                     {'serial': '2', 'description': 'temple door', 'parent_serial': None},
                     {'serial': '2-1', 'description': 'quantum lock', 'parent_serial': '2'}
                 ],
                 'edges': [
                     {'from': '1-1', 'to': '2-1', 'edge_type': 'cross', 'visual_description': ''}
                 ]
             }
             with patch.object(extractor, '_call_llm', new_callable=AsyncMock, return_value=json.dumps(mock_response)):
                 text = '玩家进入神庙大厅，地上有尸体，尸体上有书。'
                 result = await extractor.extract_from_text(text)
             assert 'background' in result
             assert len(result['nodes']) >= 4
             for e in result['edges']:
                 assert e['visual_description'] == ''
             print('PASS')
         asyncio.run(test())"
    Expected Result: 输出 PASS
    Failure Indicators: JSON解析失败, 节点数量不足
    Evidence: .sisyphus/evidence/task-7-llm-extraction.txt

  Scenario: Real LLM extraction (manual, requires API key)
    Tool: Bash (python -c)
    Preconditions: .env 中配置了有效的LLM API key（手动运行，非自动化验证）
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         import asyncio
         from app.services.graph_extractor import GraphExtractor
         async def test():
             extractor = GraphExtractor()
             text = '玩家进入赛博朋克废墟神庙大厅，地上有祭司尸体，尸体上有一本仪式手册，手册里夹着密码纸。大厅尽头有大门，门上有量子锁。'
             result = await extractor.extract_from_text(text)
             assert 'background' in result
             assert 'nodes' in result
             assert len(result['nodes']) >= 4
             print('PASS')
         asyncio.run(test())"
    Expected Result: 输出 PASS (需有效API key)
    Failure Indicators: JSON解析失败, 节点数量不足
    Evidence: .sisyphus/evidence/task-7-real-llm.txt
    Note: 此场景为手动验证，不纳入自动化QA门禁

  Scenario: Invalid LLM response handling
    Tool: Bash (python -c)
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         from app.services.graph_extractor import GraphExtractor
         import json
         extractor = GraphExtractor()
         # Test JSON repair on malformed output
         repaired = extractor._try_repair_json('{\"nodes\": [\"incomplete\"')
         assert repaired is not None or True  # either repairs or raises
         print('PASS')"
    Expected Result: 输出 PASS (不崩溃)
    Evidence: .sisyphus/evidence/task-7-error-handling.txt
  ```

  **Commit**: YES
  - Message: `feat(backend): LLM graph extraction service from free-text scene description`
  - Files: `backend/app/services/graph_extractor.py`

---

- [ ] 8. **Prompt 融合服务**

  **What to do**:
  - 新建 `backend/app/services/prompt_fusion.py`
  - 实现 `PromptFusion` 类:
    - `build_prompt(node: GraphNode, graph: KnowledgeGraph, completed_nodes: dict) -> str` 方法
    - **3段结构**:
      ```
      【生成主体】{node.description}

      【关联衔接描述】
      {对每个已完成的关联节点，融合边的visual_description}
      {例如: 与已完成资产(corpse)的衔接: book is placed on top of corpse}

      【背景光影】
      {background_node.description 中的色调和光线角度描述}
      {所有资产自然光状态}
      ```
    - 只融合 status=completed 的关联节点（跳过pending/failed）
    - 失败节点策略: 跳过，不阻塞生成
    - 输出纯英文prompt（AI生图效果更好），但保留结构标记

  **Must NOT do**:
  - 不包含游戏逻辑（如"密码打开锁"）
  - 不修改现有 PromptBuilder（标记legacy）
  - 不自动翻译用户输入（用户输入什么就融合什么）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 核心prompt构建逻辑，需要正确融合3段结构
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 6, 7)
  - **Parallel Group**: Wave 3a
  - **Blocks**: Tasks 9, 10
  - **Blocked By**: Task 1 (模型), Task 5 (Phase 1 gate)

  **References**:
  - `backend/app/models/knowledge_graph.py` — GraphNode/GraphEdge/KnowledgeGraph模型 (Task 1 canonical产出)
  - `backend/app/services/prompt_builder.py` — legacy参考（不修改，但可看结构思路）
  - 用户定义的3段结构: 主体+关联衔接+背景光影

  **Acceptance Criteria**:
  - [ ] `build_prompt` 返回包含3段结构的字符串
  - [ ] 【生成主体】包含节点自身描述
  - [ ] 【关联衔接描述】只包含已完成节点的边描述
  - [ ] 【背景光影】包含0级背景的描述
  - [ ] 失败/待生成的关联节点被跳过

  **QA Scenarios**:
  ```
  Scenario: Prompt fusion 3-section structure
    Tool: Bash (python -c)
    Preconditions: Task 1 models.py 存在
    Steps:
      1. cd H:\UGC && python -c "
         import sys; sys.path.insert(0, 'tests/graph_algorithm')
         sys.path.insert(0, 'backend')
         from models import KnowledgeGraph
         from app.services.prompt_fusion import PromptFusion
         g = KnowledgeGraph(scene_id='test')
         g.background_node_id = '0'
         g.add_node('0', 'cyberpunk temple ruins, deep blue tones, natural light from above')
         g.add_node('1', 'ancient copper lock with quantum patterns')
         g.add_node('1-1', 'glowing numeric symbols on yellowed parchment')
         g.add_edge('0', '1', '', 'tree')
         g.add_edge('1-1', '1', 'lock mechanism visually matches the glowing symbols', 'cross')
         g.nodes['1-1'].status = 'completed'
         g.nodes['0'].status = 'completed'
         completed = {'0': g.nodes['0'], '1-1': g.nodes['1-1']}
         fusion = PromptFusion()
         prompt = fusion.build_prompt(g.nodes['1'], g, completed)
         assert 'copper lock' in prompt  # subject
         assert 'glowing symbols' in prompt or 'parchment' in prompt  # relation
         assert 'blue' in prompt.lower() or 'temple' in prompt.lower()  # background
         print('PASS')"
    Expected Result: 输出 PASS
    Evidence: .sisyphus/evidence/task-8-prompt-fusion.txt

  Scenario: Failed node skipped
    Tool: Bash (python -c)
    Steps:
      1. cd H:\UGC && python -c "
         import sys; sys.path.insert(0, 'tests/graph_algorithm')
         sys.path.insert(0, 'backend')
         from models import KnowledgeGraph
         from app.services.prompt_fusion import PromptFusion
         g = KnowledgeGraph(scene_id='test')
         g.background_node_id = '0'
         g.add_node('0', 'bg')
         g.add_node('1', 'target')
         g.add_node('1-1', 'completed_dep')
         g.add_node('1-2', 'failed_dep')
         g.add_edge('0', '1', '', 'tree')
         g.add_edge('1-1', '1', 'visual relation 1', 'tree')
         g.add_edge('1-2', '1', 'visual relation 2', 'tree')
         g.nodes['0'].status = 'completed'
         g.nodes['1-1'].status = 'completed'
         g.nodes['1-2'].status = 'failed'
         completed = {'0': g.nodes['0'], '1-1': g.nodes['1-1']}
         fusion = PromptFusion()
         prompt = fusion.build_prompt(g.nodes['1'], g, completed)
         assert 'visual relation 1' in prompt  # completed included
         assert 'visual relation 2' not in prompt  # failed skipped
         print('PASS')"
    Expected Result: 输出 PASS
    Evidence: .sisyphus/evidence/task-8-failed-skip.txt
  ```

  **Commit**: YES
  - Message: `feat(backend): prompt fusion service with 3-section structure (subject + relation + background)`
  - Files: `backend/app/services/prompt_fusion.py`

---

- [ ] 9. **串行生成调度器**

  **What to do**:
  - 新建 `backend/app/services/generation_scheduler.py`
  - 实现 `GenerationScheduler` 类:
    - `async run_generation(graph: KnowledgeGraph) -> dict` 方法
    - **调度逻辑**:
      1. 调用 `cycle_detector.validate_graph(graph)` 检查无环
      2. 调用 `topo_sort.get_generation_waves(graph)` 获取分波
      3. 按波次串行执行：
         - Wave N内：节点可并发生成（asyncio.gather）
         - Wave N全部完成后才进入Wave N+1
      4. 每个节点的生成:
         - 调用 `PromptFusion.build_prompt()` 构建prompt
         - 调用 `ImageGenerator.generate()` 生成图片
         - 传入 `reference_asset_ids`（同波内已完成的+前序波完成的）
         - 更新节点status
      5. 失败处理: 跳过失败节点，不阻塞同波其他节点
      6. 返回生成结果摘要: `{total, succeeded, failed, order}`
    - 0级背景永远在Wave 0（第一个生成）
    - 支持 `asyncio.Semaphore` 限制并发数（默认3）

  **Must NOT do**:
  - 不修改现有 ImageGenerator（直接复用）
  - 不修改现有 _run_generation（新调度器独立）
  - 不实现重试/退避策略
  - 不实现ETA预估

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 核心调度逻辑，需要正确处理asyncio并发和依赖等待
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO — T9 依赖 T8 (PromptFusion)，必须在 T8 之后串行
  - **Parallel Group**: Wave 3b (after Wave 3a: T6/T7/T8)
  - **Blocks**: Task 10
  - **Blocked By**: Tasks 3 (排序), 4 (环检测), 5 (Phase 1 gate), **8 (Prompt融合)**

  **References**:
  - `backend/app/models/knowledge_graph.py` — KnowledgeGraph模型 (Task 1 canonical产出)
  - `tests/graph_algorithm/topo_sort.py` — get_generation_waves (Task 3产出)
  - `tests/graph_algorithm/cycle_detector.py` — validate_graph (Task 4产出)
  - `backend/app/ai/image_generator.py` — ImageGenerator.generate() 签名
  - `backend/app/services/prompt_fusion.py` — PromptFusion.build_prompt() (**Task 8产出 — 必须先完成**)
  - `backend/app/api/assets_routes.py:40-149` — 现有_run_generation参考（但不修改）

  **Acceptance Criteria**:
  - [ ] 有环图: 调度器拒绝执行并返回环路径
  - [ ] 无环图: 按波次顺序执行
  - [ ] Wave内节点并发生成
  - [ ] Wave间严格串行（前波完成后才进下波）
  - [ ] 0级背景在第一波
  - [ ] 失败节点不阻塞同波其他节点
  - [ ] 返回结果摘要包含total/succeeded/failed/order

  **QA Scenarios**:
  ```
  Scenario: Serial wave execution with mock generator
    Tool: Bash (python -c)
    Preconditions: Tasks 1-4 完成, Task 8 完成
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         import asyncio, sys
         sys.path.insert(0, '../tests/graph_algorithm')
         from unittest.mock import AsyncMock, MagicMock, patch
         from models import KnowledgeGraph
         from app.services.generation_scheduler import GenerationScheduler
         async def test():
             g = KnowledgeGraph(scene_id='test')
             g.background_node_id = '0'
             g.add_node('0', 'bg')
             g.add_node('1', 'parent')
             g.add_node('1-1', 'child1')
             g.add_node('1-2', 'child2')
             g.add_edge('0', '1', '', 'tree')
             g.add_edge('1-1', '1', 'relation1', 'tree')
             g.add_edge('1-2', '1', 'relation2', 'tree')
             scheduler = GenerationScheduler()
             with patch('app.services.generation_scheduler.ImageGenerator') as MockGen:
                 instance = MockGen.return_value
                 instance.generate = AsyncMock(return_value=[MagicMock(seed=1, file_path='test.png', url=None)])
                 instance.close = AsyncMock()
                 result = await scheduler.run_generation(g)
             assert result['total'] == 4
             assert result['succeeded'] == 4
             assert result['order'][0] == '0'  # bg first
             print('PASS')
         asyncio.run(test())"
    Expected Result: 输出 PASS
    Evidence: .sisyphus/evidence/task-9-scheduler.txt

  Scenario: Cycle rejection
    Tool: Bash (python -c)
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         import asyncio, sys
         sys.path.insert(0, '../tests/graph_algorithm')
         from models import KnowledgeGraph
         from app.services.generation_scheduler import GenerationScheduler
         async def test():
             g = KnowledgeGraph(scene_id='cycle')
             g.add_node('1', 'a')
             g.add_node('2', 'b')
             g.add_node('3', 'c')
             g.add_edge('1', '2', '', 'cross')
             g.add_edge('2', '3', '', 'cross')
             g.add_edge('3', '1', '', 'cross')  # cycle
             scheduler = GenerationScheduler()
             result = await scheduler.run_generation(g)
             assert result['succeeded'] == 0
             assert 'cycle' in result.get('error', '').lower() or 'cycles' in str(result)
             print('PASS')
         asyncio.run(test())"
    Expected Result: 输出 PASS
    Evidence: .sisyphus/evidence/task-9-cycle-reject.txt
  ```

  **Commit**: YES
  - Message: `feat(backend): serial generation scheduler with wave-based dependency-aware execution`
  - Files: `backend/app/services/generation_scheduler.py`

---

- [ ] 10. **图谱 API 端点**

  **What to do**:
  - 新建 `backend/app/api/graph_routes.py`
  - 定义 `graph_router = APIRouter(prefix="/api/graph", tags=["graph"])`
  - 端点列表:
    - `POST /api/graph/extract` — 接收自由文本，调用GraphExtractor返回图谱骨架JSON
    - `POST /api/graph/{scene_id}` — 保存完整图谱（GraphStore.save_graph）
    - `GET /api/graph/{scene_id}` — 加载图谱（GraphStore.load_graph）
    - `PUT /api/graph/{scene_id}/nodes/{node_id}` — 更新节点描述
    - `PUT /api/graph/{scene_id}/edges/{edge_id}` — 更新边描述
    - `POST /api/graph/{scene_id}/nodes` — 添加节点
    - `POST /api/graph/{scene_id}/edges` — 添加边
    - `DELETE /api/graph/{scene_id}` — 删除图谱
    - `GET /api/graph/{scene_id}/order` — 返回生成顺序（调用topo_sort）
    - `GET /api/graph/{scene_id}/waves` — 返回分波列表
    - `POST /api/graph/{scene_id}/validate` — 环检测（返回is_valid + cycles）
    - `POST /api/graph/{scene_id}/generate` — 触发串行生成（调用GenerationScheduler）
    - `GET /api/graph/{scene_id}/generate/status` — 查询生成状态
  - 在 `backend/app/main.py` 中注册 graph_router
  - 生成是async后台任务（asyncio.create_task），status端点可轮询

  **Must NOT do**:
  - 不修改现有 assets_routes.py（新端点独立）
  - 不在前端直接调用LLM
  - 不阻塞HTTP请求等生成完成（生成是后台任务）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: API层设计，需要正确编排多个服务
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4
  - **Blocks**: Tasks 11, 12
  - **Blocked By**: Tasks 6, 7, 8, 9

  **References**:
  - `backend/app/api/assets_routes.py` — 现有router模式参考
  - `backend/app/main.py` — router注册位置
  - Tasks 6-9 产出代码

  **Acceptance Criteria**:
  - [ ] 所有端点返回正确的HTTP状态码
  - [ ] **每个端点附带 inline smoke test**（最小 curl 验证，确认端点可访问且返回预期结构）
  - [ ] `POST /api/graph/extract` 返回图谱骨架JSON
  - [ ] `POST /api/graph/{scene_id}/generate` 启动后台生成任务
  - [ ] `GET /api/graph/{scene_id}/generate/status` 返回当前状态
  - [ ] `POST /api/graph/{scene_id}/validate` 返回环检测结果
  - [ ] graph_router 在 main.py 中注册

  **QA Scenarios**:
  ```
  Scenario: Extract graph from text
    Tool: Bash (curl)
    Preconditions: 后端运行中, LLM API key 配置
    Steps:
      1. curl -X POST http://localhost:8000/api/graph/extract -H "Content-Type: application/json" -d '{"text":"玩家进入神庙大厅，地上有尸体，尸体上有书。"}'
      2. 解析JSON响应
      3. 断言响应包含 background, nodes, edges 字段
    Expected Result: 200 OK, JSON包含图谱结构
    Evidence: .sisyphus/evidence/task-10-extract.txt

  Scenario: Save and load graph
    Tool: Bash (curl)
    Steps:
      1. curl -X POST http://localhost:8000/api/graph/test_scene -H "Content-Type: application/json" -d '{"scene_id":"test_scene","nodes":[...],"edges":[...]}'
      2. curl -X GET http://localhost:8000/api/graph/test_scene
      3. 断言加载的图谱与保存的一致
    Expected Result: 200 OK, 数据一致
    Evidence: .sisyphus/evidence/task-10-save-load.txt

  Scenario: Validate graph (cycle detection)
    Tool: Bash (curl)
    Steps:
      1. 保存一个有环的图谱
      2. curl -X POST http://localhost:8000/api/graph/cycle_scene/validate
      3. 断言返回 is_valid=false, cycles 非空
    Expected Result: 200 OK, is_valid=false
    Evidence: .sisyphus/evidence/task-10-validate.txt

  Scenario: Trigger generation
    Tool: Bash (curl)
    Steps:
      1. 保存一个无环图谱
      2. curl -X POST http://localhost:8000/api/graph/test_scene/generate
      3. 断言返回 task_started=true
      4. curl -X GET http://localhost:8000/api/graph/test_scene/generate/status
      5. 断言返回包含 progress 或 status 字段
    Expected Result: 200 OK, 生成任务启动
    Evidence: .sisyphus/evidence/task-10-generate.txt
  ```

  **Commit**: YES
  - Message: `feat(backend): graph API endpoints for CRUD, validation, and generation trigger`
  - Files: `backend/app/api/graph_routes.py`, `backend/app/main.py`

---

- [ ] 11. **后端集成测试**

  **What to do**:
  - 新建 `backend/tests/test_graph_integration.py`
  - 测试完整后端链路:
    1. `test_extract_and_save` — LLM提取→保存→加载→验证一致
    2. `test_cycle_validation` — 有环图→validate返回false
    3. `test_generation_order` — 无环图→order端点返回正确顺序
    4. `test_generation_waves` — 星型结构→waves端点返回正确分波
    5. `test_mock_generation` — mock ImageGenerator→generate端点→status轮询→全部completed
    6. `test_prompt_fusion_in_generation` — mock生成→验证传入的prompt包含3段结构
  - 使用 `httpx.AsyncClient` 测试FastAPI端点
  - 使用mock ImageGenerator（不调用真实AI API）
  - 使用临时数据库（测试后清理）

  **Must NOT do**:
  - 不调用真实LLM API（mock GraphExtractor）
  - 不调用真实ImageGenerator（mock）
  - 不修改现有测试

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 综合集成测试
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4
  - **Blocks**: F1-F3
  - **Blocked By**: Task 10

  **References**:
  - `backend/tests/unit/test_assets_api.py` — 现有API测试模式参考
  - Task 10 产出代码

  **Acceptance Criteria**:
  - [ ] 6+集成测试全部PASS
  - [ ] mock生成正确验证了串行顺序
  - [ ] mock生成正确验证了prompt融合
  - [ ] 环检测端点正确工作

  **QA Scenarios**:
  ```
  Scenario: Backend integration test suite
    Tool: Bash (pytest)
    Preconditions: Task 10 完成
    Steps:
      1. cd backend && .venv\Scripts\python -m pytest tests/test_graph_integration.py -v
    Expected Result: 6+ tests PASS
    Evidence: .sisyphus/evidence/task-11-integration.txt
  ```

  **Commit**: YES
  - Message: `test(backend): graph integration tests for API endpoints, generation order, and prompt fusion`
  - Files: `backend/tests/test_graph_integration.py`

---

- [ ] 12. **前端共享基础设施 (graph.ts + types + 共享组件)**

  **What to do**:
  - 新建 `frontend/src/api/graph.ts` — 图谱API客户端，封装所有后端端点调用
    - `extractGraph(text: string)` → POST /api/graph/extract
    - `saveGraph(sceneId, graph)` → POST /api/graph/{sceneId}
    - `loadGraph(sceneId)` → GET /api/graph/{sceneId}
    - `updateNode(sceneId, nodeId, desc)` → PUT /api/graph/{sceneId}/nodes/{nodeId}
    - `updateEdge(sceneId, edgeId, desc)` → PUT /api/graph/{sceneId}/edges/{edgeId}
    - `addNode(sceneId, node)` → POST /api/graph/{sceneId}/nodes
    - `addEdge(sceneId, edge)` → POST /api/graph/{sceneId}/edges
    - `deleteGraph(sceneId)` → DELETE /api/graph/{sceneId}
    - `getOrder(sceneId)` → GET /api/graph/{sceneId}/order
    - `getWaves(sceneId)` → GET /api/graph/{sceneId}/waves
    - `validateGraph(sceneId)` → POST /api/graph/{sceneId}/validate
    - `triggerGeneration(sceneId)` → POST /api/graph/{sceneId}/generate
    - `getGenerationStatus(sceneId)` → GET /api/graph/{sceneId}/generate/status
  - 新建 `frontend/src/types/graph.ts` — TypeScript类型定义，与后端Pydantic模型对齐
    - `GraphNode` (id, serial_number, level, description, status)
    - `GraphEdge` (from_node_id, to_node_id, edge_type, visual_description)
    - `KnowledgeGraph` (scene_id, nodes, edges, background_node_id)
    - `GenerationWave` (wave_index, node_ids[])
    - `GenerationResult` (total, succeeded, failed, order)
    - `ValidationResult` (is_valid, cycles[][])
  - 新建 `frontend/src/components/graph/NodeBadge.tsx` — 节点状态颜色徽章
    - pending=灰, generating=黄, completed=绿, failed=红
    - 显示 serial_number + description 前20字
  - 新建 `frontend/src/components/graph/WaveDivider.tsx` — Wave分组分隔线
    - 显示 "Wave N: 叶子节点" 等标签
    - 视觉分隔不同wave的节点列表
  - 新建 `frontend/src/components/graph/PromptPreview.tsx` — 3段prompt只读预览面板
    - 【生成主体】节点description（只读）
    - 【关联衔接描述】已完成关联节点+边描述（只读）
    - 【背景光影】0级背景描述（只读）

  **Must NOT do**:
  - 不创建页面组件（T13/T14负责）
  - 不安装 React Flow（T13负责）
  - 不修改现有 assets.ts / App.tsx

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: 前端API客户端+类型+共享组件开发
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: 组件设计、TypeScript类型设计

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 5
  - **Blocks**: Tasks 13, 14
  - **Blocked By**: Task 10 (API端点)

  **References**:
  - `frontend/src/api/assets.ts` — 现有API客户端模式（fetchWithTimeout, 类型化返回）
  - `frontend/src/api/client.ts` — fetchWithTimeout 基础工具
  - `frontend/src/types/scene.ts` — TypeScript类型定义模式（DTO pattern）
  - Task 10 的API端点定义 — 端点路径和请求/响应结构

  **WHY Each Reference Matters**:
  - assets.ts: 展示了如何封装API调用、处理错误、返回类型化结果
  - client.ts: 提供fetchWithTimeout工具函数，graph.ts应复用
  - scene.ts: 展示了DTO类型定义模式，graph.ts应对齐
  - Task 10: 提供所有端点的路径和schema，graph.ts必须精确匹配

  **Acceptance Criteria**:
  - [ ] `graph.ts` 封装所有13个API端点
  - [ ] `types/graph.ts` 类型定义与后端模型对齐
  - [ ] `NodeBadge` 组件根据status显示正确颜色
  - [ ] `WaveDivider` 组件显示wave标签
  - [ ] `PromptPreview` 组件渲染3段结构
  - [ ] `npm run build` 无类型错误

  **QA Scenarios**:
  ```
  Scenario: API client type safety
    Tool: Bash (npx tsc --noEmit)
    Preconditions: graph.ts 和 types/graph.ts 已创建
    Steps:
      1. cd frontend && npx tsc --noEmit
      2. 检查无类型错误
    Expected Result: 0 errors
    Failure Indicators: 类型不匹配错误
    Evidence: .sisyphus/evidence/task-12-tsc.txt

  Scenario: Component render check
    Tool: Playwright
    Preconditions: 前端运行中
    Steps:
      1. 编写一个临时测试页面，渲染NodeBadge(status='completed')、WaveDivider(waveIndex=1)、PromptPreview
      2. 验证组件渲染无报错
      3. 验证NodeBadge显示绿色
    Expected Result: 组件正常渲染
    Evidence: .sisyphus/evidence/task-12-components.png
  ```

  **Commit**: YES
  - Message: `feat(frontend): shared graph infrastructure — API client, types, and UI components`
  - Files: `frontend/src/api/graph.ts`, `frontend/src/types/graph.ts`, `frontend/src/components/graph/NodeBadge.tsx`, `frontend/src/components/graph/WaveDivider.tsx`, `frontend/src/components/graph/PromptPreview.tsx`

---

- [ ] 13. **React Flow 图谱编辑器**

  **What to do**:
  - 安装 `@xyflow/react` 依赖
  - 新建 `frontend/src/pages/GraphEditor.tsx`
  - **复用 T12 共享层**: `graph.ts` API客户端 + `types/graph.ts` 类型 + `NodeBadge` 组件
  - **界面布局**:
    - 顶部：场景描述输入框 + "提取图谱"按钮
    - 左侧：React Flow画布（节点+边可视化编辑）
    - 右侧：选中节点/边的属性编辑面板
  - **节点设计**:
    - 自定义节点组件：显示serial_number + description前20字 + status颜色
    - 0级背景节点特殊样式（如边框加粗）
    - 不同level的节点用不同颜色区分
  - **边设计**:
    - tree边用实线，cross边用虚线
    - 点击边显示visual_description编辑框
    - 新建边时弹出输入框要求填写visual_description
  - **交互功能**:
    - 拖拽创建新节点（输入serial + description）
    - 从节点A拖到节点B创建边（弹出visual_description输入）
    - 点击节点选中，右侧显示编辑面板
    - "验证图谱"按钮（调用validate端点，有环时高亮冲突边红色）
    - "生成顺序"按钮（调用order端点，在节点上显示序号）
    - "保存图谱"按钮
  - **LLM提取流程**:
    - 用户输入场景描述文本
    - 点击"提取图谱"→调用 `/api/graph/extract`
    - 返回的图谱渲染到React Flow画布
    - 自动布局（React Flow默认dagre布局）

  **Must NOT do**:
  - 不修改现有 AssetReview.tsx
  - 不实现自动布局算法（用React Flow默认）
  - 不实现实时协同编辑
  - 不实现图谱版本控制
  - 不自动生成visual_description（用户必须手写）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: 前端React Flow图谱编辑器开发
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: 前端UI/UX设计，组件布局，交互设计

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 14)
  - **Parallel Group**: Wave 6
  - **Blocks**: Task 15
  - **Blocked By**: Task 12 (前端共享层)

  **References**:
  - `frontend/src/pages/AssetReview.tsx` — 现有页面结构参考（布局模式，API调用模式）
  - `frontend/src/api/graph.ts` — **共享API客户端 (Task 12产出，直接复用)**
  - `frontend/src/types/graph.ts` — **共享类型定义 (Task 12产出)**
  - `frontend/src/components/graph/NodeBadge.tsx` — **共享节点徽章组件 (Task 12产出)**
  - React Flow官方文档: https://reactflow.dev/learn
  - Task 10 的API端点定义

  **Acceptance Criteria**:
  - [ ] `npm run build` 无错误
  - [ ] 输入文本→提取图谱→画布显示节点和边
  - [ ] 点击节点→右侧显示编辑面板
  - [ ] 拖拽创建新边→弹出visual_description输入
  - [ ] "验证图谱"按钮→有环时高亮冲突边
  - [ ] "生成顺序"按钮→节点上显示顺序号
  - [ ] "保存图谱"按钮→调用保存API

  **QA Scenarios**:
  ```
  Scenario: Graph editor loads and displays
    Tool: Playwright
    Preconditions: 后端运行中, 前端运行中
    Steps:
      1. 导航到 http://localhost:5173/graph-editor (或对应路由)
      2. 断言页面标题包含"图谱"或"Graph"
      3. 断言存在场景描述输入框
      4. 断言存在"提取图谱"按钮
      5. 断言存在React Flow画布区域
    Expected Result: 页面正常加载，所有元素可见
    Evidence: .sisyphus/evidence/task-12-editor-load.png

  Scenario: Extract graph from text
    Tool: Playwright
    Preconditions: 后端配置 mock LLM 响应（或使用 local provider placeholder）
    Steps:
      1. 在场景描述输入框输入: "玩家进入神庙大厅，地上有尸体，尸体上有书。"
      2. 点击"提取图谱"按钮
      3. 等待3秒（LLM响应或mock响应）
      4. 断言React Flow画布上出现节点（.react-flow__node 元素）
      5. 断言节点数量 >= 3
    Expected Result: 画布上显示提取的节点
    Evidence: .sisyphus/evidence/task-12-extract.png
    Note: 自动化测试使用 mock 后端，真实 LLM 测试为手动验证

  Scenario: Add edge with visual description
    Tool: Playwright
    Steps:
      1. 有节点在画布上
      2. 从节点A的handle拖到节点B
      3. 断言弹出visual_description输入框
      4. 输入"A在B上方"
      5. 确认
      6. 断言画布上出现新边（.react-flow__edge 元素）
    Expected Result: 边创建成功，visual_description已填写
    Evidence: .sisyphus/evidence/task-12-add-edge.png

  Scenario: Cycle validation highlight
    Tool: Playwright
    Steps:
      1. 创建一个有环的图谱（A→B→C→A）
      2. 点击"验证图谱"按钮
      3. 断言冲突边被高亮（红色或警告样式）
      4. 断言显示环路径提示
    Expected Result: 环被检测并高亮
    Evidence: .sisyphus/evidence/task-12-cycle-highlight.png
  ```

  **Commit**: YES
  - Message: `feat(frontend): React Flow graph editor with node/edge editing and cycle validation`
  - Files: `frontend/src/pages/GraphEditor.tsx`, `frontend/src/api/graph.ts`, `frontend/package.json`

---

- [ ] 14. **资产生成页面变体 (GraphAssetReview)**

  **What to do**:
  - 新建 `frontend/src/pages/GraphAssetReview.tsx`
  - **复用 T12 共享层**: `graph.ts` API客户端 + `types/graph.ts` 类型 + `WaveDivider` + `NodeBadge` + `PromptPreview` 组件
  - **界面布局**（基于AssetReview变体 + Generation Timeline视图）:
    - 顶部：场景选择 + "开始生成"按钮 + 生成进度条
    - 左侧：资产列表，按生成顺序（wave）排列
      - 每个wave用分隔线标注（"Wave 1: 叶子节点"等）
      - 同wave内按serial_number排序
      - 每项显示: serial + name + status颜色
    - 中间：选中资产的预览图
    - 右侧：生成prompt预览（3段结构）
      - 【生成主体】显示节点description（只读）
      - 【关联衔接描述】显示已完成的关联节点+边描述（只读）
      - 【背景光影】显示0级背景描述（只读）
      - 底部"生成"按钮（单个资产）或"生成全部"按钮
  - **轮询逻辑**:
    - 生成进行中时每3秒轮询 `/api/graph/{scene_id}/generate/status`
    - 更新节点status，刷新列表
  - **路由**:
    - 在 App.tsx 中添加 `/graph-assets` 路由
    - 保留原 `/admin/assets` 路由不动

  **Must NOT do**:
  - 不修改现有 AssetReview.tsx
  - 不修改现有路由
  - 不实现prompt编辑（右侧只读预览）
  - 不实现ETA预估

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: 前端页面开发
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: 前端UI/UX设计

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 13)
  - **Parallel Group**: Wave 6
  - **Blocks**: Task 15
  - **Blocked By**: Task 12 (前端共享层)

  **References**:
  - `frontend/src/pages/AssetReview.tsx` — 现有资产页面参考（布局模式，轮询逻辑，状态颜色）
  - `frontend/src/api/graph.ts` — **共享API客户端 (Task 12产出，直接复用)**
  - `frontend/src/components/graph/WaveDivider.tsx` — **Wave分组分隔线 (Task 12产出)**
  - `frontend/src/components/graph/NodeBadge.tsx` — **节点徽章 (Task 12产出)**
  - `frontend/src/components/graph/PromptPreview.tsx` — **3段prompt预览 (Task 12产出)**
  - Task 10 的API端点定义

  **Acceptance Criteria**:
  - [ ] `npm run build` 无错误
  - [ ] 资产列表按wave分组排列
  - [ ] 选中资产→右侧显示3段prompt结构
  - [ ] "开始生成"→触发后台生成→轮询更新status
  - [ ] 生成进度实时更新

  **QA Scenarios**:
  ```
  Scenario: Asset list ordered by generation waves
    Tool: Playwright
    Preconditions: 后端运行中, 已有图谱数据
    Steps:
      1. 导航到 http://localhost:5173/graph-assets
      2. 断言资产列表按wave分组（存在wave分隔标记）
      3. 断言Wave 1在Wave 2之前
      4. 断言0级背景在最前
    Expected Result: 列表按生成顺序排列
    Evidence: .sisyphus/evidence/task-13-ordered-list.png

  Scenario: Prompt preview 3-section structure
    Tool: Playwright
    Steps:
      1. 点击列表中一个资产
      2. 断言右侧面板显示3段结构
      3. 断言【生成主体】包含资产描述
      4. 断言【背景光影】包含背景描述
    Expected Result: 3段prompt结构可见
    Evidence: .sisyphus/evidence/task-13-prompt-preview.png

  Scenario: Trigger generation and poll status
    Tool: Playwright
    Preconditions: mock ImageGenerator 已配置 或 local provider
    Steps:
      1. 点击"开始生成"按钮
      2. 断言按钮变为"生成中..."状态
      3. 等待5秒
      4. 断言至少一个资产status变为completed或generating
      5. 断言进度条有更新
    Expected Result: 生成启动，状态实时更新
    Evidence: .sisyphus/evidence/task-13-generation.png
  ```

  **Commit**: YES
  - Message: `feat(frontend): graph asset review page with wave-ordered list and 3-section prompt preview`
  - Files: `frontend/src/pages/GraphAssetReview.tsx`, `frontend/src/App.tsx`

---

- [ ] 15. **前端 Playwright 测试**

  **What to do**:
  - 新建 `frontend/tests/graph-editor.spec.ts`
  - 新建 `frontend/tests/graph-asset-review.spec.ts`
  - 测试用例:
    1. **图谱编辑器加载**: 页面加载，元素可见
    2. **文本提取**: 输入文本→提取→节点显示
    3. **添加节点**: 拖拽创建→输入描述→节点出现
    4. **添加边**: 连接两节点→输入visual_description→边出现
    5. **环验证**: 创建环→点击验证→冲突高亮
    6. **资产生成页面加载**: 页面加载，列表可见
    7. **wave分组**: 列表按wave分组
    8. **prompt预览**: 点击资产→3段结构显示
  - 使用 mock 后端或 local provider（不依赖真实LLM）

  **Must NOT do**:
  - 不测试真实图片生成（用local provider placeholder）
  - 不测试需要用户肉眼判断的视觉一致性

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Playwright测试编写
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 7
  - **Blocks**: F1-F3
  - **Blocked By**: Tasks 13, 14

  **References**:
  - `backend/tests/test_asset_views.py` — 现有Playwright测试模式参考
  - Tasks 13, 14 产出代码

  **Acceptance Criteria**:
  - [ ] 8+ Playwright测试全部PASS
  - [ ] 图谱编辑器核心功能验证
  - [ ] 资产生成页面核心功能验证

  **QA Scenarios**:
  ```
  Scenario: Frontend Playwright test suite
    Tool: Bash (npx playwright test)
    Preconditions: 前端运行中, 后端运行中
    Steps:
      1. cd frontend && npx playwright test tests/graph-*.spec.ts
    Expected Result: 8+ tests PASS
    Evidence: .sisyphus/evidence/task-14-playwright.txt
  ```

  **Commit**: YES
  - Message: `test(frontend): Playwright tests for graph editor and asset review pages`
  - Files: `frontend/tests/graph-editor.spec.ts`, `frontend/tests/graph-asset-review.spec.ts`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 3 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [ ] F1. **合规审计 + 代码质量** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan. Run `ruff check` + `mypy` + `pytest`. Review all changed files for: `as any`/`@ts-ignore`, empty catches, console.log in prod, commented-out code, unused imports. Verify no existing code modified (git diff on scene_graph.py, puzzle_graph.py, prompt_builder.py should be empty).
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Legacy untouched [YES/NO] | VERDICT: APPROVE/REJECT`

- [ ] F2. **端到端 QA** — `unspecified-high` (+ `playwright` skill)
  Start backend + frontend from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration: input free text → LLM extract → edit graph → add edge descriptions → trigger generation → verify serial order → verify prompt fusion. Test cycle detection by creating circular dependency. Test edge cases: empty state, invalid input. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | Cycle detection [PASS/FAIL] | Serial order [PASS/FAIL] | Prompt fusion [PASS/FAIL] | VERDICT`

- [ ] F3. **范围一致性检查** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance — especially: no modifications to legacy files, no auto features, no multi-scene. Detect cross-task contamination: Task N touching Task M's files. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Phase 1**: `feat(algorithm): implement graph-driven generation ordering with cycle detection`
- **Phase 2**: `feat(backend): graph-driven asset generation system with SQLite persistence and serial scheduler`
- **Phase 3a**: `feat(frontend): shared graph infrastructure — API client, types, and UI components`
- **Phase 3b**: `feat(frontend): React Flow graph editor and generation order asset review`

---

## Success Criteria

### Verification Commands
```bash
cd backend && .venv\Scripts\python -m pytest tests/graph_algorithm/ -v  # Phase 1: all pass
cd backend && .venv\Scripts\python -m pytest tests/ -v                   # Phase 2: all pass
cd frontend && npm run build                                              # Phase 3: success
```

### Final Checklist
- [ ] Phase 1 算法测试全部PASS（6+核心用例，覆盖率≥95%）
- [ ] 分层拓扑排序：0级背景先→叶子→核心→逐级向上
- [ ] 环检测：返回具体环路径
- [ ] 串行调度器：依赖串行+无关并发
- [ ] Prompt融合：3段结构（主体+关联衔接+背景光影）
- [ ] 前端共享层：graph.ts + types + 共享组件（NodeBadge/WaveDivider/PromptPreview）
- [ ] React Flow图谱编辑器：可视化编辑节点+边
- [ ] 资产生成页面：按生成顺序排列+prompt预览+Generation Timeline视图
- [ ] 现有 SceneGraph/PuzzleGraph/PromptBuilder 未被修改
