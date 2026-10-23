# 波次三·前端视图施工单（A1 访谈体验升级）

## TL;DR

> **Quick Summary**: 波次三纯前端批——活地图七大陆视图（拍3-3）+ 开场语前端同源替换（拍3-1）+ 图谱页新边渲染（波次二遗留：迁移边/衔接边/支线衔接边）+ 灵感架图谱页安家 UI（波次二遗留）。拍板全按推荐闭卷（2026-10-14 产品方「全按推荐」）。label 层记二期（拍3-2，不在本波次）；D24 二期按钮暂缓先补埋点（不在本波次）。
>
> **Deliverables**:
> - 活地图七大陆视图组件（L1×7 大陆，L2 节点亮起，用户看见世界长到哪了）
> - 开场语前端 A1Workspace.tsx L647 旧语替换为 cadfcb3 后端同源说人话版
> - 图谱页消费迁移边/衔接边/支线衔接边（EdgeType.MIGRATION/LINKAGE + 概念边家族）渲染 + 未知边降级
> - 灵感架图谱页安家 UI（material_pool 存量可见 + 安家操作入口）
> - D24 knowledge_used 埋点补线（为二期按钮决策取数，非按钮本身）
>
> **Estimated Effort**: Large（4 任务，前端为主，含 React Flow 图谱扩展）
> **Parallel Execution**: PARTIAL——活地图/开场语/图谱边/灵感架 UI 四件可部分并行（不同组件文件）
> **Critical Path**: T1(探查) → T2/T3/T4/T5(并行) → T6(集成门禁) → F1-F4

---

## Context

### Original Request
产品方 2026-10-14 指令「全按推荐」——波次二验收 okay + 拍3-1 一并改 / 拍3-2 记二期 / 拍3-3 归波次三。总基线 §4 波次三行：「3.1 / 3.2 前端视图 + D24 二期，tsc/vitest + Playwright」。

### Interview Summary
- 波次二验收：正式 okay（四审 4×APPROVE，1838/0/85.04%，防幻觉复核过）
- E0 实据（`.sisyphus/evidence/wave2-e0-telemetry.md`）：2450 真机事件/536 会话；mirror 312/rack_stowed 12/list_append 652 高价值；reanchor 1 观察项；stall 1147 间接支持开场语收益
- 拍3-2 label 层记二期（展示链路广，单独评审）
- D24 二期按钮暂缓（先补 knowledge_used 埋点取数再决策）

### Research Findings（T1 探查完成 2026-10-14，主会话接管——代理死亡）
- **图谱组件**：`frontend/src/components/graph/A1KnowledgeGraph.tsx`（React Flow 主组件）+ `A1GraphSection.tsx`（图谱区容器）+ `EdgeReviewPanel.tsx`（边审核）+ `NodeDetailPanel.tsx`（节点详情）
- **EdgeType 前端消费**：`frontend/src/api/graph.ts` L9/20/22/53（类型定义+序列化）+ `relationLabel.ts` L20（边标签纯函数）
- **material_pool 前端零消费**（grep 空）——须新建组件 + 扩 api/a1.ts 类型
- **knowledge_used 后端旗标**：`guide_engine.py` L1669（`if getattr(result, "knowledge_used", False)`——已有旗标消费，但**未 emit_event 埋点**，须补 `inspiration_log.emit_event("knowledge_used", session)`）
- **开场语前端旧语**：`A1Workspace.tsx` L647「我将围绕这个基调引导你展开世界观」+ L649「我将围绕它引导你展开世界观」——后端 cadfcb3（interviewer.py L477）已改为「接下来我会一次问你一个问题，帮你把它变成一个完整的世界...」
- **活地图**：无既有进度/世界全貌组件（grep 空）——全新组件，数据源 = /file/{id} graph 端点既有 + THREE_TIER_TREE L1×7 结构
- **A1Workspace 路径**：`frontend/src/pages/a1/A1Workspace.tsx`（1913 行）；路由入口 `frontend/src/App.tsx`
- **收尾三连问组件**：`frontend/src/components/guided/ClosingPanel.tsx`（灵感架收尾摊开复用先例）

### Metis Review（待补——施工单生成后召唤）

---

## Work Objectives

