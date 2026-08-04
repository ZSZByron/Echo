# Phase 1: 五图模型 — 数据模型层 + SPEC v3 接口注册

## TL;DR

> **Quick Summary**: 实现五图模型的 Pydantic v2 数据模型层（4个新文件 + 1个扩展），并创建 SYSTEM_DESIGN_SPEC_v3.md 接口注册文档。
>
> **Deliverables**:
> - `docs/SYSTEM_DESIGN_SPEC_v3.md` — 在 v2 基础上新增 §17 分阶段接口注册区
> - `backend/app/models/story_graph.py` — StoryNodeType, StoryCondition, StoryChoice, StoryEdge, StoryNode, StoryGraph
> - `backend/app/models/event_graph.py` — EventNodeType, EventTriggerType, EventRewardType, EventTrigger, EventAction, EventReward, EventNode, EventGraph
> - `backend/app/models/culture.py` — CultureNode, CultureTree
> - `backend/app/models/constraint.py` — ConstraintType, ConstraintNode, ConstraintTree
> - `backend/app/models/asset.py` — 扩展: AssetClassification + 3个新字段
> - 每个模型的单元测试文件
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 2 waves
> **Critical Path**: T1(v3 spec) → T2(story_graph) → T6(asset扩展) → T7(集成验证)

---

## Context

### Original Request
基于 SYSTEM_DESIGN_SPEC_v2.md 和编辑器设计方案，分阶段实现五图模型 AI 剧情场景编辑器。Phase 1 聚焦数据模型层。

### Interview Summary
**Key Discussions**:
- 用户要求分阶段生成计划，而非一次性全部
- 每个阶段的接口/参数名要注册到 SPEC v3 文件
- 前端依赖情况: reactflow ^11.11.4 已安装（但版本与SPEC ≥12.0 有差异），Zustand/Radix/D3 未安装

**Research Findings**:
- 现有 asset.py 无 classification/related_story_node/related_event_node 字段
- models/__init__.py 为空文件（无导出惯例）
- 现有模型均未使用 model_config（纯 BaseModel）
- Asset 用 `default_factory=lambda: datetime.now(timezone.utc)` 处理时间
- pyproject.toml 有 `--cov-fail-under=85` 覆盖率门禁

### Metis Review
**Identified Gaps** (addressed):
- `edges: list[dict]` 不通过 mypy strict → 新增 `StoryEdge(BaseModel)` 类型化模型
- `metadata: dict = {}` 可变默认值 antipattern → 统一 `Field(default_factory=dict)`
- `datetime.now(timezone.utc)` 默认值 → 用 `Field(default_factory=...)`
- SPEC v2 vs 编辑器设计类型冲突 → SPEC v2 §5 为权威源
- Asset 扩展不加重排序 → 3个新字段追加到类末尾
- Asset 不加 model_config → 避免向后兼容风险
- 覆盖率门禁 → 每个模型必须含单元测试

---

## Work Objectives

### Core Objective
创建五图模型的核心 Pydantic v2 数据模型，零业务逻辑，零外部依赖，为后续 Phase 2-5 奠定类型基础。

### Concrete Deliverables
- 4 个新模型文件（纯 Pydantic，mypy strict 通过）
- 1 个扩展模型（向后兼容追加字段）
- 1 个 V3 规范文档（接口注册）
- 5 个单元测试文件（覆盖率 ≥80%）

### Definition of Done
- [ ] `cd H:\UGC\backend && .venv\Scripts\python -m mypy app/models/story_graph.py app/models/event_graph.py app/models/culture.py app/models/constraint.py app/models/asset.py` → 零错误
- [ ] `cd H:\UGC\backend && .venv\Scripts\python -m ruff check app/models/` → 零错误
- [ ] `cd H:\UGC\backend && .venv\Scripts\python -m pytest tests/ --cov=app --cov-fail-under=85` → 全部通过
- [ ] `docs/SYSTEM_DESIGN_SPEC_v3.md` 存在且包含 §17 接口注册区

### Must Have
- 所有枚举为 `class X(str, Enum)` 并带 docstring
- 所有可变默认值使用 `Field(default_factory=...)`
- 所有 datetime 字段使用 `Field(default_factory=lambda: datetime.now(timezone.utc))`
- 所有新字段有默认值（向后兼容）
- StoryEdge 类型化模型替代 `list[dict]`

### Must NOT Have (Guardrails)
- **禁止** 添加业务逻辑（YAML I/O、拓扑排序、验证逻辑属于 Phase 2）
- **禁止** 修改 Asset 现有字段的类型/默认值/顺序
- **禁止** 给 Asset 类添加 `model_config`（向后兼容风险）
- **禁止** 使用裸 `any` 类型
- **禁止** 使用裸 `dict` / `list` 类型注解（mypy strict）
- **禁止** 创建服务层、API 路由、前端组件
- **禁止** 在 models/__init__.py 中注册导出（保持现有空文件惯例）
- **禁止** 使用 `datetime.now(timezone.utc)` 作为直接默认值

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: YES (pytest + pytest-cov, pyproject.toml 有 cov-fail-under=85)
- **Automated tests**: YES (tests-after, 每个模型含单元测试)
- **Framework**: pytest

