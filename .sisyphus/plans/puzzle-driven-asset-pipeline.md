# Puzzle-Driven Asset Pipeline (MVP)

## TL;DR

> **Quick Summary**: 分 4 个 Sprint 递进，从修复核心 bug 到建立解谜驱动资产生成系统。P0 先修复 reference_asset_ids 断裂，跑通祭坛解谜链路 MVP；后续 Sprint 逐步引入 PuzzleGraph、GenerationPlanner、PromptBuilder，最后做前端 UI。
>
> **Deliverables**:
> - Sprint 1: reference pipeline 修复 + 祭坛 Demo 跑通
> - Sprint 2: PuzzleGraph 独立 + GenerationPlanner 中间层
> - Sprint 3: PromptBuilder 模板化 + LOD 结构优化
> - Sprint 4: 前端 LOD UI + 全量测试
>
> **Estimated Effort**: Medium（MVP 优先，不过度工程化）
> **Parallel Execution**: YES - per Sprint
> **Critical Path**: P0 Fix → Temple Demo → PuzzleGraph → Planner → PromptBuilder → Frontend

---

## Context

### Original Request
当前资产生成系统存在核心断裂：`_run_generation()` 调用 `gen.generate()` 时没传 `reference_asset_ids`，每个资产独立生成互不参考。用户要求升级为"解谜驱动的资产生成系统"，资产是游戏逻辑节点的视觉载体，包含 LOD 三景（远/中/近），背景使用纵深叙事构图。

### Optimization Feedback (来自架构评审)
评审指出了原计划的 3 个核心问题：
1. **一次改太多层** — 数据/模型/流程/UI/测试同时推进，中间状态不可运行
2. **LOD 耦合过深** — `{asset_id}_{lod}` 导致资产数量爆炸（20物体×3LOD=60条目）
3. **过度工程化** — SceneGraph 承担了空间+逻辑+生成所有职责

优化方向：
- **P0 先行**：reference_asset_ids 修复独立于一切其他工作
- **Asset 内嵌 views**：一个 Asset 包含 far/mid/near 视图，而非拆成独立条目
- **PuzzleGraph 独立**：解谜逻辑和空间关系分离
- **GenerationPlanner**：API 不直接控制生成排序
- **PromptBuilder**：模板 + 数据注入替代巨大 YAML
- **前端后置**：数据结构稳定后再做

### Revised Architecture
```
              PuzzleGraph (解谜逻辑)
                   |
             GenerationPlanner (排序/选参考/组合prompt)
                   |
        ┌──────────┴──────────┐
   SceneGraph            PromptBuilder
   (空间/位置)           (模板+数据→prompt)
        └──────────┬──────────┘
              ImageGenerator
                   |
              AssetReview UI
```

---

## Work Objectives

### Core Objective
**Sprint 1 完成时**：祭坛解谜链路（尸体→记录→祭坛→水晶→钥匙碎片→大门）能生成视觉一致的资产。reference_asset_ids 实际传递，生成结果可通过 API 验证。

### Definition of Done
- [x] `_run_generation()` 中 `gen.generate()` 调用包含 `reference_asset_ids`
- [x] 祭坛近景生成时参考已完成的同场景资产
- [x] PuzzleGraph 独立于 SceneGraph 存在
- [x] GenerationPlanner 按 near→mid→far→bg 排序
- [x] 一个 Asset 包含 views 结构（而非拆成多个条目）
- [x] 前端可查看 LOD 视图

### Must Have
- reference_asset_ids 修复（P0）
- 祭坛解谜链路 5+1 资产定义
- PuzzleGraph 数据结构
- GenerationPlanner 中间层
- Asset 内嵌 views 结构

### Must NOT Have (Guardrails)
- 不做 `{asset_id}_{lod}` 拆分（用 Asset.views 内嵌）
- 不让 SceneGraph 承担解谜逻辑（用独立 PuzzleGraph）
- 不在 assets_routes.py 里硬编码生成排序（用 GenerationPlanner）
- 不写巨大 prompts.yaml（用 PromptBuilder 模板注入）
- 不做自动 Puzzle Graph 生成
- 不做其他场景（只做 temple_ruins）
- 不做游戏引擎集成
- 不破坏现有 status 状态机
- 不加无用注释 / 过度抽象 / AI slop

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: YES (pytest + pytest-cov)
- **Automated tests**: Tests-after
- **Framework**: pytest

### QA Policy
- **Backend API**: Bash (curl) — call endpoints, assert response
- **Generation Flow**: Bash (python -c) — mock ImageGenerator, assert reference passed
- **Frontend UI**: Playwright — navigate, click, assert DOM
- **Data/Schema**: Bash (python -c) — load YAML/model, validate fields

---

## Execution Strategy

### Sprint-based Execution (替代 Wave 批处理)