### Core Objective
让用户「看见我的世界长什么样、长到哪了」——活地图七大陆 + 图谱新边可视化 + 灵感架安家入口；同时清波次二前端遗留（开场语同源旧语 + 图谱边渲染）。

### Concrete Deliverables
见 TL;DR Deliverables 清单。

### Definition of Done
- [ ] tsc --noEmit 零新增
- [ ] vitest 全绿（基线 310+，净增 ≥15）
- [ ] Playwright E2E：活地图渲染/开场语/图谱边/灵感架安家各一幕绿
- [ ] 后端零改动（纯前端批——除 D24 knowledge_used 埋点补线外）
- [ ] ruff 增量 0（仅埋点补线触碰后端）
- [ ] D28 治理收官 + PROJECT_STATE/MOC 落痕

### Must Have
- 活地图七大陆视图：L1×7 大陆（IP/世界观/剧情/角色/玩法/视觉/设定边界），L2 节点亮起表示已答，用户可一览世界全貌与进度
- 开场语前端与后端 cadfcb3 同源（一字不差或语义同声口）
- 图谱页迁移边/衔接边/支线衔接边可渲染（与●节点共存，未知边降级不炸）
- 灵感架 material_pool 存量在图谱页/收尾可见 + 安家操作入口
- D24 knowledge_used 埋点 jsonl（为二期决策取数）

### Must NOT Have（红线）
- **后端业务逻辑改动**（除 knowledge_used 埋点补线 1 处外，backend/ 业务代码零触碰）
- **label 层改动**（拍3-2 记二期——模块名/字段名展示不动）
- **D24 二期按钮实现**（暂缓，仅补埋点）
- **guide_engine L1398 拼接语**（归二期不动）
- **波次二已落机制字节回改**（六通道/值形态/清单/灵感架回收——前端只读消费不改后端）
- **新 LLM 调用**（纯前端渲染 + 既有端点数据消费）
- **reanchor 触发词扩词表**（E0 观察项，记二期不本批改）

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - 全部 agent 可执行。

### Test Decision
- **Infrastructure exists**: YES（vitest 310 + tsc + Playwright）
- **Automated tests**: TDD（每组件红→绿）
- **Framework**: vitest + Playwright（前端 E2E）

### QA Policy
- **前端单测**: vitest 每组件 ≥3 用例（渲染/交互/边界）
- **E2E**: Playwright 各交付件一幕（导航→断言 DOM→截图）
- **后端零改动核对**: git diff --stat backend/ 仅 knowledge_used 埋点 1 文件
- **tsc/vitest 基线**: 零新增错误 / 全绿

---

## Execution Strategy

### 部分并行波次

```
Wave 1（T1 探查，先行）:
└── T1: 前端结构探查 + 既有组件清单 + 数据端点核对

Wave 2（T2-T5 并行，依赖 T1）:
├── T2: 活地图七大陆视图组件
├── T3: 开场语前端同源替换
├── T4: 图谱页新边渲染 + 未知边降级
└── T5: 灵感架图谱页安家 UI + D24 knowledge_used 埋点补线

Wave 3（T6 集成门禁）:
└── T6: tsc + vitest + Playwright + 白名单 + 治理收官 D28

Wave FINAL: F1-F4 四审并行 → 用户 okay
```

Critical Path: T1 → T2/T4（图谱依赖探查）→ T6 → F
Parallel Speedup: ~50%（Wave 2 四件并行）
Max Concurrent: 4（Wave 2）

### Dependency Matrix

| 任务 | 依赖 | 被依赖 |
|---|---|---|
| T1 | 无 | T2-T6 全部 |
| T2 | T1 | T6 |
| T3 | T1 | T6 |
| T4 | T1 | T6 |
| T5 | T1 | T6 |
| T6 | T2-T5 | F1-F4 |

### Agent Dispatch Summary

- **T1**: `explore`（前端结构探查）
- **T2**: `visual-engineering`（活地图 React 组件）
- **T3**: `quick`（开场语替换，单文件）
- **T4**: `visual-engineering`（React Flow 边扩展）
- **T5**: `unspecified-high`（灵感架 UI + 后端埋点 1 处）
- **T6**: `quick`（门禁复跑 + 治理登记）
- **FINAL**: F1 `oracle` / F2 `unspecified-high` / F3 `unspecified-high`(+playwright) / F4 `deep`

---

