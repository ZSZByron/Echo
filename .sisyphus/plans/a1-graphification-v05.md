# A1 图谱化 v0.5 实施计划

## TL;DR

> **Quick Summary**: 按治理文档 v0.5（docs/governance/2-A1-v0.5-内容图谱化统一模型与契约.md）实施 A1 知识图谱构建管线改造：NL answers → graphify 单次 LLM 调用（五字段 SIR）→ 确定性组装（双树+tier+语义边+cst复活）→ 图谱页呈现（tier分组/L4布局/降级角标/失效区）→ open_questions 闭环。
>
> **Deliverables**:
> - graphify.py（SIR 契约模型 + LLM 统一调用 + 校验 + 降级三机制）
> - _build_graph/finalize 改造（双树组装 + warnings 持久化 + 两阶段退役 + cst 复活）
> - 前端（isDepthNode + L4 布局 + tier 分组 + 降级角标 + 失效区 + open_questions 问出）
> - C1-C7 契约测试全绿 + 不变量五条 + id 稳定性快照 + 压测报告
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 6 waves
> **Critical Path**: T1 → T6 → T9 → T12 → F1-F4

---

## Context

### Original Request
用户描述知识图谱构建三阶段（种子→访谈→图谱化），图谱化四能力（总结/提炼/节点提取/条目结构化嵌套），要求结合现有 A1 世界观工坊图谱页逻辑改造。经三轮会话：决策考古（tag= 断链还原）→ 统一模型（三轴分离）→ 治理文档 v0.5 定型 → R1-R4 风险评审收编。

### Interview Summary
**Key Discussions**:
- 自然语言原则：用户只给纯自然语言，结构化+关系化是系统职责（LLM 定稿时一次调用）
- 双树异号：概念树 0/N/N-M（问卷投影）vs 深度树 D{锚点}-{k}（LLM提取，id 内容锚定 d:{anchor}:{title}）
- tier≠level：v0.4 七层以模块属性+派生边落地，不加深概念树
- 决策5=方案2（constraint_fields 并入 graphify，重建被斩断的生产方）
- 决策6=tier 方案；测试=Tests-after + C1-C7 契约集成测试强制

**Research Findings**:
- 现行两阶段编排（finalize抽词→确认→POST抽边）由 graphify 取代，阶段2端点降级保留
- a1_routes.py:762 失效边静默 continue（必须改为失效区）；warnings 未持久化 rec（必须修）
- EdgeType 已 5 值 + GraphEdge 已有 relation/confidence/confirmed（模型层就绪）
- 概念词恢复 :753-772 的 confirmed 合并模式 = cst 复活幂等的抄写范本
- **Metis 保护区块**：finalize 内 :688-696 门禁、:698-710 issuer/stale、:803-818 visual-bg 线程块——改造时逐字保留

### Metis Review
**Identified Gaps** (addressed):
- 4 个契约级开放问题 → 已按默认收口（见 Work Objectives "契约默认值"）
- 保护区块未列入 → 已写入任务 Must NOT do
- 6 条可执行验收缺失 → 已并入各任务 QA 场景
- stub provider 可能不存在 → P0 T5 含确认/补建
- 混合版本会话首次 re-finalize 死区洪泛 → 接受为预期行为（有测试）

---

## Work Objectives

### Core Objective
将 A1 定稿图谱从"问卷骨架机械投影"升级为"graphify 结构化+关系化 → 双树+tier 确定性组装"的完整管线，闭合 08-24 考古断链，七层理论落地。

### 契约默认值（Metis 开放问题收口，披露于摘要）

| # | 问题 | 默认决议 |
|---|------|---------|
| D1 | 旧 confirmed_edges（term: 键）命运 | **声明自然失效**：v0.5 后 term: 节点不再产出 → 旧边端点失效 → 首次 re-finalize 全部流入失效区（可见可废弃），不写迁移适配器；混合版本死区洪泛=预期行为（有测试） |
| D2 | d:{anchor}:{title} 冲突/卫生化 | title 卫生化（去 `:`、空白归一、截断32字）；id 解析 split(':', 2)（anchor=module.subfield 无冒号）；同锚点同 title → 去重保留首条+warning |
| D3 | graphify 超时策略 | 服务端 asyncio.wait_for，超时=GRAPHIFY_TIMEOUT 环境变量（默认 60s）；异常与超时同走降级链 |
| D4 | 空 SIR 语义 | entries:[] 等列表字段空=**合法响应非错误**（无对应产出，无角标）；类型错误=整调用降级；Pydantic 列表字段带默认值实现部分接受 |

### Concrete Deliverables
- `backend/app/domains/creation/a1/graphify.py`（新增）
- `backend/app/api/a1_routes.py`（_build_graph/finalize 改造）
- `backend/app/models/knowledge_graph.py`（+tier）
- `frontend/src/components/graph/A1KnowledgeGraph.tsx / EdgeReviewPanel.tsx / A1GraphSection.tsx`
- `tests/unit/a1/test_contracts/`（C1-C7）+ 压测脚本

### Definition of Done
- [ ] `pytest backend/tests -q` 全绿（692 基线 + 新增，零回归）
- [ ] C1-C7 契约测试全绿（含负向五类、降级三场景、id 快照、边核算不变量）
- [ ] 明华样本定稿：L2 摘要✓ 深度树✓ 语义边≥3 cst>0
- [ ] 图谱页：tier 分组、L4、降级角标、失效区、open_questions 问出全部可见（Playwright 证据）

### Must Have
- finalize 永不因 LLM 失败/超时阻塞（降级链+三机制）
- 铁律保留：永不删除永不覆盖（版本）、门禁、issuer/stale、visual-bg 线程块逐字保留
- id 内容锚定（不变量5）+ confirmed 三元组精确匹配 + 失效边可见
- POST /concept/extract-edges 仅降级（OpenAPI 标 deprecated）不删除不改行为

### Must NOT Have (Guardrails)
- 不重写 concept_edge_extractor.py（637行）——复用其词表校验/open_questions 转译/截断，仅适配输出形状
- isConceptTermNode 收紧=一行改动，4 个调用点（:216/:219/:543/:961）不做超出正确性要求的重构
- P1 阶段 children 越权消费=违规（SIR 摄入时扁平化）
- 不修 vitest e2e 收集 bug（前序遗留）；不做视觉抛光（动画/minimap 调优）
- 治理文档为输入非交付物——P1-P4 期间不改 doc
- C1-C7 骨架用 xfail/skip 标记，692 基线每阶段边界全绿

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: YES（pytest 692+ / vitest）
- **Automated tests**: Tests-after + 契约骨架先行（P0 建 xfail 骨架，实现阶段转绿）
- **Framework**: pytest（后端）/ vitest（前端组件，如适用）

### QA Policy
每任务含 agent 执行 QA 场景（见各 TODO）。证据存 `.sisyphus/evidence/task-{N}-{slug}.{ext}`。
- **后端 API**: Bash curl + pytest，断言 JSON 字段/状态码
- **前端 UI**: Playwright（playwright skill），`[data-testid=...]` 选择器
- **LLM 环节**: stub provider 注入（T5 提供），provider-kill/timeout 场景用注入失败 double

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (P0 契约定型 — 5 并行, 新文件/独立文件):
├── T1: SIR 契约模型 + graphify.py 骨架 [quick]
├── T2: 词表编译整合（v0.4 §3 全量 + tier 派生边）[unspecified-high]
├── T3: tier 映射表 + GraphNode.tier [quick]
├── T4: open_questions 结构化模型（C6/C7 数据面）[quick]
└── T5: C1-C7 测试骨架 + LLM stub provider 确认/补建 [unspecified-high]