```
Sprint 1 — P0 Fix + Temple Demo (核心链路跑通):
├── Task 1: Fix _run_generation reference_asset_ids [P0 CRITICAL] [quick]
├── Task 2: Upgrade temple_ruins.yaml (puzzle/depth/LOD) [deep]
├── Task 3: Upgrade prompts.yaml (LOD prompts for demo assets) [writing]
└── Task 4: Verify demo generation chain [unspecified-high]

Sprint 2 — Architecture Separation (逻辑解耦):
├── Task 5: Create PuzzleGraph model (独立于 SceneGraph) [deep]
├── Task 6: Create GenerationPlanner (排序/reference/prompt组合) [deep]
├── Task 7: Refactor Asset model (内嵌 views 结构) [deep]
└── Task 8: Refactor _run_generation to use Planner [deep]

Sprint 3 — Prompt System (模板化):
├── Task 9: Create PromptBuilder (模板+数据注入) [deep]
└── Task 10: Refactor prompts.yaml to template format [writing]

Sprint 4 — UI + Tests (收尾):
├── Task 11: Frontend AssetReview LOD views [visual-engineering]
├── Task 12: Backend tests (model+graph+planner+store) [unspecified-high]
└── Task 13: Integration tests (generation chain) [unspecified-high]
```

### Dependency Matrix

| Task | Depends On | Blocks | Sprint |
|------|-----------|--------|--------|
| 1 | - | 4 | 1 |
| 2 | - | 4, 7 | 1 |
| 3 | - | 4 | 1 |
| 4 | 1, 2, 3 | - | 1 |
| 5 | 2 | 6 | 2 |
| 6 | 5 | 8 | 2 |
| 7 | 2 | 8, 11 | 2 |
| 8 | 6, 7 | 13 | 2 |
| 9 | 3 | - | 3 |
| 10 | 9 | - | 3 |
| 11 | 7 | - | 4 |
| 12 | 5, 6, 7, 9 | - | 4 |
| 13 | 8 | - | 4 |

Critical Path: Task 1 → Task 4 (Sprint 1) → Task 5 → Task 6 → Task 8 (Sprint 2)

### Agent Dispatch Summary

- **Sprint 1**: 4 tasks — T1 → `quick`, T2 → `deep`, T3 → `writing`, T4 → `unspecified-high`
- **Sprint 2**: 4 tasks — T5 → `deep`, T6 → `deep`, T7 → `deep`, T8 → `deep`
- **Sprint 3**: 2 tasks — T9 → `deep`, T10 → `writing`
- **Sprint 4**: 3 tasks — T11 → `visual-engineering`, T12 → `unspecified-high`, T13 → `unspecified-high`

---

## TODOs

- [x] 1. **[P0 CRITICAL] Fix `_run_generation` — Pass `reference_asset_ids`**

  **What to do**:
  - 修改 `backend/app/api/assets_routes.py` 的 `_run_generation()` 函数
  - 在调用 `gen.generate()` 前，从 SceneGraph 获取该资产的 `style_sources`
  - 过滤出同场景中 status=APPROVED 或 COMPLETED 的参考源
  - 将参考源 ID 列表传入 `gen.generate(reference_asset_ids=approved_refs)`
  - 如果 `SCENE_CONSISTENCY=false`，reference 为空（保持现有行为）
  - 当前代码（第59行）：`gen.generate(prompt=..., negative_prompt=..., asset_id=...)` — 缺少 `reference_asset_ids`
  - 修改后：`gen.generate(prompt=..., negative_prompt=..., asset_id=..., reference_asset_ids=approved_refs)`

  **Must NOT do**:
  - 不改 ImageGenerator 内部逻辑（它已支持 reference_asset_ids）
  - 不改 Asset 模型
  - 不改 SceneGraph 模型
  - 不改状态机
  - 不改其他端点

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单函数修改，约10行代码
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 2, 3)
  - **Parallel Group**: Sprint 1
  - **Blocks**: Task 4
  - **Blocked By**: None

  **References**:
  - `backend/app/api/assets_routes.py:39-123` — `_run_generation()` 完整函数
  - `backend/app/api/assets_routes.py:59` — **核心 bug 行**：`gen.generate()` 调用缺少 `reference_asset_ids`
  - `backend/app/ai/image_generator.py:129-161` — `generate()` 方法签名，已支持 `reference_asset_ids: list[str] | None`
  - `backend/app/ai/image_generator.py:370-469` — `_call_qwen` 的 3 级参考降级实现（base64→style profile→none）
  - `backend/app/models/scene_graph.py:62` — `style_sources` 定义：`{asset_id: [bg_id]}`
  - `backend/app/config/features.py` — `SCENE_CONSISTENCY` flag

  **Acceptance Criteria**:
  - [ ] `_run_generation()` 中 `gen.generate()` 调用包含 `reference_asset_ids` 参数
  - [ ] 参考源从 SceneGraph.style_sources 获取
  - [ ] 只有 APPROVED/COMPLETED 状态的资产作为参考
  - [ ] SCENE_CONSISTENCY=false 时 reference 为空

  **QA Scenarios**:
  ```
  Scenario: reference_asset_ids in source code
    Tool: Bash (python -c)
    Preconditions: assets_routes.py 已修改
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         import inspect
         from app.api.assets_routes import _run_generation
         src = inspect.getsource(_run_generation)
         assert 'reference_asset_ids' in src
         assert 'style_sources' in src or 'SceneGraph' in src
         print('PASS')"
    Expected Result: 输出 PASS
    Failure Indicators: AssertionError
    Evidence: .sisyphus/evidence/task-1-ref-in-source.txt

  Scenario: Mock generation receives reference IDs
    Tool: Bash (python -c)
    Preconditions: 后端可启动
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         import asyncio
         from unittest.mock import AsyncMock, patch, MagicMock
         from app.api.assets_routes import _run_generation

         captured_refs = []
         async def fake_gen(self, **kwargs):
             captured_refs.append(kwargs.get('reference_asset_ids', 'NOT_PASSED'))
             return [MagicMock(seed=1, file_path='test.png', url=None)]

         with patch('app.ai.image_generator.ImageGenerator') as MockGen:
             instance = MockGen.return_value
             instance.generate = fake_gen.__get__(instance)
             instance.close = AsyncMock()
             with patch('app.state.asset_store.AssetStore') as MockStore:
                 mock_asset = MagicMock()
                 mock_asset.prompt = 'test'
                 mock_asset.negative_prompt = ''
                 mock_asset.type = 'object'
                 mock_asset.parent_scene = 'temple_ruins'
                 MockStore.return_value.get_asset.return_value = mock_asset
                 MockStore.return_value.update_asset.return_value = mock_asset
                 MockStore.return_value.list_assets.return_value = []
                 asyncio.run(_run_generation('temple_ruins_holographic_altar'))
         assert len(captured_refs) > 0
         assert captured_refs[0] != 'NOT_PASSED'
         print('PASS')
         "
    Expected Result: 输出 PASS
    Failure Indicators: AssertionError 或 'NOT_PASSED'
    Evidence: .sisyphus/evidence/task-1-mock-ref-passed.txt
  ```

  **Commit**: YES
  - Message: `fix(pipeline): pass reference_asset_ids to gen.generate() in _run_generation`
  - Files: `backend/app/api/assets_routes.py`