## TODOs

> Implementation + Test = ONE Task. EVERY task MUST have QA Scenarios.

### Wave 1：T1 探查（已完成，见 Research Findings）

### Wave 2：并行施工

- [ ] 2. 活地图七大陆视图组件

  **What to do**:
  - 新建 `frontend/src/components/graph/WorldMap.tsx`（或 `LiveMap.tsx`）：React 组件渲染 L1×7 大陆（IP定位/世界观/剧情/角色/玩法/视觉/设定边界），每大陆内 L2 节点亮起表示已答（数据源=GET /file/{id}/graph 既有端点的 answers 视图 + THREE_TIER_TREE 结构）
  - 七大陆布局：卡片网格或放射状（设计自由度，但须一目了然"世界长到哪了"）
  - 接入 A1Workspace 或 A1GraphSection（作为图谱页的一个视图 tab 或独立面板）
  - vitest ≥3 用例（渲染/空状态/已答亮起）

  **Must NOT do**:
  - 不改后端；不新建后端端点（复用既有 /file/{id}/graph）
  - 不动既有 A1KnowledgeGraph React Flow 逻辑

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**: Can Run In Parallel: YES | Wave 2（与 T3/T4/T5 并行）| Blocks: T6 | Blocked By: T1

  **References**:
  - `frontend/src/components/graph/A1KnowledgeGraph.tsx` — React Flow 既有用法（布局/节点样式先例）
  - `frontend/src/components/graph/A1GraphSection.tsx` — 图谱区容器（接入点）
  - `backend/app/domains/creation/seed/story_modules.py` THREE_TIER_TREE — L1×7 结构源
  - GET `/api/a1/file/{file_id}/graph` — 既有端点（answers 视图数据源）

  **Acceptance Criteria**:
  - [ ] WorldMap 组件渲染七大陆，已答 L2 亮起
  - [ ] vitest ≥3 用例全绿
  - [ ] tsc 零新增

  **QA Scenarios**:
  ```
  Scenario: 活地图渲染
    Tool: Bash (vitest) + Playwright
    Steps:
      1. vitest: 渲染 WorldMap with mock graph data → 断言七大陆标题在
      2. 断言已答模块亮起、未答灰
      3. Playwright: 导航 /a1 → 完成访谈 → 图谱页 → 断言 WorldMap 可见
    Expected: 七大陆全在，亮起与答案对应
    Evidence: .sisyphus/evidence/wave3-t2-worldmap.txt
  ```

  **Commit**: YES
  - Message: `feat(frontend): 活地图七大陆视图组件`

- [ ] 3. 开场语前端同源替换

  **What to do**:
  - `frontend/src/pages/a1/A1Workspace.tsx` L647/L649：替换「我将围绕这个基调引导你展开世界观」/「我将围绕它引导你展开世界观」为后端 cadfcb3 同源说人话版（interviewer.py L477「接下来我会一次问你一个问题，帮你把它变成一个完整的世界。每题都可以自己写、从我给的选项里挑，或者跳过。」）
  - 两种入口（种子选择/一句话开始）各替换一行，保持模板变量 `{response.seed.name}` 等插值
  - vitest：A1Workspace 开场渲染测试 ≥1 用例断言新语

  **Must NOT do**:
  - 不改后端（cadfcb3 已落）；不动 seedPrefix 模板逻辑结构（只换文案）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**: Can Run In Parallel: YES | Wave 2 | Blocks: T6 | Blocked By: T1

  **References**:
  - `frontend/src/pages/a1/A1Workspace.tsx` L646-650 — 旧开场语两行
  - `backend/app/domains/creation/a1/interviewer.py` L477 — 后端说人话版原文
  - `.sisyphus/evidence/wave1-t9-notes.md` — 波次一登记的前端旧语遗留

  **Acceptance Criteria**:
  - [ ] grep「我将围绕」在 A1Workspace.tsx = 0 命中
  - [ ] vitest 开场测试绿
  - [ ] tsc 零新增

  **QA Scenarios**:
  ```
  Scenario: 开场语替换
    Tool: Bash (grep + vitest)
    Steps:
      1. grep -c '我将围绕' frontend/src/pages/a1/A1Workspace.tsx → 0
      2. vitest A1Workspace 开场渲染 → 断言新语「一次问你一个问题」在
    Expected: 旧语清零、新语在
    Evidence: .sisyphus/evidence/wave3-t3-opening.txt
  ```

  **Commit**: YES
  - Message: `copy(frontend): 开场语前端同源替换（说人话）`