### QA Policy
每个任务含 Agent-Executed QA 场景（Python REPL + pytest）。
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`。

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: 创建 SPEC v3 接口注册文档 [deep]
├── Task 2: story_graph.py 模型 + 测试 [deep]
├── Task 3: event_graph.py 模型 + 测试 [deep]
├── Task 4: culture.py 模型 + 测试 [quick]
└── Task 5: constraint.py 模型 + 测试 [quick]

Wave 2 (After Wave 1):
├── Task 6: asset.py 扩展 (classification + 3 fields) + 测试 [deep]
└── Task 7: 集成验证 — mypy/ruff/pytest 全量门禁 [quick]

Wave FINAL (After ALL tasks):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)

Critical Path: T1 → T2 → T6 → T7 → F1-F4
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 5 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| T1 | None | T7 |
| T2 | None | T6, T7 |
| T3 | None | T7 |
| T4 | None | T7 |
| T5 | None | T7 |
| T6 | T2 (StoryNode for related_story_node type ref) | T7 |
| T7 | T1-T6 | F1-F4 |

### Agent Dispatch Summary

- **Wave 1**: T1 → `deep`, T2 → `deep`, T3 → `deep`, T4 → `quick`, T5 → `quick`
- **Wave 2**: T6 → `deep`, T7 → `quick`
- **FINAL**: F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [ ] 1. 创建 SYSTEM_DESIGN_SPEC_v3.md 接口注册文档

  **What to do**:
  - 复制 `docs/SYSTEM_DESIGN_SPEC_v2.md` 为 `docs/SYSTEM_DESIGN_SPEC_v3.md`（覆盖已存在的 v3 副本）
  - 修改头部：版本 v2.0 → v3.0，更新更新日志行
  - 在文档末尾（§16 之后、附录之前）追加 **§17 分阶段实施接口注册区**
  - §17 内容格式见下方的 **V3 §17 完整内容** — 直接写入文件

  **V3 §17 完整内容**（执行器直接复制以下内容到文件中）:

  ```markdown
  ## 17. 分阶段实施接口注册区 (V3 新增)

  > **本章为 V3 新增**：锁定每个实施阶段的文件清单、类名、字段、方法签名。
  > **权威源声明**: Python 模型定义以 §5 为准（NOT 编辑器设计 §7.1）。
  > TypeScript 类型定义以 §9 为准。

  ### 17.1 Phase 1: 数据模型层

  #### 文件清单

  | # | 文件路径 | 操作 | 类/枚举 |
  |---|---------|------|---------|
  | 1 | `backend/app/models/story_graph.py` | 新增 | StoryNodeType, StoryCondition, StoryChoice, StoryEdge, StoryNode, StoryGraph |
  | 2 | `backend/app/models/event_graph.py` | 新增 | EventNodeType, EventTriggerType, EventRewardType, EventTrigger, EventAction, EventReward, EventNode, EventGraph |
  | 3 | `backend/app/models/culture.py` | 新增 | CultureNode, CultureTree |
  | 4 | `backend/app/models/constraint.py` | 新增 | ConstraintType, ConstraintNode, ConstraintTree |
  | 5 | `backend/app/models/asset.py` | 扩展 | AssetClassification (枚举) + 3个新字段 |

  #### story_graph.py — 完整接口签名

  ```python
  # backend/app/models/story_graph.py

  class StoryNodeType(str, Enum):
      """剧情节点类型。"""
      START = "start"
      END = "end"
      CHOICE = "choice"
      EVENT = "event"
      CONDITION = "condition"

  class StoryCondition(BaseModel):
      """剧情条件。"""
      type: str                         # "item_required" | "stat_check" | "custom"
      requirement: str | dict[str, Any] # 禁止裸 any，以 §5 为准

  class StoryChoice(BaseModel):
      """剧情选择支。"""
      text: str
      target_node: str
      conditions: list[StoryCondition] = Field(default_factory=list)

  class StoryEdge(BaseModel):
      """剧情图边（类型化，替代裸 dict）。"""
      from_node: str
      to_node: str
      condition: StoryCondition | None = None

  class StoryNode(BaseModel):
      """剧情节点。"""
      id: str
      type: StoryNodeType
      name: str
      description: str
      required_assets: list[str] = Field(default_factory=list)
      conditions: list[StoryCondition] = Field(default_factory=list)
      choices: list[StoryChoice] = Field(default_factory=list)
      scene_link: str | None = None
      metadata: dict[str, Any] = Field(default_factory=dict)

  class StoryGraph(BaseModel):
      """跨场景剧情图。"""
      id: str
      name: str
      description: str
      nodes: dict[str, StoryNode] = Field(default_factory=dict)
      edges: list[StoryEdge] = Field(default_factory=list)
      metadata: dict[str, Any] = Field(default_factory=dict)
      version: str = "1.0"
      created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
      updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
  ```

  **冲突消解记录**:
  - `requirement: any` (编辑器设计 §3.1) → **修正为** `str | dict[str, Any]` (§5)
  - `edges: list[dict]` (§5) → **修正为** `list[StoryEdge]` (新增 StoryEdge 模型)
  - `datetime.now(timezone.utc)` 默认值 (§5) → **修正为** `Field(default_factory=lambda: datetime.now(timezone.utc))`
  - `metadata: dict = {}` (§5) → **修正为** `Field(default_factory=dict)`

  #### event_graph.py — 完整接口签名

  ```python
  # backend/app/models/event_graph.py

  class EventNodeType(str, Enum):
      """事件节点类型。"""
      COMBAT = "combat"
      QUEST = "quest"
      EXPLORATION = "exploration"
      SOCIAL = "social"

  class EventTriggerType(str, Enum):
      """事件触发类型。"""
      TIME = "time"
      LOCATION = "location"
      STATE = "state"
      CUSTOM = "custom"

  class EventRewardType(str, Enum):
      """事件奖励类型。"""
      ITEM = "item"
      EXPERIENCE = "experience"
      STORY_UNLOCK = "story_unlock"

  class EventTrigger(BaseModel):
      """事件触发条件。"""
      type: EventTriggerType
      condition: str | dict[str, Any]    # 禁止裸 any
      priority: int = 1

  class EventAction(BaseModel):
      """事件动作。"""
      type: str
      parameters: dict[str, str | int | bool] = Field(default_factory=dict)

  class EventReward(BaseModel):
      """事件奖励。"""
      type: EventRewardType
      value: str | int
      probability: float = 1.0

  class EventNode(BaseModel):
      """事件节点。"""
      id: str
      type: EventNodeType
      name: str
      trigger_conditions: list[EventTrigger] = Field(default_factory=list)
      actions: list[EventAction] = Field(default_factory=list)
      rewards: list[EventReward] = Field(default_factory=list)
      assets: list[str] = Field(default_factory=list)
      metadata: dict[str, Any] = Field(default_factory=dict)

  class EventGraph(BaseModel):
      """动态事件图。"""
      id: str
      name: str
      description: str
      nodes: dict[str, EventNode] = Field(default_factory=dict)
      global_triggers: list[EventTrigger] = Field(default_factory=list)
      metadata: dict[str, Any] = Field(default_factory=dict)
  ```

  #### culture.py — 完整接口签名

  ```python
  # backend/app/models/culture.py

  class CultureNode(BaseModel):
      """文化树节点（递归结构）。"""
      id: str
      name: str
      description: str
      values: list[str] = Field(default_factory=list)
      aesthetic_principles: list[str] = Field(default_factory=list)
      child_nodes: list[CultureNode] = Field(default_factory=list)

  class CultureTree(BaseModel):
      """文化树。"""
      id: str
      name: str
      root: CultureNode
      version: str = "1.0"
  ```

  **注**: CultureNode 是递归模型。Pydantic v2 自动处理递归引用，无需 `model_rebuild()`（除非使用 `frozen=True`，本计划不使用）。

  #### constraint.py — 完整接口签名

  ```python
  # backend/app/models/constraint.py

  class ConstraintType(str, Enum):
      """约束类型。"""
      HARD = "hard"    # 硬约束：违反则资产生成失败
      SOFT = "soft"    # 软约束：影响优先级评分

  class ConstraintNode(BaseModel):
      """约束节点。"""
      id: str
      type: ConstraintType
      rule: str                           # 规则描述文本
      rule_config: dict[str, Any] | None = None
      priority: int = 0                   # 0-100
      applicable_types: list[str] = Field(default_factory=list)

  class ConstraintTree(BaseModel):
      """约束树。"""
      scene_id: str | None = None         # None = 全局约束
      id: str
      name: str
      nodes: list[ConstraintNode] = Field(default_factory=list)
  ```

  #### asset.py 扩展 — 新增接口签名

  ```python
  # backend/app/models/asset.py — 在 Asset 类末尾追加

  class AssetClassification(str, Enum):
      """资产分类 — 由来源图决定。"""
      STORY = "story"             # 来自 StoryGraph
      EVENT = "event"             # 来自 EventGraph
      ENVIRONMENT = "environment"  # 无明确来源

  # 在 Asset 类中追加（现有字段之后，computed_field 之前）:
  #   classification: AssetClassification = AssetClassification.ENVIRONMENT
  #   related_story_node: str | None = None
  #   related_event_node: str | None = None
  ```

  **向后兼容规则**:
  - 现有资产默认 `classification = ENVIRONMENT`
  - 有 `puzzle_role` 的资产可在 Phase 5 迁移时升级为 `STORY`
  - 3个新字段均有默认值，不破坏现有数据

  #### Phase 1 验收标准

  | 标准 | 命令 | 预期 |
  |------|------|------|
  | mypy strict | `mypy app/models/*.py` | 0 errors |
  | ruff | `ruff check app/models/` | 0 errors |
  | pytest 覆盖率 | `pytest --cov=app --cov-fail-under=85` | all pass |
  | 向后兼容 | 现有 Asset 测试全部通过 | 0 failures |

  ### 17.2 Phase 2-5 接口注册 (待后续计划填充)

  > Phase 2: 后端服务层 (story_service, event_service, ai_assistant, asset_classifier, candidate_system)
  > Phase 3: API 路由层 (story_routes, event_routes, ai_routes, culture_routes, constraint_routes)
  > Phase 4: 前端编辑器 (React Flow 编辑器组件 + Zustand stores)
  > Phase 5: 生成管道整合 (GenerationPlanner + PromptBuilder 升级)

  ```

  **Must NOT do**:
  - 不修改 §1-§16 的任何现有内容（仅修改头部版本号 + 追加 §17）
  - 不在 §17 中添加 Phase 2-5 的具体签名（留待后续阶段计划填充）
  - 不创建任何 Python 代码文件

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 需要精确理解 V2 全文才能正确编写 V3 增量，文档准确性至关重要
  - **Skills**: [`writing`]
    - `writing`: 文档生成任务

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2-5)
  - **Blocks**: Task 7 (集成验证需要检查 v3 文件存在)
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `docs/SYSTEM_DESIGN_SPEC_v2.md` 完整文件 — V3 的基础，需要全文理解
  - `docs/SYSTEM_DESIGN_SPEC_v2.md:804-933` — §5 数据模型字典，Python 模型定义的权威源
  - `docs/SYSTEM_DESIGN_SPEC_v2.md:1599-1818` — §10 YAML 格式定义

  **WHY Each Reference Matters**:
  - v2 全文：V3 = V2 + §17，不能丢失任何现有内容
  - §5 模型定义：§17 中的 Python 签名必须与 §5 一致，但需标注修正项
  - §10 YAML 格式：确保 §17 中的模型字段与 YAML schema 对齐

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: V3 文件创建且包含 §17
    Tool: Bash (grep)
    Preconditions: docs/SYSTEM_DESIGN_SPEC_v3.md 不存在或为 v2 副本
    Steps:
      1. 执行: Select-String -Path "docs\SYSTEM_DESIGN_SPEC_v3.md" -Pattern "## 17\. 分阶段实施接口注册区"
      2. 断言: 匹配到 1 行
      3. 执行: Select-String -Path "docs\SYSTEM_DESIGN_SPEC_v3.md" -Pattern "v3.0"
      4. 断言: 头部版本号已更新为 v3.0
    Expected Result: §17 章节存在，版本号为 v3.0
    Failure Indicators: §17 不存在，或版本仍为 v2.0
    Evidence: .sisyphus/evidence/task-1-v3-spec-created.txt

  Scenario: V3 保留了 V2 的全部现有章节
    Tool: Bash (grep)
    Preconditions: V3 文件已创建
    Steps:
      1. 验证 §1-§16 标题全部存在:
         Select-String -Path "docs\SYSTEM_DESIGN_SPEC_v3.md" -Pattern "^## \d+"
      2. 断言: 至少 16 个匹配（§1 到 §16）
      3. 验证附录存在:
         Select-String -Path "docs\SYSTEM_DESIGN_SPEC_v3.md" -Pattern "附录A|附录B|附录C"
      4. 断言: 3 个附录全部匹配
    Expected Result: V2 全部内容保留
    Failure Indicators: 章节丢失
    Evidence: .sisyphus/evidence/task-1-v3-chapters-preserved.txt

  Scenario: §17 包含 Phase 1 全部接口签名
    Tool: Bash (grep)
    Preconditions: V3 文件已创建
    Steps:
      1. 搜索关键类名:
         Select-String -Path "docs\SYSTEM_DESIGN_SPEC_v3.md" -Pattern "class StoryNodeType|class EventNodeType|class CultureNode|class ConstraintType|class AssetClassification|class StoryEdge"
      2. 断言: 至少 6 个匹配
    Expected Result: 所有 Phase 1 类签名在 §17 中有记录
    Failure Indicators: 缺少类定义
    Evidence: .sisyphus/evidence/task-1-v3-interfaces-registered.txt
  ```

  **Commit**: YES (单独提交)
  - Message: `docs: create SPEC v3 with §17 phase interface registry`
  - Files: `docs/SYSTEM_DESIGN_SPEC_v3.md`