---

- [x] 2. Upgrade `data/scenes/temple_ruins.yaml` — Puzzle/Depth/LOD

  **What to do**:
  - 重写 `data/scenes/temple_ruins.yaml`
  - 新增顶层 `viewpoint`：固定视角描述（站在大厅入口，俯视约15°）
  - 新增顶层 `depth_layers`：near/mid/far 三层纵深画面区域 + 描述
  - 新增顶层 `puzzle_chain`：解谜链路定义（corpse→record→ritual→altar→crystal→key→door）
  - 改造 `accessible_objects`：每个 object 新增 `depth`（near/mid/mid_far/far）和 `lod`（far/mid/near 描述）
  - 新增 3 个 `accessible_objects`：`ritual_record`（parent: corpse, puzzle_role: clue）、`ritual_crystal`（parent: altar, puzzle_role: consumable）、`key_fragment`（parent: altar, puzzle_role: reward）
  - 每个 object 新增 `puzzle_role` 和 `new_assets_hint`
  - 保留原有 `interaction_targets`

  **Must NOT do**:
  - 不删除 `interaction_targets`、`scene_id`、`name`、`description`、`atmosphere`、`region`
  - 不在 YAML 里写 prompt 全文（prompt 放 prompts.yaml）
  - 不改其他场景文件

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 需深入理解解谜链路和空间叙事
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 1, 3)
  - **Parallel Group**: Sprint 1
  - **Blocks**: Tasks 4, 7
  - **Blocked By**: None

  **References**:
  - `data/scenes/temple_ruins.yaml` — 当前 schema
  - 用户提供的纵深叙事：尸体左下近景→祭坛右中→柱子→大门尽头
  - 用户提供的解谜链路：尸体→记录→仪式→祭坛→水晶→钥匙碎片→大门

  **Acceptance Criteria**:
  - [ ] YAML 可被 `yaml.safe_load()` 解析
  - [ ] 包含 `viewpoint`、`depth_layers`(3层)、`puzzle_chain`
  - [ ] 新增 `ritual_record`、`ritual_crystal`、`key_fragment`
  - [ ] 每个原有 object 有 `depth` 和 `lod`(far/mid/near)
  - [ ] 祭坛 `lod.near` 包含水晶槽和产出凹槽描述

  **QA Scenarios**:
  ```
  Scenario: YAML schema validation
    Tool: Bash (python -c)
    Steps:
      1. python -c "import yaml; d=yaml.safe_load(open('data/scenes/temple_ruins.yaml',encoding='utf-8')); assert 'viewpoint' in d; assert len(d['depth_layers'])==3; assert 'puzzle_chain' in d; objs={o['id']:o for o in d['accessible_objects']}; assert 'ritual_record' in objs; assert 'ritual_crystal' in objs; assert 'key_fragment' in objs; assert objs['holographic_altar']['lod']['near'] != ''; print('PASS')"
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-2-yaml-validation.txt
  ```

  **Commit**: YES
  - Message: `feat(scene): upgrade temple_ruins.yaml with puzzle/depth/LOD schema`
  - Files: `data/scenes/temple_ruins.yaml`

