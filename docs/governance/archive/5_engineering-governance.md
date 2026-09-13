---
tags: [governance, engineering, backend]
updated: 2026-08-04
---

# 表5 — 工程治理体系 (Engineering Governance)

> **管理维度**: 实现 — "代码如何组织？接口契约？长期怎么维护？"
>
> **更新频率**: 代码结构变更时持续演进
>
> **详细文档**: `docs/plans/2026-08-04-directory-structure-recommendations.md`（475行完整版）

---

## 1. 代码架构分层

> **原则**: 每层只依赖下一层，不可跨层调用。

```
API Layer (api/)          ← 接入层：HTTP路由，参数校验
    ↓
Orchestrator (orchestrator.py)  ← 编排层：串联流程
    ↓
Service Layer (services/) ← 业务逻辑：核心业务规则
    ↓
Model Layer (models/)     ← 数据契约：Pydantic 模型（唯一真相源）
    ↓
State Layer (state/)      ← 持久层：SQLite / JSON 存储
```

### 当前状态

| 层 | 目录 | 文件数 | 问题 |
|---|------|--------|------|
| API | `app/api/` | 6个路由文件 | ✅ 清晰 |
| 编排 | `app/orchestrator.py` | 1个文件 | ✅ 清晰 |
| Service | `app/services/` | 12个扁平文件 | 🔴 **核心问题**：无领域边界，详见下方 §2 |
| Model | `app/models/` | 17个文件 | 🟡 基本清晰，可按域归类 |
| State | `app/state/` | 4个文件 | ✅ 清晰 |
| AI | `app/ai/` | 10个文件 | 🟡 provider 抽象好，prompt 模板可独立 |

---

## 2. 目录结构规范

### 2.1 当前结构（问题）

```
app/services/                    ← 12个文件扁平堆放
  seed_engine.py
  backward_generator.py
  gap_detector.py
  cycle_checker.py               ← 以上4个属于"种子域"
  dimension_generator.py
  rule_mapper.py                 ← 以上2个属于"约束域"
  generation_scheduler.py
  generation_planner.py
  prompt_builder.py
  prompt_fusion.py               ← 以上4个属于"资产域"
  graph_extractor.py             ← 图谱域
```

### 2.2 目标结构（按领域拆分）

> **详细方案**: [[plans/2026-08-04-directory-structure-recommendations]]

```
app/domains/                     ← 按业务域组织
  creation/                      ← 创作工具域
    seed/                        ← 种子引擎
      seed_engine.py
      backward_generator.py
      gap_detector.py
      cycle_checker.py
    constraint/                  ← 6维约束
      dimension_generator.py
      rule_mapper.py
    asset/                       ← 资产管线
      generation_scheduler.py
      generation_planner.py
      prompt_builder.py
      prompt_fusion.py
    graph/                       ← 图谱服务
      graph_extractor.py
    module/                      ← 模组系统（新建）
      inheritor.py
      exporter.py
      filter.py
    gm_runtime/                  ← AI GM运行时（新建）
      assistant_mode.py
      auto_mode.py
      tutorial_mode.py
      emotion_fuse.py
      case_cache.py
  community/                     ← 社区域（远期）
```

### 2.3 迁移计划

| 阶段 | 内容 | 优先级 | 状态 |
|------|------|--------|------|
| Phase 0 | 不动现有代码，只在新增文件时按目标结构放 | P0 | ✅ 已完成 |
| Phase 1 | services/ → domains/ 批量迁移 + import 修正 | P2 | ✅ 已完成 (2026-08-04) |
| Phase 2 | models/ 按域归类 | P3 | ⚪ |

> **填写指引**: 确定迁移策略：是渐进式（新文件按新结构，旧文件不动）还是一次性迁移？

---

## 3. API 契约规范

### 3.1 已有 API 端点

> **完整清单**: [项目 README](../../README.md) API 端点总览章节

| 模块 | 前缀 | 文件 | 状态 |
|------|------|------|------|
| 交互终端 | `/api/action`, `/api/scene`, `/api/state` | `routes.py` | ✅ |
| 知识图谱 | `/api/graph/*` | `graph_routes.py` | ✅ |
| 资产管理 | `/api/assets/*`, `/api/scenes/*` | `assets_routes.py` | ✅ |
| 种子系统 | `/api/seed/*` | `seed_routes.py` | ✅ |
| 约束体系 | `/api/constraints/*` | `constraints_routes.py` | ✅ |

### 3.2 待建 API

| 模块 | 预期端点 | 优先级 | 对应断点 |
|------|---------|--------|---------|
| 图谱列表 | `GET /api/graph/list` | P0 | 断点I |
| StoryGraph CRUD | `/api/story/*` | P1 | 断点H |
| EventGraph CRUD | `/api/event/*` | P1 | 断点H |
| CultureTree CRUD | `/api/culture/*` | P1 | 断点H |
| ConstraintTree CRUD | `/api/constraint-tree/*` | P1 | 断点H |
| SceneGraph CRUD | `/api/scene-graph/*` | P1 | 断点H |
| 模组装订 | `POST /api/module/export` | P2 | 模组系统 |
| GM运行时 | `/api/gm/*` | P2 | GM系统 |
| <!-- 补充更多 --> | | | |

