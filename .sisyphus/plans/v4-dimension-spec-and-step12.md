# SPEC v4 标准制定 + Step 1-2 生产化

## TL;DR

> **快速摘要**: 先跑 3×3 验证实验确认 Step 1-2 路径可行，基于实验结果将 SYSTEM_DESIGN_SPEC 从 v3 升级到 v4（新增 6 维约束体系标准），验证标准完整性后，迁移为生产代码。
>
> **交付物**:
> - `backend/experiments/step12_validation.py` — 3×3 验证实验脚本
> - `docs/SYSTEM_DESIGN_SPEC_v4.md` — v3→v4 升级，新增 §18 6维约束体系接口注册区
> - `data/weight_matrix.yaml` — 6层×6维权重配置
> - `backend/app/models/dimension.py` — 6维约束 Pydantic 模型 + 枚举
> - `backend/app/services/dimension_generator.py` — 权重查找 + prompt组装 + LLM生成
> - `backend/app/api/constraints_routes.py` — API 端点
> - `backend/app/config/paths.py` — 新增 WEIGHT_MATRIX_PATH
> - 测试文件 × 3（`test_dimension_service.py` 含 weight matrix loader + prompt + generate 测试 / `test_constraints_api.py` API 端点测试 / Task 2 的模型验证内嵌在 QA 场景中）
>
> **预估工作量**: Medium
> **并行执行**: YES - 3 waves (+ Wave 0 实验)
> **关键路径**: Task 0 (实验) → Task 1 (SPEC v4) → Gate → Task 2+3 (并行) → Task 4 → Final Verification

---

## Context

### Original Request

用户要求根据当前代码和目标系统全流程，先完成 SYSTEM_DESIGN_SPEC_v3→v4 的标准更新（重点：接口和参数标准），再生成 Step 1-2 的生产代码。硬性约束："必须先有标准，再生成代码；标准不完成不终止计划。"

### Interview Summary

**关键讨论**:
- 6维模型放新建 `models/dimension.py`，与五图模型的 ConstraintTree 隔离
- WEIGHT_MATRIX 用 YAML 配置文件（灵活可调）
- Service 层 + API 端点双层结构，为商用阶段多端适配（小程序/APP/网页）预留
- 测试策略：纯 Python 逻辑 TDD，LLM 调用不测试

**研究结论**:
- 实验验证权重差异达 3.9x 内容密度差异
- 6维 JSON 输出 schema 从实验报告中提取，每维有固定子字段
- provider.chat_json() 返回 dict[str, Any]，需要 Pydantic 模型做类型验证
- 现有代码模式: paths.py 集中路径 / deps.py 用 Protocol+@lru_cache / graph_routes.py 路由模式

### Metis Review

**识别的 Gap（已处理）**:
- **命名碰撞风险**: ConstraintDimension vs ConstraintType → SPEC v4 明确声明二者共存、语义不同
- **YAML 8种异常场景**: 文件缺失/语法错误/缺层/缺维度/行和≠100/负值/浮点值/多余键 → 全部需要验证
- **LLM 输出解析失败**: 需要 per-dimension Pydantic 模型做 model_validate()
- **SPEC 完整性门禁**: 需要 8 项 grep 检查，全部通过才允许 Phase B 启动
- **权重=0 维度处理**: 低权重简略，权重=0 可省略或标记
- **WeightMatrixError 异常类**: 需要 row/detail 诊断字段

---

## Work Objectives

### Core Objective

建立 6 维约束体系的标准接口定义（SPEC v4），并基于此标准实现 Step 1（权重查找）和 Step 2（6维 LLM 生成）的生产代码。

### Concrete Deliverables

- `docs/SYSTEM_DESIGN_SPEC_v4.md`
- `data/weight_matrix.yaml`
- `backend/app/models/dimension.py`
- `backend/app/services/dimension_generator.py`
- `backend/app/api/constraints_routes.py`
- `backend/app/config/paths.py`（扩展）
- `backend/app/api/deps.py`（扩展）
- `backend/app/main.py`（注册新路由）
- `backend/tests/test_weight_matrix.py`
- `backend/tests/test_dimension_service.py`
- `backend/tests/test_constraints_api.py`

### Definition of Done

- [x] SPEC v4 包含完整 6维约束体系接口定义（8项 grep 检查全通过）
- [x] `data/weight_matrix.yaml` 存在且通过全部验证（6层×6维，每行和=100）
- [x] `dimension.py` 定义了 ConstraintDimension / CreationLayer 枚举 + WeightMatrix + 6个 DimensionOutput 子模型
- [x] `dimension_generator.py` 能从种子+层级生成6维结构化 JSON
- [x] `POST /api/constraints/generate` 端点可调用并返回结构化响应
- [x] 全部 pytest 通过（17/17 pass，新文件覆盖率 92-95%）

### Must Have

- SPEC v4 标准 **必须先于代码完成**，有明确的完整性验证步骤
- 每维度的 Pydantic 输出模型（6个 typed model，不是 dict[str, Any]）
- WeightMatrixLoader 验证 YAML 的 8 种异常场景
- ConstraintDimension 枚举值逐字: RED / LAW / ACT / NAR / WST / SOC（不允许添加或修改）
- CreationLayer 枚举值逐字: world / region / scene / campaign / npc / asset（不允许添加或修改）
- API 端点遵循 graph_routes.py 的路由模式
- 所有新路径常量加入 paths.py

### Must NOT Have (Guardrails)

- ❌ 不修改 `app/models/constraint.py` 现有类（ConstraintType / ConstraintNode / ConstraintTree）
- ❌ 不复制 prompt_builder.py 的脆弱 YAML 加载模式（无错误处理）
- ❌ 不在单元测试中调用真实 LLM
- ❌ 不添加 RED/LAW/ACT/NAR/WST/SOC 以外的维度
- ❌ 不添加 world/region/scene/campaign/npc/asset 以外的层级
- ❌ 不实现 Step 3-8（拆解器/跨图边/标签提取/prompt映射等）
- ❌ 不修改 NPC Graph（尚不存在）
- ❌ 不引入前端变更
- ❌ 不引入裸 any 类型
- ❌ 不使用可变默认值（用 Field(default_factory=...)）

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — 全部由 agent 执行验证。