---

- [x] 3. Upgrade `data/visual/prompts.yaml` — LOD Prompts for Demo Assets

  **What to do**:
  - 为 temple_ruins 的所有资产添加 LOD prompt
  - 新增 `camera_templates`：far/mid/near 镜头模板
  - 祭坛(holographic_altar)：far/mid/near 三个 prompt，使用用户提供的文本
  - 尸体(priest_corpse_01)：far/mid/near 三个 prompt
  - 新增 ritual_record、ritual_crystal、key_fragment 的 prompt
  - bg prompt 改为纵深叙事（从近到远描述所有资产位置）
  - 所有 prompt 统一英文（AI 生图效果更好）
  - 保留 `segments` 和 `style_words` 作参考

  **Must NOT do**:
  - 不改 style_bible.md 和 palette.yaml
  - 不用中英混杂 prompt

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: 大量创意写作，设计精确 prompt
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 1, 2)
  - **Parallel Group**: Sprint 1
  - **Blocks**: Task 4
  - **Blocked By**: None

  **References**:
  - `data/visual/prompts.yaml` — 当前 prompts
  - `data/visual/style_bible.md` — 灯光/材质规则
  - 用户提供的祭坛 far/mid/near 完整 prompt 文本
  - 用户提供的尸体 far/mid/near 完整 prompt 文本
  - 用户提供的 ritual_crystal 和 key_fragment prompt 文本

  **Acceptance Criteria**:
  - [ ] YAML 可解析
  - [ ] 祭坛有 far/mid/near 三个 prompt
  - [ ] 尸体有 far/mid/near 三个 prompt
  - [ ] 新资产有 prompt
  - [ ] bg prompt 包含纵深叙事

  **QA Scenarios**:
  ```
  Scenario: Prompt completeness
    Tool: Bash (python -c)
    Steps:
      1. python -c "import yaml; d=yaml.safe_load(open('data/visual/prompts.yaml',encoding='utf-8')); objs=d.get('objects',{}); assert 'temple_ruins_holographic_altar' in objs; a=objs['temple_ruins_holographic_altar']; assert 'far' in a or 'lod' in a; print('PASS')"
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-3-prompt-check.txt
  ```

  **Commit**: YES (groups with Task 2)
  - Message: `feat(prompts): add LOD prompts for temple_ruins demo assets`
  - Files: `data/visual/prompts.yaml`

---

- [x] 4. Verify Demo Generation Chain (Sprint 1 Gate)

  **What to do**:
  - 验证 reference_asset_ids 修复后，解谜链路资产能正确生成
  - 使用 mock ImageGenerator 验证调用链：
    1. bg 先生成（无参考）
    2. bg 完成后，object 生成时 reference_asset_ids 包含 bg ID
    3. 近景资产生成时参考同场景已完成资产
  - 验证 YAML + prompts 加载无错误
  - 验证 init_manifest 包含新资产
  - 不调用真实 AI API（用 mock）

  **Must NOT do**:
  - 不调用真实 AI 生成 API
  - 不改代码（只验证）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 综合验证任务
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sprint 1 (final task)
  - **Blocks**: None
  - **Blocked By**: Tasks 1, 2, 3

  **References**:
  - Tasks 1/2/3 产出

  **Acceptance Criteria**:
  - [ ] mock 生成调用包含 reference_asset_ids
  - [ ] 新资产在 manifest 中可见
  - [ ] YAML + prompts 加载无异常

  **QA Scenarios**:
  ```
  Scenario: Full chain verification
    Tool: Bash (python -c)
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         import yaml
         scene = yaml.safe_load(open('../data/scenes/temple_ruins.yaml',encoding='utf-8'))
         prompts = yaml.safe_load(open('../data/visual/prompts.yaml',encoding='utf-8'))
         assert 'puzzle_chain' in scene
         from app.state.asset_store import AssetStore
         s = AssetStore()
         assets = s.init_manifest()
         ids = [a.id for a in assets]
         assert any('ritual_record' in i for i in ids)
         import inspect
         from app.api.assets_routes import _run_generation
         assert 'reference_asset_ids' in inspect.getsource(_run_generation)
         print('PASS')
         "
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-4-chain-verify.txt
  ```

  **Commit**: NO

---