---

- [x] 2. 实现 story_graph.py 模型 + 单元测试

  **What to do**:
  - 创建 `backend/app/models/story_graph.py`
  - 实现 6 个类: StoryNodeType, StoryCondition, StoryChoice, StoryEdge, StoryNode, StoryGraph
  - 完整接口签名见 V3 §17.1 中的 story_graph.py 部分（严格按签名实现）
  - 创建 `backend/tests/models/test_story_graph.py`
  - 测试覆盖: 枚举验证、实例化、序列化 round-trip、默认值、条件/选择嵌套、StoryEdge 类型化

  **Must NOT do**:
  - 不添加 YAML I/O 逻辑（Phase 2）
  - 不添加拓扑排序或图遍历（Phase 2）
  - 不添加 model_config（现有代码库无此惯例）
  - 不在 __init__.py 中注册导出

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 模型准确性是后续所有阶段的基础，需要严格遵循 SPEC 签名
  - **Skills**: []
    - 无需特殊技能

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4, 5)
  - **Blocks**: Task 6 (asset 扩展引用 StoryNode), Task 7
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `backend/app/models/knowledge_graph.py` — 图模型结构参考（enum → node → edge → graph container 模式）
  - `backend/app/models/asset.py:12-21` — 枚举定义风格: `class X(str, Enum)` + docstring
  - `backend/app/models/asset.py:80-81` — datetime 默认值: `Field(default_factory=lambda: datetime.now(timezone.utc))`
  - `backend/app/models/asset.py:86-88` — list 默认值: `Field(default_factory=list)`

  **API/Type References**:
  - `docs/SYSTEM_DESIGN_SPEC_v2.md:804-843` — §5 StoryGraph 模型权威定义
  - V3 §17.1 story_graph.py 签名（本计划 Task 1 产出）

  **Test References**:
  - `backend/app/models/puzzle_graph.py` — 类似图结构的测试模式

  **WHY Each Reference Matters**:
  - knowledge_graph.py: 项目中已有的 graph model 模式，新模型必须匹配此风格
  - asset.py 枚举风格: 确保枚举定义一致性
  - §5 权威定义: 所有字段名、类型、默认值必须与 §5 一致

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: story_graph 模型实例化和序列化
    Tool: Bash (python)
    Preconditions: backend/app/models/story_graph.py 已创建
    Steps:
      1. 执行:
         cd H:\UGC\backend
         .venv\Scripts\python -c "from app.models.story_graph import StoryGraph, StoryNode, StoryNodeType, StoryEdge, StoryCondition, StoryChoice; g = StoryGraph(id='test', name='test', description='test'); n = StoryNode(id='n1', type=StoryNodeType.START, name='Start', description='desc'); g.nodes[n.id] = n; json_str = g.model_dump_json(); g2 = StoryGraph.model_validate_json(json_str); assert g2.nodes['n1'].type == StoryNodeType.START; print('PASS')"
      2. 断言: 输出 "PASS"
    Expected Result: StoryGraph 可实例化、可序列化为 JSON、可从 JSON 反序列化
    Failure Indicators: ImportError, ValidationError, AssertionError
    Evidence: .sisyphus/evidence/task-2-story-graph-instantiation.txt

  Scenario: StoryNodeType 枚举验证
    Tool: Bash (python)
    Preconditions: story_graph.py 已创建
    Steps:
      1. 执行:
         cd H:\UGC\backend
         .venv\Scripts\python -c "from app.models.story_graph import StoryNodeType; assert StoryNodeType('start') == StoryNodeType.START; assert StoryNodeType('end') == StoryNodeType.END"
      2. 执行:
         .venv\Scripts\python -c "from app.models.story_graph import StoryNodeType; StoryNodeType('invalid')" 2>&1
      3. 断言: 第二条命令抛出 ValueError
    Expected Result: 合法枚举值正常工作，非法值抛 ValueError
    Failure Indicators: 非法值不抛异常
    Evidence: .sisyphus/evidence/task-2-story-enum-validation.txt

  Scenario: mypy strict 通过
    Tool: Bash (mypy)
    Preconditions: story_graph.py 已创建
    Steps:
      1. 执行:
         cd H:\UGC\backend
         .venv\Scripts\python -m mypy app/models/story_graph.py --strict
      2. 断言: exit code 0, "Success" in output
    Expected Result: 零类型错误
    Failure Indicators: 任何 mypy error
    Evidence: .sisyphus/evidence/task-2-story-mypy.txt

  Scenario: pytest 单元测试通过
    Tool: Bash (pytest)
    Preconditions: test_story_graph.py 已创建
    Steps:
      1. 执行:
         cd H:\UGC\backend
         .venv\Scripts\python -m pytest tests/models/test_story_graph.py -v --cov=app.models.story_graph --cov-report=term-missing
      2. 断言: all passed, coverage ≥ 80%
    Expected Result: 全部测试通过，覆盖率达标
    Failure Indicators: 测试失败或覆盖率不足
    Evidence: .sisyphus/evidence/task-2-story-pytest.txt
  ```

  **Commit**: YES (groups with Tasks 3-5)
  - Message: `feat(models): add StoryGraph model with StoryNodeType/StoryEdge types`
  - Files: `backend/app/models/story_graph.py`, `backend/tests/models/test_story_graph.py`
  - Pre-commit: `python -m mypy app/models/story_graph.py --strict && python -m pytest tests/models/test_story_graph.py`

---

- [x] 3. 实现 event_graph.py 模型 + 单元测试

  **What to do**:
  - 创建 `backend/app/models/event_graph.py`
  - 实现 8 个类: EventNodeType, EventTriggerType, EventRewardType, EventTrigger, EventAction, EventReward, EventNode, EventGraph
  - 完整接口签名见 V3 §17.1 中的 event_graph.py 部分（严格按签名实现）
  - 创建 `backend/tests/models/test_event_graph.py`
  - 测试覆盖: 枚举验证、实例化、序列化 round-trip、触发条件嵌套、奖励概率默认值

  **Must NOT do**:
  - 不添加触发测试逻辑（Phase 2 的 test_trigger）
  - 不使用裸 `any` 类型
  - 不添加 model_config

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 模型准确性关键，8个类需要严格遵循 SPEC
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4, 5)
  - **Blocks**: Task 7
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `backend/app/models/knowledge_graph.py` — 图模型结构参考
  - `backend/app/models/asset.py:12-29` — 枚举定义风格

  **API/Type References**:
  - `docs/SYSTEM_DESIGN_SPEC_v2.md:846-895` — §5 EventGraph 模型权威定义
  - V3 §17.1 event_graph.py 签名

  **WHY Each Reference Matters**:
  - knowledge_graph.py: 项目图模型风格基准
  - §5 EventGraph: 3个枚举 + 5个模型的权威字段定义

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: event_graph 模型实例化和序列化
    Tool: Bash (python)
    Preconditions: event_graph.py 已创建
    Steps:
      1. 执行:
         cd H:\UGC\backend
         .venv\Scripts\python -c "from app.models.event_graph import EventGraph, EventNode, EventNodeType, EventTrigger, EventTriggerType; t = EventTrigger(type=EventTriggerType.TIME, condition='night'); n = EventNode(id='e1', type=EventNodeType.COMBAT, name='Wolf', trigger_conditions=[t]); g = EventGraph(id='eg1', name='Events', description='desc', nodes={n.id: n}); j = g.model_dump_json(); g2 = EventGraph.model_validate_json(j); assert g2.nodes['e1'].trigger_conditions[0].type == EventTriggerType.TIME; print('PASS')"
      2. 断言: 输出 "PASS"
    Expected Result: EventGraph 完整序列化 round-trip
    Evidence: .sisyphus/evidence/task-3-event-graph-instantiation.txt

  Scenario: EventReward 概率默认值
    Tool: Bash (python)
    Steps:
      1. 执行:
         cd H:\UGC\backend
         .venv\Scripts\python -c "from app.models.event_graph import EventReward, EventRewardType; r = EventReward(type=EventRewardType.EXPERIENCE, value=50); assert r.probability == 1.0; print('PASS')"
      2. 断言: probability 默认为 1.0
    Expected Result: 默认概率为 1.0
    Evidence: .sisyphus/evidence/task-3-event-reward-default.txt

  Scenario: mypy strict + pytest
    Tool: Bash
    Steps:
      1. 执行: cd H:\UGC\backend && .venv\Scripts\python -m mypy app/models/event_graph.py --strict
      2. 执行: .venv\Scripts\python -m pytest tests/models/test_event_graph.py -v --cov=app.models.event_graph
      3. 断言: mypy 0 errors, pytest all pass, coverage ≥ 80%
    Evidence: .sisyphus/evidence/task-3-event-mypy-pytest.txt
  ```

  **Commit**: YES (groups with Tasks 2, 4, 5)
  - Message: `feat(models): add EventGraph model with trigger/action/reward types`
  - Files: `backend/app/models/event_graph.py`, `backend/tests/models/test_event_graph.py`