### Test Decision

- **Infrastructure exists**: YES（pytest + pytest-cov + ruff + mypy）
- **Automated tests**: TDD for pure Python（模型验证 / 权重查找 / prompt组装）
- **Framework**: pytest
- **LLM 调用**: 不测试（用户明确要求），mock provider.chat_json() 边界

### QA Policy

每个 task 包含 agent 执行的 QA 场景。证据保存到 `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`。

- **模型/权重/Service**: pytest 单元测试
- **API**: FastAPI TestClient (httpx)
- **SPEC**: grep 验证完整性

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 0 (先执行 — 实验验证路径能跑通):
└── Task 0: 3×3 验证实验 (9次LLM调用, 验证Step1+Step2) [quick]

━━━━ GATE: 实验通过 (成功≥7/9, 密度差异≥2.0x) ━━━━
     不通过 → 分析失败原因，不可继续
     通过 ↓

Wave 1 (基于实验结果写标准):
└── Task 1: 编写 SYSTEM_DESIGN_SPEC_v4.md §18 [writing]

━━━━ GATE: SPEC v4 完整性验证 (8项 grep 检查) ━━━━
     不通过 → 回到 Task 1 修补
     通过 → 进入 Wave 2

Wave 2 (SPEC 通过后并行 — 生产代码):
├── Task 2: data/weight_matrix.yaml + models/dimension.py [quick]
├── Task 3: services/dimension_generator.py (权重查找 + prompt组装 + LLM生成) [deep]
└── Task 4: config/paths.py 扩展 + api/constraints_routes.py + deps.py + main.py [quick]

Wave FINAL (全部完成后 — 4并行验证):
├── Task F1: Plan compliance audit [oracle]
├── Task F2: Code quality review [unspecified-high]
├── Task F3: Real manual QA [unspecified-high]
└── Task F4: Scope fidelity check [deep]
→ 呈现结果 → 获得用户明确确认后完成

Critical Path: Task 0 → Task 1 → SPEC Gate → Task 3 → Task 4 → F1-F4 → 用户确认
Parallel Speedup: Wave 2 三任务并行
Max Concurrent: 4 (Wave FINAL)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 0 | — | 1 (实验验证路径可行性) |
| 1 | 0 (实验结果) | 2, 3, 4 (SPEC gate) |
| 2 | 1 (SPEC) | 3, 4 (import models) |
| 3 | 1 (SPEC), 2 (models) | 4 (service used by API) |
| 4 | 1 (SPEC), 2 (paths), 3 (service) | F1-F4 |
| F1-F4 | ALL | — |

### Agent Dispatch Summary