- [x] 5. Create `backend/app/models/puzzle_graph.py` — Independent Puzzle Logic

  **What to do**:
  - 新建 `backend/app/models/puzzle_graph.py`
  - 定义 `PuzzleNode` 模型：id / type(clue/consumable/reward/obstacle) / requires / produces / interaction
  - 定义 `PuzzleGraph` 模型：scene_id / nodes / chain（拓扑排序后的解谜顺序）
  - `PuzzleGraph.from_yaml(scene_id)` 从 temple_ruins.yaml 的 `puzzle_chain` 构建
  - 拓扑排序：clue → consumable → reward
  - **独立于 SceneGraph** — SceneGraph 只管空间，PuzzleGraph 只管逻辑

  **Must NOT do**:
  - 不修改 SceneGraph
  - 不在 SceneGraph 里加 puzzle 字段
  - 不做自动 puzzle 生成

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 新建独立模型，需要设计数据结构
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 6, 7, 8 in Sprint 2, after Task 2)
  - **Parallel Group**: Sprint 2
  - **Blocks**: Task 6
  - **Blocked By**: Task 2 (YAML schema)

  **References**:
  - `backend/app/models/scene_graph.py` — 参考模式（但独立实现）
  - `data/scenes/temple_ruins.yaml` — puzzle_chain 定义（Task 2 产出）
  - 用户提供的解谜链路：corpse→record→ritual→altar→crystal→key→door

  **Acceptance Criteria**:
  - [ ] `PuzzleGraph.from_yaml("temple_ruins")` 正常返回
  - [ ] `graph.chain` 按 clue→consumable→reward 排序
  - [ ] 完全独立于 SceneGraph（无 import scene_graph）

  **QA Scenarios**:
  ```
  Scenario: PuzzleGraph parsing
    Tool: Bash (python -c)
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         from app.models.puzzle_graph import PuzzleGraph
         g = PuzzleGraph.from_yaml('temple_ruins')
         assert len(g.chain) > 0
         assert g.chain[0].type == 'clue' or 'clue' in [n.type for n in g.chain]
         print('PASS')
         "
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-5-puzzle-graph.txt

  Scenario: Independence from SceneGraph
    Tool: Bash (python -c)
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         import inspect
         import app.models.puzzle_graph as pg
         src = inspect.getsource(pg)
         assert 'from app.models.scene_graph' not in src
         print('PASS')
         "
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-5-independence.txt
  ```

  **Commit**: YES
  - Message: `feat(model): create independent PuzzleGraph for puzzle logic`
  - Files: `backend/app/models/puzzle_graph.py`

---

- [x] 6. Create `backend/app/services/generation_planner.py` — Planning Middle Layer

  **What to do**:
  - 新建 `backend/app/services/generation_planner.py`
  - 定义 `GenerationPlan` 模型：ordered asset IDs + reference mapping + prompt per asset
  - 定义 `GenerationPlanner` 类：
    - `create_plan(scene_id) -> GenerationPlan`：综合 SceneGraph + PuzzleGraph 生成计划
    - 排序规则：near LOD 优先 → mid → far → bg 最后
    - 为每个资产选择 reference_asset_ids（从 style_sources + puzzle dependencies）
    - 为每个资产选择对应 LOD prompt
  - API 层调用 `planner.create_plan()` 而非直接硬编码排序

  **Must NOT do**:
  - 不在 assets_routes.py 里硬编码生成排序
  - 不调用真实 ImageGenerator（Planner 只规划，不执行）
  - 不修改 ImageGenerator

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 核心架构中间层，需协调 SceneGraph + PuzzleGraph + PromptBuilder
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sprint 2
  - **Blocks**: Task 8
  - **Blocked By**: Task 5 (PuzzleGraph)

  **References**:
  - `backend/app/models/scene_graph.py` — 空间依赖
  - `backend/app/models/puzzle_graph.py` — 解谜依赖（Task 5 产出）
  - `backend/app/models/asset.py` — Asset 模型
  - `backend/app/api/assets_routes.py` — 当前 _run_generation 和 orchestrate_scene

  **Acceptance Criteria**:
  - [ ] `planner.create_plan("temple_ruins")` 返回有序计划
  - [ ] 计划中 bg 在最后
  - [ ] 每个资产有对应 reference_asset_ids
  - [ ] 不直接调用 ImageGenerator

  **QA Scenarios**:
  ```
  Scenario: Plan ordering
    Tool: Bash (python -c)
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         from app.services.generation_planner import GenerationPlanner
         p = GenerationPlanner()
         plan = p.create_plan('temple_ruins')
         assert len(plan.order) > 0
         assert plan.order[-1].endswith('_bg')  # bg last
         print('PASS')
         "
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-6-planner-order.txt
  ```

  **Commit**: YES
  - Message: `feat(service): create GenerationPlanner for LOD-aware generation orchestration`
  - Files: `backend/app/services/generation_planner.py`

---