Wave 2 (P1 核心后端 — 2 并行不同文件):
├── T6: graphify_llm 实现（prompt+调用+超时+解析+校验+降级）[deep]
└── T7: 组装器 _build_graph 改造（双树+恢复+失效区+断言）[deep]

Wave 3 (P1 集成 — 3 并行):
├── T8: finalize 端点改造（串联+持久化+两阶段退役+保护块保留）[unspecified-high]
├── T9: 前端 L2/L3 适配（判定收紧+摘要渲染）[visual-engineering]
└── T10: C2 负向用例+降级链+不变量测试 [unspecified-high]

Wave 4 (P2 深化 — 3 并行):
├── T11: children 挂载 + cst 复活 + 断言接线 [deep]
├── T12: 前端 L4 布局 + 深度树渲染 [visual-engineering]
└── T13: id 稳定性快照 + 边核算不变量测试 [unspecified-high]

Wave 5 (P3 呈现 — 3 并行):
├── T14: 概念网 tier 分组 [visual-engineering]
├── T15: 审核台失效区 UI [visual-engineering]
└── T16: 降级角标 UI [visual-engineering]

Wave 6 (P4 闭环+压测 — 2 并行):
├── T17: open_questions 全链闭环（后端+访谈前端）[deep]
└── T18: 超长压测脚本 + 分块触发线报告 [unspecified-high]

Wave FINAL (4 并行评审 → 用户 okay):
├── F1: 计划合规审计 [oracle]
├── F2: 代码质量审查 [unspecified-high]
├── F3: 真实手动 QA [unspecified-high + playwright]
└── F4: 范围忠实检查 [deep]

Critical Path: T1 → T6 → T8 → T11 → T17 → F1-F4
Parallel Speedup: ~65% faster than sequential
Max Concurrent: 5 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| T1-T5 | - | T6,T7,T8,T10,T11,T13,T17 |
| T6 | T1,T2,T5 | T8,T10,T18 |
| T7 | T1,T3,T4 | T8,T11 |
| T8 | T6,T7 | T11,T15,T16,T17 |
| T9 | T3 | T12,T14 |
| T10 | T5,T6,T8 | F1 |
| T11 | T8 | T17 |
| T12 | T9 | T14 |
| T13 | T8 | F1 |
| T14 | T12 | F3 |
| T15 | T8 | F3 |
| T16 | T8 | F3 |
| T17 | T8,T4,T11 | F3 |
| T18 | T6 | F1 |
| F1-F4 | ALL | user okay |

### Agent Dispatch Summary

- **Wave 1**: T1 quick, T2 unspecified-high, T3 quick, T4 quick, T5 unspecified-high
- **Wave 2**: T6 deep, T7 deep
- **Wave 3**: T8 unspecified-high, T9 visual-engineering, T10 unspecified-high
- **Wave 4**: T11 deep, T12 visual-engineering, T13 unspecified-high
- **Wave 5**: T14/T15/T16 visual-engineering
- **Wave 6**: T17 deep, T18 unspecified-high
- **FINAL**: F1 oracle, F2/F3 unspecified-high, F4 deep

---

## TODOs

- [x] 1. SIR 契约模型 + graphify.py 骨架

  **What to do**:
  - 新建 `backend/app/domains/creation/a1/graphify.py`：定义 SIR 五字段 Pydantic 模型（ModuleSummaries/EntryItem 含 children 嵌套/EdgeSpec/ConstraintFields/OpenQuestions）与聚合 `GraphifyResult(success, warning, module_summaries, entries, edges, constraint_fields, open_questions)`
  - 列表字段全部 default_factory=list（D4 部分接受语义）；类型严格（str/dict 校验）
  - 实现 id 卫生化函数 `sanitize_title()`（去 `:`、空白归一、截断32字）与 `depth_id(anchor, title) -> "d:{anchor}:{title}"`；解析 `split(':', 2)`
  - 同锚点同 title 去重规则（保留首条 + duplicates warning 列表）
  - 常量 `GRAPHIFY_TIMEOUT`（env 可覆写，默认 60）
  - 校验规则四条函数化：anchor 合法性（对照 a1_question_tree all_subfield_keys）/ relation∈词表（参数注入）/ DIM.tag∈白名单（STRUCTURED_FIELDS）/ children 深度 Phase1 拒绝（抛 warning 非异常）

  **Must NOT do**: 不实现 LLM 调用（T6）；不改 a1_routes.py；不 import concept_edge_extractor（T2 整合后由 T6 消费）

  **Recommended Agent Profile**:
  - **Category**: `quick` — 单新文件、契约已在治理文档 §4 定死，纯翻译
  - **Skills**: []（无域重叠）

  **Parallelization**: Can Run In Parallel: YES | Wave 1 (with T2-T5) | Blocks: T6,T7,T8 | Blocked By: None

  **References**:
  - `docs/governance/2-A1-v0.5-内容图谱化统一模型与契约.md` §4（五字段 schema+校验规则+降级链+D1-D4 默认值）— 契约逐字翻译源
  - `backend/app/domains/creation/a1/concept_edge_extractor.py:41-90`（ExtractedEdge/ExtractResult 模型风格）— Pydantic 建模范本
  - `backend/app/domains/creation/graph/constraint_topology.py:34-41`（STRUCTURED_FIELDS 21 字段白名单）— DIM.tag 校验数据源
  - `backend/app/domains/creation/seed/a1_question_tree.py`（all_subfield_keys）— anchor 合法性数据源
  - **WHY**: §4 是唯一权威契约；extractor 的模型风格保证一致性；白名单与锚点清单是校验的封闭数据集

  **Acceptance Criteria**:
  - [ ] graphify.py 存在且 `from app.domains.creation.a1.graphify import GraphifyResult` 成功
  - [ ] sanitize_title("灵韵海：中心 奇观 ") → 无冒号、单空格、≤32字
  - [ ] depth_id 解析 round-trip 测试通过

  **QA Scenarios**:
  ```
  Scenario: SIR 模型合法解析（happy path）
    Tool: Bash (pytest)
    Steps:
      1. cd backend && python -c "from app.domains.creation.a1.graphify import GraphifyResult; r=GraphifyResult(**FIXTURE); assert r.success"
      2. pytest tests/unit/a1/test_contracts/test_sir_model.py -q
    Expected Result: 模型实例化+五字段 round-trip 全过
    Evidence: .sisyphus/evidence/task-1-sir-model.txt

  Scenario: 非法输入拒绝（D2 卫生化边界）
    Tool: Bash (pytest)
    Steps:
      1. title 含 "::" / 超32字 / 全空白 → sanitize 后无冒号、有界、非空（全空白→占位"未命名"）
      2. depth_id("力量体系.source","a:b") 解析 split(':',2) 回 anchor="力量体系.source"
    Expected Result: 边界全处理，无异常抛出
    Evidence: .sisyphus/evidence/task-1-sanitize-edge.txt
  ```

  **Commit**: YES — `feat(a1-graphify): T1 SIR contract models + id sanitization`（files: graphify.py + test）

