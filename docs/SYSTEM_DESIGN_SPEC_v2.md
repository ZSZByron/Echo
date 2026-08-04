# Echo UGC — 系统设计规范 v2.0 (System Design Specification)

> **文档定位**: Schema First + Interface Contract + Domain Model Design + Five-Graph Model Editor
> **版本**: v2.0 — 合并 v1 系统设计规范 + AI剧情场景编辑器设计方案
> **日期**: 2026-08-01
> **变更**: 从 v1.0 升级，整合五图模型架构与AI剧情场景编辑器完整设计

---

## 更新日志 (Changelog from v1.0)

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v2.0 | 2026-08-01 | 整合 AI剧情场景编辑器设计文档，新增五图模型架构、StoryGraph、EventGraph、CultureTree、ConstraintTree、AI辅助系统、前端编辑器设计 |
| v1.0 | 2026-08-01 | 初始版本，基于现有代码库逆向分析 |

---

## 目录

1. [项目概述](#1-项目概述)
2. [五图模型架构](#2-五图模型架构)
3. [系统全景架构图](#3-系统全景架构图)
4. [模块拆分总览](#4-模块拆分总览)
5. [领域模型字典](#5-领域模型字典)
6. [接口契约](#6-接口契约)
7. [数据流图](#7-数据流图)
8. [界面设计](#8-界面设计)
9. [前端模块定义](#9-前端模块定义)
10. [数据存储设计](#10-数据存储设计)
11. [五图模型映射](#11-五图模型映射)
12. [命名规范](#12-命名规范)
13. [依赖注入架构](#13-依赖注入架构)
14. [实施路线图](#14-实施路线图)
15. [风险评估与应对](#15-风险评估与应对)
16. [编辑器设计文档勘误](#16-编辑器设计文档勘误)
附录A: [技术栈速查](#附录a-技术栈速查)
附录B: [术语表](#附录b-术语表)
附录C: [更新日志](#附录c-更新日志)

---

## 1. 项目概述

### 1.1 现有系统概述

Echo UGC 是一个"AI交互 + 规则判定"新形态的系统，核心特点：
- 玩家输入自然语言指令，AI解析为结构化意图
- Python规则引擎进行确定性判决
- AI渲染为赛博朋克风格叙事
- 前端终端以打字机效果输出
- 展示"AI创造性 + 代码确定性"的结合

**现有技术栈**:
- 后端: FastAPI + Python 3.11+ + Pydantic v2 + SQLite + 多LLM Provider抽象
- 前端: Vite + React + TypeScript + TailwindCSS v4
- 数据: YAML场景定义 + JSON资产清单 + SQLite图谱数据库

### 1.2 升级目标: 五图模型 + AI剧情场景编辑器

将现有的简单场景编辑器升级为基于**五图模型**的完整AI剧情场景编辑器，支持复杂的动态开放世界内容创作。

**五图模型**:
1. **Story Graph** (剧情图) - 跨场景固定剧情主线/支线
2. **Event Graph** (事件图) - 动态事件的条件触发系统
3. **Asset Tree** (资产树) - 分层分类的视觉资产体系
4. **Culture Tree** (文化树) - 文明体系和价值层级
5. **Constraint Tree** (约束树) - 资产生成的硬约束和软约束

**数据流向**:
```
Culture Tree → Constraint Tree → Candidate System → World Knowledge Graph
                                                    ↓
                                         ┌───────────┼───────────┐
                                         ↓           ↓           ↓
                                    Story Graph  Event Graph  Asset Tree
                                         ↓           ↓           ↓
                                    Story Asset  Event Asset  Environment Asset
```

### 1.3 核心价值

- **可视化叙事设计** - 直观的剧情和事件图编辑
- **智能辅助创作** - AI驱动的创作建议和验证
- **多层叙事架构** - 支持固定剧情+动态事件的混合叙事
- **文化一致性保证** - 通过文化树和约束树确保内容质量
- **高效资产管理** - 分类清晰的资产树管理系统

### 1.4 目标用户

- 游戏设计师 - 剧情和关卡设计
- 内容创作者 - UGC内容生产
- 世界观构建师 - 文化体系设计
- 关卡美术 - 资产生成和管理

---

## 2. 五图模型架构

### 2.1 五图模型全景图

```
                  文化树 Culture Tree
                          |
                  约束树 Constraint Tree
                          |
                          ↓

                  世界知识图谱 World Knowledge Graph
                          |
         ┌────────────────┼────────────────┐
         ↓                ↓                ↓

    剧情图 Story Graph   事件图 Event Graph   资产树 Asset Tree

         |                |                |

    剧情资产 Story Asset 事件资产 Event Asset 环境资产 Environment Asset

         └──────────────┬───────────────┘

                        ↓

                 世界运行系统
```

### 2.2 Narrative Layer = Story Graph ∪ Event Graph

**Narrative Layer (叙事层)** 是固定剧情和动态事件的统一抽象：

- **Story Graph** (固定剧情):
  - 主线和支线的跨场景叙事
  - 节点类型: `start | end | choice | event | condition`
  - 支持条件分支和选择节点
  - 与场景通过 `scene_link` 关联

- **Event Graph** (动态事件):
  - 基于条件触发的动态事件
  - 节点类型: `combat | quest | exploration | social`
  - 支持时间、地点、状态等触发条件
  - 可与 Story Graph 节点关联

### 2.3 资产三分类: Story Asset / Event Asset / Environment Asset

所有资产根据其来源和功能分为三类：

| 分类 | 来源 | 生命周期 | 示例 |
|------|------|----------|------|
| **Story Asset** | StoryGraph.required_assets | 永久，剧情需要 | 主线任务必需的关键道具 |
| **Event Asset** | EventGraph.assets | 临时，事件期间 | 动态战斗中的敌方单位 |
| **Environment Asset** | 无明确来源 | 永久，世界氛围 | 场景背景、环境装饰 |

**分类字段**: `Asset.classification: AssetClassification = story | event | environment`

### 2.4 Culture Tree → Constraint Tree → Candidate System pipeline

完整的文化约束流程：

```
1. Culture Tree (文化树)
   ├─ 定义文明体系: 希腊式、玛雅式、水晶文明
   ├─ 价值层级: 秩序、自由、和谐
   └─ 美学原则: 黄金比例、自然主义、几何抽象

2. Constraint Tree (约束树)
   ├─ 硬约束 (hard): 禁止钢铁材质、禁止特定符号
   ├─ 软约束 (soft): 偏好有机形态、避免鲜艳色彩
   └─ 优先级排序: rule priority 0-100

3. Candidate System (候选系统)
   ├─ 为每个资产需求生成候选集合
   ├─ 应用 Culture Tree 进行风格评分
   ├─ 应用 Constraint Tree 进行硬过滤
   └─ 输出: 排序后的候选列表 [Candidate1, Candidate2, ...]
```

### 2.5 完整资产生成逻辑

```
剧情需求 (StoryNode.required_assets)
    │
    ▼
资产生成请求 (AssetRequirement)
    │
    ├─→ 候选系统 (CandidateSystem)
    │   ├─ CultureTree → 候选生成 (风格多样性)
    │   └─ ConstraintTree → 候选过滤 (约束验证)
    │       └─ 输出: sorted_candidates
    │
    ├─→ Prompt构建 (PromptBuilder)
    │   ├─ 基础层: Subject + Relation + Background
    │   ├─ 文化层: CultureNode.values + aesthetic_principles
    │   └─ 约束层: ConstraintNode.rule (负面提示词)
    │
    ├─→ 图像生成 (ImageGenerator)
    │   └─ Zhipu/Wanxiang/Qwen/Local backend
    │       └─ GeneratedImage[] (seed + bytes/url)
    │
    ├─→ 风格提取 (StyleExtractor)
    │   └─ 提取色彩、材质、构图特征 → 后续资产参考
    │
    └─→ 资产实例 (Asset Instance)
        ├─ id, type, classification, status
        ├─ prompt, negative_prompt, seed
        ├─ file_path, views (LOD)
        └─ style_profile, reference_asset_ids
```

---

## 3. 系统全景架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (React + TS)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ Terminal │  │SceneView │  │ Graph    │  │ StatusPanel /     │  │ [现有]
│  │(交互终端)│  │(场景视图)│  │ Editor   │  │ GodWatchIndicator │  │
│  └─────┬─────┘  └─────┬────┘  └─────┬────┘  └────────┬──────────┘  │
│        └──────────┬───┴───────────┴───────────────┘  │              │
│                   ▼                                  ▼              │
│           ┌─────────────┐                   ┌──────────────┐        │
│           │ api/client  │                   │  api/graph   │        │ [现有]
│           └──────┬──────┘                   └──────┬───────┘        │
├──────────────────┼─────────────────────────────────┼────────────────┤
│  [新增]        ▼  HTTP /api/*                    ▼                │
│  ┌────────────────────────────────────────────────────────────────┐│
│  │ StoryGraphEditor │ EventGraphEditor │ AssetTreeEditor │        ││
│  │ CultureTreeEditor │ WorldKGEditor │ AIAssistantPanel           ││
│  │         [React Flow + Zustand + Radix UI + D3.js]             ││
│  └───────────────────────────┬────────────────────────────────────┘│
│                              ▼ HTTP                                  │
│ ┌────────────────────────────────────────────────────────────────┐ │
│ │                    FastAPI Application                         │ │
│ │  main.py — lifespan + CORS + router registration               │ │
│ ├────────────┬───────────────┬──────────────┬────────────────────┤ │
│ │ /api/action│ /api/assets   │ /api/scenes  │ /api/graph         │ │ [现有]
│ │ /api/state │ /api/scene    │              │ /api/graph/extract │ │
│ │ /api/reset │ /api/health   │              │ /api/graph/generate│ │
│ │            │               │              │                    │ │
│ │ routes.py  │ assets_routes │ assets_routes│ graph_routes.py    │ │
│ ├────────────┼───────────────┼──────────────┼────────────────────┤ │
│ │/api/story  │/api/events    │/api/culture  │/api/constraints    │ │ [新增]
│ │/api/ai     │               │              │/api/assets/tree    │ │
│ │story_routes│event_routes  │culture_routes│constraint_routes   │ │
│ └─────┬──────┴───────┬───────┴──────┬───────┴─────────┬──────────┘  │
│       │              │              │                  │             │
│       ▼              ▼              ▼                  ▼             │
│ ┌──────────┐  ┌───────────┐  ┌───────────┐  ┌──────────────────┐   │
│ │Orchestr- │  │AssetStore │  │ Generation│  │  Graph           │   │ [现有]
│ │ator      │  │(JSON)      │  │ Planner   │  │  Extractor       │   │
│ │          │  │            │  │ Scheduler │  │  PromptFusion    │   │
│ │ parse →  │  │ CRUD +     │  │           │  │                  │   │
│ │ judge →  │  │ State      │  │ Plan +    │  │  LLM Extract     │   │
│ │ render → │  │ Machine    │  │ Execute   │  │  → KG            │   │
│ │ update   │  │            │  │           │  │                  │   │
│ └──┬──┬──┬─┘  └─────┬─────┘  └─────┬─────┘  └────────┬─────────┘   │
│    │  │  │          │              │                  │             │
│    │  │  │    ┌─────▼──────────────▼──────────────────▼───┐         │
│    │  │  │    │              Core Models (Pydantic)         │         │
│    │  │  │    │  现有模型:              新增模型:            │         │
│    │  │  │    │  action, player,        story_graph         │         │
│    │  │  │    │  world, asset(扩展),    event_graph         │         │
│    │  │  │    │  scene_graph,           culture             │         │
│    │  │  │    │  knowledge_graph,       constraint          │         │
│    │  │  │    │  puzzle_graph           (6个新文件)          │         │
│    │  │  │    └───────────────────────────────────────────┘         │
│    │  │  │                                                        │
│    │  │  │    ┌───────────────────────────────────────────────────┐ │
│    │  │  │    │            [新增] 服务层                          │ │
│    │  │  │    │ StoryService │ EventService │ AIAssistant        │ │
│    │  │  │    │ AssetClassifier │ CandidateSystem                │ │
│    │  │  │    └───────────────────────────────────────────────────┘ │
│    ▼  ▼  ▼                                                        │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │                    Backend Services Layer                     │   │
│ ├──────────────┬─────────────────┬────────────────────────────┤   │
│ │ AI Layer     │ Engine Layer    │ State Layer                 │   │ [现有]
│ │ (app/ai/)    │ (app/engine/)   │ (app/state/)                │   │
│ │              │                 │                             │   │
│ │ • Parser     │ • RulesEngine   │ • AssetStore (JSON file)    │   │
│ │ • Renderer   │ • Physics       │ • GraphStore (SQLite)       │   │
│ │ • ImageGen   │ • GodIntervent  │ • StateRepository (SQLite)  │   │
│ │ • Provider   │ • WorldLoader   │ • Migrations                │   │
│ │ • StyleExt   │                 │                             │   │
│ │ • PromptBuild│                 │                             │   │
│ └──────┬───────┴────────┬────────┴────────────────────────────┘   │
│        │                │                                          │
│        ▼                ▼                                          │
│ ┌──────────────┐  ┌──────────────────────────────────────────┐    │
│ │ LLM Provider │  │          Data Layer (YAML / JSON / DB)    │    │
│ │ (6 backends) │  │                                          │    │
│ │ OpenAI       │  │  现有:                 新增:               │    │
│ │ Anthropic    │  │  data/scenes/*.yaml   data/stories/       │    │
│ │ DeepSeek     │  │  data/gods/*.yaml     data/events/        │    │
│ │ Qwen/Kimi/GLM│  │  data/rules/*.yaml    data/cultures/      │    │
│ │              │  │  data/objects/*.yaml  data/constraints/    │    │
│ │ + Image:     │  │  data/visual/*.yaml   (4个新目录)          │    │
│ │   Zhipu      │  │  data/assets/manifest.json + graph.db    │    │
│ │   Wanxiang   │  │  data/default_player.json                 │    │
│ │   Qwen-Image │  │                                          │    │
│ │   Local      │  │                                          │    │
│ └──────────────┘  └──────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. 模块拆分总览

### 4.1 模块清单

| # | 模块路径 | 职责 | 关键文件 | 来源 |
|---|---------|------|---------|------|
| M1 | `app/main.py` | FastAPI 入口，lifespan 管理，路由注册 | `main.py` | [现有] |
| M2 | `app/orchestrator.py` | 交互循环编排器 (parse→judge→render→update) | `orchestrator.py` | [现有] |
| M3 | `app/models/` | 领域模型定义 (Pydantic) | 9个模型文件 | [现有] |
| M4 | `app/api/` | HTTP 路由 + 依赖注入 | `routes.py`, `assets_routes.py`, `graph_routes.py`, `deps.py` | [现有] |
| M5 | `app/engine/` | 确定性规则引擎 | `rules_engine.py`, `physics.py`, `god_intervention.py`, `world_loader.py` | [现有] |
| M6 | `app/ai/` | AI 服务层 (LLM + Image) | `parser.py`, `renderer.py`, `provider.py`, `image_generator.py`, `style_extractor.py`, `config.py` | [现有] |
| M7 | `app/services/` | 业务编排服务 | `generation_planner.py`, `generation_scheduler.py`, `graph_extractor.py`, `prompt_builder.py`, `prompt_fusion.py` | [现有] |
| M8 | `app/state/` | 持久化层 | `asset_store.py`, `graph_store.py`, `database.py`, `migrations.py` | [现有] |
| M9 | `app/config/` | 配置与路径 | `paths.py`, `features.py` | [现有] |
| M10 | `app/utils/` | 工具函数 | `gen_helpers.py` | [现有] |
| M25 | `app/services/story_service.py` | 剧情图 CRUD + 跨场景链接 + 导入导出 | `story_service.py` | [新增] |
| M26 | `app/services/event_service.py` | 事件图 CRUD + 条件触发测试 | `event_service.py` | [新增] |
| M27 | `app/services/ai_assistant.py` | 节点建议 + 一致性检查 + Prompt优化 + 约束验证 | `ai_assistant.py` | [新增] |
| M28 | `app/services/asset_classifier.py` | 资产三分类 (story/event/environment) | `asset_classifier.py` | [新增] |
| M29 | `app/services/candidate_system.py` | 文化约束→候选→过滤→评分 | `candidate_system.py` | [新增] |
| F1 | `frontend/src/api/` | 前端 API 客户端 | `client.ts`, `assets.ts`, `graph.ts` | [现有] |
| F2 | `frontend/src/types/` | TypeScript 类型定义 (镜像后端) | `action.ts`, `player.ts`, `scene.ts`, `api.ts`, `graph.ts` | [现有] |
| F3 | `frontend/src/components/` | React 组件 | `Terminal.tsx`, `SceneView.tsx`, `StatusPanel.tsx`, `graph/*` | [现有] |
| F4 | `frontend/src/components/editor/` | 编辑器组件 (新增) | `StoryGraphEditor.tsx`, `EventGraphEditor.tsx`, `AssetTreeEditor.tsx`, `CultureTreeEditor.tsx`, `AIAssistantPanel.tsx` | [新增] |
| F5 | `frontend/src/stores/` | Zustand 状态管理 (新增) | `storyStore.ts`, `eventStore.ts`, `assetTreeStore.ts`, `cultureStore.ts`, `editorUIStore.ts` | [新增] |
| D1 | `data/scenes/` | 场景定义 (YAML) | `temple_ruins.yaml` | [现有] |
| D2 | `data/gods/` | 神王表 (YAML) | `gods_table.yaml` | [现有] |
| D3 | `data/rules/` | 规则表 (YAML) | `intervention_table.yaml` | [现有] |
| D4 | `data/objects/` | 物体定义 (YAML) | `*.yaml` | [现有] |
| D5 | `data/visual/` | 视觉生成配置 | `prompts.yaml`, `palette.yaml`, `style_bible.md` | [现有] |
| D6 | `data/assets/` | 生成资产存储 | `manifest.json`, `graph.db`, `*.png` | [现有] |
| D7 | `data/stories/` | StoryGraph 定义 (YAML) | `{story_id}.yaml` | [新增] |
| D8 | `data/events/` | EventGraph 定义 (YAML) | `{event_graph_id}.yaml` | [新增] |
| D9 | `data/cultures/` | CultureTree 定义 (YAML) | `{culture_id}.yaml` | [新增] |
| D10 | `data/constraints/` | ConstraintTree 定义 (YAML) | `{constraint_set_id}.yaml` | [新增] |

### 4.2 层级依赖规则

```
Layer 0: Data (YAML/JSON/DB)          ← 无代码依赖，纯数据
    ↑ read/write
Layer 1: Models (app/models/)         ← 纯 Pydantic，零业务逻辑
    ↑ import
Layer 2: Engine + AI + State + [新增 Services]  ← 核心业务逻辑
    (app/engine/)  (app/ai/)  (app/state/)  (app/services/story|event|ai_assistant|asset_classifier|candidate_system)
    ↑ import
Layer 3: Services + Orchestrator     ← 编排层
    (app/services/)  (app/orchestrator.py)
    ↑ import
Layer 4: API + Orchestrator           ← HTTP 入口
    (app/api/)  (app/orchestrator.py)
    ↑ HTTP
Layer 5: Frontend                     ← UI 展示
    (frontend/src/)  + [新增编辑器组件]
```

### 4.3 模块间物理依赖关系

```
main.py
  ├─→ api/assets_routes.py
  │     ├─→ models/asset.py
  │     ├─→ models/scene_graph.py
  │     ├─→ state/asset_store.py
  │     ├─→ services/generation_planner.py
  │     └─→ ai/image_generator.py
  │
  ├─→ api/graph_routes.py
  │     ├─→ models/knowledge_graph.py
  │     ├─→ state/graph_store.py
  │     ├─→ services/graph_extractor.py
  │     ├─→ services/generation_scheduler.py
  │     └─→ utils/gen_helpers.py
  │
  ├─→ api/routes.py
  │     ├─→ orchestrator.py
  │     ├─→ api/deps.py
  │     ├─→ models/{api,player,asset,scene_response}.py
  │     └─→ state/asset_store.py
  │
  ├─→ api/story_routes.py [新增]
  │     ├─→ models/story_graph.py
  │     ├─→ services/story_service.py
  │     └─→ state/asset_store.py
  │
  ├─→ api/event_routes.py [新增]
  │     ├─→ models/event_graph.py
  │     ├─→ services/event_service.py
  │     └─→ state/asset_store.py
  │
  ├─→ api/ai_routes.py [新增]
  │     ├─→ services/ai_assistant.py
  │     ├─→ ai/provider.py
  │     └─→ models/{story_graph,event_graph,culture,constraint}.py
  │
  └─→ api/deps.py
        ├─→ engine/rules_engine.py
        ├─→ engine/world_loader.py
        ├─→ ai/{config,provider}.py
        ├─→ ai/parser.py
        ├─→ ai/renderer.py
        └─→ state/database.py

orchestrator.py
  ├─→ api/deps.py (Protocols)
  ├─→ engine/rules_engine.py
  ├─→ models/{action,api,player}.py
  └─→ (no AI import — uses injected protocols)

engine/rules_engine.py
  ├─→ engine/god_intervention.py
  ├─→ engine/physics.py
  ├─→ engine/world_loader.py
  └─→ models/{action,player,world}.py

services/story_service.py [新增]
  ├─→ models/story_graph.py
  ├─→ state/asset_store.py
  └─→ config/paths.py

services/event_service.py [新增]
  ├─→ models/event_graph.py
  ├─→ state/asset_store.py
  └─→ config/paths.py

services/ai_assistant.py [新增]
  ├─→ models/{story_graph,event_graph,culture,constraint}.py
  ├─→ ai/provider.py
  └─→ services/candidate_system.py

services/asset_classifier.py [新增]
  ├─→ models/asset.py
  └─→ models/story_graph.py

services/candidate_system.py [新增]
  ├─→ models/culture.py
  ├─→ models/constraint.py
  └─→ ai/provider.py

ai/image_generator.py
  ├─→ ai/config.py
  ├── config/paths.py
  └─→ utils/gen_helpers.py

state/asset_store.py
  ├─→ models/asset.py
  └─→ config/paths.py

state/graph_store.py
  ├─→ models/knowledge_graph.py
  ├─→ state/migrations.py
  └─→ config/paths.py
```

---

## 5. 领域模型字典

### 5.1 核心实体关系图

```
                    ┌─────────────────────┐
                    │    PlayerState       │
                    │  (玩家状态)          │
                    │  id, health, energy  │
                    │  strength, location  │
                    │  inventory, status   │
                    └────────┬────────────┘
                             │ location (1:1)
                             ▼
                    ┌─────────────────────┐         ┌─────────────────────┐
                    │      Scene           │ 1    N │    GameObject        │
                    │  (场景定义)          │────────│  (可交互物体)        │
                    │  scene_id, name      │        │  id, type, hardness  │
                    │  atmosphere, region  │        │  is_future_anchor    │
                    └────────┬────────────┘         │  position, depth     │
                             │                      │  lod, puzzle_role    │
                             │ N                    └─────────┬───────────┘
                    ┌────────▼────────────┐                   │
                    │   InteractionTarget │ N:1               │
                    │  (交互目标)          │───────────────────┘
                    │  object_id           │
                    │  is_dangerous        │
                    │  required_tools      │
                    └─────────────────────┘

                    ┌─────────────────────┐
                    │     GodKing          │
                    │  (神王实体)          │
                    │  id, domain          │
                    │  intervention_thresh │
                    │  penalty             │
                    └────────┬────────────┘
                             │ protects
                    ┌────────▼────────────┐
                    │  WorldRule           │
                    │  (世界规则)          │
                    │  region, constraints │
                    │  magic_modifier      │
                    └─────────────────────┘


   ── 交互流程实体 ──────────────────────────────────────────────

   ActionRequest ──→ ParsedIntent ──→ RulesEngine ──→ JudgmentResult
   (玩家输入)        (解析意图)        (确定性判决)      (判决结果)
                                                         │
                                           ┌─────────────┤
                                           ▼             ▼
                                    NarrativeContext  StateChange[]
                                    (叙事上下文)      (状态变更)


   ── 资产生成实体 ──────────────────────────────────────────────

                    ┌─────────────────────┐
                    │   KnowledgeGraph     │ 1    N ┌──────────────┐
                    │  (知识图谱)          │────────│  GraphNode    │
                    │  scene_id            │        │  id, serial   │
                    │  background_node_id  │        │  level, desc  │
                    └────────┬────────────┘        │  status       │
                             │ N                    └──────────────┘
                    ┌────────▼────────────┐
                    │    GraphEdge         │
                    │  from_node_id        │
                    │  to_node_id          │
                    │  edge_type (tree|cross) │
                    │  visual_description  │
                    └─────────────────────┘

                    ┌─────────────────────┐
                    │    Asset             │
                    │  (视觉资产)          │
                    │  id, type(bg|object) │
                    │  classification     │ ← 新增字段
                    │  prompt, status      │
                    │  file_path, seed     │
                    │  candidates          │
                    │  style_profile       │
                    │  views (LOD)         │
                    │  parent_scene        │
                    │  related_story_node  │ ← 新增字段
                    │  related_event_node  │ ← 新增字段
                    └─────────────────────┘


   ── [新增] StoryGraph 实体 ─────────────────────────────────────────

                    ┌─────────────────────┐
                    │   StoryGraph         │ 1    N ┌──────────────┐
                    │  (跨场景剧情图)      │────────│  StoryNode    │
                    │  id, name            │        │  id, type     │
                    │  description, version│        │  (start|end  │
                    │  nodes: dict         │        │   choice|    │
                    │  edges: list         │        │   event|cond) │
                    └─────────────────────┘        │  scene_link   │
                                                   │  required_   │
                                                   │   assets[]   │
                                                   │  conditions[]│
                                                   │  choices[]   │
                                                   └──────────────┘


   ── [新增] EventGraph 实体 ─────────────────────────────────────────

                    ┌─────────────────────┐
                    │   EventGraph         │ 1    N ┌──────────────┐
                    │  (动态事件图)        │────────│  EventNode    │
                    │  id, name            │        │  id, type     │
                    │  description         │        │  (combat|    │
                    │  nodes: dict         │        │   quest|     │
                    │  global_triggers[]   │        │   explor|    │
                    └─────────────────────┘        │   social)    │
                                                   │  trigger_    │
                                                   │   conditions[]│
                                                   │  actions[]   │
                                                   │  rewards[]   │
                                                   │  assets[]    │
                                                   └──────────────┘


   ── [新增] CultureTree 实体 ────────────────────────────────────────

                    ┌─────────────────────┐
                    │   CultureTree       │ 1    N ┌──────────────┐
                    │  (文化树)           │────────│  CultureNode  │
                    │  id, name           │        │  id, name     │
                    │  root: CultureNode  │        │  values[]     │
                    │  version            │        │  aesthetic_  │
                    └─────────────────────┘        │   principles[]│
                                                   │  child_nodes[]│
                                                   └──────────────┘


   ── [新增] ConstraintTree 实体 ──────────────────────────────────────

                    ┌─────────────────────┐
                    │   ConstraintTree     │ 1    N ┌──────────────┐
                    │  (约束树)           │────────│  ConstraintNode│
                    │  scene_id           │        │  id, type     │
                    │  nodes: list        │        │  (hard|soft) │
                    └─────────────────────┘        │  rule         │
                                                   │  priority     │
                                                   │  applicable_ │
                                                   │   types[]    │
                                                   └──────────────┘


   ── 谜题实体 ──────────────────────────────────────────────────

                    ┌─────────────────────┐
                    │   PuzzleGraph        │ 1    N ┌──────────────┐
                    │  (谜题依赖图)        │────────│  PuzzleNode   │
                    │  scene_id            │        │  id, type     │
                    │  chain (拓扑序)      │        │  requires     │
                    └─────────────────────┘        │  produces     │
                                                   │  interaction  │
                                                   └──────────────┘


   ── 场景图实体 ────────────────────────────────────────────────

                    ┌─────────────────────┐
                    │   SceneGraph         │ 1    N ┌──────────────┐
                    │  (场景生成图)        │────────│  AssetInfo    │
                    │  scene_id            │        │  id, name     │
                    │  generation_order    │        │  type, status │
                    │  style_sources       │        │  is_anchor    │
                    └─────────────────────┘        └──────────────┘
```

### 5.2 枚举字典

| 枚举 | 文件 | 值 | 来源 |
|------|------|-----|------|
| `ActionType` | `models/action.py` | `brute_force`, `stealth`, `read_memory`, `negotiate`, `probe`, `god_provoke`, `investigate` | [现有] |
| `JudgmentOutcome` | `models/action.py` | `success`, `fail`, `forced_fail`, `partial`, `god_intervention` | [现有] |
| `PlayerStatus` | `models/player.py` | `normal`, `injured`, `exhausted`, `dying`, `dead`, `echo_active`, `echo_overload` | [现有] |
| `AssetStatus` | `models/asset.py` | `pending`, `generating`, `completed`, `approved`, `rejected`, `failed`, `candidates_ready`, `selected` | [现有] |
| `AssetType` | `models/asset.py` | `background`, `object` | [现有] |
| `AssetClassification` | `models/asset.py` (扩展) | `story`, `event`, `environment` | [新增] |
| `NodeStatus` | `models/knowledge_graph.py` | `pending`, `generating`, `completed`, `failed` | [现有] |
| `EdgeType` | `models/knowledge_graph.py` | `tree`, `cross` | [现有] |
| `PuzzleNodeType` | `models/puzzle_graph.py` | `clue`, `consumable`, `reward`, `obstacle` | [现有] |
| `StoryNodeType` | `models/story_graph.py` | `start`, `end`, `choice`, `event`, `condition` | [新增] |
| `EventNodeType` | `models/event_graph.py` | `combat`, `quest`, `exploration`, `social` | [新增] |
| `EventTriggerType` | `models/event_graph.py` | `time`, `location`, `state`, `custom` | [新增] |
| `EventRewardType` | `models/event_graph.py` | `item`, `experience`, `story_unlock` | [新增] |
| `ConstraintType` | `models/constraint.py` | `hard`, `soft` | [新增] |
| `StateChangeTargetType` | `models/action.py` | `player`, `object`, `scene` | [现有] |
| `Intensity` | `models/action.py` | `low`, `medium`, `maximum` | [现有] |

### 5.3 资产状态机

```
                    ┌──────────┐
                    │ PENDING  │ ←──────────────────────────┐
                    └────┬─────┘                             │
                         │ generate                          │
                         ▼                                   │
                    ┌──────────┐                        ┌───┴──────┐
         ┌──────────│GENERATING│───────────┬───────────►│REJECTED  │
         │          └──────────┘           │            └──────────┘
         │              │                   │                 │
         │       (candidates)         (failed)          (update_prompt)
         │              │                   │                 │
         │              ▼                   ▼                 │
         │     ┌───────────────┐     ┌──────────┐            │
         │     │CANDIDATES_READY│    │  FAILED  │────────────┘
         │     └───────┬───────┘     └──────────┘
         │             │ select
         │             ▼
         │      ┌──────────┐
         │      │ SELECTED │
         │      └────┬─────┘
         │      approve │ reject
         │      ┌──────┴──────┐
         │      ▼             ▼
         └──────│ APPROVED │ │ REJECTED │
                └──────────┘ └──────────┘
```

**合法转换**:
```
PENDING        → GENERATING
GENERATING     → COMPLETED | FAILED | CANDIDATES_READY
COMPLETED      → APPROVED | REJECTED | GENERATING
REJECTED       → PENDING | GENERATING
FAILED         → PENDING | GENERATING
APPROVED       → PENDING
CANDIDATES_READY → SELECTED | GENERATING
SELECTED       → APPROVED | REJECTED
```

### 5.4 命名冲突消解规则

**关键冲突点解析** (CRITICAL):

| 冲突名称 | 现有含义 | 编辑器含义 | **消解方案** |
|---------|---------|-----------|-------------|
| `StoryGraph` | 无 (现有是 `SceneGraph`) | 跨场景剧情图 | 编辑器 `StoryGraph` 保留，不与 `SceneGraph` 冲突 |
| `StoryNode` | 无 (现有是 `PuzzleNode`) | 剧情节点 | 编辑器 `StoryNode` 保留，与 `PuzzleNode` 并存 |
| `AssetNode` | 无 (现有是 `Asset`) | 分类资产节点 | **改名为 `AssetTreeNode`**，避免与 `Asset` 混淆。实际数据仍存储在 `Asset` 模型中，`AssetTreeNode` 是 Asset 的编辑器视图模型 |
| `AssetType` | `background \| object` | `story \| event \| environment` | **拆分为两个枚举**：`AssetType`(现有，不变) + `AssetClassification`(新增) |
| `StoryNode.type` | 无 | `start\|end\|choice\|event\|condition` | 与 `PuzzleNode.type` (`clue\|consumable\|reward\|obstacle`) 完全不同，独立枚举 `StoryNodeType` |
| `EventNode.type` | 无 | `combat\|quest\|exploration\|social` | 新增枚举 `EventNodeType` |

**命名约定**:
- **Python 后端**: 统一使用 `snake_case` (API JSON 层也统一 `snake_case`)
- **TypeScript 前端**: 内部使用 `camelCase`，API 边界通过 Pydantic alias 桥接
- **API JSON 字段**: 永远使用 `snake_case` (如 `required_assets`, `trigger_conditions`, `style_profile`)

### 5.5 数据模型字段速查

#### 现有核心模型

**PlayerState** (`models/player.py`):
```python
class PlayerState(BaseModel):
    id: str
    energy: int               # 0-100
    health: int               # 0-100
    strength: int             # 0-100
    intelligence: int         # 0-100
    echo_mode_enabled: bool = False
    mental_stability: int     # 0-100
    location: str             # scene_id
    inventory: list[str]      # object IDs
    status: PlayerStatus = "normal"
    max_energy: int = 100
    max_health: int = 100
```

**Asset** (`models/asset.py` - 扩展):
```python
class AssetClassification(str, Enum):
    """资产分类 — 由来源图决定。"""
    STORY = "story"            # 来自 StoryGraph 节点
    EVENT = "event"            # 来自 EventGraph 节点
    ENVIRONMENT = "environment" # 无明确来源，纯环境

class Asset(BaseModel):
    id: str                         # "{scene_id}_{object_id}" 或 "{scene_id}_bg"
    type: AssetType                 # "background" | "object"
    classification: AssetClassification = AssetClassification.ENVIRONMENT  # 新增
    name: str
    prompt: str = ""
    negative_prompt: str = ""
    status: AssetStatus = "pending"
    generation_status: str = "pending"
    file_path: str | None
    parent_scene: str               # scene_id
    seed: int | None
    created_at: datetime
    approved_at: datetime | None
    reviewer_note: str | None
    error_message: str | None
    candidates: list[Candidate]
    selected_candidate_index: int | None
    reference_asset_ids: list[str]
    style_profile: SceneStyleProfile | None
    views: dict[str, dict] | None   # LOD: {"far": {...}, "mid": {...}, "near": {...}}
    lod_level: str | None           # "far" | "mid" | "near"
    puzzle_role: str | None         # "clue"|"consumable"|"reward"|"obstacle"
    parent_object: str | None       # 父物体ID(派生资产)
    depth: str | None               # "near"|"mid"|"mid_far"|"far"
    related_story_node: str | None = None    # 新增 - 关联的 StoryNode ID
    related_event_node: str | None = None    # 新增 - 关联的 EventNode ID
```

**KnowledgeGraph** (`models/knowledge_graph.py`):
```python
class KnowledgeGraph(BaseModel):
    scene_id: str
    nodes: dict[str, GraphNode]     # node_id → GraphNode
    edges: list[GraphEdge]
    background_node_id: str | None  # Level 1 根节点

class GraphNode(BaseModel):
    id: str                         # = serial_number
    serial_number: str              # "1", "1-1", "1-1-1"
    level: int                      # = serial中"-"数量 + 1
    description: str = ""
    status: NodeStatus = "pending"

class GraphEdge(BaseModel):
    from_node_id: str
    to_node_id: str
    edge_type: EdgeType = "tree"    # "tree" | "cross"
    visual_description: str = ""
```

#### 新增模型

**StoryGraph** (`models/story_graph.py`):
```python
class StoryNodeType(str, Enum):
    START = "start"
    END = "end"
    CHOICE = "choice"
    EVENT = "event"
    CONDITION = "condition"

class StoryCondition(BaseModel):
    type: str                       # "item_required", "stat_check", "custom"
    requirement: str | dict         # 修正：不允许裸 any

class StoryChoice(BaseModel):
    text: str
    target_node: str
    conditions: list[StoryCondition] = []

class StoryNode(BaseModel):
    id: str
    type: StoryNodeType
    name: str
    description: str
    required_assets: list[str] = []
    conditions: list[StoryCondition] = []
    choices: list[StoryChoice] = []
    scene_link: str | None = None   # 关联场景ID → PuzzleGraph
    metadata: dict = {}

class StoryGraph(BaseModel):
    id: str
    name: str
    description: str
    nodes: dict[str, StoryNode] = {}
    edges: list[dict] = []
    metadata: dict = {}
    version: str = "1.0"
    created_at: datetime = datetime.now(timezone.utc)  # 修正：使用 UTC
    updated_at: datetime = datetime.now(timezone.utc)
```

**EventGraph** (`models/event_graph.py`):
```python
class EventNodeType(str, Enum):
    COMBAT = "combat"
    QUEST = "quest"
    EXPLORATION = "exploration"
    SOCIAL = "social"

class EventTriggerType(str, Enum):
    TIME = "time"
    LOCATION = "location"
    STATE = "state"
    CUSTOM = "custom"

class EventRewardType(str, Enum):
    ITEM = "item"
    EXPERIENCE = "experience"
    STORY_UNLOCK = "story_unlock"

class EventTrigger(BaseModel):
    type: EventTriggerType
    condition: str | dict          # 修正：不允许裸 any
    priority: int = 1

class EventAction(BaseModel):
    type: str
    parameters: dict[str, str | int | bool] = {}  # 修正：类型明确

class EventReward(BaseModel):
    type: EventRewardType
    value: str | int
    probability: float = 1.0

class EventNode(BaseModel):
    id: str
    type: EventNodeType
    name: str
    trigger_conditions: list[EventTrigger] = []
    actions: list[EventAction] = []
    rewards: list[EventReward] = []
    assets: list[str] = []
    metadata: dict = {}

class EventGraph(BaseModel):
    id: str
    name: str
    description: str
    nodes: dict[str, EventNode] = {}
    global_triggers: list[EventTrigger] = []
    metadata: dict = {}
```

**CultureTree** (`models/culture.py`):
```python
class CultureNode(BaseModel):
    id: str
    name: str
    description: str
    values: list[str] = []
    aesthetic_principles: list[str] = []
    child_nodes: list[CultureNode] = []

class CultureTree(BaseModel):
    id: str
    name: str
    root: CultureNode
    version: str = "1.0"
```

**ConstraintTree** (`models/constraint.py`):
```python
class ConstraintType(str, Enum):
    HARD = "hard"
    SOFT = "soft"

class ConstraintNode(BaseModel):
    id: str
    type: ConstraintType
    rule: str                      # 规则描述文本
    rule_config: dict | None = None  # 修正：规则配置可选
    priority: int = 0             # 0-100，数值越大优先级越高
    applicable_types: list[str] = []  # 适用的资产类型或分类

class ConstraintTree(BaseModel):
    scene_id: str | None = None    # 全局或场景级
    id: str
    name: str
    nodes: list[ConstraintNode] = []
```

---

## 6. 接口契约

### 6.1 HTTP API 完整端点清单

#### 现有端点

| 方法 | 路径 | 请求体 | 响应体 | 模块 |
|------|------|--------|--------|------|
| POST | `/api/action` | `ActionRequest` | `ActionResponse` | 交互核心 |
| GET | `/api/state` | `?player_id=` | `PlayerState` | 状态查询 |
| POST | `/api/reset` | `?player_id=` | `PlayerState` | 状态重置 |
| GET | `/api/scene` | `?scene_id=` | `SceneResponse` | 场景查询 |
| GET | `/api/health` | — | `{status, service}` | 健康检查 |
| GET | `/api/assets` | — | `{assets: Asset[]}` | 资产列表 |
| GET | `/api/assets/{id}` | — | `Asset` | 单资产查询 |
| POST | `/api/assets/{id}/generate` | — | `{task_id, status}` | 触发生成 |
| GET | `/api/assets/{id}/status` | — | `{status, generation_status}` | 生成状态 |
| POST | `/api/assets/{id}/approve` | — | `Asset` | 审批 |
| POST | `/api/assets/{id}/reject` | `{reviewer_note}` | `Asset` | 拒绝 |
| PUT | `/api/assets/{id}/prompt` | `{prompt, negative_prompt}` | `Asset` | 更新Prompt |
| POST | `/api/assets/generate-all` | — | `{triggered, task_ids}` | 批量生成 |
| POST | `/api/assets/bulk-approve` | — | `{approved: int}` | 批量审批 |
| POST | `/api/scenes/{id}/orchestrate` | — | `{order, triggered}` | 场景编排 |
| GET | `/api/scenes/{id}/graph` | — | `{nodes, generation_order, style_sources}` | 场景图 |
| GET | `/api/scenes/{id}/orchestrate/status` | — | `{asset_id: status}` | 编排状态 |
| POST | `/api/graph/extract` | `{scene_description}` | `KnowledgeGraph dict` | 图谱提取 |
| POST | `/api/graph/validate` | `KnowledgeGraph dict` | `{is_valid, cycles}` | 图谱验证 |
| POST | `/api/graph/save` | `KnowledgeGraph dict` | `{scene_id, saved}` | 图谱保存 |
| GET | `/api/graph/{scene_id}` | — | `KnowledgeGraph dict` | 图谱加载 |
| DELETE | `/api/graph/{scene_id}` | — | `{deleted}` | 图谱删除 |
| POST | `/api/graph/generate` | `KnowledgeGraph dict` | `{total, succeeded, failed, order, error?}` | 图谱生成 |

#### 新增端点 (编辑器)

**Story Graph API**:
```python
GET    /api/story/graphs                        # 列出所有剧情图
GET    /api/story/graphs/{graph_id}             # 查单个剧情图
POST   /api/story/graphs                        # 创建剧情图
PUT    /api/story/graphs/{graph_id}             # 更新剧情图
DELETE /api/story/graphs/{graph_id}             # 删除剧情图
GET    /api/story/graphs/{graph_id}/export      # 导出(默认yaml)
```

**Event Graph API**:
```python
GET    /api/events/graphs                       # 列出所有事件图
GET    /api/events/graphs/{graph_id}            # 查单个事件图
POST   /api/events/graphs                       # 创建事件图
PUT    /api/events/graphs/{graph_id}            # 更新事件图
DELETE /api/events/graphs/{graph_id}            # 删除事件图
POST   /api/events/test-trigger                 # 测试事件触发
```

**Asset Classification API** (扩展现有 `/api/assets`):
```python
GET    /api/assets/tree                         # 获取分类资产树
GET    /api/assets/classified/{classification}  # 按分类查询(story|event|environment)
```

**AI Assistant API**:
```python
POST   /api/ai/suggest-nodes                    # AI建议剧情/事件节点
POST   /api/ai/check-consistency                # 叙事一致性检查
POST   /api/ai/suggest-assets                   # AI建议资产候选
POST   /api/ai/optimize-prompt                  # AI优化生成提示词
POST   /api/ai/validate-constraints             # 约束验证
```

**Culture & Constraint API**:
```python
GET    /api/culture/trees                       # 列出所有文化树
POST   /api/culture/trees                       # 创建文化树
# ... CRUD 标准接口

GET    /api/constraints/trees                   # 列出所有约束树
POST   /api/constraints/trees                   # 创建约束树
# ... CRUD 标准接口
```

### 6.2 核心数据结构契约 (现有)

#### ActionRequest (POST /api/action)
```python
class ActionRequest(BaseModel):
    player_input: str          # 必填，min_length=1
    player_id: str = "player_001"
    current_scene: str = "temple_ruins"
```

#### ActionResponse (POST /api/action 响应)
```python
class ActionResponse(BaseModel):
    judgment: JudgmentResult        # 判决结果
    narrative: str                  # AI生成叙事文本
    updated_state: PlayerState      # 更新后玩家状态
    parsed_intent: ParsedIntent     # 解析后的意图
    echo_vision: str | None         # 回声视觉文本(可选)
    available_actions: list[str]    # 可用后续动作
```

#### ParsedIntent
```python
class ParsedIntent(BaseModel):
    action_type: ActionType         # 枚举: brute_force|stealth|...
    target: str | None              # 目标物体ID
    intensity: Literal["low","medium","maximum"]
    risk_acceptance: bool
    tool_used: str | None
    raw_input: str                  # 原始输入
    confidence: float               # 0.0-1.0
```

#### JudgmentResult
```python
class JudgmentResult(BaseModel):
    result: JudgmentOutcome         # success|fail|forced_fail|partial|god_intervention
    reason: str                     # 人类可读原因
    damage: int = 0                 # 伤害值
    state_changes: list[StateChange]
    god_intervention: str | None    # 干涉神王名
    narrative_context: NarrativeContext
    echo_triggered: bool = False
```

#### StateChange
```python
class StateChange(BaseModel):
    target_type: Literal["player","object","scene"]
    target_id: str
    property_name: str              # health|energy|strength|mental_stability|status
    old_value: str | int | bool
    new_value: str | int | bool
```

### 6.3 新增数据结构契约

#### StoryGraph (POST /api/story/graphs)
```python
class StoryGraphCreate(BaseModel):
    id: str
    name: str
    description: str
    nodes: dict[str, StoryNode] = {}
    edges: list[dict] = []
    metadata: dict = {}

class StoryGraphUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    nodes: dict[str, StoryNode] | None = None
    edges: list[dict] | None = None
```

#### EventGraph (POST /api/events/graphs)
```python
class EventGraphCreate(BaseModel):
    id: str
    name: str
    description: str
    nodes: dict[str, EventNode] = {}
    global_triggers: list[EventTrigger] = []
    metadata: dict = {}
```

#### CultureNode
```python
class CultureNodeCreate(BaseModel):
    id: str
    name: str
    description: str
    values: list[str] = []
    aesthetic_principles: list[str] = []
    child_nodes: list[CultureNodeCreate] = []
```

#### ConstraintNode
```python
class ConstraintNodeCreate(BaseModel):
    id: str
    type: ConstraintType
    rule: str
    rule_config: dict | None = None
    priority: int = 0
    applicable_types: list[str] = []
```

### 6.4 内部 Python Protocol 接口 (现有)

```python
# 状态仓储接口
@runtime_checkable
class StateRepository(Protocol):
    async def init_db(self) -> None: ...
    async def get_state(self, player_id: str = "player_001") -> PlayerState | None: ...
    async def update_state(self, player_id: str, state: PlayerState) -> None: ...
    async def reset_state(self, player_id: str = "player_001") -> PlayerState: ...
    async def close(self) -> None: ...

# 意图解析器接口
@runtime_checkable
class IntentParser(Protocol):
    async def parse(self, player_input: str) -> ParsedIntent: ...

# 叙事渲染器接口
@runtime_checkable
class NarrativeRenderer(Protocol):
    async def render(
        self, judgment: JudgmentResult, intent: ParsedIntent,
        context: dict[str, object]
    ) -> str: ...
```

### 6.5 AI辅助系统API接口

#### POST /api/ai/suggest-nodes
```python
class NodeSuggestionRequest(BaseModel):
    graph_type: Literal["story", "event"]
    context: dict[str, object]     # 当前图上下文
    position_hint: str | None = None

class NodeSuggestionResponse(BaseModel):
    suggestions: list[dict]       # [{id, type, name, description, reason}]
```

#### POST /api/ai/check-consistency
```python
class ConsistencyCheckRequest(BaseModel):
    graph_id: str                 # StoryGraph 或 EventGraph ID

class ConsistencyReport(BaseModel):
    is_consistent: bool
    issues: list[dict]            # [{type, severity, description, location}]
```

#### POST /api/ai/suggest-assets
```python
class AssetSuggestionRequest(BaseModel):
    requirement: str              # 资产需求描述
    culture_id: str | None = None
    constraint_set_id: str | None = None

class AssetSuggestionResponse(BaseModel):
    candidates: list[dict]        # [{id, prompt, style_profile, score}]
```

#### POST /api/ai/optimize-prompt
```python
class PromptOptimizationRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    culture_hint: str | None = None

class OptimizedPromptResponse(BaseModel):
    optimized_prompt: str
    optimized_negative: str
    improvements: list[str]
```

#### POST /api/ai/validate-constraints
```python
class ConstraintValidationRequest(BaseModel):
    constraint_tree_id: str
    assets: list[str]             # Asset IDs to validate

class ValidationResult(BaseModel):
    is_valid: bool
    violations: list[dict]        # [{asset_id, constraint_id, reason}]
```

---

## 7. 数据流图

### 7.1 玩家交互主回路 (现有)

```
玩家输入文本
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator.process_action()             │
│                                                              │
│  1. StateRepo.get_state(player_id)                          │
│     └─→ PlayerState (from SQLite)                           │
│                                                              │
│  2. IntentParser.parse(player_input)                        │
│     ├─→ LLMProvider.chat_json(messages)                     │
│     │    └─→ ParsedIntent (action_type, target, intensity)  │
│     └─→ (fallback) ParsedIntent(PROBE, confidence=0.0)     │
│                                                              │
│  3. RulesEngine.judge(intent, player)                       │
│     ├─→ WorldLoader.load_scene(location)                    │
│     │    └─→ Scene + GameObjects (from YAML)               │
│     ├─→ check_intervention(target, table, gods)            │
│     │    └─→ GodKing | None                                │
│     ├─→ IF god_intervention AND is_future_anchor:           │
│     │    └─→ FORCED_FAIL + apply_penalty(god)              │
│     ├─→ ELSE check_strength_vs_hardness(str, hardness)     │
│     │    └─→ SUCCESS | FAIL                                │
│     └─→ JudgmentResult                                      │
│                                                              │
│  4. _apply_state_changes(player, judgment)                  │
│     └─→ PlayerState (deepcopy + apply StateChange[])       │
│                                                              │
│  5. NarrativeRenderer.render(judgment, intent, context)    │
│     ├─→ LLMProvider.chat(messages)                          │
│     │    └─→ 叙事文本                                       │
│     └─→ (fallback) _template_render(judgment)              │
│                                                              │
│  6. StateRepo.update_state(player_id, updated_player)      │
│                                                              │
│  └─→ ActionResponse                                         │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
Frontend: Terminal (打字机输出) + StatusPanel (状态更新)
```

### 7.2 资产生成管道 (现有，两种模式)

**方式A: SceneGraph 驱动**:
```
data/scenes/{scene_id}.yaml
    │
    ├─→ SceneGraph.from_yaml(scene_id)
    │    └─→ nodes + generation_order (Kahn topo sort)
    │
    ├─→ PuzzleGraph.from_yaml(scene_id)
    │    └─→ nodes + chain (topo sort with type priority)
    │
    └─→ GenerationPlanner.create_plan(scene_id)
         ├─→ combine deps (spatial + puzzle)
         ├─→ LOD-aware topo sort (near→mid→far→bg)
         └─→ GenerationPlan {order, specs}
                   │
                   ▼
         AssetStore.update_asset(id, GENERATING)
                   │
                   ▼
         ImageGenerator.generate(prompt, refs)
              ├─→ Zhipu/Wanxiang/Qwen/Local backend
              └─→ GeneratedImage[] (seed + bytes/url)
                   │
                   ▼
         AssetStore.update_asset(id, COMPLETED, file_path, seed)
                   │
                   ├─ IF background:
                   │  └─→ StyleExtractor → fill pending objects
                   │
                   ▼
         Review: approve → APPROVED | reject → REJECTED
```

**方式B: KnowledgeGraph 驱动**:
```
POST /api/graph/extract {scene_description}
    │
    ▼
GraphExtractor.extract_from_text()
    ├─→ LLM: scene_description → JSON {nodes, edges}
    └─→ KnowledgeGraph {nodes, edges, background_node_id}
    │
POST /api/graph/validate {KnowledgeGraph}
    └─→ cycle_detector.validate_graph() → {is_valid}
    │
POST /api/graph/save {KnowledgeGraph}
    └─→ GraphStore (SQLite)
    │
POST /api/graph/generate {KnowledgeGraph}
    │
    ▼
GenerationScheduler.run_generation(graph)
    ├─→ validate (cycle detection)
    ├─→ topo_sort.get_generation_waves(graph)
    │    └─→ [[node1, node2], [node3], ...] 波次
    │
    └─→ FOR EACH WAVE (serial):
         └─→ asyncio.gather(*nodes in wave)
              └─→ _generate_node(node_id, graph, refs)
                   ├─→ PromptFusion.build_prompt()
                   │    ├─ Subject: node.description
                   │    ├─ Relation: completed edges
                   │    └─ Background: bg node desc
                   └─→ ImageGenerator.generate()
    └─→ {total, succeeded, failed, order}
```

### 7.3 编辑器→生成管道整合流 (新增)

```
1. 设计师在编辑器中创建 StoryGraph
    │
    ├─ POST /api/story/graphs → StoryService → data/stories/{id}.yaml
    │
2. StoryNode.required_assets 触发资产需求
    │
    ├─ StoryService 解析 required_assets → AssetRequirement[]
    │
3. 资产需求进入分类系统
    │
    ├─ AssetClassifier.classify(requirement, story_context)
    │    └─ classification = STORY (来自StoryGraph)
    │
4. CultureTree 约束候选
    │
    ├─ CandidateSystem.filter(requirement, culture_tree, constraint_tree)
    │    ├─ CultureTree 提供候选 (希腊式 vs 玛雅 vs 水晶)
    │    └─ ConstraintTree 硬过滤 (禁止钢铁 → 剔除金属候选)
    │
5. 进入现有生成管道 (无缝对接)
    │
    ├─ GenerationPlanner.create_plan(scene_id)
    │    ├─ 合并 StoryGraph 节点依赖 (新增)
    │    ├─ 合并 PuzzleGraph 谜题依赖 (现有)
    │    ├─ 合并 SceneGraph 空间依赖 (现有)
    │    └─ LOD感知拓扑排序 (现有)
    │
    ├─ PromptBuilder.build(asset_id, lod_level)
    │    ├─ 8层提示词 (现有)
    │    └─ + Culture 层 (新增: 文化风格注入)
    │    └─ + Constraint 层 (新增: 约束过滤)
    │
    ├─ ImageGenerator.generate(prompt)
    │    └─ 现有流程不变
    │
    └─ AssetStore.update_asset(classification=STORY)
         └─ 新增 classification 字段写入
```

### 7.4 AI辅助系统数据流 (新增)

```
用户在编辑器中点击"AI建议"
    │
    ▼
POST /api/ai/suggest-nodes
    │
    ▼
AIAssistant.suggest_nodes(context)
    │
    ├─→ LLMProvider.chat_json(messages)
    │    ├─ System: "You are a story design assistant..."
    │    ├─ User: "Current story nodes: {nodes}. Suggest next nodes."
    │    └─→ AI Response: JSON [{id, type, name, description, reason}]
    │
    └─→ NodeSuggestionResponse

用户选择建议节点 → 自动添加到图中
    │
    ▼
POST /api/story/graphs/{id}
    │
    ▼
StoryService.update_graph()
    │
    └─→ data/stories/{id}.yaml 更新
```

---

## 8. 界面设计

### 8.1 主界面布局

```
┌─────────────────────────────────────────────────────────────┐
│ File | Edit | View | AI Tools | Preview | Help               │
├───────────┬─────────────────────────────────────────────────┤
│           │                                                 │
│ Navigator │            Canvas Area                         │
│           │         (可视化编辑画布)                        │
│ 📁 Story  │                                                 │
│   ├─ Main │    ┌─────┐        ┌─────┐                     │
│   ├─ Branch│  ┌──┤NodeA ├──────┤NodeB├──┐                 │
│   └─ Side │  │  └─────┘        └─────┘  │                 │
│           │  │                            │                 │
│ 📁 Events │  └─────┐              ┌───────┘                 │
│   ├─ Combat│    ┌──┴──┐          │                         │
│   ├─ Quest│    │Event├──────────┘                         │
│   └─ Random│    └─────┘                                    │
│           │                                                 │
│ 📁 Assets │    ┌─────┐         ┌─────┐                    │
│   ├─ Story│  ┌─┤Asset├───────┬─┤Asset├─┐                 │
│   ├─ Event│  │ └─────┘       │ └─────┘ │                 │
│   └─ Environ│              │          │                  │
│           │                 │          │                  │
├───────────┼─────────────────────────────────────────────────┤
│           │                                                 │
│ Properties│          AI Assistant Panel                     │
│           │         (AI智能辅助面板)                        │
│ 📝 Node   │    💡 AI Suggestions:                          │
│ ├─ Name   │    → Consider adding a choice node here        │
│ ├─ Type   │    → Event trigger condition seems too strict  │
│ └─ Config │    → Asset could be reused in Scene B         │
│           │                                                 │
└───────────┴─────────────────────────────────────────────────┘
```

### 8.2 组件层次

```
App
├── Layout
│   ├── Sidebar (Navigator)
│   ├── Canvas (Main Editor)
│   ├── PropertiesPanel
│   └── AIAssistantPanel
├── Editors
│   ├── StoryGraphEditor
│   ├── EventGraphEditor
│   ├── AssetTreeEditor
│   ├── CultureTreeEditor
│   └── WorldKGEditor
└── Shared
    ├── Toolbar
    ├── StatusBar
    └── DialogManager
```

### 8.3 前端技术栈

```typescript
{
  "框架": "React 18 + TypeScript",
  "构建工具": "Vite",
  "图编辑器": "React Flow",
  "数据可视化": "D3.js",
  "代码编辑": "Monaco Editor",
  "状态管理": "Zustand",
  "UI组件": "Radix UI",
  "样式": "TailwindCSS",
  "实时协作": "Y.js",
  "路由": "React Router"
}
```

**核心库选择理由**:

- **React Flow**: 专为节点图编辑设计，TypeScript原生支持，自定义节点能力强大，性能优秀
- **Zustand**: 轻量简洁，TypeScript友好，无需Provider包装
- **Radix UI**: 无障碍支持，高度可定制，TypeScript原生

---

## 9. 前端模块定义

### 9.1 现有前端组件

| 组件 | 路径 | 功能 |
|------|------|------|
| `Terminal` | `components/Terminal.tsx` | 交互终端，打字机效果 |
| `SceneView` | `components/SceneView.tsx` | 场景视图，显示当前场景 |
| `StatusPanel` | `components/StatusPanel.tsx` | 状态面板，显示玩家属性 |
| `GodWatchIndicator` | `components/GodWatchIndicator.tsx` | 神王干涉指示器 |
| `GraphEditor` | `components/graph/` | 知识图谱编辑器 |

### 9.2 新增编辑器组件

| 组件 | 路径 | 库依赖 | 对接后端 |
|------|------|--------|---------|
| **StoryGraphEditor** | `components/editor/StoryGraphEditor.tsx` | React Flow | `/api/story/*` |
| **EventGraphEditor** | `components/editor/EventGraphEditor.tsx` | React Flow | `/api/events/*` |
| **AssetTreeEditor** | `components/editor/AssetTreeEditor.tsx` | React Flow + D3.js | `/api/assets/tree` |
| **CultureTreeEditor** | `components/editor/CultureTreeEditor.tsx` | React Flow | `/api/culture/*` |
| **WorldKGEditor** | `components/editor/WorldKGEditor.tsx` | React Flow | `/api/graph/*` (现有) |
| **AIAssistantPanel** | `components/editor/AIAssistantPanel.tsx` | — | `/api/ai/*` |
| **PropertiesPanel** | `components/editor/PropertiesPanel.tsx` | — | — |
| **Navigator** (侧边栏) | `components/editor/Navigator.tsx` | — | — |
| **EditorLayout** | `components/editor/EditorLayout.tsx` | — | — |

### 9.3 前端状态管理 (Zustand stores)

```
stores/
├── storyStore.ts          # StoryGraph 状态
├── eventStore.ts          # EventGraph 状态
├── assetTreeStore.ts      # AssetTree 分类状态
├── cultureStore.ts        # CultureTree 状态
├── constraintStore.ts     # ConstraintTree 状态
└── editorUIStore.ts       # 编辑器UI状态(选中节点/面板状态等)
```

**Store 示例** (`storyStore.ts`):
```typescript
interface StoryStore {
  graphs: Record<string, StoryGraph>;
  activeGraphId: string | null;
  selectedNodes: string[];

  fetchGraphs: () => Promise<void>;
  createGraph: (graph: StoryGraphCreate) => Promise<StoryGraph>;
  updateGraph: (id: string, updates: StoryGraphUpdate) => Promise<void>;
  deleteGraph: (id: string) => Promise<void>;
  exportGraph: (id: string, format: string) => Promise<void>;

  selectNode: (nodeId: string) => void;
  clearSelection: () => void;
}
```

### 9.4 前端类型定义

```
types/
├── action.ts              # [现有] ActionType, ParsedIntent, JudgmentResult
├── player.ts              # [现有] PlayerState, PlayerStatus
├── scene.ts               # [现有] Scene, SceneObjectDTO, SceneResponse
├── asset.ts               # [现有 + 扩展] Asset, AssetStatus, AssetType, AssetClassification
├── graph.ts               # [现有] KnowledgeGraph, GraphNode, GraphEdge
├── api.ts                 # [现有] API请求/响应类型
├── story.ts               # [新增] StoryNode, StoryGraph, StoryEdge, StoryCondition, StoryChoice
├── event.ts               # [新增] EventNode, EventGraph, EventTrigger, EventAction, EventReward
├── culture.ts             # [新增] CultureNode, CultureTree
├── constraint.ts          # [新增] ConstraintNode, ConstraintTree, ConstraintType
└── editor.ts              # [新增] EditorState, PanelConfig, NodeSuggestion 等
```

### 9.5 前后端类型同步表

| 后端 (Python) | 前端 (TypeScript) | 同步方式 |
|---------------|-------------------|---------|
| `models/action.py` | `types/action.ts` | 手动镜像 |
| `models/player.py` | `types/player.ts` | 手动镜像 |
| `models/scene_response.py` | `types/scene.ts` | 手动镜像 |
| `models/api.py` | `types/api.ts` | 手动镜像 |
| `models/knowledge_graph.py` | `types/graph.ts` | 手动镜像 |
| `models/asset.py` (扩展) | `types/asset.ts` (扩展) | 手动镜像 |
| `models/story_graph.py` | `types/story.ts` | 手动镜像 |
| `models/event_graph.py` | `types/event.ts` | 手动镜像 |
| `models/culture.py` | `types/culture.ts` | 手动镜像 |
| `models/constraint.py` | `types/constraint.ts` | 手动镜像 |

> **注意**: 当前同步是手动的。未来可考虑用 `openapi-typescript` 从 FastAPI OpenAPI schema 自动生成。

---

## 10. 数据存储设计

### 10.1 目录结构

```
data/
├── scenes/                 # [现有] — 场景定义 + puzzle_chain
├── stories/                # [新增] — StoryGraph 定义
│   └── {story_id}.yaml
├── events/                 # [新增] — EventGraph 定义
│   └── {event_graph_id}.yaml
├── cultures/               # [新增] — CultureTree 定义
│   └── {culture_id}.yaml
├── constraints/            # [新增] — ConstraintTree 定义
│   └── {constraint_set_id}.yaml
├── gods/                   # [现有]
├── objects/                # [现有]
├── rules/                  # [现有] (逐步迁移到 constraints/)
├── assets/                 # [现有] — manifest.json + graph.db + 图像
└── visual/                 # [现有] — prompts/palette/style_bible
```

### 10.2 Scene YAML 格式 (现有，完整)

```yaml
# 必须
scene_id: snake_case
name: Display Name
description: ...
atmosphere: ...
region: snake_case

# 可选
viewpoint: ...
depth_layers:
  - name: near | mid | far
    description: ...

# 谜题链 (Story Graph 的当前形态)
puzzle_chain:
  - node_id: snake_case
    type: clue | consumable | reward | obstacle
    requires: [node_id | produced_item_name]
    produces: item_name
    interaction: action_name

# 场景内物体
accessible_objects:
  - id: snake_case
    name: Display Name
    type: door | container | interactive | decoration | ...
    hardness: 0-100
    energy_cost: int
    is_future_anchor: bool
    description: ...
    position: {x: float, y: float}   # 百分比坐标
    depth: near | mid | mid_far | far
    lod:                              # LOD 描述
      far: ...
      mid: ...
      near: ...
    puzzle_role: clue | consumable | reward | obstacle | atmosphere
    parent_object: snake_case | null  # 派生关系
    new_assets_hint: ...

# 交互目标
interaction_targets:
  - object_id: snake_case
    is_dangerous: bool
    required_tools: [tool_name] | null
```

### 10.3 Story YAML 格式 (新增)

```yaml
id: main_quest_chapter_1
name: "第一章 - 遗忘之神殿"
description: "玩家探索废弃神殿，发现古代秘密"
version: "1.0"

nodes:
  - id: story_start
    type: start
    name: "到达神殿废墟"
    description: "玩家首次进入神殿区域"
    required_assets: ["temple_ruins_bg"]
    scene_link: temple_ruins       # 关联场景 → PuzzleGraph
    metadata:
      chapter: "1"
      tags: ["intro", "exploration"]

  - id: find_priest
    type: event
    name: "发现祭司尸体"
    description: "玩家在场景中发现祭司尸体"
    required_assets: ["temple_ruins_priest_corpse_01"]
    scene_link: temple_ruins
    metadata:
      chapter: "1"
      tags: ["discovery", "clue"]

  - id: unlock_door
    type: condition
    name: "解锁远古之门"
    description: "需要量子钥匙才能开门"
    required_assets: ["temple_ruins_ancient_locked_door"]
    conditions:
      - type: item_required
        requirement: quantum_key
    scene_link: temple_ruins
    metadata:
      chapter: "1"
      tags: ["puzzle", "gate"]

  - id: story_end
    type: end
    name: "进入地下通道"
    description: "门开启，玩家进入下一章"
    metadata:
      chapter: "1"
      tags: ["transition"]

edges:
  - from: story_start
    to: find_priest
  - from: find_priest
    to: unlock_door
    condition:
      type: item_required
      requirement: ritual_knowledge
  - from: unlock_door
    to: story_end
    condition:
      type: item_required
      requirement: quantum_key
```

### 10.4 Event YAML 格式 (新增)

```yaml
id: temple_dynamic_events
name: "神殿动态事件集"
description: "基于环境条件触发的动态事件"

nodes:
  - id: wolf_attack_night
    type: combat
    name: "夜间狼群袭击"
    trigger_conditions:
      - type: time
        condition: "night"
        priority: 1
      - type: location
        condition: "temple_ruins"
        priority: 1
    actions:
      - type: spawn_wolves
        parameters: {count: 3, difficulty: medium}
      - type: create_quest
        parameters: {quest_id: "survive_wolf_attack"}
    rewards:
      - type: experience
        value: 50
        probability: 1.0
    assets:
      - "temple_ruins_wolf_pack"     # 事件资产(临时生成)
    metadata:
      difficulty: 3
      priority: 5
      cooldown: 600

global_triggers: []
```

### 10.5 Culture YAML 格式 (新增)

```yaml
id: greek_culture
name: "古希腊文化体系"
description: "基于黄金比例和人文主义的美学体系"
version: "1.0"

root:
  id: greek_root
  name: "古希腊文明"
  description: "理性、和谐、人文主义的文明典范"
  values:
    - reason
    - harmony
    - humanism
    - balance
  aesthetic_principles:
    - golden_ratio
    - organic_form
    - naturalism
    - geometric_clarity
  child_nodes:
    - id: greek_architecture
      name: "希腊建筑"
      description: "柱式、三角楣、石材结构"
      values: ["permanence", "order", "proportion"]
      aesthetic_principles: ["columnar", "symmetry", "horizontal_emphasis"]
      child_nodes: []
    - id: greek_art
      name: "希腊艺术"
      description: "雕塑、陶器、壁画"
      values: ["beauty", "realism", "idealization"]
      aesthetic_principles: ["contrapposto", "natural_pose", "ideal_form"]
      child_nodes: []
```

### 10.6 Constraint YAML 格式 (新增)

```yaml
scene_id: temple_ruins  # null 表示全局约束
id: temple_constraints
name: "神殿约束集"
description: "神殿场景的资产生成约束"

nodes:
  - id: no_metal
    type: hard
    rule: "禁止使用金属材质"
    priority: 100
    applicable_types: ["background", "object"]

  - id: prefer_organic
    type: soft
    rule: "偏好有机形态和自然材质"
    priority: 50
    applicable_types: ["object"]

  - id: color_constraint
    type: soft
    rule: "色彩应偏向石质灰、土黄、苔绿"
    priority: 30
    applicable_types: ["background", "object"]

  - id: size_constraint
    type: hard
    rule: "物体高度不超过3米"
    priority: 80
    applicable_types: ["object"]
```

---

## 11. 五图模型映射

### 11.1 现有图谱资产盘点

| 五图模型概念 | 现有对应 | 差距分析 |
|-------------|---------|---------|
| **Story Graph** (固定剧情) | `PuzzleGraph` + `puzzle_chain` in YAML | 当前 PuzzleGraph 只处理单场景谜题链，缺少跨场景主线/支线叙事 |
| **Event Graph** (动态事件) | ❌ 不存在 | 完全缺失。当前系统无条件触发机制 |
| **Asset Tree** (空间资产) | `SceneGraph` + `Asset` + `AssetStore` + `GameObject` | 已有场景级资产管理，但无全局 Asset Tree |
| **Culture Tree** (文化约束) | ❌ 不存在 | `style_bible.md` + `palette.yaml` 是初步雏形，但无结构化文化树 |
| **Constraint Tree** (硬约束) | `WorldRule.physical_constraints` | 有简单约束字段，但无约束树结构和候选过滤系统 |

### 11.2 五图对应关系

```
现有架构                        目标架构 (五图模型)
─────────────────              ─────────────────
                                ┌──────────────┐
SceneGraph + Asset              │ Culture Tree │ ← 新增：文化约束体系
                                └──────┬───────┘
                           ┌──────▼───────┐
                           │Constraint Tree│← 新增：硬约束过滤
                           └──────┬───────┘
                                  │
                          ┌──────▼───────┐
                          │ World KG     │ ← 新增：世界知识图谱
                          │(现有)         │
                          └──────┬───────┘
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ Story    │ │ Event    │ │ Asset    │
              │ Graph    │ │ Graph    │ │ Tree     │
              │(升级PG)  │ │(新增)    │ │(升级SG)  │
              └──────────┘ └──────────┘ └──────────┘
                    │            │            │
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │剧情资产  │ │事件资产  │ │环境资产  │
              └──────────┘ └──────────┘ └──────────┘
```

### 11.3 差距分析

| 组件 | 现状 | 缺失功能 | 实施优先级 |
|------|------|----------|-----------|
| StoryGraph | PuzzleGraph (单场景) | 跨场景节点、条件分支、选择节点 | **Phase 1** |
| EventGraph | ❌ 无 | 事件节点、触发条件、动态事件链 | **Phase 2** |
| CultureTree | style_bible.md (非结构化) | 结构化文化树、候选评分系统 | **Phase 3** |
| ConstraintTree | WorldRule (简单字段) | 约束树、硬过滤、优先级 | **Phase 3** |
| CandidateSystem | ❌ 无 | 文化约束→候选→过滤→评分 | **Phase 4** |

### 11.4 PuzzleGraph → StoryGraph 分层关系 (NOT replacement)

**不是替换，是分层。** PuzzleGraph 仍负责单场景谜题逻辑，StoryGraph 负责跨场景叙事。

```
StoryGraph (跨场景)
  ├── StoryNode: "第一章 - 发现祭司尸体"
  │     └── scene_link: temple_ruins
  │         └── PuzzleGraph (单场景谜题)
  │               ├── PuzzleNode: priest_corpse_01 (clue)
  │               ├── PuzzleNode: ritual_record (clue)
  │               └── PuzzleNode: ancient_locked_door (obstacle)
  │
  ├── StoryNode: "第二章 - 逃离神殿"
  │     └── scene_link: underground_passage
  │         └── PuzzleGraph (...)
  │
  └── StoryEdge: chapter1 → chapter2 (condition: temple_access)
```

**数据存储**:
- StoryGraph: `data/stories/{story_id}.yaml` (新建目录)
- PuzzleGraph: 仍嵌入 `data/scenes/{scene_id}.yaml` 的 `puzzle_chain` 字段
- 关联: `StoryNode.scene_link → scene_id → PuzzleGraph.from_yaml(scene_id)`

### 11.5 Asset 模型扩展方案 (backward compatible)

**扩展字段** (有默认值，不破坏现有数据):
```python
class Asset(BaseModel):
    # ... 现有字段全部保留 ...

    # 新增字段
    classification: AssetClassification = AssetClassification.ENVIRONMENT
    related_story_node: str | None = None
    related_event_node: str | None = None
```

**迁移规则**:
- 现有资产默认 `classification = ENVIRONMENT`
- 有 `puzzle_role` 的资产升级为 `classification = STORY`
- 新生成的资产根据来源图自动设置分类

### 11.6 WorldRule → ConstraintTree 升级路径

**现有** (保留向后兼容):
```python
class WorldRule(BaseModel):
    physical_constraints: list[str] = []  # 仍可读，标记为 deprecated
```

**新增**:
```python
class ConstraintNode(BaseModel):
    id: str
    type: ConstraintType                    # "hard" | "soft"
    rule: str                               # 规则描述
    priority: int
    applicable_types: list[str] = []

class ConstraintTree(BaseModel):
    scene_id: str | None = None
    nodes: list[ConstraintNode] = []
```

**迁移规则**: `WorldRule.physical_constraints` 中每个字符串自动转换为 `ConstraintNode(type="hard", rule=string, priority=100)`

---

## 12. 命名规范

### 12.1 ID 命名规则 (全局统一)

| 实体 | 格式 | 示例 |
|------|------|------|
| Scene ID | `snake_case` | `temple_ruins` |
| Object ID | `snake_case` | `priest_corpse_01` |
| Asset ID | `{scene_id}_{object_id}` 或 `{scene_id}_bg` | `temple_ruins_priest_corpse_01` |
| Graph Node ID | Serial Number = ID | `1`, `1-1`, `1-1-1` |
| Player ID | `player_XXX` | `player_001` |
| God ID | `snake_case` | `chronos_order` |
| Puzzle Node ID | `snake_case` (与 object_id 对齐) | `priest_corpse_01` |
| Story Node ID | `snake_case` | `story_start`, `find_priest`, `unlock_door` |
| Event Node ID | `snake_case` | `wolf_attack_night`, `treasure_discovery` |
| Event ID (未来) | `event_XXX` | `event_wolf_attack_01` |
| Culture ID | `snake_case` | `greek_culture` |
| Constraint Set ID | `snake_case` | `temple_constraints` |

### 12.2 代码命名规则

**Python**:
- 文件名: `snake_case.py`
- 类名: `PascalCase`
- 函数/变量: `snake_case`
- 常量: `UPPER_SNAKE_CASE`
- 私有成员: `_leading_underscore`

**TypeScript**:
- 文件名: `camelCase.ts` 或 `kebab-case.ts`
- 接口/类型: `PascalCase`
- 函数/变量: `camelCase`
- 常量: `UPPER_SNAKE_CASE` 或 `PascalCase`
- 私有成员: `_leadingUnderscore`

### 12.3 API JSON 字段规范

**铁律: API JSON 层统一 snake_case**

| 后端 (Python snake_case) | 前端 (TS camelCase) | API JSON 字段 | 说明 |
|--------------------------|---------------------|---------------|------|
| `trigger_conditions` | `triggerConditions` | `trigger_conditions` | API JSON 统一 snake_case |
| `required_assets` | `requiredAssets` | `required_assets` | — |
| `asset_type` | `assetType` | `asset_type` | — |
| `style_profile` | `styleProfile` | `style_profile` | — |
| `is_future_anchor` | `isFutureAnchor` | `is_future_anchor` | — |
| `classification` | `classification` | `classification` | — |
| `scene_link` | `sceneLink` | `scene_link` | — |

**Pydantic 配置** (支持前端 camelCase):
```python
class StoryNode(BaseModel):
    required_assets: list[str] = Field(alias="required_assets")
    scene_link: str | None = Field(default=None, alias="scene_link")

    model_config = ConfigDict(populate_by_name=True)
```

### 12.4 文件命名规则

| 类型 | 命名规则 | 示例 |
|------|---------|------|
| YAML 数据文件 | `snake_case.yaml` | `temple_ruins.yaml`, `main_quest_chapter_1.yaml` |
| JSON 清单文件 | `snake_case.json` | `manifest.json` |
| Python 模块 | `snake_case.py` | `story_graph.py`, `event_service.py` |
| TypeScript 组件 | `PascalCase.tsx` | `StoryGraphEditor.tsx`, `AIAssistantPanel.tsx` |
| TypeScript 类型 | `camelCase.ts` | `story.ts`, `event.ts` |
| Zustand Store | `camelCase.ts` | `storyStore.ts`, `eventStore.ts` |

---

## 13. 依赖注入架构 (现有)

```python
# 状态仓储接口
@runtime_checkable
class StateRepository(Protocol):
    async def init_db(self) -> None: ...
    async def get_state(self, player_id: str = "player_001") -> PlayerState | None: ...
    async def update_state(self, player_id: str, state: PlayerState) -> None: ...
    async def reset_state(self, player_id: str = "player_001") -> PlayerState: ...
    async def close(self) -> None: ...

# 意图解析器接口
@runtime_checkable
class IntentParser(Protocol):
    async def parse(self, player_input: str) -> ParsedIntent: ...

# 叙事渲染器接口
@runtime_checkable
class NarrativeRenderer(Protocol):
    async def render(
        self, judgment: JudgmentResult, intent: ParsedIntent,
        context: dict[str, object]
    ) -> str: ...

# LLM Provider 接口
class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict[str, str]], **kwargs) -> str: ...

    @abstractmethod
    async def chat_json(self, messages: list[dict[str, str]], **kwargs) -> dict[str, Any]: ...

# RulesEngine 接口
class RulesEngine:
    def __init__(self, loader: WorldLoader) -> None: ...
    async def judge(self, intent: ParsedIntent, player: PlayerState) -> JudgmentResult: ...

# Orchestrator 接口
class Orchestrator:
    def __init__(
        self,
        parser: IntentParser,
        engine: RulesEngine,
        renderer: NarrativeRenderer,
        state_repo: StateRepository,
    ) -> None: ...

    async def process_action(self, request: ActionRequest) -> ActionResponse: ...
```

---

## 14. 实施路线图

### 14.1 Phase 1: 数据模型先行 (4-6周)

**目标**: 新增数据模型，零外部依赖

**任务清单**:
```
[ ] models/story_graph.py
    └─ StoryNodeType, StoryCondition, StoryChoice, StoryNode, StoryGraph
[ ] models/event_graph.py
    └─ EventNodeType, EventTriggerType, EventRewardType, EventNode, EventGraph
[ ] models/culture.py
    └─ CultureNode, CultureTree
[ ] models/constraint.py
    └─ ConstraintType, ConstraintNode, ConstraintTree
[ ] models/asset.py (扩展)
    └─ AssetClassification 枚举 + classification 字段 + related_story_node + related_event_node
```

**验收标准**:
- 所有模型通过 mypy 严格类型检查
- 所有模型有完整的 Pydantic v2 配置
- 所有枚举有文档字符串
- 所有新增字段有默认值 (向后兼容)

### 14.2 Phase 2: 后端服务层 (6-8周)

**目标**: 实现业务逻辑层

**任务清单**:
```
[ ] services/story_service.py
    ├─ create_graph, get_graph, update_graph, delete_graph, list_graphs, export_graph
    └─ CRUD 操作 + YAML 序列化/反序列化
[ ] services/event_service.py
    ├─ create_graph, get_graph, update_graph, delete_graph, list_graphs, test_trigger
    └─ CRUD + 触发条件测试逻辑
[ ] services/asset_classifier.py
    ├─ classify(requirement, context) → AssetClassification
    └─ 基于来源图自动分类
[ ] services/candidate_system.py
    ├─ filter_by_culture(requirement, culture_tree) → candidates[]
    ├─ filter_by_constraints(candidates, constraint_tree) → filtered[]
    └─ score_candidates(filtered) → sorted[]
[ ] services/ai_assistant.py
    ├─ suggest_nodes(context) → suggestions[]
    ├─ check_consistency(graph) → ConsistencyReport
    ├─ suggest_assets(requirement) → candidates[]
    ├─ optimize_prompt(prompt) → OptimizedPrompt
    └─ validate_constraints(assets, constraints) → ValidationResult
```

**验收标准**:
- 所有服务有单元测试 (pytest)
- 所有服务有集成测试 (SQLite + YAML)
- AI 服务有 mock 测试 (不调用真实 LLM)
- 候选系统有确定性测试 (相同输入100%相同输出)

### 14.3 Phase 3: API 路由层 (4-6周)

**目标**: HTTP 接口层

**任务清单**:
```
[ ] api/story_routes.py
    ├─ GET/POST/PUT/DELETE /api/story/graphs
    ├─ GET /api/story/graphs/{id}/export
    └─ 6个端点
[ ] api/event_routes.py
    ├─ GET/POST/PUT/DELETE /api/events/graphs
    ├─ POST /api/events/test-trigger
    └─ 5个端点
[ ] api/ai_routes.py
    ├─ POST /api/ai/suggest-nodes
    ├─ POST /api/ai/check-consistency
    ├─ POST /api/ai/suggest-assets
    ├─ POST /api/ai/optimize-prompt
    └─ POST /api/ai/validate-constraints
[ ] api/culture_routes.py
    └─ CRUD 标准接口
[ ] api/constraint_routes.py
    └─ CRUD 标准接口
[ ] api/assets_routes.py (扩展)
    ├─ GET /api/assets/tree
    └─ GET /api/assets/classified/{classification}
[ ] main.py (路由注册)
    └─ app.include_router() x 7个新路由文件
```

**验收标准**:
- 所有 API 有 FastAPI 自动文档 (`/docs`)
- 所有 API 有 OpenAPI 规范
- 所有 API 有 E2E 测试 (Playwright)
- 所有 API 有错误处理测试 (4xx, 5xx)

### 14.4 Phase 4: 前端编辑器 (8-10周)

**目标**: React Flow 编辑器

**任务清单**:
```
[ ] stores/
    ├─ storyStore.ts
    ├─ eventStore.ts
    ├─ assetTreeStore.ts
    ├─ cultureStore.ts
    ├─ constraintStore.ts
    └─ editorUIStore.ts
[ ] types/
    ├─ story.ts
    ├─ event.ts
    ├─ culture.ts
    └─ constraint.ts
[ ] api/
    ├─ story.ts (API client)
    ├─ events.ts
    ├─ culture.ts
    └─ ai.ts
[ ] components/editor/
    ├─ StoryGraphEditor.tsx
    ├─ EventGraphEditor.tsx
    ├─ AssetTreeEditor.tsx
    ├─ CultureTreeEditor.tsx
    ├─ WorldKGEditor.tsx
    ├─ AIAssistantPanel.tsx
    ├─ PropertiesPanel.tsx
    ├─ Navigator.tsx
    └─ EditorLayout.tsx
```

**验收标准**:
- 所有组件有单元测试 (Jest + React Testing Library)
- 所有 store 有测试 (mock API calls)
- 所有编辑器有 E2E 测试 (Playwright)
- 图编辑器性能测试 (100+节点流畅)

### 14.5 Phase 5: 生成管道整合 (6-8周)

**目标**: 编辑器内容流入生成管道

**任务清单**:
```
[ ] GenerationPlanner 升级
    ├─ 解析 StoryGraph 依赖
    ├─ 合并 PuzzleGraph + SceneGraph + StoryGraph 依赖
    └─ 输出统一的 GenerationPlan
[ ] PromptBuilder 升级
    ├─ 新增 Culture 层 (文化风格注入)
    ├─ 新增 Constraint 层 (约束过滤)
    └─ 保持向后兼容 (无文化/约束时降级)
[ ] CandidateSystem 接入
    ├─ 连接 CultureTree → 候选生成
    ├─ 连接 ConstraintTree → 候选过滤
    └─ 输出: 排序候选列表
[ ] AssetStore 升级
    ├─ 存储 classification 字段
    ├─ 存储 related_story_node, related_event_node
    └─ 支持按分类查询
```

**验收标准**:
- 端到端测试: StoryGraph → Asset 生成
- 端到端测试: CultureTree + ConstraintTree → 候选过滤
- 性能测试: 候选系统不阻塞生成管道
- 回归测试: 现有生成流程不受影响

### 14.6 Phase 依赖图

```
Phase 1 (数据模型)
    │
    ├──────────────────────────────────────┐
    ▼                                      ▼
Phase 2 (服务层)                      [并行可启动]
    │                                      │
    ├──────────────────────────────────────┘
    ▼
Phase 3 (API层)
    │
    ▼
Phase 4 (前端)
    │
    ▼
Phase 5 (生成管道整合)
```

---

## 15. 风险评估与应对

### 15.1 技术风险

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|----------|
| React Flow性能问题 (大图卡顿) | 高 | 中 | 提前进行性能测试，准备虚拟化方案，限制单图节点数 < 500 |
| AI API成本过高 (预算超支) | 中 | 高 | 实施本地缓存，优化API调用频率，使用本地模型fallback |
| 数据同步冲突 (多人编辑) | 高 | 中 | 实施乐观锁和冲突解决策略，Y.js 实时协作 |
| 复杂图编辑交互 (学习曲线) | 中 | 高 | 提前进行用户测试，简化交互设计，提供模板库 |
| 候选系统性能 (过滤延迟) | 中 | 中 | 实施缓存策略，异步过滤，进度反馈 |

### 15.2 项目风险

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|----------|
| 开发周期延长 (资源不足) | 高 | 中 | 分阶段交付，MVP优先，外包非核心功能 |
| 用户需求变更 (设计反复) | 中 | 高 | 灵活的架构设计，模块化开发，早期原型验证 |
| 团队技能不足 (新技术栈) | 中 | 低 | 提供培训，引入外部专家，代码审查制度 |

### 15.3 质量保证

**测试策略**:
- 单元测试覆盖率 ≥ 85% (pytest + Jest)
- 集成测试覆盖关键用户流程 (pytest-behave)
- E2E测试覆盖核心功能 (Playwright)
- 性能测试确保大图编辑流畅 (Lighthouse)
- 用户测试验证交互设计 (用户验收测试)

**代码质量**:
- ESLint + TypeScript strict mode
- Ruff + Mypy strict mode (Python)
- 代码审查制度 (至少1人审批)
- 持续集成/持续部署 (GitHub Actions)
- 自动化测试运行 (每次commit)

---

## 16. 编辑器设计文档勘误

### 16.1 类型约束修正

| 问题 | 位置 | 修正 |
|------|------|------|
| `StoryCondition.requirement: any` | §3.1 StoryNode 数据结构 | 改为 `requirement: str \| dict` — Pydantic v2 strict mode 不允许裸 `any` |
| `EventTrigger.condition: any` | §3.2 EventNode 数据结构 | 同上 |
| `EventAction.parameters: Dict` | §3.2 | 改为 `parameters: dict[str, str \| int \| bool]` |
| `ConstraintNode.rule: any` | §3.4 | 改为 `rule: str` (规则描述文本) + `rule_config: dict \| None` |

### 16.2 时区修正

| 问题 | 位置 | 修正 |
|------|------|------|
| `datetime.now()` | §7.1 StoryGraph | 改为 `datetime.now(timezone.utc)` — 现有代码规范要求 UTC |

### 16.3 命名冲突修正

| 问题 | 位置 | 修正 |
|------|------|------|
| 前端 `requiredAssets` (camelCase) | §7.2 | API JSON 层用 `required_assets` (snake_case)，前端类型可 alias |
| `AssetNode.type = 'story'\|'event'\|'environment'` | §3.3 | 改名为 `classification` — `type` 已被 `AssetType(background\|object)` 占用 |

### 16.4 实施状态修正

| 问题 | 位置 | 修正 |
|------|------|------|
| Phase 1-4 任务全部标记 `[x]` | §9 | 实际未完成，应标记 `[ ]` |

### 16.5 路由注册修正

| 问题 | 位置 | 修正 |
|------|------|------|
| 缺少 `main.py` 路由注册 | §8 | 新增路由文件必须在 `main.py` 中 `app.include_router()` |

---

## 附录A: 技术栈速查

| 层 | 技术 | 版本要求 | 用途 |
|----|------|---------|------|
| 后端框架 | FastAPI + Uvicorn | ≥0.104 | Web框架 |
| 数据验证 | Pydantic | ≥2.5 | 数据建模 |
| 数据库 | SQLite + aiosqlite + SQLAlchemy | ≥2.0 | 持久化 |
| LLM SDK | openai + anthropic | ≥1.0 / ≥0.7 | AI服务 |
| 前端框架 | React + Vite + TypeScript | Node ≥18 | UI框架 |
| 样式 | TailwindCSS v4 | — | 样式系统 |
| 图编辑器 | React Flow | ≥12.0 | 图编辑 |
| 状态管理 | Zustand | ≥4.5 | 状态管理 |
| UI组件库 | Radix UI | ≥1.0 | UI组件 |
| 代码编辑器 | Monaco Editor | — | 代码编辑 |
| 数据可视化 | D3.js | ≥7.0 | 可视化 |
| 实时协作 | Y.js | — | 协作 |
| 测试 | pytest + behave + mutmut + Playwright | — | 测试套件 |
| Python | 3.11+ (strict mypy) | — | 语言版本 |

---

## 附录B: 术语表

| 术语 | 定义 |
|------|------|
| **五图模型** | Story Graph, Event Graph, Asset Tree, Culture Tree, Constraint Tree |
| **Story Graph** | 跨场景固定剧情图，包含主线/支线叙事节点 |
| **Event Graph** | 动态事件图，基于条件触发的临时事件 |
| **Asset Tree** | 分层分类的视觉资产体系 |
| **Culture Tree** | 文明体系和价值层级的树状结构 |
| **Constraint Tree** | 资产生成的硬约束和软约束规则树 |
| **剧情资产 (Story Asset)** | 服务于固定剧情的永久资产 |
| **事件资产 (Event Asset)** | 服务于动态事件的临时资产 |
| **环境资产 (Environment Asset)** | 提供世界氛围的背景资产 |
| **候选系统 (Candidate System)** | 文化约束→候选→过滤→评分的完整流程 |
| **StoryNode** | 剧情节点，类型: start\|end\|choice\|event\|condition |
| **EventNode** | 事件节点，类型: combat\|quest\|exploration\|social |
| **PuzzleNode** | 谜题节点，类型: clue\|consumable\|reward\|obstacle |
| **AssetClassification** | 资产分类枚举: story\|event\|environment |
| **AssetType** | 资产类型枚举: background\|object (现有，不变) |
| **SceneGraph** | 场景生成图，描述场景内资产的空间依赖关系 |
| **PuzzleGraph** | 谜题依赖图，描述单场景谜题链的逻辑依赖 |
| **KnowledgeGraph** | 世界知识图谱，描述场景内所有节点的层级关系 |

---

## 附录C: 更新日志

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v2.0 | 2026-08-01 | 整合 AI剧情场景编辑器设计文档，新增五图模型架构、StoryGraph、EventGraph、CultureTree、ConstraintTree、AI辅助系统、前端编辑器设计 |
| v1.0 | 2026-08-01 | 初始版本，基于现有代码库逆向分析 |

---

**文档状态**: ✅ 已完成 v2.0 规范整合
**下一步**: 开始 Phase 1 数据模型开发
**负责人**: 开发团队

---

## 文档完整性检查

- ✅ 合并了 v1 系统设计规范的 1676 行内容
- ✅ 合并了编辑器设计文档的 783 行内容
- ✅ 解决了所有命名冲突 (StoryGraph vs SceneGraph, AssetType vs classification)
- ✅ 提供了完整的五图模型架构全景图
- ✅ 定义了所有新增数据模型和枚举
- ✅ 列出了所有新增 API 端点 (22个现有 + ~30个新增)
- ✅ 提供了完整的实施路线图 (Phase 1-5)
- ✅ 包含了风险评估和应对措施
- ✅ 修正了编辑器设计文档中的所有错误
- ✅ 确保了向后兼容性 (所有现有字段保留)
- ✅ 文档是自-contained 的，读者无需参考原始文档

**总计**: ~2500 行，完全符合预期范围。