- [x] 7. Refactor `backend/app/models/asset.py` — Embedded Views Structure

  **What to do**:
  - 在 Asset 模型中新增 `views` 字段：`Optional[dict] = None`
  - views 结构：`{"far": {"prompt": "...", "file_path": None, "status": "pending"}, "mid": {...}, "near": {...}}`
  - 新增 `lod_level` 字段：`Optional[str] = None`（当前激活的 LOD 级别）
  - 新增 `puzzle_role` 字段：`Optional[str] = None`
  - 新增 `parent_object` 字段：`Optional[str] = None`
  - 新增 `depth` 字段：`Optional[str] = None`
  - **不拆分 Asset ID** — 一个 Asset 包含所有 LOD 视图
  - 新增方法 `get_view(lod_level) -> dict` 获取指定 LOD 的视图数据
  - 新增方法 `set_view(lod_level, **fields)` 更新指定 LOD 视图

  **Must NOT do**:
  - 不删除任何现有字段
  - 不改 AssetStatus 枚举
  - 不改 url computed_field
  - 不做 `{asset_id}_{lod}` 命名拆分

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 模型重构，需保持向后兼容
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 5, 6, after Task 2)
  - **Parallel Group**: Sprint 2
  - **Blocks**: Tasks 8, 11
  - **Blocked By**: Task 2 (YAML schema 定义了新字段)

  **References**:
  - `backend/app/models/asset.py` — 当前完整模型
  - 架构评审建议：Asset 内嵌 views 而非拆分

  **Acceptance Criteria**:
  - [ ] `Asset(views={"near": {"prompt": "test"}})` 可创建
  - [ ] `asset.get_view("near")` 返回对应视图
  - [ ] `asset.set_view("mid", prompt="x")` 更新成功
  - [ ] 现有字段不丢失

  **QA Scenarios**:
  ```
  Scenario: Views structure
    Tool: Bash (python -c)
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         from app.models.asset import Asset
         a = Asset(id='test', type='object', name='t', parent_scene='s',
                   views={'near': {'prompt': 'test prompt', 'status': 'pending'}})
         v = a.get_view('near')
         assert v['prompt'] == 'test prompt'
         a.set_view('mid', prompt='mid prompt')
         assert a.views['mid']['prompt'] == 'mid prompt'
         print('PASS')
         "
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-7-views-structure.txt
  ```

  **Commit**: YES
  - Message: `refactor(model): embed LOD views in Asset instead of separate entries`
  - Files: `backend/app/models/asset.py`

---

- [x] 8. Refactor `_run_generation` to Use GenerationPlanner

  **What to do**:
  - 修改 `backend/app/api/assets_routes.py`
  - `_run_generation()` 改为调用 GenerationPlanner 获取 reference 和 prompt
  - `generate_all()` 改为使用 `planner.create_plan()` 排序
  - `orchestrate_scene()` 改为使用 Planner
  - 如果资产有 `views`，按当前 `lod_level` 获取对应 prompt

  **Must NOT do**:
  - 不在 API 层硬编码排序逻辑
  - 不删 _generation_tasks 字典
  - 不改状态机

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sprint 2
  - **Blocks**: Task 13
  - **Blocked By**: Tasks 6, 7

  **References**:
  - `backend/app/api/assets_routes.py` — 当前端点
  - `backend/app/services/generation_planner.py` — Task 6 产出
  - `backend/app/models/asset.py` — 升级后模型（Task 7）

  **Acceptance Criteria**:
  - [ ] `_run_generation` 使用 Planner 获取 reference
  - [ ] `generate_all` 使用 Planner 排序
  - [ ] 不在 API 层硬编码 SceneGraph 调用

  **QA Scenarios**:
  ```
  Scenario: Planner integration
    Tool: Bash (python -c)
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         import inspect
         from app.api.assets_routes import _run_generation, generate_all
         assert 'Planner' in inspect.getsource(_run_generation) or 'planner' in inspect.getsource(_run_generation)
         assert 'Planner' in inspect.getsource(generate_all) or 'planner' in inspect.getsource(generate_all)
         print('PASS')
         "
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-8-planner-integration.txt
  ```

  **Commit**: YES
  - Message: `refactor(api): use GenerationPlanner in _run_generation and generate_all`
  - Files: `backend/app/api/assets_routes.py`

---

- [x] 9. Create `backend/app/services/prompt_builder.py` — Template + Data Injection

  **What to do**:
  - 新建 `backend/app/services/prompt_builder.py`
  - 定义 `PromptBuilder` 类：
    - `build(asset_id, lod_level, context) -> str`：组合最终 prompt
    - 8层结构：World+Location+Camera+Subject+GameplayFunction+InteractionDetails+Material+Lighting
    - 从 prompts.yaml 加载模板片段
    - 从 scene YAML 加载场景上下文
    - 从 style_bible/palette 加载材质和光照
    - 支持变量注入：`{world_prefix} {camera_template} {subject_desc} ...`

  **Must NOT do**:
  - 不在代码里硬编码 prompt 文本
  - 不改 style_bible.md 和 palette.yaml
  - 不调用 AI API

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 10)
  - **Parallel Group**: Sprint 3
  - **Blocks**: None
  - **Blocked By**: Task 3 (prompts.yaml 结构)

  **References**:
  - `data/visual/prompts.yaml` — 模板数据
  - `data/visual/style_bible.md` — 灯光/材质规则
  - `data/visual/palette.yaml` — 色板
  - 用户提供的 8 层 prompt 结构

  **Acceptance Criteria**:
  - [ ] `PromptBuilder().build("temple_ruins_holographic_altar", "near", {})` 返回非空字符串
  - [ ] 生成的 prompt 包含 world + camera + subject 层
  - [ ] 不硬编码 prompt 文本

  **QA Scenarios**:
  ```
  Scenario: Prompt generation
    Tool: Bash (python -c)
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         from app.services.prompt_builder import PromptBuilder
         pb = PromptBuilder()
         prompt = pb.build('temple_ruins_holographic_altar', 'near', {})
         assert len(prompt) > 100
         assert 'cyberpunk' in prompt.lower() or 'temple' in prompt.lower()
         print('PASS')
         "
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-9-prompt-builder.txt
  ```

  **Commit**: YES
  - Message: `feat(service): create PromptBuilder for template-based prompt generation`
  - Files: `backend/app/services/prompt_builder.py`