- [x] 2. 词表编译整合（v0.4 §3 全量 + tier 派生边）

  **What to do**:
  - 读 `docs/governance/2-A1-v0.4-世界观底层拓扑概念树.md` §3 派生边总表（★/◆/◇）与 §2 槽位注册表
  - 复核 `concept_edge_vocab.py`（EDGE_VOCAB 16 边 / AXIS_SLOTS / VOCAB_RELATION_NAMES）与 `concept_relation_vocab.py`（RelationRegistry）
  - 补全：v0.4 派生边总表中缺失的边入 EDGE_VOCAB（tier 间派生边如 tier0→tier1 "力量源自"）；每边标注 confidence 级（rule/semantic/structure）与 from_slots/to_slots
  - 封闭性：VOCAB_RELATION_NAMES = EDGE_VOCAB 全量名字集合，导出供 graphify prompt 与组装器校验共用
  - 更新对应词表测试（封闭断言：词表外关系必被拒）

  **Must NOT do**: 不重写 concept_edge_extractor.py（复用不改）；不改 API 签名（RelationRegistry 对外接口保持）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — 需通读 409 行治理文档并精确编译，工作量大但路径清晰
  - **Skills**: []（文档编译任务，无 skill 域重叠）

  **Parallelization**: Can Run In Parallel: YES | Wave 1 | Blocks: T6 | Blocked By: None

  **References**:
  - `docs/governance/2-A1-v0.4-世界观底层拓扑概念树.md` §2-§3（槽位注册表+派生边总表）— 编译源，**逐槽位核对上下游**
  - `backend/app/domains/creation/a1/concept_edge_vocab.py`（现有 16 边结构 EdgeSpec 字段名）— 增量补全不重构
  - `backend/app/domains/creation/a1/concept_relation_vocab.py`（RelationRegistry）— 保持对外接口
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §5.1（EDGE_VOCAB 示例三条）— 形状范本
  - **WHY**: C4 契约要求词表封闭且来自 v0.4 权威；现有 16 边是基线，缺口=v0.4 总表差集

  **Acceptance Criteria**:
  - [ ] EDGE_VOCAB 覆盖 v0.4 §3 总表全部条目（对照清单入库测试）
  - [ ] VOCAB_RELATION_NAMES 与 EDGE_VOCAB 逐名一致（封闭断言测试）
  - [ ] 每条边含 confidence/from_slots/to_slots

  **QA Scenarios**:
  ```
  Scenario: 词表封闭性（C4）
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/unit/a1/test_concept_edge_vocab.py -q
      2. 断言 "力量源自" ∈ VOCAB_RELATION_NAMES 且 from_slots 含 力量体系.source
    Expected Result: 封闭+覆盖断言全绿
    Evidence: .sisyphus/evidence/task-2-vocab.txt

  Scenario: 表外关系被拒（负向）
    Tool: Bash (pytest)
    Steps:
      1. relation="力气很大" ∉ VOCAB_RELATION_NAMES → 校验函数返回 False
    Expected Result: 表外必拒（后续由组装器移入 open_questions）
    Evidence: .sisyphus/evidence/task-2-vocab-negative.txt
  ```

  **Commit**: YES — `feat(a1-vocab): T2 compile v0.4 derivation edge table + tier edges`

- [x] 3. tier 映射表 + GraphNode.tier 字段

  **What to do**:
  - `knowledge_graph.py`: GraphNode 增加 `tier: int | None = None`（可选，向后兼容旧 JSON 反序列化）
  - 新建常量（`a1_question_tree.py` 尾部或独立 `tier_map.py`）：`TIER_MAP = {"世界本体":0,"力量体系":1,"地理空间":2,"文明与社会":2,"历史时间线":3,"视觉设计":4,"玩法设计DNA":4,"骰子设定":4,"IP定位":5,"设定边界":6}` + `MODULE_TIER_COVERAGE` 断言辅助
  - C5 测试：10 模块全覆盖、tier∈[0,6]

  **Must NOT do**: 不动 EdgeType/GraphEdge；不加第 11 个模块的 tier（封闭）

  **Recommended Agent Profile**:
  - **Category**: `quick` — 两处小改+常量+测试
  - **Skills**: []

  **Parallelization**: YES | Wave 1 | Blocks: T7,T9 | Blocked By: None

  **References**:
  - `docs/governance/2-A1-v0.5...md` §3（tier 映射表逐字源）
  - `backend/app/models/knowledge_graph.py:34-50`（GraphNode 字段区）— 追加位置
  - `backend/app/domains/creation/seed/a1_question_tree.py:8-10`（模块 id 锁定清单）— key 必须与 module_ids() 一致
  - **WHY**: C5 契约数据面；module id 拼写必须与 question_tree 逐字一致（中文 id）

  **Acceptance Criteria**:
  - [ ] `GraphNode(id="x", serial_number="1", level=2, tier=3)` 实例化通过
  - [ ] 旧 graph_json（无 tier 字段）反序列化不报错
  - [ ] C5 测试绿

  **QA Scenarios**:
  ```
  Scenario: tier 覆盖断言（C5）
    Tool: Bash (pytest)
    Steps: pytest tests/unit/a1/test_tier_map.py -q
    Expected: 10 模块全覆盖，值域 [0,6]，与 module_ids() 集合相等
    Evidence: .sisyphus/evidence/task-3-tier.txt
  Scenario: 向后兼容
    Tool: Bash (python -c)
    Steps: 用无 tier 的旧节点 JSON dict 实例化 GraphNode → 成功且 tier=None
    Evidence: .sisyphus/evidence/task-3-compat.txt
  ```

  **Commit**: YES — `feat(a1-model): T3 GraphNode.tier + static tier map (C5)`

- [x] 4. open_questions 结构化模型（C6/C7 数据面）

  **What to do**:
  - 新建 `backend/app/domains/creation/a1/open_questions.py`：`OpenQuestion(id, question, status: pending|asked|answered|skipped, answer: str="", created_at, source_hint: str="")` + `OpenQuestionLog`（list 封装，含 upsert/next_pending/mark_answered 序列化往返）
  - 禁止裸 `list[str]`（C6 铁律）——提供 `from_bare_list()` 迁移函数（旧数据兼容读取）
  - 转正证据模型：`AnsweredEvidence`（question_id, answer_text, answered_at）供 graphify prompt 注入（C7 数据面）

  **Must NOT do**: 不接访谈器/finalize（T17 实现接线）；不改 file 记录结构（消费在 T8/T17）

  **Recommended Agent Profile**:
  - **Category**: `quick` — 单文件模型+序列化
  - **Skills**: []

  **Parallelization**: YES | Wave 1 | Blocks: T8,T17 | Blocked By: None

  **References**:
  - `docs/governance/2-A1-v0.5...md` §6 C6/C7 行（格式逐字源）
  - `backend/app/api/a1_routes.py:779`（现行裸 passthrough）— 迁移源行为
  - **WHY**: C6 禁裸 list[str] 是防 tag= 死路复发的注册契约

  **Acceptance Criteria**:
  - [ ] OpenQuestionLog round-trip 序列化测试绿
  - [ ] from_bare_list(["问句"]) → [OpenQuestion(status=pending)]
  - [ ] C6 骨架测试（xfail→绿路径）就位

  **QA Scenarios**:
  ```
  Scenario: C6 往返序列化
    Tool: Bash (pytest)
    Steps: pytest tests/unit/a1/test_contracts/test_c6_openq.py -q
    Expected: 结构化记录 dump→load→逐字段相等；状态机 pending→asked→answered 流转合法
    Evidence: .sisyphus/evidence/task-4-openq-model.txt
  ```

  **Commit**: YES — `feat(a1-openq): T4 C6/C7 structured open_questions models`

