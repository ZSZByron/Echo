# Echo UGC — 系统设计规范 (System Design Specification)

> **文档定位**: Schema First + Interface Contract + Domain Model Design
> **版本**: v1.0 — 基于现有代码库逆向分析 + 五图模型升级方向
> **日期**: 2026-08-01

---

## 目录

1. [系统全景架构图](#1-系统全景架构图)
2. [现有模块拆分](#2-现有模块拆分)
3. [领域模型 (Domain Model)](#3-领域模型-domain-model)
4. [接口契约 (Interface Contracts)](#4-接口契约-interface-contracts)
5. [数据流图](#5-数据流图)
6. [模块间依赖关系图](#6-模块间依赖关系图)
7. [五图模型升级映射](#7-五图模型升级映射)
8. [命名规范与标准化](#8-命名规范与标准化)
9. [附录A: 技术栈速查](#附录-a-技术栈速查)
10. [附录B: AI剧情场景编辑器对接规范](#附录-b-ai剧情场景编辑器对接规范)

---

## 1. 系统全景架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (React + TS)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ Terminal  │  │SceneView │  │ Graph    │  │ StatusPanel /     │  │
│  │ (交互终端)│  │ (场景视图)│  │ Editor   │  │ GodWatchIndicator │  │
│  └─────┬─────┘  └─────┬────┘  └─────┬────┘  └────────┬──────────┘  │
│        └──────────┬───┴───────────┴───────────────┘  │              │
│                   ▼                                  ▼              │
│           ┌─────────────┐                   ┌──────────────┐        │
│           │ api/client  │                   │  api/graph   │        │
│           └──────┬──────┘                   └──────┬───────┘        │
├──────────────────┼─────────────────────────────────┼────────────────┤
│                  ▼  HTTP /api/*                    ▼                │
│ ┌────────────────────────────────────────────────────────────────┐  │
│ │                    FastAPI Application                         │  │
│ │  main.py — lifespan + CORS + router registration               │  │
│ ├────────────┬───────────────┬──────────────┬────────────────────┤  │
│ │ /api/action│ /api/assets   │ /api/scenes  │ /api/graph         │  │
│ │ /api/state │ /api/scene    │              │ /api/graph/extract │  │
│ │ /api/reset │ /api/health   │              │ /api/graph/generate│  │
│ │            │               │              │                    │  │
│ │ routes.py  │ assets_routes │ assets_routes│ graph_routes.py    │  │
│ └─────┬──────┴───────┬───────┴──────┬───────┴─────────┬──────────┘  │
│       │              │              │                  │             │
│       ▼              ▼              ▼                  ▼             │
│ ┌──────────┐  ┌───────────┐  ┌───────────┐  ┌──────────────────┐   │
│ │Orchestr- │  │AssetStore │  │ Generation│  │  Graph           │   │
│ │ator      │  │ (JSON)    │  │ Planner   │  │  Extractor       │   │
│ │          │  │           │  │ Scheduler │  │  PromptFusion    │   │
│ │ parse →  │  │ CRUD +    │  │           │  │                  │   │
│ │ judge →  │  │ State     │  │ Plan +    │  │  LLM Extract     │   │
│ │ render → │  │ Machine   │  │ Execute   │  │  → KG            │   │
│ │ update   │  │           │  │           │  │                  │   │
│ └──┬──┬──┬─┘  └─────┬─────┘  └─────┬─────┘  └────────┬─────────┘   │
│    │  │  │          │              │                  │             │
│    │  │  │    ┌─────▼──────────────▼──────────────────▼───┐         │
│    │  │  │    │              Core Models (Pydantic)         │         │
│    │  │  │    │  action │ player │ world │ asset            │         │
│    │  │  │    │  scene_graph │ knowledge_graph │ puzzle     │         │
│    │  │  │    │  api │ scene_response                     │         │
│    │  │  │    └───────────────────────────────────────────┘         │
│    │  │  │                                                        │
│    ▼  ▼  ▼                                                        │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │                    Backend Services Layer                     │   │
│ ├──────────────┬─────────────────┬────────────────────────────┤   │
│ │ AI Layer     │ Engine Layer    │ State Layer                 │   │
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
│ │ OpenAI       │  │  data/scenes/*.yaml   (Scene 定义)        │    │
│ │ Anthropic    │  │  data/gods/*.yaml     (神王表)            │    │
│ │ DeepSeek     │  │  data/rules/*.yaml    (干涉表)            │    │
│ │ Qwen/Kimi/GLM│  │  data/objects/*.yaml  (物体定义)          │    │
│ │              │  │  data/visual/*.yaml   (Prompt/Palette)    │    │
│ │ + Image:     │  │  data/assets/manifest.json (资产清单)     │    │
│ │   Zhipu      │  │  data/assets/graph.db (图谱DB)            │    │
│ │   Wanxiang   │  │  data/default_player.json (初始状态)      │    │
│ │   Qwen-Image │  │                                          │    │
│ │   Local      │  │                                          │    │
│ └──────────────┘  └──────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. 现有模块拆分

### 2.1 模块清单

| # | 模块路径 | 职责 | 关键文件 |
|---|---------|------|---------|
| M1 | `app/main.py` | FastAPI 入口，lifespan 管理，路由注册 | `main.py` |
| M2 | `app/orchestrator.py` | 交互循环编排器 (parse→judge→render→update) | `orchestrator.py` |
| M3 | `app/models/` | 领域模型定义 (Pydantic) | 9 个模型文件 |
| M4 | `app/api/` | HTTP 路由 + 依赖注入 | `routes.py`, `assets_routes.py`, `graph_routes.py`, `deps.py` |
| M5 | `app/engine/` | 确定性规则引擎 | `rules_engine.py`, `physics.py`, `god_intervention.py`, `world_loader.py` |
| M6 | `app/ai/` | AI 服务层 (LLM + Image) | `parser.py`, `renderer.py`, `provider.py`, `image_generator.py`, `style_extractor.py`, `config.py` |
| M7 | `app/services/` | 业务编排服务 | `generation_planner.py`, `generation_scheduler.py`, `graph_extractor.py`, `prompt_builder.py`, `prompt_fusion.py` |
| M8 | `app/state/` | 持久化层 | `asset_store.py`, `graph_store.py`, `database.py`, `migrations.py` |
| M9 | `app/config/` | 配置与路径 | `paths.py`, `features.py` |
| M10 | `app/utils/` | 工具函数 | `gen_helpers.py` |
| F1 | `frontend/src/api/` | 前端 API 客户端 | `client.ts`, `assets.ts`, `graph.ts` |
| F2 | `frontend/src/types/` | TypeScript 类型定义 (镜像后端) | `action.ts`, `player.ts`, `scene.ts`, `api.ts`, `graph.ts` |
| F3 | `frontend/src/components/` | React 组件 | `Terminal.tsx`, `SceneView.tsx`, `StatusPanel.tsx`, `graph/*` |
| D1 | `data/scenes/` | 场景定义 (YAML) | `temple_ruins.yaml` |
| D2 | `data/gods/` | 神王表 (YAML) | `gods_table.yaml` |
| D3 | `data/rules/` | 规则表 (YAML) | `intervention_table.yaml` |
| D4 | `data/objects/` | 物体定义 (YAML) | `*.yaml` |
| D5 | `data/visual/` | 视觉生成配置 | `prompts.yaml`, `palette.yaml`, `style_bible.md` |
| D6 | `data/assets/` | 生成资产存储 | `manifest.json`, `graph.db`, `*.png` |

### 2.2 模块层级关系

```
Layer 0: Data (YAML/JSON/DB)          ← 无代码依赖，纯数据
    ↑ read/write
Layer 1: Models (app/models/)         ← 纯 Pydantic，零业务逻辑
    ↑ import
Layer 2: Engine + AI + State          ← 核心业务逻辑
    (app/engine/)  (app/ai/)  (app/state/)
    ↑ import
Layer 3: Services                     ← 编排层
    (app/services/)
    ↑ import
Layer 4: API + Orchestrator           ← HTTP 入口
    (app/api/)  (app/orchestrator.py)
    ↑ HTTP
Layer 5: Frontend                     ← UI 展示
    (frontend/src/)
```

---

## 3. 领域模型 (Domain Model)

### 3.1 核心实体关系图

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
                    │  prompt, status      │
                    │  file_path, seed     │
                    │  candidates          │
                    │  style_profile       │
                    │  views (LOD)         │
                    │  parent_scene        │
                    └─────────────────────┘


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

### 3.2 枚举值定义 (不可随意修改)

| 枚举 | 文件 | 值 |
|------|------|-----|
| `ActionType` | `models/action.py` | `brute_force`, `stealth`, `read_memory`, `negotiate`, `probe`, `god_provoke`, `investigate` |
| `JudgmentOutcome` | `models/action.py` | `success`, `fail`, `forced_fail`, `partial`, `god_intervention` |
| `PlayerStatus` | `models/player.py` | `normal`, `injured`, `exhausted`, `dying`, `dead`, `echo_active`, `echo_overload` |
| `AssetStatus` | `models/asset.py` | `pending`, `generating`, `completed`, `approved`, `rejected`, `failed`, `candidates_ready`, `selected` |
| `AssetType` | `models/asset.py` | `background`, `object` |
| `NodeStatus` | `models/knowledge_graph.py` | `pending`, `generating`, `completed`, `failed` |
| `EdgeType` | `models/knowledge_graph.py` | `tree`, `cross` |
| `PuzzleNodeType` | `models/puzzle_graph.py` | `clue`, `consumable`, `reward`, `obstacle` |
| `StateChangeTargetType` | `models/action.py` | `player`, `object`, `scene` |
| `Intensity` | `models/action.py` | `low`, `medium`, `maximum` |

### 3.3 资产状态机

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
         │ ┌──────────┐ ┌──────────┐
         └─│ APPROVED │ │ REJECTED │
           └──────────┘ └──────────┘
```

合法转换 (from `asset_store.py`):
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

---

## 4. 接口契约 (Interface Contracts)

### 4.1 HTTP API 端点总览

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

### 4.2 核心数据结构契约

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
    old_value: Any
    new_value: Any
```

#### PlayerState
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

#### Asset
```python
class Asset(BaseModel):
    id: str                         # "{scene_id}_{object_id}" 或 "{scene_id}_bg"
    type: AssetType                 # "background" | "object"
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
```

#### KnowledgeGraph
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

#### SceneGraph (内部计算模型)
```python
class SceneGraph(BaseModel):
    scene_id: str
    nodes: dict[str, AssetInfo]
    generation_order: list[str]     # Kahn拓扑排序结果
    style_sources: dict[str, list[str]]  # asset_id → 参考资产IDs
```

#### PuzzleGraph (内部计算模型)
```python
class PuzzleGraph(BaseModel):
    scene_id: str
    nodes: dict[str, PuzzleNode]
    chain: list[str]                # 拓扑排序解题顺序

class PuzzleNode(BaseModel):
    id: str
    type: PuzzleNodeType            # clue|consumable|reward|obstacle
    requires: list[str]             # 前置节点ID或产物名
    produces: str                   # 产出物品名
    interaction: str                # 玩家动作类型
```

#### SceneResponse (GET /api/scene)
```python
class SceneResponse(BaseModel):
    scene_id: str
    name: str
    description: str
    atmosphere: str
    background_asset: str | None    # 审批后才有路径
    objects: list[SceneObjectDTO]

class SceneObjectDTO(BaseModel):
    id: str
    name: str
    type: str
    description: str
    position: Position               # {x: float, y: float} 百分比
    asset: str | None               # 审批后才有路径
    is_primary: bool                # anchor或dangerous
    is_dangerous: bool
```

### 4.3 内部接口 (Python Protocol)

#### 依赖注入协议 (deps.py)

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

#### LLM Provider 接口

```python
class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict[str, str]], **kwargs) -> str: ...

    @abstractmethod
    async def chat_json(self, messages: list[dict[str, str]], **kwargs) -> dict[str, Any]: ...
```

#### RulesEngine 接口

```python
class RulesEngine:
    def __init__(self, loader: WorldLoader) -> None: ...
    async def judge(self, intent: ParsedIntent, player: PlayerState) -> JudgmentResult: ...
```

#### Orchestrator 接口

```python
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

#### GenerationPlanner 接口

```python
class GenerationPlanner:
    def create_plan(self, scene_id: str) -> GenerationPlan: ...
    # 纯规划，不执行生成

class GenerationPlan(BaseModel):
    scene_id: str
    order: list[str]                    # 有序资产ID列表
    specs: dict[str, AssetGenerationSpec]
```

#### GenerationScheduler 接口

```python
class GenerationScheduler:
    def __init__(self, max_concurrency: int = 3) -> None: ...
    async def run_generation(self, graph: KnowledgeGraph) -> dict: ...
    # 返回: {total, succeeded, failed, order, error?}
```

#### ImageGenerator 接口

```python
class ImageGenerator:
    _VALID_PROVIDERS = frozenset({"zhipu", "wanxiang", "qwen", "local"})

    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        asset_id: str = "",
        reference_asset_ids: list[str] | None = None,
    ) -> list[GeneratedImage]: ...

    async def close(self) -> None: ...
```

---

## 5. 数据流图

### 5.1 交互循环数据流 (Core Game Loop)

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

### 5.2 资产生成数据流 (Asset Generation Pipeline)

```
┌─────────────────── 方式A: SceneGraph 驱动 ───────────────────┐
│                                                              │
│  data/scenes/{scene_id}.yaml                                │
│     │                                                        │
│     ├─→ SceneGraph.from_yaml(scene_id)                      │
│     │    └─→ nodes + generation_order (Kahn topo sort)     │
│     │                                                        │
│     ├─→ PuzzleGraph.from_yaml(scene_id)                     │
│     │    └─→ nodes + chain (topo sort with type priority)  │
│     │                                                        │
│     └─→ GenerationPlanner.create_plan(scene_id)            │
│          ├─→ combine deps (spatial + puzzle)                │
│          ├─→ LOD-aware topo sort (near→mid→far→bg)         │
│          └─→ GenerationPlan {order, specs}                 │
│                    │                                         │
│                    ▼                                         │
│  AssetStore.update_asset(id, GENERATING)                   │
│     │                                                        │
│     ▼                                                        │
│  ImageGenerator.generate(prompt, refs)                     │
│     ├─→ Zhipu/Wanxiang/Qwen/Local backend                  │
│     └─→ GeneratedImage[] (seed + bytes/url)                │
│          │                                                   │
│          ▼                                                   │
│  AssetStore.update_asset(id, COMPLETED, file_path, seed)  │
│     │                                                        │
│     ├─ IF background:                                        │
│     │  └─→ StyleExtractor → fill pending objects            │
│     │                                                        │
│     ▼                                                        │
│  Review: approve → APPROVED | reject → REJECTED            │
│                                                              │
└──────────────────────────────────────────────────────────────┘

┌─────────────────── 方式B: KnowledgeGraph 驱动 ──────────────┐
│                                                              │
│  POST /api/graph/extract {scene_description}                │
│     │                                                        │
│     ▼                                                        │
│  GraphExtractor.extract_from_text()                         │
│     ├─→ LLM: scene_description → JSON {nodes, edges}       │
│     └─→ KnowledgeGraph {nodes, edges, background_node_id}  │
│                                                              │
│  POST /api/graph/validate {KnowledgeGraph}                 │
│     └─→ cycle_detector.validate_graph() → {is_valid}      │
│                                                              │
│  POST /api/graph/save {KnowledgeGraph}                     │
│     └─→ GraphStore (SQLite)                                 │
│                                                              │
│  POST /api/graph/generate {KnowledgeGraph}                 │
│     │                                                        │
│     ▼                                                        │
│  GenerationScheduler.run_generation(graph)                 │
│     ├─→ validate (cycle detection)                         │
│     ├─→ topo_sort.get_generation_waves(graph)              │
│     │    └─→ [[node1, node2], [node3], ...] 波次           │
│     │                                                        │
│     └─→ FOR EACH WAVE (serial):                            │
│          └─→ asyncio.gather(*nodes in wave)                │
│               └─→ _generate_node(node_id, graph, refs)    │
│                    ├─→ PromptFusion.build_prompt()         │
│                    │    ├─ Subject: node.description       │
│                    │    ├─ Relation: completed edges       │
│                    │    └─ Background: bg node desc        │
│                    └─→ ImageGenerator.generate()           │
│                                                              │
│     └─→ {total, succeeded, failed, order}                  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. 模块间依赖关系图

### 6.1 后端模块导入关系 (物理依赖)

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

engine/world_loader.py
  ├─→ models/world.py
  └─→ config/paths.py

services/generation_planner.py
  ├─→ models/scene_graph.py
  ├─→ models/puzzle_graph.py
  └─→ config/paths.py

services/generation_scheduler.py
  ├─→ models/knowledge_graph.py
  ├─→ ai/image_generator.py
  ├─→ services/prompt_fusion.py
  └─→ utils/gen_helpers.py

services/graph_extractor.py
  ├─→ models/knowledge_graph.py
  └─→ ai/{config,provider}.py

services/prompt_builder.py
  └─→ config/paths.py

ai/parser.py
  ├─→ ai/prompts/parser_prompt.py
  ├─→ ai/provider.py
  └─→ models/action.py

ai/renderer.py
  ├─→ ai/prompts/renderer_prompt.py
  ├─→ ai/provider.py
  └─→ models/action.py

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

state/database.py
  ├─→ models/player.py
  └─→ config/paths.py
```

### 6.2 逻辑分层依赖 (简化)

```
         ┌─────────────────────────┐
         │       API Layer          │
         │ routes / assets_routes   │
         │ graph_routes / deps      │
         └────────┬────────────────┘
                  │
          ┌───────┴────────┐
          │                │
          ▼                ▼
  ┌──────────────┐ ┌──────────────┐
  │ Orchestrator │ │   Services   │
  │ (交互编排)    │ │ GenPlanner   │
  └──────┬───────┘ │ GenScheduler │
         │         │ GraphExtract │
         │         │ PromptBuild  │
         │         │ PromptFusion │
         │         └──────┬───────┘
         │                │
    ┌────┴────────────────┴────┐
    │                          │
    ▼                          ▼
┌──────────┐            ┌──────────┐
│ Engine   │            │    AI    │
│ Rules    │            │ Parser   │
│ Physics  │            │ Renderer │
│ GodInter │            │ ImageGen │
│ Loader   │            │ Provider │
└────┬─────┘            └────┬─────┘
     │                       │
     └────────┬──────────────┘
              │
              ▼
     ┌──────────────┐
     │   Models     │  ← 纯数据定义，零依赖
     │ (Pydantic)   │
     └──────────────┘
              │
              ▼
     ┌──────────────┐
     │    State     │  ← 持久化
     │ AssetStore   │
     │ GraphStore   │
     │ Database     │
     └──────────────┘
              │
              ▼
     ┌──────────────┐
     │  Data (YAML) │  ← 静态数据
     └──────────────┘
```

---

## 7. 五图模型升级映射

### 7.1 现有结构 → 五图模型对照

| 五图模型概念 | 现有对应 | 差距分析 |
|-------------|---------|---------|
| **Story Graph** (固定剧情) | `PuzzleGraph` + `puzzle_chain` in YAML | 当前 PuzzleGraph 只处理单场景谜题链，缺少跨场景主线/支线叙事 |
| **Event Graph** (动态事件) | ❌ 不存在 | 完全缺失。当前系统无条件触发机制 |
| **Asset Tree** (空间资产) | `SceneGraph` + `Asset` + `AssetStore` + `GameObject` | 已有场景级资产管理，但无全局 Asset Tree |
| **Culture Tree** (文化约束) | ❌ 不存在 | `style_bible.md` + `palette.yaml` 是初步雏形，但无结构化文化树 |
| **Constraint Tree** (硬约束) | `WorldRule.physical_constraints` | 有简单约束字段，但无约束树结构和候选过滤系统 |

### 7.2 升级路线图

```
现有架构:
                    ┌──────────────┐
                    │  SceneGraph  │ ← 场景级资产生成
                    │  + Asset     │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ ImageGen     │ ← AI生成
                    └──────────────┘


目标架构 (五图模型):
                    ┌──────────────┐
                    │ Culture Tree │ ← 新增：文化约束体系
                    └──────┬───────┘
                    ┌──────▼───────┐
                    │Constraint Tree│← 新增：硬约束过滤
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ World KG     │ ← 新增：世界知识图谱
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

### 7.3 所需新增模块

| 新模块 | 位置 | 职责 |
|--------|------|------|
| `models/story_graph.py` | `app/models/` | 主线/支线节点定义，跨场景链接 |
| `models/event_graph.py` | `app/models/` | 条件触发事件定义 |
| `models/culture_tree.py` | `app/models/` | 文化层级体系，候选评分 |
| `models/constraint_tree.py` | `app/models/` | 硬约束规则，候选过滤 |
| `engine/event_engine.py` | `app/engine/` | 运行时事件条件检测与触发 |
| `services/candidate_system.py` | `app/services/` | 文化约束 → 候选 → 过滤 → 评分 |
| `data/story/` | `data/` | 主线/支线 YAML |
| `data/events/` | `data/` | 事件定义 YAML |
| `data/culture/` | `data/` | 文化树 YAML |
| `data/constraints/` | `data/` | 约束规则 YAML |

---

## 8. 命名规范与标准化

### 8.1 ID 命名规则 (全局统一)

| 实体 | 格式 | 示例 |
|------|------|------|
| Scene ID | `snake_case` | `temple_ruins` |
| Object ID | `snake_case` | `priest_corpse_01` |
| Asset ID | `{scene_id}_{object_id}` 或 `{scene_id}_bg` | `temple_ruins_priest_corpse_01` |
| Graph Node ID | Serial Number = ID | `1`, `1-1`, `1-1-1` |
| Player ID | `player_XXX` | `player_001` |
| God ID | `snake_case` | `chronos_order` |
| Puzzle Node ID | `snake_case` (与 object_id 对齐) | `priest_corpse_01` |
| Event ID (未来) | `event_XXX` | `event_wolf_attack_01` |

### 8.2 YAML 数据格式规范

#### Scene YAML (主格式)
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

### 8.3 API 响应规范

所有 API 响应遵循以下规则：
- **成功**: 直接返回数据模型 (Pydantic 序列化)
- **失败**: `HTTPException(status_code, detail=message)`
- **状态码**: 200(成功), 404(不存在), 409(状态冲突), 422(验证失败), 500(服务器错误)

### 8.4 前后端类型同步

| 后端 (Python) | 前端 (TypeScript) | 同步方式 |
|---------------|-------------------|---------|
| `models/action.py` | `types/action.ts` | 手动镜像 |
| `models/player.py` | `types/player.ts` | 手动镜像 |
| `models/scene_response.py` | `types/scene.ts` | 手动镜像 |
| `models/api.py` | `types/api.ts` | 手动镜像 |
| `models/knowledge_graph.py` | `types/graph.ts` | 手动镜像 |

> **注意**: 当前同步是手动的。未来可考虑用 `openapi-typescript` 从 FastAPI OpenAPI schema 自动生成。

---

## 附录 A: 技术栈速查

| 层 | 技术 | 版本要求 |
|----|------|---------|
| 后端框架 | FastAPI + Uvicorn | ≥0.104 |
| 数据验证 | Pydantic | ≥2.5 |
| 数据库 | SQLite + aiosqlite + SQLAlchemy | ≥2.0 |
| LLM SDK | openai + anthropic | ≥1.0 / ≥0.7 |
| 前端框架 | React + Vite + TypeScript | Node ≥18 |
| 样式 | TailwindCSS v4 | — |
| 图编辑器 | React Flow | ≥12.0 |
| 状态管理 | Zustand | ≥4.5 |
| UI组件库 | Radix UI | ≥1.0 |
| 代码编辑器 | Monaco Editor | — |
| 数据可视化 | D3.js | ≥7.0 |
| 实时协作 | Y.js | — |
| 测试 | pytest + behave + mutmut + Playwright | — |
| Python | 3.11+ (strict mypy) | — |

---

## 附录 B: AI剧情场景编辑器对接规范

> **关联文档**: `docs/plans/2026-08-01-ai-story-scene-editor-design.md`
>
> 本章节将编辑器设计方案中的所有概念映射回系统设计规范，
> 解决命名冲突，定义迁移路径，确保两份文档一致性。

---

### B.1 概念映射表 (编辑器 → 系统设计)

编辑器设计引入了大量新概念，以下是与现有系统的逐项映射：

#### B.1.1 数据模型映射

| 编辑器设计概念 | 现有对应 | 对接方式 | 冲突点 |
|---------------|---------|---------|--------|
| **StoryGraph** (跨场景主线/支线) | PuzzleGraph (单场景谜题链) | **升级**: PuzzleGraph 成为 StoryGraph 的子模块 | 名称冲突：编辑器 StoryGraph ≠ 现有 SceneGraph |
| **StoryNode** (`start\|end\|choice\|event\|condition`) | PuzzleNode (`clue\|consumable\|reward\|obstacle`) | **并存**: StoryNode 是叙事层，PuzzleNode 是解谜层 | type 枚举完全不同，需要独立枚举 |
| **EventGraph** | 不存在 | **新建** | — |
| **EventNode** (`combat\|quest\|exploration\|social`) | 不存在 | **新建** | — |
| **AssetNode** (`story\|event\|environment` 分类) | Asset (无分类字段) | **扩展**: Asset 增加 `classification` 字段 | 字段名不同：编辑器 `type` vs 现有 `classification` |
| **CultureNode** | 不存在 | **新建** | — |
| **ConstraintNode** (`hard\|soft`) | WorldRule.physical_constraints | **升级**: WorldRule 拆分为结构化 ConstraintNode | — |
| **World Knowledge Graph** | KnowledgeGraph | **复用**: 编辑器直接使用现有 KnowledgeGraph | — |

#### B.1.2 命名冲突消解规则

编辑器设计文档使用 **camelCase** (TypeScript 惯例)，现有系统使用 **snake_case** (Python 惯例)。

**消解策略：后端 snake_case 不变，前端 camelCase 不变，API 边界由 Pydantic alias 桥接。**

| 后端 (Python snake_case) | 前端 (TS camelCase) | API JSON 字段 | 说明 |
|--------------------------|---------------------|---------------|------|
| `trigger_conditions` | `triggerConditions` | `trigger_conditions` | API JSON 统一 snake_case |
| `required_assets` | `requiredAssets` | `required_assets` | — |
| `asset_type` | `assetType` | `asset_type` | — |
| `style_profile` | `styleProfile` | `style_profile` | — |
| `is_future_anchor` | `isFutureAnchor` | `is_future_anchor` | — |

> **铁律：API JSON 层统一 snake_case。** Pydantic 用 `Field(alias=...)` 或 `model_config = ConfigDict(populate_by_name=True)` 支持前端 camelCase。现有代码已遵循此规则，编辑器新增模型必须保持一致。

#### B.1.3 名称占用消解

| 冲突名称 | 现有含义 | 编辑器含义 | **消解方案** |
|---------|---------|-----------|-------------|
| `StoryGraph` | 无 (现有是 `SceneGraph`) | 跨场景剧情图 | 编辑器 `StoryGraph` 保留，不与 `SceneGraph` 冲突 |
| `StoryNode` | 无 (现有是 `PuzzleNode`) | 剧情节点 | 编辑器 `StoryNode` 保留，与 `PuzzleNode` 并存 |
| `AssetNode` | 无 (现有是 `Asset`) | 分类资产节点 | **改名为 `AssetTreeNode`**，避免与 `Asset` 混淆。实际数据仍存储在 `Asset` 模型中，`AssetTreeNode` 是 Asset 的编辑器视图模型 |
| `AssetType` | `background \| object` | `story \| event \| environment` | **拆分为两个枚举**：`AssetType`(现有，不变) + `AssetClassification`(新增) |

---

### B.2 新增模块定义 (对接编辑器设计)

以下模块由编辑器设计触发，需添加到系统设计规范的模块清单中。

#### B.2.1 后端新增模块

| # | 模块 | 路径 | 职责 | 对接编辑器功能 |
|---|------|------|------|---------------|
| M25 | **Story Service** | `app/services/story_service.py` | 剧情图 CRUD + 跨场景链接 + 导入导出 | StoryGraphEditor |
| M26 | **Event Service** | `app/services/event_service.py` | 事件图 CRUD + 条件触发测试 | EventGraphEditor |
| M27 | **AI Assistant Service** | `app/services/ai_assistant.py` | 节点建议 + 一致性检查 + Prompt优化 + 约束验证 | AIAssistantPanel |
| M28 | **Asset Classification** | `app/services/asset_classifier.py` | 资产三分类 (story/event/environment) | AssetTreeEditor 分类管理 |
| M29 | **Candidate System** | `app/services/candidate_system.py` | 文化约束→候选→过滤→评分 | CultureEditor 候选管理 |

#### B.2.2 后端新增模型

| 文件 | 模型 | 字段要点 | 来源 |
|------|------|---------|------|
| `models/story_graph.py` | `StoryNode` | `id, type(start\|end\|choice\|event\|condition), name, description, required_assets, conditions, choices, metadata(chapter,tags)` | 编辑器 §3.1 |
| | `StoryEdge` | `from_node, to_node, condition` | 编辑器 §3.1 |
| | `StoryGraph` | `id, name, description, nodes: dict, edges: list, version` | 编辑器 §3.1 |
| | `StoryCondition` | `type, requirement` | 编辑器 §3.1 |
| | `StoryChoice` | `text, target_node, conditions` | 编辑器 §3.1 |
| `models/event_graph.py` | `EventNode` | `id, type(combat\|quest\|exploration\|social), name, trigger_conditions, actions, rewards, assets, metadata(difficulty,priority,cooldown)` | 编辑器 §3.2 |
| | `EventTrigger` | `type(time\|location\|state\|custom), condition, priority` | 编辑器 §3.2 |
| | `EventAction` | `type, parameters` | 编辑器 §3.2 |
| | `EventReward` | `type(item\|experience\|story_unlock), value, probability` | 编辑器 §3.2 |
| | `EventGraph` | `id, name, description, nodes: dict, global_triggers` | 编辑器 §3.2 |
| `models/culture.py` | `CultureNode` | `id, name, description, values[], aesthetic_principles[], child_nodes[]` | 编辑器 §3.4 |
| | `CultureTree` | `root: CultureNode, version` | 编辑器 §3.4 |
| `models/constraint.py` | `ConstraintNode` | `id, type(hard\|soft), rule, priority, applicable_types[]` | 编辑器 §3.4 |
| | `ConstraintTree` | `nodes: list[ConstraintNode]` | 编辑器 §3.4 |
| `models/asset.py` (扩展) | `AssetClassification` (新枚举) | `story \| event \| environment` | 编辑器 §3.3 |

#### B.2.3 后端新增 API 路由

编辑器设计的 API 需注册到 `main.py`。以下是完整的路由前缀分配：

| 路由前缀 | 路由文件 | 端点数 | 说明 |
|---------|---------|--------|------|
| `/api/story` (新增) | `api/story_routes.py` | 6 | 剧情图 CRUD + 导出 |
| `/api/events` (新增) | `api/event_routes.py` | 6+1 | 事件图 CRUD + 触发测试 |
| `/api/assets` (扩展) | `api/assets_routes.py` (现有) | +2 | 分类查询 + 树结构 |
| `/api/ai` (新增) | `api/ai_routes.py` | 5 | AI 辅助全套 |
| `/api/culture` (新增) | `api/culture_routes.py` | CRUD | 文化树管理 |
| `/api/constraints` (新增) | `api/constraint_routes.py` | CRUD | 约束树管理 |

**新增端点清单:**

```
# Story Graph API
GET    /api/story/graphs                        列出所有剧情图
GET    /api/story/graphs/{graph_id}             查单个剧情图
POST   /api/story/graphs                        创建剧情图
PUT    /api/story/graphs/{graph_id}             更新剧情图
DELETE /api/story/graphs/{graph_id}             删除剧情图
GET    /api/story/graphs/{graph_id}/export      导出(默认yaml)

# Event Graph API
GET    /api/events/graphs                       列出所有事件图
GET    /api/events/graphs/{graph_id}            查单个事件图
POST   /api/events/graphs                       创建事件图
PUT    /api/events/graphs/{graph_id}            更新事件图
DELETE /api/events/graphs/{graph_id}            删除事件图
POST   /api/events/test-trigger                 测试事件触发

# Asset Classification API (扩展现有 /api/assets)
GET    /api/assets/tree                         获取分类资产树
GET    /api/assets/classified/{classification}  按分类查询(story|event|environment)

# AI Assistant API
POST   /api/ai/suggest-nodes                    AI建议剧情/事件节点
POST   /api/ai/check-consistency                叙事一致性检查
POST   /api/ai/suggest-assets                   AI建议资产候选
POST   /api/ai/optimize-prompt                  AI优化生成提示词
POST   /api/ai/validate-constraints             约束验证
```

#### B.2.4 前端新增模块

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

**前端新增状态管理 (Zustand stores):**

```
stores/
├── storyStore.ts          # StoryGraph 状态
├── eventStore.ts          # EventGraph 状态
├── assetTreeStore.ts      # AssetTree 分类状态
├── cultureStore.ts        # CultureTree 状态
├── constraintStore.ts     # ConstraintTree 状态
└── editorUIStore.ts       # 编辑器UI状态(选中节点/面板状态等)
```

**前端新增类型定义:**

```
types/
├── story.ts               # StoryNode, StoryGraph, StoryEdge (新增)
├── event.ts               # EventNode, EventGraph, EventTrigger (新增)
├── culture.ts             # CultureNode, CultureTree (新增)
├── constraint.ts          # ConstraintNode, ConstraintTree (新增)
└── editor.ts              # EditorState, PanelConfig 等编辑器类型 (新增)
```

---

### B.3 新增枚举定义 (不允许随意修改)

| 枚举 | 文件 | 值 | 来源 |
|------|------|-----|------|
| `StoryNodeType` | `models/story_graph.py` | `start`, `end`, `choice`, `event`, `condition` | 编辑器 §3.1 |
| `EventNodeType` | `models/event_graph.py` | `combat`, `quest`, `exploration`, `social` | 编辑器 §3.2 |
| `EventTriggerType` | `models/event_graph.py` | `time`, `location`, `state`, `custom` | 编辑器 §3.2 |
| `EventRewardType` | `models/event_graph.py` | `item`, `experience`, `story_unlock` | 编辑器 §3.2 |
| `ConstraintType` | `models/constraint.py` | `hard`, `soft` | 编辑器 §3.4 |
| `AssetClassification` | `models/asset.py` (扩展) | `story`, `event`, `environment` | 编辑器 §3.3 |

---

### B.4 数据模型扩展契约

#### B.4.1 Asset 模型扩展 (向后兼容)

现有 `Asset` 模型需要新增字段以支持编辑器的分类系统：

```python
# models/asset.py 新增字段 (向后兼容，有默认值)

class AssetClassification(str, Enum):
    """资产分类 — 由来源图决定。"""
    STORY = "story"            # 来自 StoryGraph 节点
    EVENT = "event"            # 来自 EventGraph 节点
    ENVIRONMENT = "environment" # 无明确来源，纯环境

class Asset(BaseModel):
    # ... 现有字段全部保留 ...

    # 新增字段 (有默认值，不破坏现有数据)
    classification: AssetClassification = AssetClassification.ENVIRONMENT
    related_story_node: str | None = None    # 关联的 StoryNode ID
    related_event_node: str | None = None    # 关联的 EventNode ID
```

**迁移规则:**
- 现有资产默认 `classification = ENVIRONMENT`
- 有 `puzzle_role` 的资产升级为 `classification = STORY`
- 新生成的资产根据来源图自动设置分类

#### B.4.2 WorldRule → ConstraintTree 升级

现有 `WorldRule.physical_constraints: list[str]` 升级为结构化约束：

```python
# 现有 (保留向后兼容)
class WorldRule(BaseModel):
    physical_constraints: list[str] = []  # 仍可读，标记为 deprecated

# 新增
class ConstraintNode(BaseModel):
    id: str
    type: ConstraintType                    # "hard" | "soft"
    rule: str                               # 规则描述
    priority: int                           # 优先级
    applicable_types: list[str] = []        # 适用的资产类型

class ConstraintTree(BaseModel):
    scene_id: str | None = None             # 全局或场景级
    nodes: list[ConstraintNode] = []
```

**迁移规则:** `WorldRule.physical_constraints` 中每个字符串自动转换为 `ConstraintNode(type="hard", rule=string, priority=100)`

#### B.4.3 PuzzleGraph → StoryGraph 关系

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

**数据存储:**
- StoryGraph: `data/stories/{story_id}.yaml` (新建目录)
- PuzzleGraph: 仍嵌入 `data/scenes/{scene_id}.yaml` 的 `puzzle_chain` 字段
- 关联: `StoryNode.scene_link → scene_id → PuzzleGraph.from_yaml(scene_id)`

---

### B.5 系统架构升级图 (整合后)

```
                         ┌──────────────────────────────────────────────┐
                         │              前端 Frontend                     │
                         │                                               │
                         │  ┌─────────────┐  ┌──────────────────────┐   │
                         │  │  现有UI      │  │  编辑器 UI (新增)     │   │
                         │  │  Terminal    │  │  StoryGraphEditor    │   │
                         │  │  SceneView   │  │  EventGraphEditor    │   │
                         │  │  StatusPanel │  │  AssetTreeEditor     │   │
                         │  │  Graph UI    │  │  CultureTreeEditor   │   │
                         │  │             │  │  AIAssistantPanel    │   │
                         │  └──────┬──────┘  └──────────┬───────────┘   │
                         │         └──────────┬─────────┘               │
                         │              API Client Layer                 │
                         └────────────────────┬─────────────────────────┘
                                              │ HTTP
                    ┌─────────────────────────┼─────────────────────┐
                    │                         │                     │
              现有 API                  编辑器 API (新增)           AI API (新增)
          /api/action               /api/story/*              /api/ai/*
          /api/assets               /api/events/*             /api/ai/suggest-*
          /api/scenes               /api/culture/*            /api/ai/check-*
          /api/graph/*              /api/constraints/*
                                    /api/assets/tree
                    │                         │                     │
                    └─────────────────────────┼─────────────────────┘
                                              │
                    ┌─────────────────────────▼─────────────────────┐
                    │              后端 Backend                       │
                    │                                               │
                    │  ┌─────────────────────────────────────────┐   │
                    │  │           Models (数据契约)               │   │
                    │  │                                         │   │
                    │  │  现有模型:              新增模型:         │   │
                    │  │  action, player,        story_graph     │   │
                    │  │  world, asset(扩展),    event_graph     │   │
                    │  │  scene_graph,           culture         │   │
                    │  │  knowledge_graph,       constraint      │   │
                    │  │  puzzle_graph           (6个新文件)      │   │
                    │  └─────────────────────────────────────────┘   │
                    │                                               │
                    │  ┌──────────────┐  ┌──────────────────────┐   │
                    │  │ 现有 Services │  │  新增 Services        │   │
                    │  │ GenPlanner   │  │  StoryService        │   │
                    │  │ GenScheduler │  │  EventService        │   │
                    │  │ GraphExtract │  │  AIAssistant         │   │
                    │  │ PromptBuild  │  │  AssetClassifier     │   │
                    │  │ PromptFusion │  │  CandidateSystem     │   │
                    │  └──────────────┘  └──────────────────────┘   │
                    │                                               │
                    │  ┌─────────────────────────────────────────┐   │
                    │  │           Engine + AI (不变)              │   │
                    │  │  RulesEngine, Parser, Renderer,          │   │
                    │  │  ImageGenerator, Provider                │   │
                    │  └─────────────────────────────────────────┘   │
                    │                                               │
                    │  ┌─────────────────────────────────────────┐   │
                    │  │           Data Layer                      │   │
                    │  │                                         │   │
                    │  │  现有:                 新增:              │   │
                    │  │  data/scenes/         data/stories/      │   │
                    │  │  data/gods/           data/events/       │   │
                    │  │  data/rules/          data/cultures/     │   │
                    │  │  data/objects/        data/constraints/  │   │
                    │  │  data/assets/         (4个新目录)        │   │
                    │  │  data/visual/                           │   │
                    │  └─────────────────────────────────────────┘   │
                    └───────────────────────────────────────────────┘
```

---

### B.6 数据流整合 (编辑器 → 生成管道)

编辑器创建的内容如何流入现有的资产生成管道：

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

---

### B.7 AI辅助系统对接

编辑器的 AI Assistant 面板映射到后端 AI Service：

| 编辑器 AI 功能 | 后端端点 | 现有基础设施复用 | 新增逻辑 |
|---------------|---------|----------------|---------|
| 剧情节点建议 | `POST /api/ai/suggest-nodes` | LLMProvider.chat_json() | StoryPromptBuilder (新增) |
| 叙事一致性检查 | `POST /api/ai/check-consistency` | LLMProvider.chat_json() | ConsistencyValidator (新增) |
| 资产候选建议 | `POST /api/ai/suggest-assets` | LLMProvider.chat_json() | CandidateScorer (新增) |
| Prompt优化 | `POST /api/ai/optimize-prompt` | LLMProvider.chat() | PromptOptimizer (新增) |
| 约束验证 | `POST /api/ai/validate-constraints` | 纯规则引擎 (确定性) | ConstraintValidator (新增) |

**关键约束：AI 辅助全部通过现有 LLMProvider 抽象层调用，不直接耦合具体 LLM SDK。**

---

### B.8 数据目录扩展

```
data/
├── scenes/                 # 现有 — 场景定义 + puzzle_chain
├── stories/                # 新增 — StoryGraph 定义
│   └── {story_id}.yaml
├── events/                 # 新增 — EventGraph 定义
│   └── {event_graph_id}.yaml
├── cultures/               # 新增 — CultureTree 定义
│   └── {culture_id}.yaml
├── constraints/            # 新增 — ConstraintTree 定义
│   └── {constraint_set_id}.yaml
├── gods/                   # 现有
├── objects/                # 现有
├── rules/                  # 现有 (逐步迁移到 constraints/)
├── assets/                 # 现有 — manifest.json + graph.db + 图像
└── visual/                 # 现有 — prompts/palette/style_bible
```

#### Story YAML 格式 (`data/stories/{story_id}.yaml`)

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

#### Event YAML 格式 (`data/events/{event_graph_id}.yaml`)

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

---

### B.9 前后端类型同步扩展

编辑器引入的类型同步对照表（在现有基础上新增）：

| 后端 (Python) | 前端 (TypeScript) | 同步方式 |
|---------------|-------------------|---------|
| `models/story_graph.py` | `types/story.ts` | 手动镜像 |
| `models/event_graph.py` | `types/event.ts` | 手动镜像 |
| `models/culture.py` | `types/culture.ts` | 手动镜像 |
| `models/constraint.py` | `types/constraint.ts` | 手动镜像 |
| `Asset.classification` (扩展) | `types/asset.ts` (扩展) | 手动镜像 |
| `api/story_routes.py` DTO | `types/story.ts` (API 部分) | 手动镜像 |
| `api/event_routes.py` DTO | `types/event.ts` (API 部分) | 手动镜像 |
| `api/ai_routes.py` DTO | `types/ai.ts` (新增) | 手动镜像 |

---

### B.10 实施优先级与依赖关系

```
Phase 1 — 数据模型先行 (无外部依赖)
──────────────────────────────────
  models/story_graph.py ──────┐
  models/event_graph.py ──────┤ 互相独立，可并行
  models/culture.py ──────────┤
  models/constraint.py ───────┘
  asset.py 扩展 classification ── 依赖上面的模型定义

Phase 2 — 后端服务层 (依赖 Phase 1)
──────────────────────────────────
  services/story_service.py ──────── 依赖 models/story_graph.py
  services/event_service.py ──────── 依赖 models/event_graph.py
  services/asset_classifier.py ───── 依赖 Asset 扩展 + Story/Event
  services/candidate_system.py ───── 依赖 culture + constraint models
  services/ai_assistant.py ───────── 依赖以上全部 + LLMProvider

Phase 3 — API 路由层 (依赖 Phase 2)
──────────────────────────────────
  api/story_routes.py ────── 依赖 StoryService
  api/event_routes.py ────── 依赖 EventService
  api/ai_routes.py ───────── 依赖 AIAssistantService
  api/culture_routes.py ──── 依赖 CultureStore
  api/constraint_routes.py ─ 依赖 ConstraintStore

Phase 4 — 前端编辑器 (依赖 Phase 3 API)
──────────────────────────────────
  stores/*.ts (Zustand) ──────────┐
  types/*.ts (TS类型) ────────────┤ 并行
  api/*.ts (API client) ──────────┘
  components/editor/*.tsx ──────── 依赖以上全部
    ├── StoryGraphEditor ─────────── 依赖 React Flow
    ├── EventGraphEditor ─────────── 依赖 React Flow
    ├── AssetTreeEditor ──────────── 依赖 React Flow + D3
    ├── CultureTreeEditor ────────── 依赖 React Flow
    └── AIAssistantPanel ─────────── 依赖 /api/ai/*

Phase 5 — 生成管道整合 (依赖 Phase 1-4)
──────────────────────────────────
  GenerationPlanner 升级 ──── 加入 StoryGraph 依赖
  PromptBuilder 升级 ──────── 加入 Culture + Constraint 层
  CandidateSystem 接入 ────── 连接 CultureTree → 生成管道
```

---

### B.11 编辑器设计文档勘误与约束补充

以下是对编辑器设计文档 (`2026-08-01-ai-story-scene-editor-design.md`) 的约束修正：

| 问题 | 位置 | 修正 |
|------|------|------|
| `StoryCondition.requirement: any` | §3.1 StoryNode 数据结构 | 改为 `requirement: str \| dict` — Pydantic v2 strict mode 不允许裸 `any` |
| `EventTrigger.condition: any` | §3.2 EventNode 数据结构 | 同上 |
| `EventAction.parameters: Dict` | §3.2 | 改为 `parameters: dict[str, str \| int \| bool]` |
| `ConstraintNode.rule: any` | §3.4 | 改为 `rule: str` (规则描述文本) + `rule_config: dict \| None` |
| `datetime.now()` | §7.1 StoryGraph | 改为 `datetime.now(timezone.utc)` — 现有代码规范要求 UTC |
| 前端 `requiredAssets` (camelCase) | §7.2 | API JSON 层用 `required_assets` (snake_case)，前端类型可 alias |
| `AssetNode.type = 'story'\|'event'\|'environment'` | §3.3 | 改名为 `classification` — `type` 已被 `AssetType(background\|object)` 占用 |
| Phase 1-4 任务全部标记 `[x]` | §9 | 实际未完成，应标记 `[ ]` |
| 缺少 `main.py` 路由注册 | §8 | 新增路由文件必须在 `main.py` 中 `app.include_router()` |