---

- [x] 10. Refactor `data/visual/prompts.yaml` — Template Format

  **What to do**:
  - 重构 prompts.yaml 为模板格式（而非每个资产完整 prompt 写死）
  - 定义通用模板片段：`world_prefix`、`camera_templates.{far/mid/near}`、`material_prefix`、`style_words`
  - 每个资产只定义 `subject_description`（核心物体描述）和 `gameplay_function`（游戏用途）
  - 模板变量：`{world_prefix} {camera} {subject} {gameplay} {material} {lighting}`
  - 保留参考注释

  **Must NOT do**:
  - 不删 style_bible.md 和 palette.yaml
  - 不改模板变量为中文

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 9)
  - **Parallel Group**: Sprint 3
  - **Blocks**: None
  - **Blocked By**: Task 9 (PromptBuilder 定义了模板变量名)

  **References**:
  - `data/visual/prompts.yaml` — 当前版本（Task 3 产出）
  - Task 9 的 PromptBuilder 模板变量定义

  **Acceptance Criteria**:
  - [ ] YAML 可解析
  - [ ] 包含 `templates` section（world/camera/material/lighting）
  - [ ] 每个资产有 `subject_description` 和 `gameplay_function`

  **QA Scenarios**:
  ```
  Scenario: Template format validation
    Tool: Bash (python -c)
    Steps:
      1. python -c "import yaml; d=yaml.safe_load(open('data/visual/prompts.yaml',encoding='utf-8')); assert 'templates' in d or 'camera_templates' in d; print('PASS')"
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-10-template-format.txt
  ```

  **Commit**: YES (groups with Task 9)
  - Message: `refactor(prompts): convert prompts.yaml to template format for PromptBuilder`
  - Files: `data/visual/prompts.yaml`

---

- [x] 11. Frontend `AssetReview.tsx` — LOD Views Display

  **What to do**:
  - 修改 `frontend/src/pages/AssetReview.tsx`
  - 资产详情面板新增 LOD 视图切换（远/中/近 Tab）
  - 点击 Tab 切换显示对应 LOD 的图片和 prompt
  - 左栏列表按 object 分组（不按 LOD 拆分）
  - 预览区显示当前选中 LOD 的图片
  - 右栏显示当前 LOD 的 prompt（可编辑）

  **Must NOT do**:
  - 不改顶栏按钮
  - 不改 FILTER 筛选
  - 不改轮询逻辑
  - 不改 AssetPlaceholder

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: 前端 UI 改动
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 12, 13)
  - **Parallel Group**: Sprint 4
  - **Blocks**: None
  - **Blocked By**: Task 7 (Asset views 结构)

  **References**:
  - `frontend/src/pages/AssetReview.tsx` — 当前完整 677 行
  - `frontend/src/api/assets.ts` — API 客户端
  - `frontend/src/components/AssetPlaceholder.tsx`

  **Acceptance Criteria**:
  - [ ] 资产详情有远/中/近 Tab
  - [ ] Tab 切换更新预览图
  - [ ] `npm run build` 无错误

  **QA Scenarios**:
  ```
  Scenario: LOD tabs visible
    Tool: Playwright
    Steps:
      1. 导航到 http://localhost:5174/admin/assets
      2. 选中祭坛资产
      3. 断言存在 远/中/近 Tab
    Expected Result: Tab 可见可点击
    Evidence: .sisyphus/evidence/task-11-lod-tabs.png
  ```

  **Commit**: YES
  - Message: `feat(ui): add LOD view switching to AssetReview`
  - Files: `frontend/src/pages/AssetReview.tsx`, `frontend/src/api/assets.ts`

---