---

- [x] 4. 实现 culture.py 模型 + 单元测试

  **What to do**:
  - 创建 `backend/app/models/culture.py`
  - 实现 2 个类: CultureNode, CultureTree
  - CultureNode 是递归模型（child_nodes: list[CultureNode]）— Pydantic v2 自动处理
  - 完整接口签名见 V3 §17.1 中的 culture.py 部分
  - 创建 `backend/tests/models/test_culture.py`
  - 测试覆盖: 递归结构实例化、深层嵌套序列化、空 child_nodes 默认值

  **Must NOT do**:
  - 不使用 frozen=True（递归模型复杂度高，非必要）
  - 不添加 model_config
  - 不添加候选评分逻辑（Phase 2）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 仅 2 个类，结构简单
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 5)
  - **Blocks**: Task 7
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `backend/app/models/asset.py:41-48` — SceneStyleProfile 嵌套模型示例

  **API/Type References**:
  - `docs/SYSTEM_DESIGN_SPEC_v2.md:897-912` — §5 CultureTree 模型权威定义
  - `docs/SYSTEM_DESIGN_SPEC_v2.md:1749-1784` — §10.5 Culture YAML 格式
  - V3 §17.1 culture.py 签名

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 递归 CultureNode 嵌套实例化
    Tool: Bash (python)
    Steps:
      1. 执行:
         cd H:\UGC\backend
         .venv\Scripts\python -c "from app.models.culture import CultureNode, CultureTree; child = CultureNode(id='c1', name='Child', description='d'); root = CultureNode(id='root', name='Root', description='d', child_nodes=[child]); tree = CultureTree(id='t1', name='Tree', root=root); j = tree.model_dump_json(); t2 = CultureTree.model_validate_json(j); assert t2.root.child_nodes[0].id == 'c1'; print('PASS')"
      2. 断言: 输出 "PASS"
    Expected Result: 递归结构正确序列化和反序列化
    Evidence: .sisyphus/evidence/task-4-culture-recursive.txt

  Scenario: 空默认值验证
    Tool: Bash (python)
    Steps:
      1. 执行:
         .venv\Scripts\python -c "from app.models.culture import CultureNode; n = CultureNode(id='n', name='n', description='d'); assert n.values == []; assert n.aesthetic_principles == []; assert n.child_nodes == []; print('PASS')"
    Expected Result: 所有 list 字段默认为空列表
    Evidence: .sisyphus/evidence/task-4-culture-defaults.txt

  Scenario: mypy + pytest
    Tool: Bash
    Steps:
      1. .venv\Scripts\python -m mypy app/models/culture.py --strict → 0 errors
      2. .venv\Scripts\python -m pytest tests/models/test_culture.py -v --cov=app.models.culture → all pass, cov ≥ 80%
    Evidence: .sisyphus/evidence/task-4-culture-mypy-pytest.txt
  ```

  **Commit**: YES (groups with Tasks 2, 3, 5)
  - Message: `feat(models): add CultureTree model with recursive CultureNode`
  - Files: `backend/app/models/culture.py`, `backend/tests/models/test_culture.py`

---

- [x] 5. 实现 constraint.py 模型 + 单元测试

  **What to do**:
  - 创建 `backend/app/models/constraint.py`
  - 实现 3 个类: ConstraintType, ConstraintNode, ConstraintTree
  - 完整接口签名见 V3 §17.1 中的 constraint.py 部分
  - 创建 `backend/tests/models/test_constraint.py`
  - 测试覆盖: 枚举验证(HARD/SOFT)、优先级默认值、applicable_types 默认空列表、scene_id=None 全局约束

  **Must NOT do**:
  - 不添加约束验证逻辑（Phase 2 的 candidate_system）
  - 不添加 WorldRule 迁移逻辑（Phase 5）
  - 不添加 model_config

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 仅 3 个类，结构最简单
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 4)
  - **Blocks**: Task 7
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `backend/app/models/asset.py:12-29` — 枚举风格

  **API/Type References**:
  - `docs/SYSTEM_DESIGN_SPEC_v2.md:914-933` — §5 ConstraintTree 模型权威定义
  - `docs/SYSTEM_DESIGN_SPEC_v2.md:1786-1818` — §10.6 Constraint YAML 格式
  - V3 §17.1 constraint.py 签名

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: constraint 模型实例化
    Tool: Bash (python)
    Steps:
      1. 执行:
         cd H:\UGC\backend
         .venv\Scripts\python -c "from app.models.constraint import ConstraintType, ConstraintNode, ConstraintTree; n = ConstraintNode(id='c1', type=ConstraintType.HARD, rule='no metal'); t = ConstraintTree(id='t1', name='Temple', nodes=[n], scene_id='temple_ruins'); j = t.model_dump_json(); t2 = ConstraintTree.model_validate_json(j); assert t2.nodes[0].type == ConstraintType.HARD; assert t2.scene_id == 'temple_ruins'; print('PASS')"
      2. 断言: 输出 "PASS"
    Expected Result: 完整序列化 round-trip
    Evidence: .sisyphus/evidence/task-5-constraint-instantiation.txt

  Scenario: 全局约束 scene_id=None
    Tool: Bash (python)
    Steps:
      1. 执行:
         .venv\Scripts\python -c "from app.models.constraint import ConstraintTree; t = ConstraintTree(id='global', name='Global'); assert t.scene_id is None; print('PASS')"
    Expected Result: 全局约束 scene_id 默认为 None
    Evidence: .sisyphus/evidence/task-5-constraint-global.txt

  Scenario: mypy + pytest
    Tool: Bash
    Steps:
      1. mypy → 0 errors
      2. pytest → all pass, cov ≥ 80%
    Evidence: .sisyphus/evidence/task-5-constraint-mypy-pytest.txt
  ```

  **Commit**: YES (groups with Tasks 2-4)
  - Message: `feat(models): add ConstraintTree model with hard/soft types`
  - Files: `backend/app/models/constraint.py`, `backend/tests/models/test_constraint.py`