### 3.3 API 设计规范

| 规则 | 说明 |
|------|------|
| 路径风格 | RESTful，kebab-case：`/api/graph-assets` |
| 响应格式 | 统一 JSON，Pydantic 模型驱动 |
| 错误格式 | HTTP 状态码 + `{ "detail": "..." }` |
| 分页 | `?offset=0&limit=20` |
| 版本化 | <!-- 填写: 是否需要 /api/v1/ 前缀？当前无版本 --> |
| 认证 | <!-- 填写: 当前无认证，社区系统需要 JWT --> |

---

## 4. 数据契约规范

### 4.1 核心原则

> **Pydantic 模型是唯一数据契约源。** 所有 API 请求/响应、服务间传递、持久化，都以 `models/` 下的 Pydantic 模型为准。

### 4.2 模型清单

> **完整版**: [[SYSTEM_DESIGN_SPEC_v4]] §5 领域模型字典

| 模型 | 文件 | 用途 |
|------|------|------|
| KnowledgeGraph | `models/knowledge_graph.py` | 核心知识图谱 |
| StoryGraph | `models/story_graph.py` | 剧情分支图 |
| EventGraph | `models/event_graph.py` | 动态事件图 |
| PuzzleGraph | `models/puzzle_graph.py` | 谜题依赖图 |
| CultureTree | `models/culture.py` | 递归文化树 |
| ConstraintTree | `models/constraint.py` | 约束树 |
| DimensionResultSet | `models/dimension.py` | 6维约束输出 |
| ConceptNode | `models/concept.py` | 种子概念 |
| Asset | `models/asset.py` | 资产状态机 |
| Player | `models/player.py` | 玩家状态 |

---

## 5. 编码规范

### 5.1 后端 (Python)

| 规则 | 工具 | 状态 |
|------|------|------|
| 代码风格 | ruff | ✅ 已配置 |
| 类型检查 | mypy | ✅ 已配置 |
| 测试框架 | pytest + pytest-cov | ✅ 已配置 |
| BDD | pytest-behave | ✅ 已配置 |
| 变异测试 | mutmut | ✅ 已配置 |
| 覆盖率目标 | 总体≥85%，规则引擎≥95% | <!-- 填写: 当前实际覆盖率 --> |

### 5.2 前端 (TypeScript)

| 规则 | 工具 | 状态 |
|------|------|------|
| 代码风格 | oxlint | ✅ 已配置 |
| 类型检查 | tsc (strict) | ✅ 已配置 |
| 测试框架 | Vitest + Playwright | ✅ 已配置 |
| 构建工具 | Vite | ✅ 已配置 |

### 5.3 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| Python 文件 | snake_case | `seed_engine.py` |
| Python 类 | PascalCase | `SeedEngine` |
| Python 函数 | snake_case | `generate_seed()` |
| TS 文件 | PascalCase（组件）/ camelCase（工具） | `GraphEditor.tsx` / `client.ts` |
| TS 组件 | PascalCase | `GraphEditor` |
| TS 函数 | camelCase | `generateAsset()` |
| API 路径 | kebab-case | `/api/graph-assets` |
| 数据库表 | snake_case | `knowledge_graphs` |
| 环境变量 | UPPER_SNAKE | `OPENAI_API_KEY` |

---

## 6. Git 规范

| 规则 | 说明 | 状态 |
|------|------|------|
| 分支命名 | `feature/xxx`、`fix/xxx`、`docs/xxx` | <!-- 填写: 实际使用情况 --> |
| Commit 格式 | <!-- 填写: Conventional Commits? 自由格式? --> | |
| CI/CD | GitHub Actions | ✅ 已配置 |
| PR 流程 | <!-- 填写: 是否需要 PR review? --> | |

---

## 7. 测试规范

### 7.1 测试金字塔

| 层级 | 工具 | 范围 | 目标覆盖率 | 当前 |
|------|------|------|-----------|------|
| 单元测试 | pytest | models / engine / services | ≥85% | <!-- 填写 --> |
| BDD | pytest-behave | 关键用户流程 | 关键路径全覆盖 | <!-- 填写 --> |
| 集成测试 | pytest | API 端到端 | <!-- 填写 --> | <!-- 填写 --> |
| 变异测试 | mutmut | 规则引擎 | ≥80% | <!-- 填写 --> |
| 前端 E2E | Playwright | 图谱编辑器 + 资产生成 | 关键页面 | ✅ 有基础 |
| 前端单元 | Vitest | 组件/hooks | <!-- 填写 --> | <!-- 填写 --> |

### 7.2 测试文件组织

```
backend/tests/
  unit/           ← 单元测试（按模块）
  integration/    ← 集成测试（跨模块）
  models/         ← 模型测试
  features/       ← BDD Gherkin 特性文件
```

---

## 8. 部署规范

| 项目 | 方式 | 状态 |
|------|------|------|
| 本地开发 | `start.ps1` 一键启动 | ✅（路径硬编码待修，断点J） |
| Docker | `docker-compose.yml` + `docker-compose.production.yml` | ✅ 已有 |
| 生产部署 | `deploy.ps1` | ✅ 已有 |
| 反向代理 | nginx | ✅ 已有 `nginx.conf` |
| <!-- 补充: CI/CD 部署流程 --> | | |