- [x] 5. C1-C7 测试骨架 + LLM stub provider 确认/补建

  **What to do**:
  - 核查现有 provider 测试 double（`tests/unit/` 下 provider fake/stub 模式，如 test_provider.py 的 fake 范式）
  - 若无通用 stub：在 `tests/unit/a1/conftest.py` 建 `StubLLMProvider`（可编程响应/可注入异常/可注入超时 sleep）
  - 建 `tests/unit/a1/test_contracts/` 骨架：test_c1_answers_smoke / test_c2_sir_schema（含五类负向 xfail 占位）/ test_c3_dualtree_invariants（五条不变量 xfail 占位）/ test_c4_vocab_closed / test_c5_tier_map / test_c6_openq（接 T4）/ test_c7_loop_e2e（xfail 占位）
  - 全部 xfail/skip 标记，692 基线全绿不受影响

  **Must NOT do**: 不让骨架失败态破坏基线（xfail 严格标记）；不建真实 LLM 调用测试

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — 测试架构工作，需摸清现有 conftest/fixture 生态
  - **Skills**: [`test-driven-development`] — 骨架即 RED 态设计，TDD 纪律适用

  **Parallelization**: YES | Wave 1 | Blocks: T6,T10,T13 | Blocked By: None

  **References**:
  - `backend/tests/unit/a1/`（现有 conftest/Fake 注入范式，如 FakeInterviewer 用法）— stub 风格对齐
  - `backend/tests/unit/test_provider.py`（provider 测试 double 现状）— 确认是否可复用
  - `docs/governance/2-A1-v0.5...md` §6（C1-C7 测试要求逐条）— 骨架清单源
  - **WHY**: Metis 指出"若无 stub，C1-C7 将永远 skip"——本任务是契约可验证性的地基

  **Acceptance Criteria**:
  - [ ] test_contracts/ 七文件存在，收集 `pytest tests/unit/a1/test_contracts/ --collect-only -q` 全部登记
  - [ ] `pytest backend/tests -q` 仍全绿（692 基线）
  - [ ] StubLLMProvider 可编程返回+异常+超时三模式

  **QA Scenarios**:
  ```
  Scenario: 骨架不破坏基线
    Tool: Bash (pytest)
    Steps: pytest backend/tests -q
    Expected: 692+xfail 计数正确，0 failed
    Evidence: .sisyphus/evidence/task-5-baseline.txt
  Scenario: stub 三模式
    Tool: Bash (pytest)
    Steps: StubLLMProvider(response=X)→返回X；raise_error=True→RuntimeError；sleep_beyond→超时可控
    Evidence: .sisyphus/evidence/task-5-stub.txt
  ```

  **Commit**: YES — `test(a1): T5 C1-C7 contract skeletons + stub provider`

- [x] 6. graphify_llm 实现（prompt+调用+超时+解析+校验+降级）

  **What to do**:
  - `graphify.py` 内实现 `graphify_llm(session, provider) -> GraphifyResult`：
    - prompt 构造：answers 全文 + 边词表（T2 VOCAB_RELATION_NAMES）+ 不可动清单（设定边界.immutable_core）+ tier 映射表 + 节点引用规则（`d:{anchor}:{title}` 编发规则预先告知 LLM）+ C7 转正证据（answered open_questions 注入，T17 接线前先留参数位）
    - 调用：`asyncio.run(asyncio.wait_for(provider.chat_json(...), timeout=GRAPHIFY_TIMEOUT))`（D3 超时=降级）
    - 解析：raw dict → GraphifyResult（复用 T1 模型校验）；校验失败/异常/超时 → `GraphifyResult(success=False, warning="graphify failed: ...")`
  - 降级三机制数据面：warning 文案分级（module_summaries/entries/edges/constraint_fields 四类标记，供组装器分域兜底）；部分接受（D4：列表字段缺失=空，类型错=整体失败）
  - 校验拦截：anchor 非法/表外 relation（转 open_questions）/超白名单 DIM.tag（丢弃+warning）/children Phase1 拒（扁平化+warning）
  - 单测：stub provider 三模式全场景（成功五字段/部分空/异常/超时）

  **Must NOT do**: 不直写 graph_json（铁律1c）；不调用组装逻辑；prompt 不含退役术语（tag= 等）

  **Recommended Agent Profile**:
  - **Category**: `deep` — LLM prompt 工程+降级矩阵+校验管线，核心复杂度
  - **Skills**: []（provider 契约已在库内，无外部新库）

  **Parallelization**: YES（与 T7 并行，不同文件）| Wave 2 | Blocks: T8,T10,T18 | Blocked By: T1,T2,T5

  **References**:
  - `backend/app/domains/creation/a1/interviewer.py:189-270`（RealLLMInterviewer 调用范式：asyncio.run+chat_json+log_event+异常包装）— 逐模式照抄
  - `backend/app/domains/creation/a1/concept_edge_extractor.py:98-200`（抽取函数结构：prompt 注入词表/不可动清单/解析/降级）— 可复用片段参考
  - `docs/governance/2-A1-v0.5...md` §4-§5（五字段+校验五条+降级三机制）— 行为规范
  - `backend/app/ai/provider.py`（chat_json 契约）— 调用接口
  - **WHY**: interviewer 的调用/降级/log 范式是项目内已验证的 LLM 单调用模式，照抄保证一致性

  **Acceptance Criteria**:
  - [ ] stub 成功场景：五字段全解析+校验通过
  - [ ] stub 异常/超时：success=False + warning 含 "graphify"，不抛出
  - [ ] 表外 relation 自动转 open_questions；非法 anchor 丢弃+warning
  - [ ] prompt 含词表封闭声明与 d: 编发规则（快照断言 prompt 关键段）

  **QA Scenarios**:
  ```
  Scenario: 五字段成功解析（happy）
    Tool: Bash (pytest + stub)
    Steps:
      1. StubLLMProvider 返回治理文档 §4 示例 JSON
      2. graphify_llm(session, stub) → entries 含 修士/灵器，edges 含 中心位于
    Expected: success=True，全字段校验通过
    Evidence: .sisyphus/evidence/task-6-happy.txt

  Scenario: 超时降级（D3）
    Tool: Bash (pytest + stub sleep)
    Steps:
      1. stub sleep > GRAPHIFY_TIMEOUT(env 设 1s)
      2. graphify_llm → success=False, warning 含 "graphify"
    Expected: 不抛 TimeoutError，受控降级
    Evidence: .sisyphus/evidence/task-6-timeout.txt

  Scenario: 负向五类全拒（C2 核心）
    Tool: Bash (pytest)
    Steps: 伪造 anchor / 表外 relation / 越权 DIM.tag / children 嵌套 / 幻觉节点引用 → 逐类断言被拒+warning
    Evidence: .sisyphus/evidence/task-6-negative.txt
  ```

  **Commit**: YES — `feat(a1-graphify): T6 unified LLM call + validation + degradation`