- **Wave 0**: 1 task — T0 → `quick`
- **Wave 1**: 1 task — T1 → `writing`
- **Wave 2**: 3 tasks — T2 → `quick`, T3 → `deep`, T4 → `quick`
- **FINAL**: 4 tasks — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 0. 3×3 验证实验 — 先跑通再写标准

  **What to do**:
  - 创建 `backend/experiments/step12_validation.py`
  - 复用实验代码中已验证的逻辑: `from experiments.layered_weight_experiment import WEIGHT_MATRIX, build_system_prompt, ...`
  - **3 个种子 × 3 个层级 = 9 次 LLM 调用**:
    - 种子1「古代水晶祭坛」→ world / asset / scene 层
    - 种子2「星辉教派」→ region / npc / world 层
    - 种子3「魔法消耗理智值」→ world / asset / npc 层
  - 验证5项:
    1. **权重表完整性**: 6层×6维, 每行和=100, 全部整数, 无负值
    2. **prompt 组装正确性**: 含全部6维名称 + 条形图字符(█░) + 高权重★标记
    3. **LLM 返回6维JSON**: 全部6维键存在 (RED/LAW/ACT/NAR/WST/SOC)
    4. **密度差异验证**: 高权重(≥25%)平均内容量 vs 低权重(≤5%)平均内容量, 比值 ≥2.0x
    5. **层级侧重验证**: 同一种子在不同层级的高权重维度不同
  - 输出结果保存到 `backend/experiments/results/step12_validation_{timestamp}.json`
  - 终端打印对比表：每维度(权重/内容量/条形图) + 高低比值汇总

  **Why this task exists**:
    用户要求"先跑实验验证路径能跑通，再基于实验结果写标准"。这是对 SPEC v4 的**实证基础**——不是凭空设计接口，而是从实际跑通的代码中提取标准。

  **Must NOT do**:
  - 不创建任何生产代码（models/dimension.py 等）——这是实验，不是生产化
  - 不修改现有实验文件 layered_weight_experiment.py
  - 不写 SPEC 文档

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单文件实验脚本，逻辑全部来自已验证的实验代码复用
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 0 (alone, before everything)
  - **Blocks**: Task 1 (SPEC v4 — 基于实验结果写标准)
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `backend/experiments/layered_weight_experiment.py:1-560` — 完整的实验框架，step12_validation.py 复用其中的 WEIGHT_MATRIX(L109-116), DIMENSION_INFO(L72-103), LAYER_NAMES(L118-125), build_system_prompt(L172-259), build_user_prompt(L262-272)
  - `backend/experiments/layered_weight_experiment.py:528-560` — main() 入口模式：asyncio.run + provider 初始化 + 结果保存

  **API/Type References**:
  - `backend/app/ai/provider.py:13-22` — LLMProvider.chat_json() 接口
  - `backend/app/ai/config.py:57-101` — load_provider_config() 从 .env 读取

  **WHY Each Reference Matters**:
  - 实验代码: step12_validation 是实验代码的精简验证版，直接 import 复用已验证逻辑，不重新设计
  - provider 接口: 确认 chat_json() 的调用方式与实验一致

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 3×3 实验成功执行
    Tool: Bash (python)
    Preconditions: backend/.env 配置了有效的 LLM API key
    Steps:
      1. cd backend && .venv\Scripts\python -m experiments.step12_validation
    Expected Result:
      - 终端输出 "[验证] Provider: ..." 开头
      - 9 次调用, 成功≥7 (允许2次网络错误)
      - 打印权重表预览 (6层×6维, 每行和=100)
      - 每次调用打印6维内容量分布 + 条形图
      - 打印密度差异汇总表
      - 保存 JSON 结果文件
    Failure Indicators: ImportError / 9次全部失败 / 无输出文件
    Evidence: .sisyphus/evidence/task-0-experiment-output.txt (终端输出重定向)

  Scenario: 权重表验证通过
    Tool: Bash (python)
    Steps:
      1. 从实验输出中查找 "✅ 6层×6维, 每行和=100, 全部通过"
    Expected Result: 该字符串存在
    Evidence: .sisyphus/evidence/task-0-weight-check.txt

  Scenario: 密度差异 ≥ 2.0x
    Tool: Bash (python)
    Steps:
      1. 从保存的 JSON 结果文件中读取每次调用的 density.ratio
      2. 计算平均值
    Expected Result: 平均 ratio ≥ 2.0 (高权重维度内容量至少是低权重的2倍)
    Evidence: .sisyphus/evidence/task-0-density-ratio.txt
  ```

  **Commit**: YES
  - Message: `experiment(step12): add 3x3 validation experiment for weight lookup and 6-dim generation`
  - Files: `backend/experiments/step12_validation.py`, `backend/experiments/results/step12_validation_*.json`

---

- [x] 1. 编写 SYSTEM_DESIGN_SPEC_v4.md — §18 6维约束体系接口注册区

  **What to do**:
  - 复制 `docs/SYSTEM_DESIGN_SPEC_v3.md` 为 `docs/SYSTEM_DESIGN_SPEC_v4.md`
  - 更新版本头: v4.0 / 2026-08-03 / 新增 §18 6维约束体系接口注册区
  - 更新 Changelog 表新增 v4.0 行
  - 在目录中新增 §18 条目
  - 新增 §18 完整章节，包含以下子节:
    - **§18.1 概述**: 说明 6维约束体系是"种子→6维→五图"流程的上游概念，与五图模型的 ConstraintTree 是不同层级。明确 ConstraintDimension（语义类别 RED/LAW/ACT/NAR/WST/SOC）与 ConstraintType（强制力 hard/soft）共存且语义不同。
    - **§18.2 枚举定义**: `ConstraintDimension` 和 `CreationLayer` 的完整枚举表，逐字列出所有合法值
    - **§18.3 权重矩阵配置**: WeightMatrix YAML 格式定义、验证规则（8种异常场景）、文件路径 `data/weight_matrix.yaml`
    - **§18.4 6维输出数据模型**: 6个 DimensionOutput 子模型（RedOutput/LawOutput/ActOutput/NarOutput/WstOutput/SocOutput）的完整字段表
    - **§18.5 生产代码文件清单**: 文件路径 / 操作 / 类名表格
    - **§18.6 完整接口签名**: Python 代码块逐字写出所有类和方法签名
    - **§18.7 API 端点契约**: `POST /api/constraints/generate` 的请求/响应 schema
    - **§18.8 数据流图**: `WeightMatrix(YAML) → WeightMatrixLoader → PromptBuilder → LLMProvider.chat_json() → DimensionValidator → ConstraintResponse`
    - **§18.9 命名碰撞消解声明**: ConstraintDimension ≠ ConstraintType，两者共存
  - 各子节的 Python 签名必须与实验代码 `backend/experiments/layered_weight_experiment.py` 一致（DIMENSION_INFO L72-103, WEIGHT_MATRIX L109-116, build_system_prompt L172-259, build_user_prompt L262-272, 6维 JSON schema L225-256）

  **Must NOT do**:
  - 不修改或删除 v3 的任何现有章节内容（只新增）
  - 不在 SPEC 中写实现代码逻辑（只写接口签名和数据结构）
  - 不添加 RED/LAW/ACT/NAR/WST/SOC 或 world/region/scene/campaign/npc/asset 以外的枚举值

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: 大型技术文档编写任务，需要严谨的结构和术语一致性
  - **Skills**: [`handle-large-files`]
    - `handle-large-files`: SPEC v3 有 2668 行，需要大文件处理技巧（offset/limit 读取，Grep 定位章节）

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 1 (alone)
  - **Blocks**: Tasks 2, 3, 4 (SPEC gate — 这些任务依赖 SPEC 中定义的接口签名)
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `docs/SYSTEM_DESIGN_SPEC_v3.md` — 完整的 v3 文档（2668行），作为 v4 的基础。特别关注 §17 的格式和写作风格（Phase 1 的接口签名写法）
  - `docs/SYSTEM_DESIGN_SPEC_v3.md:2359-2582` — §17 Phase 1 的完整格式，v4 §18 应遵循同样的代码块风格、表格格式、冲突消解记录格式
  - `backend/experiments/layered_weight_experiment.py:72-103` — DIMENSION_INFO 定义，6维的名称/描述/data_essence，SPEC §18.2 必须与此一致
  - `backend/experiments/layered_weight_experiment.py:109-116` — WEIGHT_MATRIX 完整 6×6 权重表，SPEC §18.3 和 YAML 文件的数据源
  - `backend/experiments/layered_weight_experiment.py:118-125` — LAYER_NAMES 中英文映射
  - `backend/experiments/layered_weight_experiment.py:172-259` — build_system_prompt() 完整实现，SPEC §18.6 中 build_system_prompt 的签名必须与此一致
  - `backend/experiments/layered_weight_experiment.py:225-256` — 6维 JSON 输出格式模板，SPEC §18.4 的 DimensionOutput 模型字段必须覆盖这些子字段
  - `backend/experiments/layered_weight_experiment.py:262-272` — build_user_prompt() 实现
  - `backend/experiments/layered_weight_experiment.py:279-324` — run_single() 实现，是 dimension_generator.generate() 的原型
  - `backend/experiments/results/layered_weight_20260803_123001.md` — 实验报告，包含真实 LLM 输出的完整 JSON 样例，用于验证 DimensionOutput 模型字段覆盖度

  **API/Type References**:
  - `backend/app/models/constraint.py:1-34` — 现有 ConstraintType(HARD/SOFT) / ConstraintNode / ConstraintTree，SPEC §18.9 必须明确声明新枚举不替换这些
  - `backend/app/ai/provider.py:13-22` — LLMProvider ABC，chat_json() 签名，SPEC §18.6 的 generate() 方法签名依赖此接口
  - `backend/app/ai/config.py:13-31` — ProviderConfig dataclass，SPEC §18.7 的商用预留说明参考此结构
  - `backend/app/config/paths.py:1-36` — 现有路径常量模式，SPEC §18.5 中 WEIGHT_MATRIX_PATH 的定义遵循同样模式

  **WHY Each Reference Matters**:
  - v3 SPEC §17 格式: 确保 v4 写出的接口签名风格一致，便于执行者对照
  - 实验代码各函数: SPEC 中定义的接口签名必须与已验证的实验代码一致，否则生产代码会偏离已验证的行为
  - 实验报告 JSON: 真实 LLM 输出样例用于验证 Pydantic 模型的字段覆盖度——如果模型字段遗漏了实验输出中的子字段，运行时会丢弃数据
  - constraint.py 现有类: 命名碰撞消解声明必须基于对现有代码的准确理解

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: SPEC v4 完整性 — 8项 grep 检查全部通过
    Tool: Bash (grep)
    Preconditions: docs/SYSTEM_DESIGN_SPEC_v4.md 已创建
    Steps:
      1. grep -c "ConstraintDimension" docs/SYSTEM_DESIGN_SPEC_v4.md → count ≥ 1
      2. grep -c "CreationLayer" docs/SYSTEM_DESIGN_SPEC_v4.md → count ≥ 1
      3. grep -c "WeightMatrix" docs/SYSTEM_DESIGN_SPEC_v4.md → count ≥ 1
      4. grep -c "DimensionOutput" docs/SYSTEM_DESIGN_SPEC_v4.md → count ≥ 1
      5. grep -c "constraints/generate" docs/SYSTEM_DESIGN_SPEC_v4.md → count ≥ 1
      6. grep -c "constraints_routes" docs/SYSTEM_DESIGN_SPEC_v4.md → count ≥ 1
      7. grep -c "dimension\.py" docs/SYSTEM_DESIGN_SPEC_v4.md → count ≥ 1
      8. grep -c "weight_matrix\.yaml" docs/SYSTEM_DESIGN_SPEC_v4.md → count ≥ 1
    Expected Result: 全部 8 项 count ≥ 1。如有任何一项为 0，回到 Task 1 补充。
    Failure Indicators: 任何 grep 返回 0
    Evidence: .sisyphus/evidence/task-1-spec-grep-check.txt

  Scenario: SPEC v4 版本头正确
    Tool: Bash (grep)
    Steps:
      1. grep "v4.0" docs/SYSTEM_DESIGN_SPEC_v4.md → 存在
      2. grep "2026-08-03" docs/SYSTEM_DESIGN_SPEC_v4.md → 存在
      3. grep "§18" docs/SYSTEM_DESIGN_SPEC_v4.md → 存在
    Expected Result: 全部存在
    Evidence: .sisyphus/evidence/task-1-spec-version.txt

  Scenario: SPEC v4 不破坏 v3 内容
    Tool: Bash (grep)
    Steps:
      1. grep "StoryGraph" docs/SYSTEM_DESIGN_SPEC_v4.md → 仍然存在
      2. grep "EventGraph" docs/SYSTEM_DESIGN_SPEC_v4.md → 仍然存在
      3. grep "CultureTree" docs/SYSTEM_DESIGN_SPEC_v4.md → 仍然存在
      4. grep "ConstraintTree" docs/SYSTEM_DESIGN_SPEC_v4.md → 仍然存在
      5. grep "AssetClassification" docs/SYSTEM_DESIGN_SPEC_v4.md → 仍然存在
    Expected Result: v3 的所有关键概念仍然存在
    Evidence: .sisyphus/evidence/task-1-spec-v3-preserved.txt
  ```

  **Commit**: YES
  - Message: `docs(spec): upgrade SYSTEM_DESIGN_SPEC v3→v4 with 6-dimension constraint system §18`
  - Files: `docs/SYSTEM_DESIGN_SPEC_v4.md`
  - Pre-commit: 8项 grep 检查