- [ ] 4. 图谱页迁移边/衔接边渲染 + 未知边降级

  **What to do**:
  - `frontend/src/api/graph.ts`：扩展 EdgeType 类型定义加 MIGRATION/LINKAGE（后端 EdgeType 枚举已落 56f8053）
  - `frontend/src/components/graph/relationLabel.ts`：迁移边/衔接边标签纯函数（迁移边=「从X到Y」/衔接边=「维度·方向」）
  - `frontend/src/components/graph/A1KnowledgeGraph.tsx`：React Flow 边渲染消费新类型（样式区分：迁移边=实线箭头、衔接边=虚线、概念边=既有）；未知边类型降级（灰色+tooltip「未知边类型」，s2-unknown-enum-degrade 先例）
  - `frontend/src/components/graph/NodeDetailPanel.tsx`：边详情面板展示新边属性（trigger/dimension/direction）
  - vitest ≥3 用例（迁移边渲染/衔接边渲染/未知边降级）

  **Must NOT do**:
  - 不改后端 EdgeType 枚举（56f8053 已落）；不改 graphify/live_projection 确定性编译
  - 不动既有概念边审核逻辑（EdgeReviewPanel）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**: Can Run In Parallel: YES | Wave 2 | Blocks: T6 | Blocked By: T1

  **References**:
  - `frontend/src/api/graph.ts` L9/20/22/53 — EdgeType 既有类型定义
  - `frontend/src/components/graph/relationLabel.ts` L20 — 边标签纯函数先例
  - `frontend/src/components/graph/A1KnowledgeGraph.tsx` — React Flow 边渲染逻辑
  - `backend/app/models/knowledge_graph.py` L34-35 — MIGRATION/LINKAGE 枚举（后端源）
  - `.sisyphus/evidence/s2-unknown-enum-degrade.txt` — 未知枚举降级先例

  **Acceptance Criteria**:
  - [ ] 迁移边/衔接边在图谱页可渲染（样式区分）
  - [ ] 未知边类型降级不炸（灰色+tooltip）
  - [ ] vitest ≥3 用例全绿 + tsc 零新增

  **QA Scenarios**:
  ```
  Scenario: 新边渲染
    Tool: Bash (vitest)
    Steps:
      1. 构造 mock graph 含 MIGRATION + LINKAGE + 未知边 → 渲染 A1KnowledgeGraph
      2. 断言：迁移边实线箭头、衔接边虚线、未知边灰色 tooltip
    Expected: 三类边正确渲染、零崩溃
    Evidence: .sisyphus/evidence/wave3-t4-edges.txt
  ```

  **Commit**: YES
  - Message: `feat(frontend): 图谱页迁移边/衔接边渲染+未知边降级`