- [x] 7. 组装器 _build_graph 改造（双树+恢复+失效区+断言）

  **What to do**:
  - `a1_routes.py::_build_graph(session, file_rec, llm_result)` 签名扩展（默认 None=全降级，保旧测试兼容路径）
  - 步骤 a：概念树投影（现有逻辑），L2 description ← module_summaries（缺失回退 label）
  - 步骤 b：深度树挂载——遍历 entries，`d:{anchor}:{title}` id（T1 函数），TREE 边 L3→L4 "分条目"，serial=`D{锚点}-{k}`；Phase1 children 扁平化拒收
  - 步骤 c：语义边合并——edges→GraphEdge（SEMANTIC/RULE/STRUCTURE by confidence）；re-finalize 恢复：三元组精确匹配 confirmed_edges；**失效边（端点不存在）→ `rec["dead_edges"]` 列表（数据面），替换 :762 静默 continue**
  - 步骤 d-e：constraint_fields 通道预留在 T11 接线；tier 标注（T3 TIER_MAP 写模块节点）
  - 运行时断言：constraint_fields 非空但 cst=0 / edges 非空但语义边=0 → log_event("assemble_assertion")
  - 边核算不变量：input_edges == graph_edges + dead_edges（测试钩子）
  - 更新 test_finalize_graph_topology 不变量（TREE=模块+条目+分条目）

  **Must NOT do**: 不动 :688-696/:698-710/:803-818 保护块（本任务只改 _build_graph 函数体与其调用契约）；不做 children 递归（T11）；不动 apply_constraints 本体

  **Recommended Agent Profile**:
  - **Category**: `deep` — 组装核心，多契约汇合点，不变量敏感
  - **Skills**: []（纯后端域内）

  **Parallelization**: YES（与 T6 并行）| Wave 2 | Blocks: T8,T11 | Blocked By: T1,T3,T4

  **References**:
  - `backend/app/api/a1_routes.py:198-266`（现行 _build_graph）— 改造基底
  - `backend/app/api/a1_routes.py:753-772`（confirmed 合并范本 + 失效丢弃 :762 待修点）— 恢复逻辑抄写/修正源
  - `backend/app/api/a1_routes.py:110-122`（_STRUCTURED_TAGS 旧解析，仅参考不删）— 历史对照
  - `docs/governance/2-A1-v0.5...md` §2（双树+不变量五条）§5（组装 a-g）— 行为规范
  - `backend/tests/unit/a1/test_a1_routes.py::test_finalize_graph_topology`— 不变量更新对象
  - **WHY**: :753-772 是项目验证过的恢复合并范本；:762 是 R2 补丁的精确手术点

  **Acceptance Criteria**:
  - [ ] llm_result=None 时行为=现状（旧测试全绿）
  - [ ] 明华 fixture：深度树 d: 节点+D 序号+TREE 分条目边；L2=LLM 摘要
  - [ ] 失效边进 dead_edges 不丢（核算等式成立）
  - [ ] 三元组匹配恢复 confirmed=true

  **QA Scenarios**:
  ```
  Scenario: 双树组装（明华样本 happy）
    Tool: Bash (pytest + GraphifyResult fixture)
    Steps:
      1. fixture: entries 含 世界本体.existence 4 items
      2. _build_graph(...) → 4 个 d: 节点 level=4，serial D2-2-1..4，TREE 边 L3→L4
    Expected: 不变量1（TREE=模块+条目+分条目）成立
    Evidence: .sisyphus/evidence/task-7-dualtree.txt

  Scenario: 失效边核算不变量（R2 核心）
    Tool: Bash (pytest)
    Steps:
      1. confirmed_edges 快照引用不存在节点
      2. 组装后 len(dead_edges)==快照数，graph.edges 无静默丢失
    Expected: input == graph + deadzone 等式成立
    Evidence: .sisyphus/evidence/task-7-deadzone.txt
  ```

  **Commit**: YES — `feat(a1-assembler): T7 dual-tree assembly + dead-edge zone + assertions`

- [x] 8. finalize 端点改造（串联+持久化+两阶段退役+保护块保留）

  **What to do**:
  - finalize 内串联：graphify_llm(session, provider) → _build_graph(session, rec, llm_result)
  - 退役两阶段：移除 finalize 内 extract_concept_terms 调用块（:717-776 的 T-B 逻辑），term 恢复/入图逻辑由 SIR entries+dead_edges 取代；`POST /concept/extract-edges` 端点**保留不删不改行为**，OpenAPI `deprecated=True` + docstring 标注
  - warnings 持久化：`rec["finalize_warnings"] = warnings`（rec.update 补键）；graphify 降级 warning 并入
  - **逐字保留保护块**：:688-696 门禁 / :698-710 issuer+stale / :803-818 visual-bg 线程块（diff 中这三段必须零变化）
  - edge_stats 重算保留（:782 语义：confirmed=false 语义边计入 semantic_total——现状语义即如此，不改变）
  - 更新 finalize 相关测试（stub 注入路径 + 降级路径）

  **Must NOT do**: 不删 extract-edges 端点；不碰三个保护块；不改变 409 门禁契约

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — 精密手术（同文件保护块），路径明确但零容错
  - **Skills**: []（域内重构）

  **Parallelization**: YES（与 T9/T10 并行，但**必须在 T7 合入后开始**——同文件 a1_routes.py 串行）| Wave 3 | Blocks: T11,T15,T16,T17 | Blocked By: T6,T7

  **References**:
  - `backend/app/api/a1_routes.py:683-822`（finalize 全函数）— 手术对象，保护块行号已标
  - `backend/app/api/a1_routes.py:1421+`（extract-edges 端点）— 仅加 deprecated 标记
  - `docs/governance/2-A1-v0.5...md` §8.1（两阶段处置行）— 退役规范
  - **WHY**: Metis 强调 visual-bg 线程块最易被 _build_graph 改造静默杀死——本任务 diff 审查保护块零变化

  **Acceptance Criteria**:
  - [ ] git diff 显示三个保护块零改动（F4 审查点）
  - [ ] stub 成功：finalize 200 + graph_json 含深度树+语义边 + finalize_warnings 键存在
  - [ ] stub 失败：finalize 200 + 纯概念树 + finalize_warnings 含 graphify 标记
  - [ ] extract-edges 端点仍可调用（deprecated 标记可见于 /docs）

  **QA Scenarios**:
  ```
  Scenario: 降级路径端到端（Metis 验收#1）
    Tool: Bash (pytest + stub raise)
    Steps:
      1. 注入失败 provider → POST finalize
      2. 响应 200；rec["finalize_warnings"] 含 "graphify"；graph_json 仅 TREE 节点
    Expected: 永不阻塞铁律成立
    Evidence: .sisyphus/evidence/task-8-degrade-e2e.txt

  Scenario: 保护块零变化
    Tool: Bash (git diff)
    Steps: git diff HEAD~1 -- backend/app/api/a1_routes.py | 核对三段
    Expected: 门禁/issuer+stale/visual-bg 三段无 -/+ 行
    Evidence: .sisyphus/evidence/task-8-preserve.txt
  ```

  **Commit**: YES — `feat(a1-finalize): T8 wire graphify + persist warnings + retire two-stage`