- [x] 2. 创建 weight_matrix.yaml + models/dimension.py

  **What to do**:
  - 创建 `data/weight_matrix.yaml`:
    ```yaml
    # 6层×6维权重矩阵 — 每行和=100
    # 值来自实验验证: backend/experiments/layered_weight_experiment.py L109-116
    world:
      RED: 20
      LAW: 30
      ACT: 5
      NAR: 35
      WST: 5
      SOC: 5
    region:
      RED: 10
      LAW: 10
      ACT: 10
      NAR: 20
      WST: 5
      SOC: 45
    scene:
      RED: 10
      LAW: 25
      ACT: 5
      NAR: 10
      WST: 40
      SOC: 10
    campaign:
      RED: 10
      LAW: 5
      ACT: 10
      NAR: 40
      WST: 5
      SOC: 30
    npc:
      RED: 5
      LAW: 10
      ACT: 25
      NAR: 20
      WST: 10
      SOC: 30
    asset:
      RED: 10
      LAW: 30
      ACT: 30
      NAR: 10
      WST: 10
      SOC: 10
    ```
  - 创建 `backend/app/models/dimension.py`，包含:
    - `ConstraintDimension(str, Enum)`: RED / LAW / ACT / NAR / WST / SOC（逐字列出，不允许添加）
    - `CreationLayer(str, Enum)`: world / region / scene / campaign / npc / asset（逐字列出，不允许添加）
    - `DIMENSION_INFO: dict[ConstraintDimension, DimensionInfo]`: 每维的 name/desc/data_essence（从实验代码 L72-103 迁移）
    - `LAYER_NAMES: dict[CreationLayer, str]`: 中英文映射（从实验代码 L118-125 迁移）
    - `DimensionInfo(BaseModel)`: name: str / desc: str / data_essence: str
    - `WeightMatrixEntry(BaseModel)`: dict[ConstraintDimension, int] 的 typed wrapper，验证 sum=100 且所有值≥0
    - `WeightMatrix(BaseModel)`: dict[CreationLayer, WeightMatrixEntry]
    - 6个 DimensionOutput 子模型:
      - `RedOutput`: forbidden: list[str] = Field(default_factory=list) / note: str = ""
      - `LawOutput`: rules: list[str] = Field(default_factory=list) / mechanism: str = ""
      - `ActOutput`: actions: list[dict[str, Any]] = Field(default_factory=list)  # 每个action有 trigger/check/success/failure
      - `NarOutput`: style: str = "" / keywords: list[str] = Field(default_factory=list) / tone: str = ""
      - `WstOutput`: effects: list[dict[str, Any]] = Field(default_factory=list)  # 每个effect有 name/type/magnitude
      - `SocOutput`: relations: list[dict[str, Any]] = Field(default_factory=list)  # 每个relation有 target/type/value
    - `DimensionResultSet(BaseModel)`: RED: RedOutput / LAW: LawOutput / ACT: ActOutput / NAR: NarOutput / WST: WstOutput / SOC: SocOutput
    - `WeightMatrixError(Exception)`: 自定义异常，含 row: str | None 和 detail: str 字段

  **Must NOT do**:
  - 不修改 `app/models/constraint.py`
  - 不添加枚举以外的维度或层级
  - 不用裸 dict 类型（用 dict[str, Any] 或 typed model）
  - 不用可变默认值

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 两个文件的创建，逻辑清晰（从实验代码迁移），边界明确
  - **Skills**: []
    - 不需要特殊 skill

  **Parallelization**:
  - **Can Run In Parallel**: YES（与 Task 3 并行，但 Task 3 依赖此任务的模型 import，实际需先完成或同步）
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 3 (import dimension models), Task 4 (import for API schema)
  - **Blocked By**: Task 1 (SPEC v4 must define interfaces first)

  **References**:

  **Pattern References**:
  - `backend/app/models/constraint.py:1-34` — 文件结构模板：imports → enum → BaseModel 类。dimension.py 遵循同样的结构
  - `backend/app/models/asset.py:1-120` — 复杂模型的参考：枚举 + Field(default_factory) + field_validator 模式
  - `backend/experiments/layered_weight_experiment.py:72-103` — DIMENSION_INFO 逐字数据源
  - `backend/experiments/layered_weight_experiment.py:109-125` — WEIGHT_MATRIX 和 LAYER_NAMES 逐字数据源
  - `backend/experiments/results/layered_weight_20260803_123001.md:25-88` — 真实 LLM 输出 JSON，验证 6个 DimensionOutput 模型的字段覆盖度

  **API/Type References**:
  - `docs/SYSTEM_DESIGN_SPEC_v4.md` §18 — 刚完成的 SPEC v4 标准，所有模型签名以此为准

  **WHY Each Reference Matters**:
  - constraint.py: 文件结构和代码风格的模板——新文件必须看起来像是同一个代码库的一部分
  - 实验代码: 数据是逐字迁移的，不是重新设计——任何值偏差都意味着生产代码行为偏离已验证的实验
  - 实验报告 JSON: 检查每个 DimensionOutput 模型的字段是否覆盖了真实 LLM 输出的所有子字段——遗漏 = 数据丢失

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: YAML 权重表加载成功
    Tool: Bash (python)
    Preconditions: data/weight_matrix.yaml 和 dimension.py 已创建
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         import yaml
         from pathlib import Path
         data = yaml.safe_load(Path('../data/weight_matrix.yaml').read_text(encoding='utf-8'))
         assert len(data) == 6, f'Expected 6 layers, got {len(data)}'
         for layer, weights in data.items():
             assert sum(weights.values()) == 100, f'{layer} sums to {sum(weights.values())}, not 100'
             assert len(weights) == 6, f'{layer} has {len(weights)} dims, expected 6'
         print('PASS: weight_matrix.yaml valid')
         "
    Expected Result: "PASS: weight_matrix.yaml valid"
    Failure Indicators: AssertionError with specific message
    Evidence: .sisyphus/evidence/task-2-yaml-valid.txt

  Scenario: dimension.py 模型导入成功
    Tool: Bash (python)
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         from app.models.dimension import (
             ConstraintDimension, CreationLayer, DimensionInfo,
             DIMENSION_INFO, LAYER_NAMES, WeightMatrix, WeightMatrixEntry,
             RedOutput, LawOutput, ActOutput, NarOutput, WstOutput, SocOutput,
             DimensionResultSet, WeightMatrixError
         )
         assert len(ConstraintDimension) == 6
         assert len(CreationLayer) == 6
         # 验证枚举值逐字
         assert ConstraintDimension.RED.value == 'RED'
         assert CreationLayer.WORLD.value == 'world'
         print('PASS: dimension.py imports and enums correct')
         "
    Expected Result: "PASS: dimension.py imports and enums correct"
    Evidence: .sisyphus/evidence/task-2-models-import.txt

  Scenario: DimensionResultSet 从实验 JSON 验证成功
    Tool: Bash (python)
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         from app.models.dimension import DimensionResultSet
         import json
         # 使用实验报告中的真实 LLM 输出
         fixture = {
             'RED': {'forbidden': ['test'], 'note': 'ok'},
             'LAW': {'rules': ['rule1'], 'mechanism': 'mech'},
             'ACT': {'actions': [{'trigger': 't', 'check': 'c', 'success': 's', 'failure': 'f'}]},
             'NAR': {'style': 'mystic', 'keywords': ['k'], 'tone': 'somber'},
             'WST': {'effects': [{'name': 'e', 'type': 'buff', 'magnitude': '+1'}]},
             'SOC': {'relations': [{'target': 'x', 'type': 'ally', 'value': 'friendly'}]},
         }
         result = DimensionResultSet.model_validate(fixture)
         assert result.RED.forbidden == ['test']
         assert result.LAW.mechanism == 'mech'
         print('PASS: DimensionResultSet validates experiment JSON')
         "
    Expected Result: "PASS: DimensionResultSet validates experiment JSON"
    Evidence: .sisyphus/evidence/task-2-model-validate.txt

  Scenario: WeightMatrixEntry 验证行和=100
    Tool: Bash (python)
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         from app.models.dimension import WeightMatrixEntry, ConstraintDimension, WeightMatrixError
         # 合法
         valid = {ConstraintDimension.RED: 20, ConstraintDimension.LAW: 30, ConstraintDimension.ACT: 5,
                  ConstraintDimension.NAR: 35, ConstraintDimension.WST: 5, ConstraintDimension.SOC: 5}
         entry = WeightMatrixEntry.model_validate(valid)
         assert entry.sum() == 100
         # 非法: 和=99
         try:
             invalid = dict(valid)
             invalid[ConstraintDimension.RED] = 19
             WeightMatrixEntry.model_validate(invalid)
             assert False, 'Should have raised'
         except (ValueError, WeightMatrixError):
             pass
         print('PASS: WeightMatrixEntry validates sum=100')
         "
    Expected Result: "PASS: WeightMatrixEntry validates sum=100"
    Evidence: .sisyphus/evidence/task-2-weight-validation.txt
  ```

  **Commit**: YES (groups with Task 3, 4)
  - Message: `feat(dimension): add weight_matrix.yaml and dimension.py models`
  - Files: `data/weight_matrix.yaml`, `backend/app/models/dimension.py`

---

- [x] 3. 创建 services/dimension_generator.py — 权重查找 + prompt组装 + LLM生成

  **What to do**:
  - 创建 `backend/app/services/dimension_generator.py`，包含:

  - **WeightMatrixLoader 类**:
    - `__init__(self, path: Path | None = None)`: 默认从 `paths.WEIGHT_MATRIX_PATH` 加载
    - `load(self) -> WeightMatrix`: 读取 YAML，执行8种验证（文件缺失/YAML错误/缺层/缺维度/行和≠100/负值/浮点值/多余键），返回 WeightMatrix 对象
    - 验证失败时 raise `WeightMatrixError(row=..., detail=...)` 带具体诊断信息
    - `get_weights(self, layer: CreationLayer) -> WeightMatrixEntry`: 查找指定层级的权重

  - **DimensionPromptBuilder 类**（从实验 build_system_prompt / build_user_prompt 迁移）:
    - `__init__(self)`: 预加载 DIMENSION_INFO 和 LAYER_NAMES
    - `build_system_prompt(self, layer: CreationLayer, weights: WeightMatrixEntry, intent: str) -> str`: 组装 system prompt，含权重条形图和维度描述。逻辑逐字迁移自实验代码 L172-259
    - `build_user_prompt(self, seed_input: str, seed_description: str) -> str`: 组装 user prompt。逻辑逐字迁移自实验代码 L262-272
    - 高权重维度(≥25%)标注 ★主要约束，低权重(≤5%)标注"简单提一句即可"

  - **DimensionGenerator 类**（核心生成器，从实验 run_single 迁移）:
    - `__init__(self, provider: LLMProvider, matrix_loader: WeightMatrixLoader | None = None)`: 注入 LLM provider 和权重加载器
    - `async def generate(self, seed_input: str, seed_description: str, layer: CreationLayer, intent: str = "") -> DimensionResultSet`:
      1. `weights = self._loader.get_weights(layer)`
      2. `system_prompt = self._prompt_builder.build_system_prompt(layer, weights, intent)`
      3. `user_prompt = self._prompt_builder.build_user_prompt(seed_input, seed_description)`
      4. `messages = [{"role":"system",...}, {"role":"user",...}]`
      5. `raw = await self._provider.chat_json(messages)`
      6. `result = DimensionResultSet.model_validate(raw)` — Pydantic 验证
      7. return result
    - 验证失败时 raise `DimensionParseError(original=raw, errors=...)`

  - **DimensionParseError(Exception)**: 自定义异常，含 original: dict 和 errors: list 字段

  - 创建测试 `backend/tests/test_dimension_service.py`:
    - `test_weight_matrix_loads_successfully`: 加载真实 weight_matrix.yaml，断言6层6维，每行和=100
    - `test_weight_matrix_missing_file_raises`: mock open() 抛 FileNotFoundError → WeightMatrixError
    - `test_weight_matrix_invalid_yaml_raises`: 喂 "{not valid" → WeightMatrixError
    - `test_weight_matrix_row_sum_not_100_raises`: fixture YAML 某行和=99 → WeightMatrixError
    - `test_weight_matrix_negative_value_raises`: fixture 含 -1 → WeightMatrixError
    - `test_weight_matrix_missing_layer_raises`: fixture 只有5层 → WeightMatrixError
    - `test_weight_matrix_missing_dimension_raises`: 某行只有5维 → WeightMatrixError
    - `test_build_system_prompt_includes_all_dimensions`: mock weights, 断言 prompt 含全部6个维度名称
    - `test_build_system_prompt_high_weight_marked`: 断言权重≥25%的维度有 ★ 标记
    - `test_build_system_prompt_low_weight_simplified`: 断言权重≤5%的维度有"简单提一句"提示
    - `test_generate_parses_llm_response`: mock provider.chat_json 返回 fixture JSON → DimensionResultSet
    - `test_generate_invalid_llm_output_raises`: mock 返回 {} → DimensionParseError

  **Must NOT do**:
  - 不在测试中调用真实 LLM
  - 不复制 prompt_builder.py 的脆弱 YAML 加载模式（无错误处理）
  - 不修改实验文件 layered_weight_experiment.py
  - 不在 prompt 中添加实验代码以外的内容

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 核心业务逻辑（权重查找 + prompt组装 + LLM调用），需要仔细从实验代码迁移并添加完整验证逻辑和测试
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: 纯 Python 部分用 TDD（先写测试再实现），确保覆盖 8 种 YAML 异常场景

  **Parallelization**:
  - **Can Run In Parallel**: YES（与 Task 2 同 wave，但实际依赖 Task 2 的 models）
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 4 (API 端点调用 DimensionGenerator)
  - **Blocked By**: Task 1 (SPEC), Task 2 (models/dimension.py)

  **References**:

  **Pattern References**:
  - `backend/app/services/graph_extractor.py` — service+LLM 模式模板：__init__ 创建 provider，async 方法，dict 返回
  - `backend/app/services/prompt_builder.py:1-80` — YAML 加载的现有实现（作为反面教材——新代码必须有验证）
  - `backend/experiments/layered_weight_experiment.py:172-259` — build_system_prompt() 逐字迁移源码
  - `backend/experiments/layered_weight_experiment.py:262-272` — build_user_prompt() 逐字迁移源码
  - `backend/experiments/layered_weight_experiment.py:279-324` — run_single() 迁移为 DimensionGenerator.generate() 的原型

  **API/Type References**:
  - `backend/app/ai/provider.py:13-22` — LLMProvider ABC，chat_json() 签名
  - `backend/app/models/dimension.py`（Task 2 创建）— WeightMatrix, WeightMatrixEntry, DimensionResultSet

  **Test References**:
  - `backend/tests/unit/test_graph_extractor.py` — LLM service 测试模式：mock provider，fixture JSON
  - `backend/tests/conftest.py` — pytest fixtures 模式

  **WHY Each Reference Matters**:
  - graph_extractor.py: 唯一的"service + LLM provider"现有实现，新代码必须遵循同样的注入模式和异步方法风格
  - prompt_builder.py 反面教材: 它的 YAML 加载没有任何验证——WeightMatrixLoader 必须解决它忽略的全部8种异常场景
  - 实验代码: prompt 组装逻辑是逐字迁移，不是重新设计。实验验证了这套 prompt 能让 LLM 产生 3.9x 密度差异

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: WeightMatrixLoader 8种异常全部覆盖
    Tool: Bash (pytest)
    Preconditions: test_dimension_service.py 已创建
    Steps:
      1. cd backend && .venv\Scripts\python -m pytest tests/test_dimension_service.py -v -k "weight_matrix"
    Expected Result: 全部 weight_matrix 相关测试 PASS（至少7个测试通过：正常加载+6个异常场景）
    Failure Indicators: 任何 FAIL
    Evidence: .sisyphus/evidence/task-3-weight-matrix-tests.txt

  Scenario: Prompt 组装保留实验行为
    Tool: Bash (pytest)
    Steps:
      1. cd backend && .venv\Scripts\python -m pytest tests/test_dimension_service.py -v -k "build_system_prompt"
    Expected Result: 全部 prompt 相关测试 PASS
    Evidence: .sisyphus/evidence/task-3-prompt-tests.txt

  Scenario: DimensionGenerator mock 集成
    Tool: Bash (pytest)
    Steps:
      1. cd backend && .venv\Scripts\python -m pytest tests/test_dimension_service.py -v -k "generate"
    Expected Result: mock provider 测试 PASS，返回 DimensionResultSet 对象
    Evidence: .sisyphus/evidence/task-3-generate-tests.txt

  Scenario: 全部 dimension service 测试通过
    Tool: Bash (pytest)
    Steps:
      1. cd backend && .venv\Scripts\python -m pytest tests/test_dimension_service.py -v
    Expected Result: ALL PASS, 0 failures
    Evidence: .sisyphus/evidence/task-3-all-tests.txt
  ```

  **Commit**: YES (groups with Task 2, 4)
  - Message: `feat(dimension): productionize 6-dimension weight lookup and LLM generation`
  - Files: `backend/app/services/dimension_generator.py`, `backend/tests/test_dimension_service.py`