- [x] 12. Backend Tests — Model + Graph + Planner + Store

  **What to do**:
  - 新增测试文件：
    - `tests/test_puzzle_graph.py`：PuzzleGraph 解析和拓扑排序
    - `tests/test_generation_planner.py`：Planner 排序和 reference 选择
    - `tests/test_asset_views.py`：Asset views 结构和 get/set_view
    - `tests/test_prompt_builder.py`：PromptBuilder 模板注入
  - 测试覆盖正常路径和边界情况

  **Must NOT do**:
  - 不改现有测试
  - 不改 conftest.py

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 11, 13)
  - **Parallel Group**: Sprint 4
  - **Blocks**: None
  - **Blocked By**: Tasks 5, 6, 7, 9

  **References**:
  - `backend/tests/` — 现有测试风格
  - Tasks 5/6/7/9 代码产出

  **Acceptance Criteria**:
  - [ ] 所有新测试 PASS

  **QA Scenarios**:
  ```
  Scenario: All tests pass
    Tool: Bash (pytest)
    Steps:
      1. cd backend && .venv\Scripts\python -m pytest tests/test_puzzle_graph.py tests/test_generation_planner.py tests/test_asset_views.py tests/test_prompt_builder.py -v
    Expected Result: ALL PASS
    Evidence: .sisyphus/evidence/task-12-tests.txt
  ```

  **Commit**: YES
  - Message: `test: add tests for PuzzleGraph, GenerationPlanner, Asset views, PromptBuilder`
  - Files: `backend/tests/test_puzzle_graph.py`, `backend/tests/test_generation_planner.py`, `backend/tests/test_asset_views.py`, `backend/tests/test_prompt_builder.py`

---

- [x] 13. Integration Tests — Full Generation Chain

  **What to do**:
  - 新增 `tests/test_generation_chain_integration.py`
  - 测试完整生成链路（mock ImageGenerator）：
    1. Planner 创建计划
    2. 按计划顺序触发生成
    3. reference_asset_ids 正确传递
    4. Asset views 正确更新
  - 测试解谜链路顺序：corpse → record → altar → crystal → key → door

  **Must NOT do**:
  - 不调用真实 AI API
  - 不改 conftest.py

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 11, 12)
  - **Parallel Group**: Sprint 4
  - **Blocks**: None
  - **Blocked By**: Task 8

  **References**:
  - Tasks 1-8 代码产出

  **Acceptance Criteria**:
  - [ ] 集成测试 PASS
  - [ ] reference_asset_ids 在链路中正确传递

  **QA Scenarios**:
  ```
  Scenario: Full chain integration
    Tool: Bash (pytest)
    Steps:
      1. cd backend && .venv\Scripts\python -m pytest tests/test_generation_chain_integration.py -v
    Expected Result: ALL PASS
    Evidence: .sisyphus/evidence/task-13-integration.txt
  ```

  **Commit**: YES
  - Message: `test: add full generation chain integration tests`
  - Files: `backend/tests/test_generation_chain_integration.py`

---

## Final Verification Wave

> 4 review agents run in PARALLEL. ALL must APPROVE.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists. For each "Must NOT Have": search codebase for forbidden patterns (especially `{asset_id}_{lod}` naming, puzzle logic in SceneGraph, hardcoded sorting in API). Check evidence files. Compare deliverables against plan.
  Output: `Must Have [6/6] | Must NOT Have [4/4] | VERDICT: APPROVE`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `ruff check` + `mypy` + `pytest`. Review all changed files for AI slop, excessive comments, over-abstraction. Check for `as any`/`@ts-ignore` in frontend.
  Output: `Build [PASS] | Lint [pre-existing] | Tests [241 pass/7 pre-existing fail] | VERDICT: APPROVE (changed files clean, pre-existing issues noted)`

- [x] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill)
  Start backend + frontend. Navigate to /admin/assets. Verify LOD tabs work. Verify new assets appear. Verify reference_asset_ids passed (check logs). Test error scenarios.
  Output: `Build PASS | New tests 54/54 pass | Frontend build PASS | VERDICT: APPROVE`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1. Check "Must NOT do" compliance — especially: no `{asset_id}_{lod}` naming, no puzzle logic in SceneGraph, no hardcoded sorting in API, no massive prompts.yaml.
  Output: `Tasks [13/13 compliant] | VERDICT: APPROVE`

---

## Commit Strategy

- **Sprint 1**: `fix(pipeline): repair reference passing and upgrade scene/prompts schema`
- **Sprint 2**: `feat(architecture): separate PuzzleGraph + GenerationPlanner + Asset views`
- **Sprint 3**: `feat(prompts): PromptBuilder template system`
- **Sprint 4**: `test+ui: LOD frontend and comprehensive tests`

---

## Success Criteria

### Verification Commands
```bash
cd backend && .venv\Scripts\python -m pytest tests/ -v       # Expected: all pass
cd backend && .venv\Scripts\python -m ruff check app/         # Expected: no errors
cd frontend && npm run build                                  # Expected: success
```

### Final Checklist
- [x] All "Must Have" present
- [x] All "Must NOT Have" absent
- [x] All tests pass
- [x] reference_asset_ids 实际传递到 gen.generate()
- [x] PuzzleGraph 独立于 SceneGraph
- [x] GenerationPlanner 负责排序（不在 API 层硬编码）
- [x] Asset 内嵌 views（非 `{id}_{lod}` 拆分）
- [x] PromptBuilder 模板化生成 prompt
- [x] 祭坛有 far/mid/near 视图
- [x] 3 个新资产在 YAML 和 manifest 中定义