- [x] 9. 前端 L2/L3 适配（判定收紧+摘要渲染）

  **What to do**:
  - `A1KnowledgeGraph.tsx`: isConceptTermNode 收紧为**仅 `term:` 前缀**（一行）；新增 `isDepthNode = id.startsWith('d:')` 导出
  - 核对 4 个调用点（:216/:219/:543/:961 附近）——term 判定语义不扩散重构；新增 d: 节点渲染分支（level4 深度树样式：模块簇色系复用 termClusterColor）
  - L2 节点渲染 LLM 摘要（description 已是摘要文本，渲染层验证换行/截断≤2行+tooltip 全文）
  - L3 渲染现状保留（label 拆分逻辑不变）
  - tier 类型：`types/graph.ts` GraphNode + `tier?: number`

  **Must NOT do**: 不动布局函数（T12）；不做 tier 分组（T14）；4 调用点外不重构

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering` — 前端组件改造
  - **Skills**: [`frontend-ui-ux`] — React Flow 节点渲染域

  **Parallelization**: YES | Wave 3 | Blocks: T12,T14 | Blocked By: T3

  **References**:
  - `frontend/src/components/graph/A1KnowledgeGraph.tsx:55-57`（判定函数）+ `:216/:219/:543/:961`（调用点）
  - `frontend/src/components/graph/A1KnowledgeGraph.tsx:60-75`（TERM_CLUSTER_COLORS/termClusterColor）— d: 节点复用
  - `frontend/src/types/graph.ts`（GraphNode 类型）— tier 字段追加
  - **WHY**: Metis 指令：tightening 前用 lsp_find_references 核对全部引用点，防漏改

  **Acceptance Criteria**:
  - [ ] `npx tsc --noEmit` PASS
  - [ ] isConceptTermNode({id:"term:x",level:9})===true；({id:"d:a:b",level:4})===false
  - [ ] d: fixture 渲染快照（vitest 若适用，否则 Playwright）

  **QA Scenarios**:
  ```
  Scenario: 判定收紧回归
    Tool: Bash (vitest scoped) 或 Playwright
    Steps: 单测断言三态（term:/d:/普通）
    Evidence: .sisyphus/evidence/task-9-predicate.txt
  Scenario: 深度树节点渲染
    Tool: Playwright（本地起服务+stub fixture 页面或组件测试页）
    Steps: 渲染含 d: 节点 graph → 节点可见且带簇色边框
    Evidence: .sisyphus/evidence/task-9-render.png
  ```

  **Commit**: YES — `feat(a1-ui): T9 predicate tightening + depth node rendering`

- [x] 10. C2 负向用例+降级链+不变量测试（契约转绿）

  **What to do**:
  - T5 骨架转绿：test_c2_sir_schema 五类负向（伪造 anchor/表外 relation/超白名单 DIM.tag/children 越权/幻觉引用）——经 T6+T7+T8 全链注入 stub 断言拒绝
  - test_c3_dualtree_invariants 五条不变量（TREE 计数/序号同构/d: 可解析/引用存在/id 无顺序成分）
  - 降级链三场景（异常/超时/部分空）端到端断言 finalize_warnings 分域标记
  - 运行时断言场景：constraint_fields 非空但 cst=0（T11 前 cst 通道未接，断言以 log_event 为准 xfail→T11 转绿）

  **Must NOT do**: 不写真实 LLM 测试；不测前端（T9 自带）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — 契约测试工程
  - **Skills**: [`test-driven-development`] — 骨架转绿纪律

  **Parallelization**: YES | Wave 3 | Blocks: F1 | Blocked By: T5,T6,T8

  **References**:
  - `tests/unit/a1/test_contracts/`（T5 骨架）+ `tests/unit/a1/conftest.py`（stub）
  - `docs/governance/2-A1-v0.5...md` §2（不变量）§4（降级）§8.3（验收 9-12 条）
  - **WHY**: v0.5 §8.3 验收 9/10/11/12 条的测试载体

  **Acceptance Criteria**:
  - [ ] C2/C3 契约测试全绿（xfail 清零）
  - [ ] 降级三场景 warnings 分域断言通过

  **QA Scenarios**:
  ```
  Scenario: 契约全绿门
    Tool: Bash
    Steps: pytest tests/unit/a1/test_contracts/ -q
    Expected: 全 pass，0 xfail 残留（T11 范围除外）
    Evidence: .sisyphus/evidence/task-10-contracts-green.txt
  ```

  **Commit**: YES — `test(a1): T10 contract negative cases + degradation + invariants green`

- [x] 11. children 递归挂载 + cst 复活 + 断言接线

  **What to do**:
  - children 递归：entries[].items[].children → 递归建 L4+ 节点（id=`d:{anchor}:{title}` 层级内 title 唯一化，serial `D{锚点}-{k}-{j}`）+ TREE 边链；深度上限 2 层（防无限）；Phase2 开关 env `A1_DEPTH_CHILDREN=1` 控制（默认开）
  - cst 复活：constraint_fields → DimensionResultSet 构造（DIM.tag→对应 Output 模型字段）→ apply_constraints(graph, drs, stage="A1")；**幂等抄 :753-772 合并范本**（同 DIM.tag 已存在跳过）；_build_dimension_result_set 旧函数标记 deprecated 注释（不删，考古保留）
  - 断言接线：T7 的运行时断言在 cst 通道打通后转绿（constraint_fields 非空但 cst=0 → log_event 告警）
  - 更新 test_finalize_graph_topology：cst>0 + CROSS>0 场景 fixture

  **Must NOT do**: 不删 _build_dimension_result_set（历史考古保留）；children 深度>2 违规

  **Recommended Agent Profile**:
  - **Category**: `deep` — 递归组装+约束管线复活，考古敏感
  - **Skills**: []

  **Parallelization**: YES（与 T12/T13 并行；**T8 合入后开始**——同文件串行）| Wave 4 | Blocks: T17 | Blocked By: T8

  **References**:
  - `backend/app/domains/creation/graph/constraint_topology.py:81-163`（apply_constraints 幂等范本）— 直接消费方
  - `backend/app/api/a1_routes.py:753-772`（confirmed 合并范本）— cst 幂等抄写源
  - `backend/app/models/dimension.py`（LawOutput 等 21 字段）— constraint_fields→Output 映射
  - `docs/governance/2-A1-v0.5...md` §8.3 验收4（cst 复活=考古断链闭合）
  - **WHY**: constraint_fields 值类型为 str，Output 模型字段也全 str——直构造可行，无类型转换层

  **Acceptance Criteria**:
  - [ ] fixture constraint_fields={"LAW.world_structure":"九层嵌套"} → cst_LAW_world_structure 节点+CROSS 边出现
  - [ ] 同 inputs 二次组装 → cst 不重复（幂等）
  - [ ] children fixture → L4 下 L5 孙节点+TREE 链；深度 3 层被拒+warning

  **QA Scenarios**:
  ```
  Scenario: 考古断链闭合（v0.5 验收4）
    Tool: Bash (pytest)
    Steps: constraint_fields 非空 → 断言 graph.nodes 含 cst_* 且 CROSS 边数>0
    Evidence: .sisyphus/evidence/task-11-cst-revival.txt
  Scenario: cst 幂等
    Tool: Bash (pytest)
    Steps: 同 drs 连续两次 apply → 节点/边数不变
    Evidence: .sisyphus/evidence/task-11-idempotent.txt
  ```

  **Commit**: YES — `feat(a1-p2): T11 children mounting + cst revival + assertion wiring`

- [x] 12. 前端 L4 布局 + 深度树渲染

  **What to do**:
  - `calculateNodePosition`：+level 4 y 坐标（如 y=760）；深度树节点按父 L3 x 分组对齐（复用 level3 parentX 模式）；L5（若 children 两层）y=1000
  - LEVEL_Y_POSITIONS 常量化扩展；MiniMap/fitView 适配新高度
  - 图例补深度树节点样式（d: 簇色+细边）

  **Must NOT do**: 不做动画/自动布局抛光；不动 tier 分组（T14）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**: YES | Wave 4 | Blocks: T14 | Blocked By: T9

  **References**:
  - `frontend/src/components/graph/A1KnowledgeGraph.tsx:100-140`（calculateNodePosition+间距常量）— 扩展点
  - `docs/governance/2-A1-v0.1...md` §3（带状布局契约）— 延续规范
  - **WHY**: 布局函数硬编码 L0-L3——扩 L4/L5 是最小侵入路径

  **Acceptance Criteria**:
  - [ ] 含 d: 节点图谱渲染无重叠（Playwright 截图目测+节点 bbox 断言）
  - [ ] tsc PASS

  **QA Scenarios**:
  ```
  Scenario: L4 带状布局
    Tool: Playwright
    Steps: 渲染明华 fixture（含深度树）→ 截图 → 断言 d: 节点 y 在 L4 带、x 对齐父条目
    Evidence: .sisyphus/evidence/task-12-l4-layout.png
  ```

  **Commit**: YES — `feat(a1-ui): T12 L4/L5 band layout`

- [x] 13. id 稳定性快照 + 边核算不变量测试

  **What to do**:
  - test_id_stability.py：同 answers 两次全链组装（stub 固定响应）→ 节点 id 集合 byte-identical（不变量5 快照）
  - 锚点漂移预期行为测试：用户改一条 answer → 该锚点子树 id 变化 → 相关 confirmed 边进 dead_edges（断言=预期非 bug，v0.5 D1/R3 设计）
  - 混合版本死区洪泛测试：旧 term: 快照 + 新 d: 组装 → 旧边全部可见进 dead_zone（D1 预期行为）
  - 边核算：input==graph+deadzone 全场景矩阵

  **Must NOT do**: 不写模糊匹配"修复"（明确拒绝语义合并）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`test-driven-development`]

  **Parallelization**: YES | Wave 4 | Blocks: F1 | Blocked By: T8

  **References**:
  - `docs/governance/2-A1-v0.5...md` §2 不变量5 + §4 匹配键 + D1/D2
  - `tests/unit/a1/test_contracts/`（挂载点）
  - **WHY**: Metis 验收#2/#3 的测试载体；锚点漂移不立测试将来必被报 bug

  **Acceptance Criteria**:
  - [ ] 快照测试绿：两次组装 id set 相等
  - [ ] 漂移/洪泛两测试绿（断言 dead_edges 行为）

  **QA Scenarios**:
  ```
  Scenario: id 快照（Metis 验收#2）
    Tool: Bash (pytest)
    Steps: pytest tests/unit/a1/test_id_stability.py -q → all pass
    Evidence: .sisyphus/evidence/task-13-snapshot.txt
  ```

  **Commit**: YES — `test(a1): T13 id stability + anchor drift + mixed-version deadzone`

- [x] 14. 概念网 tier 分组布局

  **What to do**:
  - concept 模式：模块节点按 tier 0-6 分组（tier 带状纵列或色彩分组带）；tier 色带图例（存在基座→治理层 七色）
  - 派生边（tier 间语义边）正常经语义边通道渲染；tier 分组开关默认开
  - tier 缺失节点（非模块节点）归"无分组"区

  **Must NOT do**: 不改 tree 模式布局；不做动画

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**: YES | Wave 5 | Blocks: F3 | Blocked By: T12

  **References**:
  - `frontend/src/components/graph/A1KnowledgeGraph.tsx`（concept 模式渲染区+筛选器）
  - `docs/governance/2-A1-v0.5...md` §3 tier 呈现规范
  - **WHY**: 七层理论的可视化落点（决策6）

  **Acceptance Criteria**:
  - [ ] concept 模式下 10 模块按 7 tier 分组可见（Playwright 断言分组容器/色彩）
  - [ ] 图例含 tier 0-6 标签

  **QA Scenarios**:
  ```
  Scenario: tier 分组可见
    Tool: Playwright
    Steps: 定稿图谱→concept 模式→断言 [data-testid="tier-group-0"].."tier-group-6" 至少模块归属正确样本 3 组
    Evidence: .sisyphus/evidence/task-14-tier-groups.png
  ```

  **Commit**: YES — `feat(a1-ui): T14 concept-net tier grouping`

- [x] 15. 审核台失效区 UI

  **What to do**:
  - EdgeReviewPanel 新增"失效区"列表：dead_edges 展示（from/to/relation+"上轮已确认，本轮源节点未再出现"文案）+ 两操作：废弃（从 confirmed_edges 删除）/保留悬置（标记，下次 re-finalize 仍尝试恢复）
  - GET /api/a1/file/{id} 扩展返回 dead_edges（a1_routes.py 尾部数据通道——**与 T8/T11 同文件，需在其后合入**）
  - 删除需二次确认（08-31 设计 6.7-6 沿用）

  **Must NOT do**: 不引入文本输入（零文本图谱页铁律）；不改 confirm/reject 既有端点语义

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**: YES | Wave 5 | Blocks: F3 | Blocked By: T8

  **References**:
  - `frontend/src/components/graph/EdgeReviewPanel.tsx`（现审核台结构）
  - `frontend/src/api/a1.ts`（confirmEdge/rejectEdge 范式）— dead_edges API 封装
  - `docs/plans/2026-08-31...md` §6.2/§6.7（审核卡+二次确认范式）
  - **WHY**: R2 补丁的 UI 落点——失效可见是"禁静默丢弃"的完成态

  **Acceptance Criteria**:
  - [ ] dead_edges fixture → 失效区列表渲染+废弃/悬置操作生效（API 往返）
  - [ ] 无任何文本输入框（页面扫描断言）

  **QA Scenarios**:
  ```
  Scenario: 失效边可见可处置
    Tool: Playwright
    Steps: 注入含 dead_edges 的 file → 图谱页 → 失效区条目可见 → 点废弃 → 条目消失且 confirmed_edges 更新
    Evidence: .sisyphus/evidence/task-15-deadzone-ui.png
  ```

  **Commit**: YES — `feat(a1-ui): T15 review panel dead-zone`

- [x] 16. 降级角标 UI

  **What to do**:
  - A1GraphSection 顶部：finalize_warnings 非空 → "本轮降级：N 项"角标（琥珀色）+ 点击展开明细浮层（分域列表：摘要/条目/边/约束）
  - data-testid="degradation-badge"

  **Must NOT do**: 不阻塞图谱查看（角标非模态）

  **Recommended Agent Profile**:
  - **Category**: `quick` — 小型 UI 组件
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**: YES | Wave 5 | Blocks: F3 | Blocked By: T8

  **References**:
  - `frontend/src/components/graph/A1GraphSection.tsx`（顶栏区+loadFileTerms 数据通道范式）
  - `docs/governance/2-A1-v0.5...md` §4 降级三机制（角标=机制2）
  - **WHY**: R1 补丁 UI 落点——区分"正常空"与"静默降级"

  **Acceptance Criteria**:
  - [ ] warnings 空时无角标；非空时角标+明细可见（Playwright testid 断言）

  **QA Scenarios**:
  ```
  Scenario: 降级角标（Metis 验收#1 前端半）
    Tool: Playwright
    Steps: stub 降级 finalize → 图谱页 → expect [data-testid="degradation-badge"] visible + 文案含 "降级"
    Evidence: .sisyphus/evidence/task-16-badge.png
  ```

  **Commit**: YES — `feat(a1-ui): T16 degradation badge`

- [x] 17. open_questions 全链闭环（C6/C7 实现：后端+访谈前端）

  **What to do**:
  - 后端（a1_routes.py 尾部+interviewer.py prompt）：
    - finalize：graphify open_questions（表外关系问句）→ OpenQuestionLog.upsert（保留已答/已跳过状态）→ rec["open_questions"]
    - chat：session 有 pending open_question 时 prompt 注入"开场问出一次一条（最老优先）"；InterviewResult 扩展 `open_question_answered: {id, answer} | None` 解析（用户答待问→记录 answer+status=answered）
    - 下次 finalize：answered 条目作为 C7 转正证据注入 graphify prompt（"用户已确认：{question}→{answer}"）→ LLM 产出对应边
  - 前端（访谈页 guided_chat）：待问提示卡（一次一条+跳过按钮）；状态角标（待问 N）
  - 单问句在场铁律：提案卡片在场时待问挂起（08-31 设计 6.5 沿用）

  **Must NOT do**: 不破坏现有 stall-guard/suggestion 序号机制；待问不得三连问

  **Recommended Agent Profile**:
  - **Category**: `deep` — 跨三组件两格式交接全链（C6/C7）
  - **Skills**: []

  **Parallelization**: YES（与 T18 并行）| Wave 6 | Blocks: F3 | Blocked By: T8,T4,T11（**T11 后合入**——同文件）

  **References**:
  - `backend/app/domains/creation/a1/open_questions.py`（T4 模型）
  - `backend/app/domains/creation/a1/interviewer.py:287-350`（prompt 规则区——新增待问规则插规则8 后）
  - `frontend/src/pages/a1/`（guided_chat 组件——访谈页输入协议表 08-31 §6.5）
  - `docs/governance/2-A1-v0.5...md` §6 C6/C7 行 + §8.3 验收（P4 全链）
  - **WHY**: C7 端到端测试是 v0.5 §6 的注册验收——表外→问→答→转正全链

  **Acceptance Criteria**:
  - [ ] C7 e2e：表外关系→finalize 进 open_questions→访谈问出→用户答→下次 finalize 该关系成边（confirmed=false）→审核台可见
  - [ ] 跳过→不再问（status=skipped 持久）
  - [ ] 单问句铁律：提案在场时无待问卡（测试）

  **QA Scenarios**:
  ```
  Scenario: C7 全链转正（v0.5 验收 P4 门）
    Tool: Bash (pytest + stub 两轮)
    Steps:
      1. stub LLM 返回表外关系"灵韵浓度" → finalize → open_questions 含世界观问句
      2. 模拟用户回答 → 下次 finalize（stub 返回对应边）→ graph.edges 含转正边
    Expected: 全链状态机流转正确
    Evidence: .sisyphus/evidence/task-17-c7-loop.txt
  Scenario: 访谈页问出 UI
    Tool: Playwright
    Steps: 有 pending 待问 → 访谈页提示卡可见 → 跳过按钮 → 卡片消失
    Evidence: .sisyphus/evidence/task-17-ask-ui.png
  ```

  **Commit**: YES — `feat(a1-p4): T17 open_questions closed loop (C6/C7)`

- [x] 18. 超长压测脚本 + 分块触发线报告

  **What to do**:
  - `scripts/stress_graphify.py`：构造超长 answers（3-5 模块满答×长文 value，模拟明华×3 体量）→ 真 provider 计时调用 graphify_llm
  - 采集：输入 token 估算/输出 token/延迟/五字段完整率/质量抽检（摘要语义合理性人工标记位）
  - 产出报告 `.sisyphus/evidence/task-18-stress-report.md`：分块触发线建议（如 input>15k tokens 建议分块）写入治理文档附录（**唯一允许的 doc 改动：附录新增**）

  **Must NOT do**: 不实现分块本身（触发线之后的立项）；不跑真实 API 超 10 次（成本）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` — 脚本+测量+报告
  - **Skills**: []

  **Parallelization**: YES | Wave 6 | Blocks: F1 | Blocked By: T6

  **References**:
  - `backend/app/ai/config.py`（provider 配置/env）
  - `%TEMP%\opencode\a1_test\*.json`（明华样本 fixture 范式——08-28 实测产物）
  - `docs/governance/2-A1-v0.5...md` §4 长内容预案（R4 补丁）
  - **WHY**: R4 补丁的量化产出——为"何时必须分块"立数据依据

  **Acceptance Criteria**:
  - [ ] 压测脚本可重跑；报告含 token/延迟/完整率三表
  - [ ] 触发线结论一行明确（"≤Xk tokens 单调用安全"）

  **QA Scenarios**:
  ```
  Scenario: 压测产出报告
    Tool: Bash
    Steps: python scripts/stress_graphify.py --rounds 3 → 报告文件生成且三表非空
    Evidence: .sisyphus/evidence/task-18-stress-report.md
  ```

  **Commit**: YES — `chore(a1): T18 graphify stress test + chunking trigger report`