- [ ] 5. 灵感架图谱页安家 UI + D24 knowledge_used 埋点补线

  **What to do**:
  - **前端**：新建 `frontend/src/components/graph/RackPanel.tsx`（或并入 NodeDetailPanel）：展示 material_pool 存量（「你还有 N 个想法在灵感架上」）+ 安家操作入口（点击条目 → 调用既有 /file/{id}/finalize 或新提议端点安家）；复用 ClosingPanel 收尾摊开先例
  - **前端 api**：`frontend/src/api/a1.ts` 扩展 A1Session 类型加 material_pool 字段（后端 /file/{id} 状态端点已可读，批D 数据面就绪）
  - **后端埋点**：`backend/app/domains/creation/a1/guide_engine.py` L1669 knowledge_used 消费点补 `inspiration_log.emit_event("knowledge_used", session)`（1 行，为 D24 二期按钮决策取数——非按钮本身）
  - vitest ≥2 用例（灵感架渲染/安家交互）+ 后端 pytest knowledge_used 埋点 1 用例

  **Must NOT do**:
  - 不实现 D24 二期「查一下」按钮（暂缓，仅补埋点）
  - 不改后端 material_pool 回收逻辑（批D 已落，前端只读消费）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**: Can Run In Parallel: YES | Wave 2 | Blocks: T6 | Blocked By: T1

  **References**:
  - `frontend/src/components/guided/ClosingPanel.tsx` — 收尾摊开先例（灵感架 UI 复用）
  - `frontend/src/api/a1.ts` — A1Session 类型扩展点
  - `backend/app/domains/creation/a1/guide_engine.py` L1669 — knowledge_used 消费点（补 emit_event）
  - `backend/app/domains/creation/a1/inspiration_log.py` — emit_event 先例（批C/D 五事件）
  - GET `/api/a1/file/{file_id}` — material_pool 数据端点（已可读）

  **Acceptance Criteria**:
  - [ ] 灵感架存量在图谱页/收尾可见
  - [ ] 安家操作入口可用（调既有端点）
  - [ ] knowledge_used 埋点 jsonl 落盘
  - [ ] vitest ≥2 + pytest ≥1 全绿 + tsc 零新增 + ruff 增量 0

  **QA Scenarios**:
  ```
  Scenario: 灵感架安家
    Tool: Bash (vitest + pytest)
    Steps:
      1. vitest: 渲染 RackPanel with mock pool 2 条 → 断言条目在
      2. pytest: 构造 knowledge_used=True 会话 → handle_message → 断言 inspiration_log 有 knowledge_used 事件
    Expected: 前端渲染+后端埋点双绿
    Evidence: .sisyphus/evidence/wave3-t5-rack.txt
  ```

  **Commit**: YES
  - Message: `feat(a1): 灵感架图谱页安家UI + D24 knowledge_used 埋点补线`

### Wave 3：集成门禁 + 治理收官

- [ ] 6. 终门禁 + D28 治理收官

  **What to do**:
  - tsc --noEmit 零新增；vitest 全绿（≥325）；Playwright E2E 四幕（活地图/开场语/图谱边/灵感架各一）
  - 后端全量 pytest ≥1838（仅 knowledge_used 埋点补线增量）；ruff 增量 0
  - git diff --stat cbeed54..HEAD -- backend/ 核对仅 guide_engine.py 1 文件（埋点补线）
  - D28 decision-log 综合条目 + PROJECT_STATE 收官两节 + MOC 变更记录 + 指南无补（波次三无新问）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**: NO | 收官 | Blocks: F1-F4 | Blocked By: T2-T5

  **Acceptance Criteria**:
  - [ ] tsc 0 / vitest 全绿 / Playwright 四幕绿 / pytest ≥1838 / ruff 0
  - [ ] backend diff 仅 1 文件（埋点）
  - [ ] D28 + PROJECT_STATE + MOC 落痕

  **Commit**: YES
  - Message: `docs(governance): 波次三收官——D28+终门禁`

---

## Final Verification Wave

- [ ] F1. Plan Compliance Audit — `oracle`
- [ ] F2. Code Quality Review — `unspecified-high`（tsc/vitest/ruff/AI slop）
- [ ] F3. Real Manual QA — `unspecified-high`(+`playwright`)（Playwright 四幕）
- [ ] F4. Scope Fidelity Check — `deep`（后端零改动核对 + label 层未动 + 二期按钮未实现）

---

## Commit Strategy

- T2: `feat(frontend): 活地图七大陆视图组件`
- T3: `copy(frontend): 开场语前端同源替换（说人话）`
- T4: `feat(frontend): 图谱页迁移边/衔接边渲染+未知边降级`
- T5: `feat(a1): 灵感架图谱页安家UI + D24 knowledge_used 埋点补线`
- T6: `docs(governance): 波次三收官——D28+终门禁`

---

## Success Criteria

### Verification Commands
```powershell
cd frontend; npx tsc --noEmit              # 零新增错误
cd frontend; npx vitest                     # 全绿（≥325）
cd frontend; npx playwright test            # E2E 四幕绿
cd backend; .venv\Scripts\python -m pytest --cov=app -q  # ≥1838（仅埋点补线增量）
git diff --stat cbeed54..HEAD -- backend/   # 仅 knowledge_used 埋点 1 文件
```

### Final Checklist
- [ ] 全部 Must Have 存在
- [ ] 全部 Must NOT Have 缺席
- [ ] tsc/vitest/Playwright 三套绿
- [ ] F1-F4 全 APPROVE + 用户 okay
- [ ] D28/PROJECT_STATE/MOC 落痕