---

- [x] 6. 扩展 asset.py — AssetClassification + 3个新字段

  **What to do**:
  - 编辑 `backend/app/models/asset.py`
  - 新增 `AssetClassification(str, Enum)` 枚举类（在 AssetType 之后、Asset 类之前）
  - 在 Asset 类末尾（`depth` 字段之后、`@field_validator` 之前）追加 3 个字段:
    - `classification: AssetClassification = AssetClassification.ENVIRONMENT`
    - `related_story_node: str | None = None`
    - `related_event_node: str | None = None`
  - 创建/扩展 `backend/tests/models/test_asset.py`
  - 测试覆盖: 向后兼容（现有字段不变）、新字段默认值、AssetClassification 枚举

  **Must NOT do**:
  - **禁止** 修改现有字段的类型、默认值、顺序
  - **禁止** 给 Asset 类添加 model_config
  - **禁止** 修改现有的 @field_validator / @computed_field
  - **禁止** 重命名现有字段
  - 新字段必须追加在 depth 字段之后

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 修改现有核心模型，向后兼容性至关重要
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (after Wave 1)
  - **Blocks**: Task 7
  - **Blocked By**: Task 2 (需要确认 StoryNode 存在以验证 related_story_node 语义)

  **References**:

  **Pattern References**:
  - `backend/app/models/asset.py:12-29` — AssetStatus/AssetType 枚举风格（AssetClassification 必须匹配）
  - `backend/app/models/asset.py:50-99` — Asset 类完整现有字段（不可修改）
  - `backend/app/models/asset.py:96-98` — `depth` 字段位置（新字段在此之后追加）

  **API/Type References**:
  - `docs/SYSTEM_DESIGN_SPEC_v2.md:744-778` — §5.5 Asset 模型扩展定义
  - `docs/SYSTEM_DESIGN_SPEC_v2.md:1899-1916` — §11.5 扩展方案和迁移规则
  - V3 §17.1 asset.py 扩展签名

  **WHY Each Reference Matters**:
  - asset.py 现有字段: 必须逐行确认不被修改
  - §5.5 扩展定义: 3个新字段的确切类型和默认值
  - §11.5 迁移规则: 现有资产默认 ENVIRONMENT 的规则

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 向后兼容 — 现有 Asset 实例化不受影响
    Tool: Bash (python)
    Preconditions: asset.py 已扩展
    Steps:
      1. 执行:
         cd H:\UGC\backend
         .venv\Scripts\python -c "from app.models.asset import Asset, AssetType; a = Asset(id='test_bg', type=AssetType.BACKGROUND, name='Test', parent_scene='scene1'); assert a.classification.value == 'environment'; assert a.related_story_node is None; assert a.related_event_node is None; print('PASS')"
      2. 断言: 输出 "PASS"
    Expected Result: 不传新字段时，默认值正确
    Failure Indicators: 现有代码因新字段报错
    Evidence: .sisyphus/evidence/task-6-asset-backward-compat.txt

  Scenario: AssetClassification 枚举
    Tool: Bash (python)
    Steps:
      1. 执行:
         .venv\Scripts\python -c "from app.models.asset import AssetClassification; assert AssetClassification('story') == AssetClassification.STORY; assert AssetClassification('event') == AssetClassification.EVENT; assert AssetClassification('environment') == AssetClassification.ENVIRONMENT; print('PASS')"
    Expected Result: 3个枚举值全部可用
    Evidence: .sisyphus/evidence/task-6-asset-classification-enum.txt

  Scenario: 现有 Asset 测试全部通过
    Tool: Bash (pytest)
    Steps:
      1. 执行:
         cd H:\UGC\backend
         .venv\Scripts\python -m pytest tests/ -v -k "asset" --tb=short
      2. 断言: 0 failures
    Expected Result: 现有 asset 相关测试无回归
    Failure Indicators: 任何现有测试失败
    Evidence: .sisyphus/evidence/task-6-asset-no-regression.txt

  Scenario: mypy strict 通过
    Tool: Bash (mypy)
    Steps:
      1. 执行: .venv\Scripts\python -m mypy app/models/asset.py --strict
      2. 断言: 0 errors
    Evidence: .sisyphus/evidence/task-6-asset-mypy.txt
  ```

  **Commit**: YES
  - Message: `feat(models): extend Asset with classification and story/event linkage`
  - Files: `backend/app/models/asset.py`, `backend/tests/models/test_asset.py`
  - Pre-commit: `python -m mypy app/models/asset.py --strict && python -m pytest tests/ -k asset`

---

- [x] 7. 集成验证 — 全量 mypy / ruff / pytest 门禁

  **What to do**:
  - 运行全量验证命令确认所有 Phase 1 交付物满足门禁
  - 验证 V3 §17 文件存在且内容完整
  - 验证 5 个模型文件之间的导入无循环依赖
  - 汇总 evidence 文件清单

  **Must NOT do**:
  - 不修复代码（发现问题应报告，不自行修复——除非是明显的 typo）
  - 不添加新功能

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 纯验证任务
  - **Skills**: [`verification-before-completion`]
    - 验证技能

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (after Task 6)
  - **Blocks**: F1-F4 (Final Verification)
  - **Blocked By**: Tasks 1-6 (all)

  **References**:
  - `backend/pyproject.toml` — ruff/mypy/pytest 配置

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 全量 mypy strict
    Tool: Bash (mypy)
    Steps:
      1. 执行:
         cd H:\UGC\backend
         .venv\Scripts\python -m mypy app/models/story_graph.py app/models/event_graph.py app/models/culture.py app/models/constraint.py app/models/asset.py --strict
      2. 断言: exit code 0
    Expected Result: 5 个文件全部 0 errors
    Evidence: .sisyphus/evidence/task-7-integration-mypy.txt

  Scenario: 全量 ruff check
    Tool: Bash (ruff)
    Steps:
      1. 执行: .venv\Scripts\python -m ruff check app/models/
      2. 断言: 0 errors
    Evidence: .sisyphus/evidence/task-7-integration-ruff.txt

  Scenario: 全量 pytest + 覆盖率门禁
    Tool: Bash (pytest)
    Steps:
      1. 执行: .venv\Scripts\python -m pytest tests/ --cov=app --cov-fail-under=85 --cov-report=term-missing
      2. 断言: all pass, coverage ≥ 85%
    Evidence: .sisyphus/evidence/task-7-integration-pytest.txt

  Scenario: 跨模型导入无循环依赖
    Tool: Bash (python)
    Steps:
      1. 执行:
         .venv\Scripts\python -c "from app.models.story_graph import StoryGraph; from app.models.event_graph import EventGraph; from app.models.culture import CultureTree; from app.models.constraint import ConstraintTree; from app.models.asset import Asset, AssetClassification; print('ALL IMPORTS OK')"
      2. 断言: 输出 "ALL IMPORTS OK"
    Evidence: .sisyphus/evidence/task-7-no-circular-deps.txt

  Scenario: V3 文件存在且 §17 完整
    Tool: Bash (grep)
    Steps:
      1. 验证: Test-Path "docs\SYSTEM_DESIGN_SPEC_v3.md"
      2. 验证: Select-String -Path "docs\SYSTEM_DESIGN_SPEC_v3.md" -Pattern "## 17\." 匹配到 1 行
    Evidence: .sisyphus/evidence/task-7-v3-exists.txt
  ```

  **Commit**: NO (验证任务不产生代码变更)

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `mypy --strict` + `ruff check` + `pytest --cov-fail-under=85`. Review all changed files for: `as any`/`@ts-ignore`, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names.
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration: import all 5 models together, verify no circular deps. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Wave 1**: `feat(models): add five-graph data models (story/event/culture/constraint)` — 4 new model files + tests
- **Wave 2**: `feat(models): extend Asset with classification fields` — asset.py + test
- **Final**: `docs: create SPEC v3 with phase interface registry` — SYSTEM_DESIGN_SPEC_v3.md

---

## Success Criteria

### Verification Commands
```bash
cd H:\UGC\backend
.venv\Scripts\python -m mypy app/models/story_graph.py app/models/event_graph.py app/models/culture.py app/models/constraint.py app/models/asset.py  # Expected: 0 errors
.venv\Scripts\python -m ruff check app/models/  # Expected: 0 errors
.venv\Scripts\python -m pytest tests/ --cov=app --cov-fail-under=85  # Expected: all pass
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass
- [ ] SPEC v3 §17 接口注册区完整