---

## Final Verification Wave (MANDATORY — after ALL tasks)

> 4 review agents in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read plan end-to-end + v0.5 governance doc. Verify every "Must Have" (run pytest, curl finalize with stub, check cst>0). Search every "Must NOT Have" pattern (extractor rewrite? guardrails touched? children consumed in P1 code paths?). Check evidence files in .sisyphus/evidence/.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [18/18] | VERDICT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  `tsc --noEmit` + ruff + mypy + `pytest backend/tests -q`（692+新增全绿）+ vitest run（scoped）. Review changed files: `as any`/`@ts-ignore`/empty catch/console.log prod/unused imports/AI slop（过度注释/泛名 data/result）.
  Output: `Build [PASS] | Lint [PASS] | Tests [N pass] | Files [N clean] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high` + `playwright` skill
  Clean state → start.ps1 → 全链：种子→访谈(≥每模块过半)→定稿→图谱页断言（tier 分组/L4/角标/失效区/语义边审核）→回退→再深化→re-finalize→id 稳定性→open_questions 问出→回答→转正成边. Screenshots to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  Per task: read "What to do" vs git diff. 1:1 无缺失无蔓延. "Must NOT do" 合规. Cross-task contamination check（T7/T8/T11 同文件改动边界）. Unaccounted changes flag.
  Output: `Tasks [18/18 compliant] | Contamination [CLEAN] | Unaccounted [CLEAN] | VERDICT`

---

## Commit Strategy

- Per-task commit, conventional: `feat(a1-graphify): T1 SIR contract models` / `feat(a1-assembler): T7 dual-tree assembly` / `test(a1): T10 negative contract cases` …
- Pre-commit: 相关 pytest 子集全绿
- T8/T11/T17 触及 a1_routes.py：commit message 注明保护区块未动（gate/issuer/stale/visual-bg）

---

## Success Criteria

### Verification Commands
```bash
pytest backend/tests/unit/a1 -q           # 全绿（契约+负向+快照+不变量）
pytest backend/tests -q                    # 692+新增全绿零回归
cd frontend && npx tsc --noEmit           # PASS
npx playwright test tests/e2e/a1-graph.spec.ts  # 图谱页 E2E 绿
```

### Final Checklist
- [ ] v0.5 治理文档 §8 验收 12 条逐条对应测试存在且绿
- [ ] C1-C7 注册表全绿；不变量五条断言在 CI
- [ ] 明华样本全链证据（含超长压测报告）
- [ ] All "Must Have" present / All "Must NOT Have" absent