---

- [x] 4. 扩展 paths.py + 创建 constraints_routes.py + 注册路由

  **What to do**:
  - **扩展 `backend/app/config/paths.py`**: 在现有路径常量后新增:
    ```python
    # Dimension constraint system
    WEIGHT_MATRIX_PATH: Path = DATA_DIR / "weight_matrix.yaml"
    ```
  - **创建 `backend/app/api/constraints_routes.py`**:
    - 遵循 `graph_routes.py` 的路由模式（APIRouter + prefix + tags）
    - `constraints_router = APIRouter(prefix="/api/constraints", tags=["constraints"])`
    - 请求模型:
      ```python
      class ConstraintGenerateRequest(BaseModel):
          seed_input: str           # 种子概念名称，min_length=1
          seed_description: str = "" # 种子描述（可选，空字符串=让LLM自行扩展）
          layer: CreationLayer       # 创作层级
          intent: str = ""           # 创作意图（可选）
      ```
    - 响应模型:
      ```python
      class ConstraintGenerateResponse(BaseModel):
          layer: CreationLayer
          weights: dict[str, int]        # 回显权重表供验证
          dimensions: DimensionResultSet  # 6维结构化结果
          elapsed_seconds: float          # 耗时
      ```
    - 端点实现:
      ```python
      @constraints_router.post("/generate", response_model=ConstraintGenerateResponse)
      async def generate_constraints(
          request: ConstraintGenerateRequest,
          generator: DimensionGenerator = Depends(get_dimension_generator),
      ) -> ConstraintGenerateResponse:
          # 调用 generator.generate()
          # 异常处理: WeightMatrixError → 503, DimensionParseError → 502
      ```
  - **扩展 `backend/app/api/deps.py`**: 新增 DI getter:
    ```python
    @lru_cache(maxsize=1)
    def get_dimension_generator() -> DimensionGenerator:
        provider = get_llm_provider()
        return DimensionGenerator(provider=provider)
    ```
  - **扩展 `backend/app/main.py`**: 注册新路由:
    ```python
    from app.api.constraints_routes import constraints_router
    app.include_router(constraints_router)
    ```
  - **创建测试 `backend/tests/test_constraints_api.py`**:
    - `test_post_generate_returns_200`: mock generator，POST /api/constraints/generate with valid body → 200 + JSON 含 dimensions 字段
    - `test_post_generate_invalid_layer_returns_422`: layer="invalid" → 422 validation error
    - `test_post_generate_missing_seed_returns_422`: 缺少 seed_input → 422
    - `test_post_generate_empty_seed_returns_422`: seed_input="" → 422 (min_length=1)

  **Must NOT do**:
  - 不在 API 端点中直接调用 LLM（通过 Depends 注入 DimensionGenerator）
  - 不在 API 层做业务逻辑（只做请求转发和异常映射）
  - 不修改现有路由文件（routes.py / graph_routes.py 等）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 标准的 FastAPI 路由创建，遵循现有 graph_routes.py 模式，逻辑简单
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO（依赖 Task 2 的模型和 Task 3 的 service）
  - **Parallel Group**: Wave 2 (但实际最后执行)
  - **Blocks**: F1-F4
  - **Blocked By**: Task 1 (SPEC), Task 2 (models), Task 3 (service)

  **References**:

  **Pattern References**:
  - `backend/app/api/graph_routes.py:1-40` — 路由文件模板：APIRouter 定义、prefix、tags、Request/Response models、endpoint 函数签名
  - `backend/app/api/deps.py:55-90` — DI getter 模式：@lru_cache + get_llm_provider() 组合
  - `backend/app/main.py:49-53` — 路由注册模式：app.include_router()

  **API/Type References**:
  - `backend/app/models/dimension.py`（Task 2）— CreationLayer, DimensionResultSet
  - `backend/app/services/dimension_generator.py`（Task 3）— DimensionGenerator, WeightMatrixError, DimensionParseError

  **Test References**:
  - `backend/tests/unit/test_graph_api.py` 或 `backend/tests/integration/test_graph_api.py` — API 测试模式：FastAPI TestClient

  **WHY Each Reference Matters**:
  - graph_routes.py: 现有的路由文件模板——新路由必须看起来像是同一个代码库的一部分（同样的 APIRouter 创建方式、同样的 prefix 风格）
  - deps.py: DI 注册模式——必须用 @lru_cache + get_llm_provider() 的组合，确保 provider 是单例
  - main.py: 路由注册——遗漏 include_router 会导致端点 404

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: API 端点正常响应
    Tool: Bash (pytest)
    Preconditions: 后端服务可启动（或使用 FastAPI TestClient）
    Steps:
      1. cd backend && .venv\Scripts\python -m pytest tests/test_constraints_api.py -v
    Expected Result: 全部 API 测试 PASS（至少4个：正常200 + 3个422验证错误）
    Evidence: .sisyphus/evidence/task-4-api-tests.txt

  Scenario: 端点在 OpenAPI 文档中可见
    Tool: Bash (curl/python)
    Preconditions: 后端服务运行中
    Steps:
      1. 启动后端: cd backend && .venv\Scripts\python -m uvicorn app.main:app --port 8000 &
      2. curl -s http://localhost:8000/openapi.json | python -c "import sys,json; d=json.load(sys.stdin); paths=list(d['paths'].keys()); assert '/api/constraints/generate' in paths, f'Not found in {paths}'; print('PASS')"
    Expected Result: "PASS"
    Evidence: .sisyphus/evidence/task-4-openapi-check.txt

  Scenario: 现有端点不受影响
    Tool: Bash (curl)
    Steps:
      1. curl -s http://localhost:8000/api/health → 仍然返回健康状态
    Expected Result: 200 + {"status":"healthy"} 或类似
    Evidence: .sisyphus/evidence/task-4-existing-endpoints.txt
  ```

  **Commit**: YES (groups with Task 2, 3)
  - Message: `feat(constraints): add /api/constraints/generate endpoint and route registration`
  - Files: `backend/app/config/paths.py`, `backend/app/api/constraints_routes.py`, `backend/app/api/deps.py`, `backend/app/main.py`, `backend/tests/test_constraints_api.py`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `cd backend && .venv\Scripts\python -m pytest --tb=short -q` + ruff + mypy. Review all changed files for: `as any`/`@ts-ignore`, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names.
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start backend server. Execute: `POST /api/constraints/generate` with `{"seed":"古代水晶祭坛","layer":"asset"}`. Assert 200 + JSON with all 6 dimensions. Test invalid layer → 422. Test invalid seed → 400. Save curl output as evidence.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built, nothing beyond spec. Check "Must NOT do" compliance. Verify `app/models/constraint.py` was NOT modified. Verify no frontend files touched.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Commit 0** (after Task 0): `experiment(step12): add 3x3 validation experiment for weight lookup and 6-dim generation`
  - Files: `backend/experiments/step12_validation.py`, `backend/experiments/results/step12_validation_*.json`
  - Pre-commit: 实验成功执行（9次调用成功≥7）
- **Commit 1** (after Task 1): `docs(spec): upgrade SYSTEM_DESIGN_SPEC v3→v4 with 6-dimension constraint system`
  - Files: `docs/SYSTEM_DESIGN_SPEC_v4.md`
  - Pre-commit: grep verification (8 checks)
- **Commit 2** (after Wave 2): `feat(dimension): productionize 6-dimension weight lookup and LLM generation`
  - Files: all Wave 2 files
  - Pre-commit: `pytest backend/tests/test_weight_matrix.py backend/tests/test_dimension_service.py backend/tests/test_constraints_api.py -v`

---

## Success Criteria

### Verification Commands
```bash
# SPEC v4 完整性
grep -c "ConstraintDimension\|CreationLayer\|WeightMatrix\|DimensionOutput\|constraints/generate\|constraints_routes\|dimension\.py\|weight_matrix\.yaml" docs/SYSTEM_DESIGN_SPEC_v4.md
# Expected: ≥ 8

# 权重表验证
cd backend && .venv\Scripts\python -c "from app.services.dimension_generator import WeightMatrixLoader; wml = WeightMatrixLoader(); m = wml.load(); print(m)"
# Expected: 6 layers, each with 6 dims summing to 100

# 全部测试
cd backend && .venv\Scripts\python -m pytest tests/test_weight_matrix.py tests/test_dimension_service.py tests/test_constraints_api.py -v
# Expected: all pass

# 类型检查
cd backend && .venv\Scripts\python -m mypy app/models/dimension.py app/services/dimension_generator.py
# Expected: 0 errors
```

### Final Checklist
- [x] All "Must Have" present
- [x] All "Must NOT Have" absent
- [x] All tests pass
- [x] SPEC v4 完整性门禁通过
- [x] `app/models/constraint.py` 未被修改
